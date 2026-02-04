# Task-Master Web (Cloudflare Pages)

This folder contains a minimal Python web app variant of Task-Master that is compatible with Cloudflare Pages.

## Quick Start (Local)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python web_app/app.py
```

4. Visit `http://127.0.0.1:5000` in your browser.

## Configuration & Environment Variables

The web app reads configuration in the following order:

1. Environment variables (recommended for Cloudflare Pages).
2. `web_app/configuration.json` for Firebase configuration.
3. `web_app/config.ini` for user defaults.

### Environment Variables

| Variable | Description |
| --- | --- |
| `FIREBASE_DATABASE_URL` | Firebase Realtime Database URL. |
| `FIREBASE_PROJECT_ID` | Firebase project ID. |
| `DEFAULT_OWNER` | Default owner value used in the UI. |
| `OWNERS` | Comma-separated or space-separated list of owners. |
| `CONFIGURATION_JSON_PATH` | Optional override for the Firebase configuration file path. |
| `CONFIG_INI_PATH` | Optional override for the config.ini file path. |

### configuration.json

Update `web_app/configuration.json` with your Firebase configuration. Example:

```json
{
  "firebase": {
    "database_url": "https://your-project-id.firebasedatabase.app",
    "project_id": "your-project-id"
  }
}
```

### config.ini

Add a `config.ini` file to `web_app/` with optional defaults:

```ini
[user]
username = Default Owner

[owners]
list = Alice, Bob, Charlie
```

### Runtime Config Snapshot

If you want the web UI to display the current configuration, run the helper script:

```bash
python web_app/generate_runtime_config.py
```

This writes `web_app/public/runtime-config.json`, which the UI will load automatically.

## Cloudflare Pages Deployment

Cloudflare Pages runs static sites. This deployment publishes the static UI from `web_app/public` and uses a build step to generate a runtime config JSON during deployment. The Flask API routes only run locally or in a separate backend.

1. Push this repository to GitHub (or update it).
2. Create a new Cloudflare Pages project connected to the repository.
3. Set the build command to:

```bash
pip install -r requirements.txt
python web_app/generate_runtime_config.py
```

4. Set the build output directory to `web_app/public`.
5. Add the environment variables from the table above in the Cloudflare Pages project settings.
6. Deploy the site.

> If you want dynamic API routes, pair this static build with a Cloudflare Worker or another backend service.
