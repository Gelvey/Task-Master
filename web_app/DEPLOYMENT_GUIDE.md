# Task-Master Web App - Quick Deployment Guide

This is a quick reference for deploying the Task-Master web application. For comprehensive documentation, see [README.md](README.md).

## 🚀 Quick Start (Local)

```bash
cd web_app
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## ☁️ Cloud Deployment (Recommended Options)

### Option 1: Railway.app (Easiest)

1. Push code to GitHub
2. Visit [railway.app](https://railway.app)
3. Connect GitHub repo
4. **IMPORTANT:** Go to Settings → Root Directory and set to `web_app`
5. Railway auto-detects Flask and deploys
6. Add environment variables in dashboard

**Environment Variables:**
- `SECRET_KEY` - Your secret key for sessions (required)
- `TASKMASTER_USERNAME` - (Optional) Username for single-user mode - skips login
- `ALLOWED_IPS` - (Optional) Comma-separated IP whitelist (e.g., `192.168.1.1,203.0.113.5`)
- `FIREBASE_DATABASE_URL` - (Optional) Firebase Realtime Database URL
- `FIREBASE_PROJECT_ID` - (Optional) Firebase project ID (if not using credentials.json)
- `FIREBASE_PRIVATE_KEY` - (Optional) Firebase private key (escape newlines as \\n)
- `FIREBASE_CLIENT_EMAIL` - (Optional) Firebase service account email
- `OWNERS` - (Optional) Space-separated list of task owners

**Note:** If you don't set the Root Directory to `web_app`, Railway won't find your Flask app. Alternatively, commit the `railway.json` file from the project root which configures this automatically.

### Option 2: Vercel (Fast Serverless)

```bash
npm install -g vercel
cd web_app
vercel
```

Set environment variables in Vercel dashboard after deployment.

### Option 3: Heroku (Traditional)

```bash
heroku create task-master-app
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set FIREBASE_DATABASE_URL=your-db-url
git subtree push --prefix web_app heroku main
```

## 📋 Required Configuration

### Minimum (Local Development)
- No configuration needed! Uses local JSON storage

### Production (Recommended)
1. Set `SECRET_KEY` environment variable to a random string
2. (Optional) Configure Firebase for cloud storage:
   - Set `FIREBASE_DATABASE_URL`
   - Add `credentials.json` to parent directory

## 🔥 Firebase Setup (Optional)

### Method 1: Environment Variables (Recommended for Railway/Cloud)

1. Create Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Realtime Database
3. Generate service account credentials (download JSON)
4. Extract values from the JSON and set as environment variables:
   - `FIREBASE_DATABASE_URL` - Your database URL
   - `FIREBASE_PROJECT_ID` - The project_id field
   - `FIREBASE_PRIVATE_KEY` - The private_key field (escape \\n as \\\\n)
   - `FIREBASE_CLIENT_EMAIL` - The client_email field
   - `FIREBASE_CLIENT_ID` - The client_id field
   - `FIREBASE_CLIENT_CERT_URL` - The client_x509_cert_url field

### Method 2: credentials.json File (For Local Development)

1. Download Firebase service account credentials as JSON
2. Place as `credentials.json` in parent directory (same location as desktop app)
3. Set `FIREBASE_DATABASE_URL` environment variable

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (prod) | Flask session secret key |
| `TASKMASTER_USERNAME` | No | Fixed username for single-user mode (skips login) |
| `ALLOWED_IPS` | No | Comma-separated IP whitelist (e.g., `1.2.3.4,5.6.7.8`) |
| `FIREBASE_DATABASE_URL` | No | Firebase Realtime Database URL |
| `FIREBASE_PROJECT_ID` | No | Firebase project ID (for env-based config) |
| `FIREBASE_PRIVATE_KEY` | No | Firebase private key (replace \\n with \\\\n) |
| `FIREBASE_CLIENT_EMAIL` | No | Firebase service account email |
| `FIREBASE_CLIENT_ID` | No | Firebase client ID |
| `FIREBASE_CLIENT_CERT_URL` | No | Firebase client cert URL |
| `OWNERS` | No | Space-separated list of task owners |

## 📦 What's Included

- ✅ Flask backend with REST API
- ✅ Responsive HTML/CSS/JS frontend
- ✅ Firebase integration + local fallback
- ✅ User authentication
- ✅ Full task management (CRUD)
- ✅ Drag-and-drop reordering
- ✅ Priority levels & status tracking
- ✅ Deployment configs for Vercel/Heroku

## 🔒 Security Notes

1. **Always** set a strong `SECRET_KEY` in production
2. **Never** commit `.env` or `credentials.json` to git
3. Configure Firebase security rules to restrict access
4. Use HTTPS in production

## 📝 CloudFlare Workers Note

CloudFlare Workers doesn't support Flask directly. Consider:
- **Railway.app** (easiest Flask deployment)
- **Vercel** (Python serverless)
- **Google Cloud Run** (containers)

For CloudFlare specifically, you would need to refactor to JavaScript/TypeScript Workers.

## 🆘 Troubleshooting

**Railway "No start command found" error?**
- Set Root Directory to `web_app` in Railway Settings
- OR ensure `railway.json` is committed to your repo root
- Verify `gunicorn` is in `web_app/requirements.txt`

**Port 5000 in use?**
```python
# In app.py, change:
app.run(debug=True, host='0.0.0.0', port=8080)
```

**Firebase not connecting?**
- Verify `credentials.json` location
- Check `FIREBASE_DATABASE_URL` format
- Enable Realtime Database in Firebase Console

**Static files not loading?**
- Check file paths in templates
- Ensure static directory structure is correct
- Clear browser cache

## 📞 Support

For detailed documentation, troubleshooting, and advanced configuration, see the full [README.md](README.md).

## ✨ Features

- User authentication with sessions
- Create, edit, delete tasks
- Task status management (To Do, In Progress, Complete)
- Priority levels (Important, Moderately Important, Not Important)
- Optional deadlines with date & time
- Task descriptions and URLs
- Drag-and-drop reordering
- Filter by status
- Responsive mobile design
- Firebase cloud storage or local JSON fallback

---

**Authors**: Circuit & Gelvey  
**License**: MIT
