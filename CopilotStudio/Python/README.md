# Copilot Studio Web Chat

A Flask-based web application that provides a chat interface for Microsoft Copilot Studio agents with OAuth authentication, adaptive cards support, and dark/light mode theming.

## Features

- 🔐 **Microsoft OAuth Authentication** - Secure authentication using MSAL (Microsoft Authentication Library)
- 💬 **Real-time Chat** - WebSocket-based communication using Flask-SocketIO
- 🎨 **Adaptive Cards Support** - Rich content rendering with markdown support
- 🌓 **Dark/Light Mode** - Theme toggle with persistent user preference
- 📝 **Comprehensive Logging** - File-based logging with rotation for all API interactions
- 🌐 **Dynamic Redirect URIs** - Automatic detection for localhost, ngrok, or any domain
- 📱 **Responsive Design** - Mobile-friendly chat interface
- 🔄 **Session Management** - Conversation persistence across messages
- 👍 **Feedback Support** - Optional thumbs up/down feedback (configurable)

## Prerequisites

- **Python 3.8+**
- **Microsoft Azure Account** with:
  - Azure AD App Registration
  - Microsoft Copilot Studio Agent
  - Power Platform Environment
- **pip** (Python package manager)
- **(Optional) ngrok** - For external access during development

## Installation

### 1. Clone or Download the Project

```bash
cd /path/to/project
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Azure AD App Registration

You need to register an application in Azure AD:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations** > **New registration**
3. Configure:
   - **Name**: Copilot Studio Web Chat
   - **Supported account types**: Choose based on your needs
   - **Redirect URI**:
     - Type: Web
     - URL: `http://localhost:7001/auth/callback`
     - (Add additional URIs for ngrok or production domains)
   - Permission:
     - Power Platform API
       - CopilotStudio.Copilots.Invoke (Delegated)
4. After registration:
   - Copy the **Application (client) ID**
   - Copy the **Directory (tenant) ID**
   - Create a **Client Secret** under "Certificates & secrets"

### 2. Copilot Studio Configuration

1. Navigate to your [Copilot Studio](https://copilotstudio.microsoft.com)
2. Open your agent/copilot
3. Go to **Settings** > **Advanced** > **Metadata**
4. Note the following values:
   - Environment ID
   - Schema Name (Agent identifier)

### 3. Environment Variables

Create a `.env` file in the project root:

```env
# Azure AD Application Configuration
COPILOTSTUDIOAGENT__AGENTAPPID=your-application-client-id
COPILOTSTUDIOAGENT__CLIENTSECRET=your-client-secret
COPILOTSTUDIOAGENT__TENANTID=your-tenant-id

# Copilot Studio Configuration
COPILOTSTUDIOAGENT__ENVIRONMENTID=your-environment-id
COPILOTSTUDIOAGENT__SCHEMANAME=your-copilot-schema-name

# Flask Configuration
FLASK_SECRET_KEY=your-random-secret-key

# UI Configuration (Optional)
# Show feedback thumbs up/down icons (true/false)
SHOW_FEEDBACK=false
```

**Notes:**
- Replace all `your-*` values with actual values from Azure and Copilot Studio
- `REDIRECT_URI` is no longer needed - it's automatically detected
- Generate a secure `FLASK_SECRET_KEY` using: `python -c "import secrets; print(secrets.token_hex(32))"`

## Running the Application

### Local Development

```bash
python app.py
```

The application will start at: `http://localhost:7001`

### Using ngrok (Optional)

For external access or testing OAuth callbacks:

1. Install ngrok: https://ngrok.com/download

2. Start the Flask application:
   ```bash
   python app.py
   ```

3. In another terminal, start ngrok:
   ```bash
   ngrok http 7001
   ```

4. ngrok will provide a public URL (e.g., `https://abc123.ngrok-free.app`)

5. Add the ngrok callback URL to your Azure AD app registration:
   - Redirect URI: `https://your-ngrok-url.ngrok-free.app/auth/callback`

6. Access your application at the ngrok URL

**Important**: The application automatically detects the redirect URI, so no code changes are needed when using ngrok.

## Project Structure

```
.
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (create this)
├── README.md                      # This file
├── templates/
│   └── index.html                 # Chat UI template
├── static/
│   ├── css/
│   │   └── adaptivecards.css     # Adaptive Cards styling
│   ├── js/
│   │   ├── socket.io.min.js      # SocketIO client library
│   │   ├── marked.min.js         # Markdown parser
│   │   ├── adaptivecards.min.js  # Adaptive Cards SDK
│   │   └── adaptivecards-templating.min.js
│   └── image/
│       └── favicon.ico            # Application icon
└── copilot_studio_YYYYMMDD.log   # Daily log file (auto-generated)
```

## Logging

The application automatically logs all interactions to daily log files:

- **File Format**: `copilot_studio_YYYYMMDD.log`
- **Location**: Project root directory
- **Rotation**: 10MB max file size, keeps 5 backup files
- **Contents**:
  - User authentication events
  - Connection/disconnection events
  - User queries and bot responses
  - Errors with stack traces
  - API interaction details

## Features Configuration

### Dark/Light Mode

- Click the theme toggle button (🌙/☀️) in the top-right corner
- Theme preference is saved to browser localStorage
- Adaptive cards automatically adjust colors based on theme

### Feedback Icons

Enable or disable thumbs up/down feedback icons:

```env
SHOW_FEEDBACK=true   # Show feedback icons
SHOW_FEEDBACK=false  # Hide feedback icons
```

## Authentication Flow

1. User visits the application
2. If not authenticated, redirected to `/login`
3. User is redirected to Microsoft OAuth login
4. After successful authentication, redirected back to the application
5. Access token is stored in server-side session
6. Chat interface is displayed
7. User can logout using `/logout` route

## Troubleshooting

### 401 Authentication Errors

**Symptoms**: "Authentication failed. Your session has expired" error

**Solutions**:
- Refresh the page to re-authenticate
- Check that your client secret hasn't expired in Azure AD
- Verify all environment variables are correct

### Connection Issues

**Symptoms**: Cannot connect to Copilot Studio

**Solutions**:
- Verify `COPILOTSTUDIOAGENT__ENVIRONMENTID` is correct
- Verify `COPILOTSTUDIOAGENT__SCHEMANAME` matches your copilot
- Check that your Azure AD app has appropriate permissions
- Review the log file for detailed error messages

### OAuth Redirect URI Mismatch

**Symptoms**: "Redirect URI mismatch" error during login

**Solutions**:
- Add your redirect URI to Azure AD app registration:
  - For localhost: `http://localhost:7001/auth/callback`
  - For ngrok: `https://your-ngrok-url.ngrok-free.app/auth/callback`
  - For production: `https://your-domain.com/auth/callback`

### Adaptive Cards Not Rendering

**Symptoms**: Adaptive cards appear blank or don't display

**Solutions**:
- Check browser console for JavaScript errors
- Verify all static files are loaded correctly
- Try toggling dark/light mode
- Clear browser cache and reload

### Port Already in Use

**Symptoms**: `Address already in use` error

**Solutions**:
```bash
# Find process using port 7001
lsof -i :7001

# Kill the process
kill -9 <PID>

# Or change the port in app.py (line 417)
socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
```

## Security Considerations

- **Never commit `.env` file** to version control
- **Rotate client secrets** regularly in Azure AD
- **Use HTTPS** in production environments
- **Set secure FLASK_SECRET_KEY** for production
- **Review Azure AD permissions** to follow principle of least privilege
- **Monitor log files** for suspicious activity

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari
- Modern mobile browsers

## Dependencies

All dependencies are listed in `requirements.txt`:

- **Flask** - Web framework
- **Flask-SocketIO** - WebSocket support
- **Flask-Session** - Server-side session management
- **MSAL** - Microsoft Authentication Library
- **python-dotenv** - Environment variable management
- **aiohttp** - Async HTTP client
- **microsoft-agents-activity** - Microsoft Bot Framework activities
- **microsoft-agents-copilotstudio-client** - Copilot Studio client SDK

## License

Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

## Support

For issues related to:
- **Copilot Studio**: [Microsoft Copilot Studio Documentation](https://learn.microsoft.com/microsoft-copilot-studio/)
- **Azure AD**: [Azure Active Directory Documentation](https://learn.microsoft.com/azure/active-directory/)
- **This Application**: Check the log files and review the troubleshooting section

## Version History

- **v1** - Initial release
