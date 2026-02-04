# Task-Master Web Application

A modern Python web application version of Task-Master, designed for deployment on CloudFlare Pages & Workers.

## Features

- **User Authentication**: Simple username-based authentication with session management
- **Task Management**: Create, read, update, and delete tasks
- **Task Status**: Track tasks as "To Do", "In Progress", or "Complete"
- **Deadlines**: Set optional deadlines with date and time
- **Priority Levels**: Assign priorities (Important, Moderately Important, Not Important)
- **Task Owners**: Assign tasks to specific owners
- **Descriptions & URLs**: Add detailed descriptions and related URLs to tasks
- **Drag & Drop**: Reorder tasks by dragging and dropping
- **Filtering**: Filter tasks by status (All, To Do, In Progress, Complete)
- **Firebase Integration**: Store tasks in Firebase Realtime Database (with local JSON fallback)
- **Responsive Design**: Modern, mobile-friendly interface

## Project Structure

```
web_app/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css      # Stylesheet
│   └── js/
│       ├── main.js        # Shared JavaScript utilities
│       └── tasks.js       # Task management JavaScript
├── templates/
│   ├── base.html          # Base template
│   ├── login.html         # Login page
│   └── tasks.html         # Tasks page
└── data/                   # Local storage directory (auto-created)
```

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. Navigate to the web_app directory:
   ```bash
   cd web_app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (optional):
   
   Create a `.env` file in the `web_app` directory:
   ```env
   SECRET_KEY=your-secret-key-here
   FIREBASE_DATABASE_URL=https://your-project-id.firebasedatabase.app/
   OWNERS=User1 User2 User3
   ```

4. Firebase Setup (optional):
   
   If using Firebase, place your `credentials.json` file in the parent directory (same location as the desktop app's credentials).

### Running Locally

Start the development server:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment to CloudFlare

### Option 1: CloudFlare Pages (Recommended for Static Frontend + Workers Backend)

CloudFlare Pages is ideal for hosting the static frontend, while CloudFlare Workers can handle the backend API.

#### Step 1: Prepare Your Repository

1. Ensure your code is in a Git repository (GitHub, GitLab, or Bitbucket)
2. Push all changes to your repository

#### Step 2: Deploy Frontend to CloudFlare Pages

1. Log in to your [CloudFlare Dashboard](https://dash.cloudflare.com/)
2. Go to **Pages** section
3. Click **Create a project**
4. Connect your Git repository
5. Configure build settings:
   - **Build command**: `echo "No build needed"`
   - **Build output directory**: `web_app/static`
   - **Root directory**: `web_app`

#### Step 3: Deploy Backend to CloudFlare Workers

CloudFlare Workers support Python through Workers Python runtime or using a WSGI adapter.

**Important Note**: Flask doesn't run directly on CloudFlare Workers. You'll need to either:

1. **Use CloudFlare Workers with a Python Worker** (requires refactoring to use Workers API)
2. **Use a serverless platform** like:
   - **Google Cloud Run** (fully supports Flask)
   - **AWS Lambda** with API Gateway
   - **Azure Functions**
   - **Vercel** (supports Python)
   - **Railway.app** (supports Flask directly)

### Option 2: Deploy to Alternative Platforms (Easier)

Since CloudFlare Workers has limitations with Flask, here are recommended alternatives:

#### Railway.app (Recommended - Easy Deployment)

1. Go to [Railway.app](https://railway.app/)
2. Sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your Task-Master repository
5. Railway will auto-detect Flask and deploy it
6. Add environment variables in the Railway dashboard:
   - `SECRET_KEY`
   - `FIREBASE_DATABASE_URL`
   - `OWNERS`

#### Vercel

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Create a `vercel.json` in the `web_app` directory:
   ```json
   {
     "builds": [
       {
         "src": "app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app.py"
       }
     ]
   }
   ```

3. Deploy:
   ```bash
   cd web_app
   vercel
   ```

#### Google Cloud Run

1. Install Google Cloud SDK
2. Build and deploy:
   ```bash
   gcloud run deploy task-master --source . --region us-central1 --allow-unauthenticated
   ```

#### Heroku

1. Install Heroku CLI
2. Create a `Procfile` in `web_app` directory:
   ```
   web: python app.py
   ```

3. Deploy:
   ```bash
   heroku create task-master-app
   git subtree push --prefix web_app heroku main
   ```

### CloudFlare Workers Alternative (API-Only Approach)

If you want to use CloudFlare Workers specifically, you would need to:

1. **Convert the Flask app to a CloudFlare Worker** (JavaScript/TypeScript)
2. **Use CloudFlare Workers KV** for data storage instead of Firebase
3. **Deploy static assets to CloudFlare Pages**

This would require significant refactoring. A sample `worker.js` structure:

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Handle API routes
  const url = new URL(request.url)
  
  if (url.pathname.startsWith('/api/')) {
    // Handle API requests with Workers KV
    return handleAPI(request)
  }
  
  // Serve static files from Pages
  return fetch(request)
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask session secret key | Yes (production) |
| `FIREBASE_DATABASE_URL` | Firebase Realtime Database URL | No (falls back to local JSON) |
| `OWNERS` | Space-separated list of task owners | No |

## Database Options

### Firebase Realtime Database (Cloud Storage)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a project or select existing one
3. Enable Realtime Database
4. Download service account credentials as `credentials.json`
5. Place in parent directory
6. Set `FIREBASE_DATABASE_URL` environment variable

### Local JSON Storage (Development/Testing)

If Firebase is not configured, the app automatically uses local JSON files stored in the `data/` directory. Each user gets their own `tasks_<username>.json` file.

## Security Considerations

1. **Change the SECRET_KEY** in production (use a strong random key)
2. **Secure Firebase credentials** (never commit `credentials.json` to version control)
3. **Use HTTPS** in production
4. **Implement proper authentication** for production use (current version uses simple username sessions)
5. **Set up Firebase Security Rules** to restrict access:

```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "auth != null && auth.uid == $uid",
        ".write": "auth != null && auth.uid == $uid"
      }
    }
  }
}
```

## Features Comparison with Desktop App

| Feature | Desktop App | Web App |
|---------|------------|---------|
| Task CRUD | ✅ | ✅ |
| Status Management | ✅ | ✅ |
| Deadlines | ✅ | ✅ |
| Priorities | ✅ | ✅ |
| Drag & Drop Reordering | ✅ | ✅ |
| Firebase Integration | ✅ | ✅ |
| Local Storage Fallback | ✅ | ✅ |
| Task Descriptions | ✅ | ✅ |
| Task URLs | ✅ | ✅ |
| Task Owners | ✅ | ✅ |
| Responsive Design | ❌ | ✅ |
| Multi-device Access | ✅ | ✅ |
| Auto-refresh | ✅ | ❌ (manual refresh) |

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
```

### Firebase Connection Issues

1. Verify `credentials.json` is in the correct location
2. Check `FIREBASE_DATABASE_URL` is set correctly
3. Ensure Firebase Realtime Database is enabled in Firebase Console

### Static Files Not Loading

Ensure the static files are in the correct directory structure and Flask can access them.

## License

This project is licensed under the MIT License - see the parent directory's LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Authors

- Circuit
- Gelvey

## Acknowledgments

- Flask web framework
- Firebase Realtime Database
- Original desktop application built with Tkinter
