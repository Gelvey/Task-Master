"""
Task-Master Web Application
A Flask-based web version of the Task-Master application
Compatible with CloudFlare Workers deployment
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import logging
import os
import json
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase configuration
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
USE_FIREBASE = False

if FIREBASE_AVAILABLE:
    try:
        cred_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
        if FIREBASE_DATABASE_URL and os.path.isfile(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
            USE_FIREBASE = True
            logger.info("Initialized Firebase backend")
        else:
            logger.warning("Firebase not configured or credentials.json missing; using local storage.")
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


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
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
    
    if USE_FIREBASE:
        try:
            tasks_ref = db.reference(f"users/{username}/tasks")
            tasks_data = tasks_ref.get()
            if tasks_data:
                for task_id, task_data in tasks_data.items():
                    task_data['id'] = task_id
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
                            tasks.append(task_data)
            except Exception as e:
                logger.error(f"Failed to read local tasks file: {e}")
    
    # Sort tasks by order
    tasks.sort(key=lambda x: x.get('order', 0))
    return tasks


def save_tasks(username, tasks):
    """Save tasks to Firebase or local storage"""
    tasks_data = {}
    for task in tasks:
        task_id = task.get('id', task['name'])
        tasks_data[task_id] = {
            'name': task['name'],
            'deadline': task.get('deadline'),
            'status': task.get('status', 'To Do'),
            'order': task.get('order', 0),
            'description': task.get('description', ''),
            'url': task.get('url', ''),
            'owner': task.get('owner', ''),
            'colour': task.get('colour', 'default'),
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
    if 'username' in session:
        return redirect(url_for('tasks'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
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
            'name': data['name'],
            'deadline': data.get('deadline'),
            'status': data.get('status', 'To Do'),
            'order': len(tasks),
            'description': data.get('description', ''),
            'url': data.get('url', ''),
            'owner': data.get('owner', ''),
            'colour': data.get('colour', 'default'),
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
                    'deadline': data.get('deadline', task.get('deadline')),
                    'status': data.get('status', task['status']),
                    'description': data.get('description', task.get('description', '')),
                    'url': data.get('url', task.get('url', '')),
                    'owner': data.get('owner', task.get('owner', '')),
                    'colour': data.get('colour', task.get('colour', 'default')),
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
        
        tasks = load_tasks(username)
        
        # Create a mapping of task_id to task
        task_map = {task['id']: task for task in tasks}
        
        # Reorder tasks based on the provided order
        reordered_tasks = []
        for i, task_id in enumerate(task_ids):
            if task_id in task_map:
                task = task_map[task_id]
                task['order'] = i
                reordered_tasks.append(task)
        
        save_tasks(username, reordered_tasks)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reordering tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
