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
- `SECRET_KEY` - Your secret key for sessions
- `FIREBASE_DATABASE_URL` - (Optional) Firebase Realtime Database URL
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

1. Create Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Realtime Database
3. Generate service account credentials
4. Download as `credentials.json`
5. Place in parent directory (same location as desktop app)
6. Set `FIREBASE_DATABASE_URL` environment variable

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (prod) | Flask session secret key |
| `FIREBASE_DATABASE_URL` | No | Firebase Realtime Database URL |
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
