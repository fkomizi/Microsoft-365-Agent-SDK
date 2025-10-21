# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Configure enhanced logging with timestamps - write to file
log_filename = f'copilot_studio_{datetime.now().strftime("%Y%m%d")}.log'

# Create a rotating file handler (max 10MB per file, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_filename,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[file_handler]
)

# Configure microsoft_agents logger to also use file handler
ms_agents_logger = logging.getLogger("microsoft_agents")
ms_agents_logger.addHandler(file_handler)
ms_agents_logger.setLevel(logging.INFO)

from os import environ
import asyncio
import uuid
from flask import Flask, render_template, request, redirect, url_for, session as flask_session
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
from microsoft_agents.activity import ActivityTypes
from microsoft_agents.copilotstudio.client import (
    ConnectionSettings,
    CopilotClient,
)
import secrets

logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', manage_session=False)

# Configuration
CLIENT_ID = environ.get("COPILOTSTUDIOAGENT__AGENTAPPID")
CLIENT_SECRET = environ.get("COPILOTSTUDIOAGENT__CLIENTSECRET")
TENANT_ID = environ.get("COPILOTSTUDIOAGENT__TENANTID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://api.powerplatform.com/.default"]

# Store active conversations
conversations = {}


def get_redirect_uri():
    """Get dynamic redirect URI based on current request"""
    # If running behind a proxy (like ngrok), use X-Forwarded-Proto and X-Forwarded-Host
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.headers.get('X-Forwarded-Host', request.host)

    # Build the redirect URI
    redirect_uri = f"{scheme}://{host}/auth/callback"
    logger.info(f"Dynamic redirect URI: {redirect_uri}")
    return redirect_uri


def get_msal_app():
    return ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )


def acquire_token_for_user(auth_code, redirect_uri):
    """Acquire token using authorization code"""
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        auth_code,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return result


def get_token_from_session():
    """Get access token from Flask session"""
    return flask_session.get('access_token')


def create_client(access_token):
    """Create Copilot client with user's access token"""
    environment_id = environ.get("COPILOTSTUDIOAGENT__ENVIRONMENTID")
    agent_identifier = environ.get("COPILOTSTUDIOAGENT__SCHEMANAME")

    settings = ConnectionSettings(
        environment_id=environment_id,
        agent_identifier=agent_identifier,
        cloud=None,
        copilot_agent_type=None,
        custom_power_platform_cloud=None,
    )

    copilot_client = CopilotClient(settings, access_token)
    logger.info(f"Copilot client created for user")

    return copilot_client


@app.route('/')
def index():
    """Main page - check if user is authenticated"""
    if not get_token_from_session():
        # User not authenticated, redirect to login
        return redirect(url_for('login'))

    # Get UI configuration
    show_feedback = environ.get('SHOW_FEEDBACK', 'true').lower() == 'true'

    # User is authenticated, show chat interface
    return render_template('index.html', show_feedback=show_feedback)


@app.route('/login')
def login():
    """Initiate OAuth login flow"""
    flask_session['state'] = str(uuid.uuid4())
    redirect_uri = get_redirect_uri()
    flask_session['redirect_uri'] = redirect_uri  # Store for callback
    msal_app = get_msal_app()

    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        state=flask_session['state'],
        redirect_uri=redirect_uri
    )

    logger.info(f"Redirecting to auth URL: {auth_url}")
    return redirect(auth_url)


@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback"""
    # Verify state to prevent CSRF
    if request.args.get('state') != flask_session.get('state'):
        return "Invalid state parameter", 400

    if 'error' in request.args:
        return f"Authentication error: {request.args.get('error_description', request.args.get('error'))}", 400

    if 'code' not in request.args:
        return "No authorization code received", 400

    # Get the redirect URI that was used in the login request
    redirect_uri = flask_session.get('redirect_uri', get_redirect_uri())

    # Exchange authorization code for token
    result = acquire_token_for_user(request.args['code'], redirect_uri)

    if 'error' in result:
        logger.error(f"Token acquisition error: {result.get('error_description', result.get('error'))}")
        return f"Failed to acquire token: {result.get('error_description', result.get('error'))}", 400

    # Store token in session
    flask_session['access_token'] = result.get('access_token')
    flask_session['user'] = result.get('id_token_claims', {}).get('preferred_username', 'User')

    logger.info(f"User authenticated: {flask_session.get('user')}")

    # Redirect to main page
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Clear session and logout"""
    flask_session.clear()
    return redirect(url_for('index'))


@socketio.on('connect')
def handle_connect(auth=None):
    """Handle WebSocket connection - initialize conversation"""
    try:
        access_token = get_token_from_session()

        if not access_token:
            logger.warning("Connection rejected - no access token")
            emit('error', {'message': 'Not authenticated. Please refresh the page to login.'})
            return False

        # Create client with user's token
        copilot_client = create_client(access_token)
        session_id = request.sid
        user = flask_session.get('user', 'Unknown')

        # Start conversation
        act = copilot_client.start_conversation(True)

        # Get initial actions
        async def get_initial_actions():
            actions = []
            attachments_list = []
            async for action in act:
                # Skip "Processing" status messages - they're just indicators, not content
                if action.text and action.text.strip().lower() != 'processing':
                    actions.append(action.text)

                # Collect attachments (e.g., adaptive cards)
                if hasattr(action, 'attachments') and action.attachments:
                    for attachment in action.attachments:
                        attachment_info = {
                            'content_type': attachment.content_type if hasattr(attachment, 'content_type') else None,
                            'name': attachment.name if hasattr(attachment, 'name') else None,
                            'content': attachment.content if hasattr(attachment, 'content') else None,
                            'content_url': attachment.content_url if hasattr(attachment, 'content_url') else None
                        }
                        attachments_list.append(attachment_info)

            conversation_id = action.conversation.id if hasattr(action, 'conversation') and action.conversation else None
            return conversation_id, actions, attachments_list

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_id, actions, initial_attachments = loop.run_until_complete(get_initial_actions())
        loop.close()

        # Store conversation
        conversations[session_id] = {
            'client': copilot_client,
            'conversation_id': conversation_id,
            'user': user
        }

        # Send initial greeting from Copilot actions
        username = flask_session.get('user', 'there')
        first_name = username.split('@')[0] if '@' in username else username

        # Format the initial message from Copilot
        # If we have attachments (like adaptive cards), don't show redundant text greeting
        if initial_attachments:
            greeting = None  # Let the adaptive card speak for itself
        elif actions:
            greeting = '\n'.join(actions)
        else:
            greeting = f"Hello, {first_name}"

        # Prepare init payload with attachments
        init_payload = {
            'greeting': greeting,
            'username': first_name
        }

        # Add attachments if present
        if initial_attachments:
            init_payload['attachments'] = initial_attachments

        emit('init', init_payload)
        logger.info(f"User connected: {user}")

    except Exception as e:
        logger.error(f"Connection error: {e}", exc_info=True)

        # Check if it's a 401 authentication error
        error_message = str(e)
        if '401' in error_message:
            logger.error("Authentication failed - access token may have expired")
            emit('error', {'message': 'Authentication failed. Your session has expired. Please refresh the page to login again.'})
        else:
            emit('error', {'message': f'Connection error: {error_message}'})
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    session_id = request.sid
    if session_id in conversations:
        user = conversations[session_id].get('user', 'Unknown')
        del conversations[session_id]
        logger.info(f"Client disconnected: {session_id} (user: {user})")


@socketio.on('send_message')
def handle_message(data):
    """Handle incoming chat messages"""
    session_id = request.sid
    query = data.get('message', '').strip()

    if not query:
        return

    if session_id not in conversations:
        emit('error', {'message': 'No active conversation. Please refresh the page.'})
        return

    try:
        copilot_client = conversations[session_id]['client']
        conversation_id = conversations[session_id]['conversation_id']
        user = conversations[session_id].get('user', 'Unknown')

        logger.info(f"User query from {user}: {query}")

        # Echo user message
        emit('message', {
            'text': query,
            'type': 'user'
        })

        # Get replies from Copilot
        async def get_replies():
            replies_data = []
            replies = copilot_client.ask_question(query, conversation_id)

            async for reply in replies:
                if reply.type == ActivityTypes.message:
                    reply_data = {'text': reply.text, 'type': 'bot'}

                    # Add suggested actions if present
                    if reply.suggested_actions:
                        suggestions = [action.title for action in reply.suggested_actions.actions]
                        reply_data['suggestions'] = suggestions

                    # Add attachments if present (e.g., adaptive cards)
                    if hasattr(reply, 'attachments') and reply.attachments:
                        attachments_data = []
                        for attachment in reply.attachments:
                            attachment_info = {
                                'content_type': attachment.content_type if hasattr(attachment, 'content_type') else None,
                                'name': attachment.name if hasattr(attachment, 'name') else None,
                                'content': attachment.content if hasattr(attachment, 'content') else None,
                                'content_url': attachment.content_url if hasattr(attachment, 'content_url') else None
                            }
                            attachments_data.append(attachment_info)
                        reply_data['attachments'] = attachments_data

                    replies_data.append(reply_data)
                elif reply.type == ActivityTypes.end_of_conversation:
                    replies_data.append({
                        'text': 'End of conversation.',
                        'type': 'system',
                        'end': True
                    })

            return replies_data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        replies_data = loop.run_until_complete(get_replies())
        loop.close()

        # Send all replies
        if replies_data:
            for reply_data in replies_data:
                emit('message', reply_data)
        else:
            logger.warning("No replies received from Copilot Studio API")
            emit('message', {
                'text': 'No response received from Copilot. Please try again.',
                'type': 'bot'
            })

        logger.info(f"Response sent to {user}")

    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)

        # Check if it's a 401 authentication error
        error_message = str(e)
        if '401' in error_message:
            logger.error("Authentication failed - access token may have expired")
            emit('error', {'message': 'Authentication failed. Your session has expired. Please refresh the page to login again.'})
        else:
            emit('error', {'message': f'Error: {error_message}'})


if __name__ == '__main__':
    # Check required environment variables
    required_vars = [
        "COPILOTSTUDIOAGENT__AGENTAPPID",
        "COPILOTSTUDIOAGENT__CLIENTSECRET",
        "COPILOTSTUDIOAGENT__TENANTID",
        "COPILOTSTUDIOAGENT__ENVIRONMENTID",
        "COPILOTSTUDIOAGENT__SCHEMANAME"
    ]

    missing_vars = [var for var in required_vars if not environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please configure your .env file with the required credentials")
        exit(1)

    logger.info("Starting Copilot Studio Web App")
    logger.info(f"Log file: {log_filename}")

    print(f"Copilot Studio Web App Starting...")
    print(f"Logs: {log_filename}")
    print(f"Server: http://0.0.0.0:7001")

    socketio.run(app, host='0.0.0.0', port=7001, allow_unsafe_werkzeug=True)
