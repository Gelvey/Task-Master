"""
Task-Master Web Application
A Flask-based web version of the Task-Master application
Compatible with CloudFlare Workers deployment
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import os
import json
import re
import socket
import uuid
from functools import wraps
from dotenv import load_dotenv

# Try to import firebase_admin (optional)
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("firebase_admin not available, using local storage only")

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'

# CORS – configurable via CORS_ORIGINS env var.
# Accepts a comma-separated list of allowed origins / patterns.
#   • Exact origins:  https://carbon.clickdns.com.au
#   • Wildcard sub-domains:  *.clickdns.com.au  (converted to a regex)
#   • "*" to allow all origins (development only!)
# Default (when unset): no CORS headers.
_cors_raw = os.getenv('CORS_ORIGINS', '')
if _cors_raw.strip():
    _cors_origins = []
    for entry in _cors_raw.split(','):
        entry = entry.strip()
        if not entry:
            continue
        if '*' in entry and entry != '*':
            # Convert wildcard pattern like *.clickdns.com.au into a regex
            escaped = re.escape(entry).replace(r'\*', r'[\w.-]+')
            _cors_origins.append(re.compile(r'^https?://' + escaped + r'$'))
        else:
            _cors_origins.append(entry)
    if _cors_origins:
        CORS(app, resources={r"/api/*": {"origins": _cors_origins}},
             supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Single-user mode - if set, username is fixed and no login required
SINGLE_USER_MODE = os.getenv('TASKMASTER_USERNAME')

# Carbon API key – allows external API access from the Carbon dashboard
CARBON_API_KEY = os.getenv('CARBON_API_KEY')

# Host/IP Whitelist configuration
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(
    ',') if os.getenv('ALLOWED_HOSTS') else []
ALLOWED_HOSTS = [host.strip()
                 # Clean up whitespace
                 for host in ALLOWED_HOSTS if host.strip()]

# Firebase configuration
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
USE_FIREBASE = False

if FIREBASE_AVAILABLE and FIREBASE_DATABASE_URL:
    try:
        # Try to initialize from environment variables first
        firebase_creds = {
            "type": os.getenv("FIREBASE_TYPE", "service_account"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
        }

        # Check if all required Firebase env vars are present
        if all([firebase_creds["project_id"], firebase_creds["private_key"], firebase_creds["client_email"]]):
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(
                cred, {"databaseURL": FIREBASE_DATABASE_URL})
            USE_FIREBASE = True
            logger.info(
                "Initialized Firebase backend from environment variables")
        else:
            # Fallback to credentials.json file
            cred_path = os.path.join(os.path.dirname(
                __file__), "..", "credentials.json")
            if os.path.isfile(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(
                    cred, {"databaseURL": FIREBASE_DATABASE_URL})
                USE_FIREBASE = True
                logger.info(
                    "Initialized Firebase backend from credentials.json")
            else:
                logger.warning(
                    "Firebase credentials not found in environment or file; using local storage.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        USE_FIREBASE = False

# Parse owners from environment variable
OWNERS = os.getenv("OWNERS", "").split()

# Color options for task priorities
COLOUR_OPTIONS = {
    "default": {"label": "Default", "class": ""},
    "Important": {"label": "Important", "class": "priority-high"},
    "Moderately Important": {"label": "Moderately Important", "class": "priority-medium"},
    "Not Important": {"label": "Not Important", "class": "priority-low"},
}


def normalize_subtasks(subtasks):
    """Normalize subtasks to stable schema with numeric IDs."""
    if isinstance(subtasks, dict):
        normalized_input = []

        def sort_key(key):
            if isinstance(key, int):
                return (0, key)
            if isinstance(key, str) and key.isdigit():
                return (0, int(key))
            return (1, str(key))

        for key in sorted(subtasks.keys(), key=sort_key):
            raw = subtasks[key]
            if isinstance(raw, dict):
                subtask = dict(raw)
                subtask.setdefault('id', key)
            else:
                subtask = {
                    'id': key,
                    'name': str(raw) if raw is not None else ''
                }
            normalized_input.append(subtask)
        subtasks = normalized_input
    elif not isinstance(subtasks, list):
        return []

    normalized = []
    used_ids = set()
    next_id = 1

    for raw in subtasks:
        if isinstance(raw, dict):
            subtask = dict(raw)
        else:
            subtask = {'name': str(raw) if raw is not None else ''}

        subtask_id = subtask.get('id')
        if isinstance(subtask_id, str) and subtask_id.isdigit():
            subtask_id = int(subtask_id)
        if not isinstance(subtask_id, int) or subtask_id <= 0 or subtask_id in used_ids:
            while next_id in used_ids:
                next_id += 1
            subtask_id = next_id

        used_ids.add(subtask_id)
        next_id = max(next_id, subtask_id + 1)

        normalized.append({
            'id': subtask_id,
            'name': (subtask.get('name') or '').strip(),
            'description': (subtask.get('description') or '').strip(),
            'url': (subtask.get('url') or '').strip(),
            'completed': bool(subtask.get('completed', False)),
        })

    normalized.sort(key=lambda st: st['id'])
    return normalized


def check_ip_whitelist():
    """Check if the request IP is in the whitelist (supports both IPs and hostnames with DNS lookup)"""
    if not ALLOWED_HOSTS:
        return True  # No whitelist configured, allow all

    # Get the client IP address
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip:
        # X-Forwarded-For can contain multiple IPs, take the first one
        client_ip = client_ip.split(',')[0].strip()

    # Check each allowed host/IP
    for allowed_host in ALLOWED_HOSTS:
        # If it's a direct IP match
        if client_ip == allowed_host:
            return True

        # Try DNS lookup (for hostnames). No caching for DynDNS support
        # Using getaddrinfo to support both IPv4 and IPv6
        try:
            # Get all IP addresses (IPv4 and IPv6) for the hostname
            addr_info = socket.getaddrinfo(allowed_host, None)
            resolved_ips = [addr[4][0] for addr in addr_info]

            if client_ip in resolved_ips:
                logger.info(
                    f"Access granted for IP {client_ip} (resolved from hostname {allowed_host})")
                return True
        except socket.gaierror:
            # Not a valid hostname, continue to next entry
            pass
        except Exception as e:
            logger.warning(f"Error resolving hostname {allowed_host}: {e}")

    logger.warning(f"Access denied for IP: {client_ip}")
    return False


@app.before_request
def ip_whitelist_check():
    """Check IP whitelist before processing any request"""
    # Exempt valid Carbon API key requests from IP whitelist
    auth_header = request.headers.get('Authorization', '')
    if CARBON_API_KEY and auth_header.startswith('Bearer '):
        if auth_header[7:] == CARBON_API_KEY:
            return None  # Allow through — auth is handled by login_required

    if not check_ip_whitelist():
        return jsonify({'error': 'Access denied', 'message': 'Your IP address is not authorized'}), 403


def login_required(f):
    """Decorator to require login for routes (unless in single-user mode or valid API key)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Carbon API key authentication (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if CARBON_API_KEY and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token == CARBON_API_KEY:
                # API key valid — use TASKMASTER_USERNAME or 'carbon' as the identity
                session['username'] = SINGLE_USER_MODE or 'carbon'
                return f(*args, **kwargs)
            else:
                return jsonify({'error': 'Invalid API key'}), 401

        if SINGLE_USER_MODE:
            # In single-user mode, automatically set the username
            session['username'] = SINGLE_USER_MODE
        elif 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_local_file_path(username):
    """Get the local JSON file path for a user"""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, f"tasks_{username}.json")


def load_tasks(username):
    """Load tasks from Firebase or local storage"""
    tasks = []
    migrated_missing_uuid = False
    migrated_subtasks = False

    if USE_FIREBASE:
        try:
            tasks_ref = db.reference(f"users/{username}/tasks")
            tasks_data = tasks_ref.get()
            if tasks_data:
                for task_id, task_data in tasks_data.items():
                    task_data['id'] = task_id
                    if not task_data.get('uuid'):
                        task_data['uuid'] = str(uuid.uuid4())
                        migrated_missing_uuid = True
                    normalized_subtasks = normalize_subtasks(
                        task_data.get('subtasks', []))
                    if task_data.get('subtasks', []) != normalized_subtasks:
                        migrated_subtasks = True
                    task_data['subtasks'] = normalized_subtasks
                    tasks.append(task_data)
        except Exception as e:
            logger.error(f"Failed to load tasks from Firebase: {e}")
    else:
        # Local JSON fallback
        local_file = get_local_file_path(username)
        if os.path.isfile(local_file):
            try:
                with open(local_file, "r", encoding="utf-8") as f:
                    tasks_data = json.load(f)
                    if tasks_data:
                        for task_id, task_data in tasks_data.items():
                            task_data['id'] = task_id
                            if not task_data.get('uuid'):
                                task_data['uuid'] = str(uuid.uuid4())
                                migrated_missing_uuid = True
                            normalized_subtasks = normalize_subtasks(
                                task_data.get('subtasks', []))
                            if task_data.get('subtasks', []) != normalized_subtasks:
                                migrated_subtasks = True
                            task_data['subtasks'] = normalized_subtasks
                            tasks.append(task_data)
            except Exception as e:
                logger.error(f"Failed to read local tasks file: {e}")

    # Sort tasks by order
    tasks.sort(key=lambda x: x.get('order', 0))

    # Backfill UUIDs without changing existing task keys/IDs.
    if (migrated_missing_uuid or migrated_subtasks) and tasks:
        try:
            save_tasks(username, tasks)
        except Exception as e:
            logger.warning(f"Failed UUID backfill for {username}: {e}")

    return tasks


def save_tasks(username, tasks):
    """Save tasks to Firebase or local storage"""
    tasks_data = {}
    for task in tasks:
        task_id = task.get('id', task['name'])
        task_uuid = task.get('uuid') or str(uuid.uuid4())
        task['uuid'] = task_uuid
        tasks_data[task_id] = {
            'name': task['name'],
            'uuid': task_uuid,
            'deadline': task.get('deadline'),
            'status': task.get('status', 'To Do'),
            'order': task.get('order', 0),
            'description': task.get('description', ''),
            'url': task.get('url', ''),
            'owner': task.get('owner', ''),
            'colour': task.get('colour', 'default'),
            'subtasks': normalize_subtasks(task.get('subtasks', [])),
        }

    if USE_FIREBASE:
        try:
            tasks_ref = db.reference(f"users/{username}/tasks")
            tasks_ref.set(tasks_data)
            logger.info(f"Tasks saved to Firebase for user {username}")
        except Exception as e:
            logger.error(f"Failed to save tasks to Firebase: {e}")
            raise
    else:
        # Local JSON fallback
        local_file = get_local_file_path(username)
        try:
            with open(local_file, "w", encoding="utf-8") as f:
                json.dump(tasks_data, f, indent=2)
            logger.info(f"Tasks saved locally for user {username}")
        except Exception as e:
            logger.error(f"Failed to save local tasks file: {e}")
            raise


def delete_task(username, task_id):
    """Delete a task from Firebase or local storage"""
    if USE_FIREBASE:
        try:
            task_ref = db.reference(f"users/{username}/tasks/{task_id}")
            task_ref.delete()
            logger.info(f"Deleted task '{task_id}' from Firebase")
        except Exception as e:
            logger.error(f"Failed to delete task from Firebase: {e}")
            raise
    else:
        local_file = get_local_file_path(username)
        try:
            tasks_data = {}
            if os.path.isfile(local_file):
                with open(local_file, "r", encoding="utf-8") as f:
                    tasks_data = json.load(f) or {}

            if task_id in tasks_data:
                del tasks_data[task_id]
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(tasks_data, f, indent=2)
                logger.info(f"Deleted task '{task_id}' locally")
        except Exception as e:
            logger.error(f"Failed to delete task from local file: {e}")
            raise


@app.route('/')
def index():
    """Redirect to login or tasks page"""
    if SINGLE_USER_MODE:
        session['username'] = SINGLE_USER_MODE
        return redirect(url_for('tasks'))
    if 'username' in session:
        return redirect(url_for('tasks'))
    return redirect(url_for('login'))


@app.route('/favicon.ico')
def favicon():
    """Serve favicon at root path for browser compatibility"""
    return app.send_static_file('favicon/favicon.ico')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # If in single-user mode, skip login and go straight to tasks
    if SINGLE_USER_MODE:
        session['username'] = SINGLE_USER_MODE
        return redirect(url_for('tasks'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if username:
            session['username'] = username
            logger.info(f"User logged in: {username}")
            return redirect(url_for('tasks'))
        return render_template('login.html', error="Please enter a username")
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    username = session.get('username')
    session.clear()
    logger.info(f"User logged out: {username}")
    return redirect(url_for('login'))


@app.route('/tasks')
@login_required
def tasks():
    """Main tasks page"""
    username = session.get('username')
    return render_template('tasks.html',
                           username=username,
                           colour_options=COLOUR_OPTIONS,
                           owners=OWNERS)


@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    """API endpoint to get all tasks"""
    username = session.get('username')
    try:
        tasks = load_tasks(username)
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f"Error loading tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    """API endpoint to create a new task"""
    username = session.get('username')
    try:
        data = request.get_json()
        tasks = load_tasks(username)

        # Create new task
        new_task = {
            'id': data['name'],
            'uuid': str(uuid.uuid4()),
            'name': data['name'],
            'deadline': data.get('deadline'),
            'status': data.get('status', 'To Do'),
            'order': len(tasks),
            'description': data.get('description', ''),
            'url': data.get('url', ''),
            'owner': data.get('owner', ''),
            'colour': data.get('colour', 'default'),
            'subtasks': normalize_subtasks(data.get('subtasks', [])),
        }

        tasks.append(new_task)
        save_tasks(username, tasks)

        return jsonify({'success': True, 'task': new_task})
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """API endpoint to update a task"""
    username = session.get('username')
    try:
        data = request.get_json()
        tasks = load_tasks(username)

        # Find and update task
        for task in tasks:
            if task['id'] == task_id:
                task.update({
                    'name': data.get('name', task['name']),
                    'uuid': task.get('uuid', str(uuid.uuid4())),
                    'deadline': data.get('deadline', task.get('deadline')),
                    'status': data.get('status', task['status']),
                    'description': data.get('description', task.get('description', '')),
                    'url': data.get('url', task.get('url', '')),
                    'owner': data.get('owner', task.get('owner', '')),
                    'colour': data.get('colour', task.get('colour', 'default')),
                    'subtasks': normalize_subtasks(data.get('subtasks', task.get('subtasks', []))),
                })
                break

        save_tasks(username, tasks)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def remove_task(task_id):
    """API endpoint to delete a task"""
    username = session.get('username')
    try:
        delete_task(username, task_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/reorder', methods=['POST'])
@login_required
def reorder_tasks():
    """API endpoint to reorder tasks"""
    username = session.get('username')
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        if not task_ids:
            return jsonify({'success': False, 'error': 'No task_ids provided'}), 400

        tasks = load_tasks(username)

        # Map and validate provided ids
        task_map = {task['id']: task for task in tasks}
        for tid in task_ids:
            if tid not in task_map:
                return jsonify({'success': False, 'error': f'Task id not found: {tid}'}), 400

        # All provided tasks must belong to the same priority (colour)
        group_colour = task_map[task_ids[0]].get('colour', 'default')
        for tid in task_ids:
            if task_map[tid].get('colour', 'default') != group_colour:
                return jsonify({'success': False, 'error': 'Reorder must be within a single priority group'}), 400

        provided_set = set(task_ids)

        # Ensure provided ids are a subset of the tasks that have the same colour
        group_task_ids = [t['id'] for t in tasks if t.get(
            'colour', 'default') == group_colour]
        if not provided_set.issubset(set(group_task_ids)):
            return jsonify({'success': False, 'error': 'Invalid task ids for priority group'}), 400

        # Build new tasks list by replacing occurrences of the group's tasks with the new ordering
        new_order_iter = iter(task_ids)
        new_tasks = []
        for t in tasks:
            if t.get('colour', 'default') == group_colour and t['id'] in provided_set:
                # take the next id from the provided ordering
                next_id = next(new_order_iter)
                new_tasks.append(task_map[next_id])
            else:
                new_tasks.append(t)

        # Reassign order indexes
        for idx, t in enumerate(new_tasks):
            t['order'] = idx

        save_tasks(username, new_tasks)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reordering tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
