# Quick Start Guide

Get up and running with Copilot Studio Web Chat in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.8 or higher installed
- [ ] Azure account with Active Directory access
- [ ] Microsoft Copilot Studio agent created
- [ ] Terminal/Command Prompt access

## Step-by-Step Setup

### 1. Get Azure AD Credentials (5 minutes)

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill in:
   - **Name**: `Copilot Studio Web Chat`
   - **Redirect URI**: `http://localhost:7001/auth/callback`
4. Click **Register**
5. **Copy these values** (you'll need them later):
   - Application (client) ID
   - Directory (tenant) ID
6. Go to **Certificates & secrets** → **New client secret**
7. **Copy the secret value** immediately (it won't be shown again)

### 2. Get Copilot Studio Information (2 minutes)

1. Go to [Copilot Studio](https://copilotstudio.microsoft.com)
2. Open your copilot
3. Go to **Settings** → **Channels** → **Mobile app**
4. Note down:
   - Environment ID
   - Schema Name (looks like: `cr###_YourCopilotName`)

### 3. Install the Application (2 minutes)

```bash
# Navigate to the project folder
cd /path/to/copilot-studio-web-chat

# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables (1 minute)

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` and replace the values:
```env
COPILOTSTUDIOAGENT__AGENTAPPID=paste-your-client-id-here
COPILOTSTUDIOAGENT__CLIENTSECRET=paste-your-client-secret-here
COPILOTSTUDIOAGENT__TENANTID=paste-your-tenant-id-here
COPILOTSTUDIOAGENT__ENVIRONMENTID=paste-your-environment-id-here
COPILOTSTUDIOAGENT__SCHEMANAME=paste-your-schema-name-here
FLASK_SECRET_KEY=any-random-string-here
SHOW_FEEDBACK=false
```

### 5. Run the Application (30 seconds)

```bash
python app.py
```

You should see:
```
Copilot Studio Web App Starting...
Logs: copilot_studio_20251021.log
Server: http://0.0.0.0:7001
```

### 6. Test It

1. Open browser: http://localhost:7001
2. Click **Login** (you'll be redirected to Microsoft login)
3. Sign in with your Microsoft account
4. Start chatting with your copilot!

## Common First-Time Issues

### Issue: "Missing required environment variables"
**Fix**: Double-check your `.env` file has all required values set

### Issue: "Redirect URI mismatch"
**Fix**: In Azure Portal, add `http://localhost:7001/auth/callback` to your app's redirect URIs

### Issue: "401 Authentication failed"
**Fix**:
- Make sure your client secret is correct and hasn't expired
- Try generating a new client secret in Azure Portal

### Issue: "Port already in use"
**Fix**:
```bash
# Find what's using port 7001
lsof -i :7001
# Kill it
kill -9 <PID>
```

## Next Steps

- ✅ Check the logs at `copilot_studio_YYYYMMDD.log` to see what's happening
- ✅ Try dark mode by clicking the 🌙 icon
- ✅ Read the full [README.md](README.md) for advanced features
- ✅ Set up ngrok for external access (see README.md)

## Testing with ngrok (Optional)

Want to test from your phone or share with others?

```bash
# In terminal 1: Run the app
python app.py

# In terminal 2: Start ngrok
ngrok http 7001
```

Then:
1. Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok-free.app`)
2. Add `https://abc123.ngrok-free.app/auth/callback` to Azure AD redirect URIs
3. Visit the ngrok URL in any browser!

## Need Help?

- **Check logs**: `copilot_studio_YYYYMMDD.log` in the project folder
- **Review errors**: Look for red error messages in the terminal
- **Read docs**: See [README.md](README.md) for detailed troubleshooting

## Security Reminder

⚠️ **NEVER commit your `.env` file to Git!** It contains sensitive credentials.

The `.gitignore` file already excludes it, but be careful if you rename or move files.

---

**Ready to deploy to production?** See the full README.md for security best practices and production considerations.
