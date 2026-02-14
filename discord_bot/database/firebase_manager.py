"""
Firebase database manager - uses same backend as web app and desktop client
"""
import os
import json
import logging
from typing import List, Optional, Dict
import firebase_admin
from firebase_admin import credentials, db
from .task_model import Task

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for tasks"""
    
    def __init__(self, use_firebase: bool = True):
        """Initialize database manager"""
        self.use_firebase = use_firebase
        self.initialized = False
        
        if use_firebase:
            self._initialize_firebase()
        else:
            self._initialize_local()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            firebase_database_url = os.getenv("FIREBASE_DATABASE_URL")
            if not firebase_database_url:
                logger.warning("FIREBASE_DATABASE_URL not set, falling back to local storage")
                self.use_firebase = False
                self._initialize_local()
                return
            
            # Check if already initialized
            try:
                firebase_admin.get_app()
                logger.info("Firebase already initialized")
                self.initialized = True
                return
            except ValueError:
                pass
            
            # Try environment variables first
            firebase_creds = {
                "type": os.getenv("FIREBASE_TYPE", "service_account"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL", 
                                                         "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            if all([firebase_creds["project_id"], firebase_creds["private_key"], firebase_creds["client_email"]]):
                cred = credentials.Certificate(firebase_creds)
                firebase_admin.initialize_app(cred, {"databaseURL": firebase_database_url})
                logger.info("Firebase initialized from environment variables")
                self.initialized = True
            else:
                # Fallback to credentials.json in parent directory
                cred_path = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")
                if os.path.isfile(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {"databaseURL": firebase_database_url})
                    logger.info("Firebase initialized from credentials.json")
                    self.initialized = True
                else:
                    logger.warning("Firebase credentials not found, using local storage")
                    self.use_firebase = False
                    self._initialize_local()
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.use_firebase = False
            self._initialize_local()
    
    def _initialize_local(self):
        """Initialize local JSON storage"""
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Using local storage at {self.data_dir}")
        self.initialized = True
    
    def _get_local_file_path(self, username: str) -> str:
        """Get local JSON file path for a username"""
        return os.path.join(self.data_dir, f"tasks_{username}.json")
    
    def load_tasks(self, username: str) -> List[Task]:
        """Load all tasks for a user"""
        tasks = []
        
        if self.use_firebase:
            try:
                tasks_ref = db.reference(f"users/{username}/tasks")
                tasks_data = tasks_ref.get()
                if tasks_data:
                    for task_id, task_data in tasks_data.items():
                        task = Task.from_dict(task_data, task_id)
                        tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to load tasks from Firebase: {e}")
        else:
            # Local JSON
            local_file = self._get_local_file_path(username)
            if os.path.isfile(local_file):
                try:
                    with open(local_file, "r", encoding="utf-8") as f:
                        tasks_data = json.load(f)
                        if tasks_data:
                            for task_id, task_data in tasks_data.items():
                                task = Task.from_dict(task_data, task_id)
                                tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to read local tasks file: {e}")
        
        # Sort by order
        tasks.sort(key=lambda x: x.order)
        return tasks
    
    def save_tasks(self, username: str, tasks: List[Task]):
        """Save all tasks for a user"""
        tasks_data = {}
        for task in tasks:
            task_id = task.id or task.name
            tasks_data[task_id] = task.to_dict()
        
        if self.use_firebase:
            try:
                tasks_ref = db.reference(f"users/{username}/tasks")
                tasks_ref.set(tasks_data)
                logger.info(f"Tasks saved to Firebase for user {username}")
            except Exception as e:
                logger.error(f"Failed to save tasks to Firebase: {e}")
                raise
        else:
            # Local JSON
            local_file = self._get_local_file_path(username)
            try:
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(tasks_data, f, indent=2)
                logger.info(f"Tasks saved locally for user {username}")
            except Exception as e:
                logger.error(f"Failed to save local tasks file: {e}")
                raise
    
    def add_task(self, username: str, task: Task):
        """Add a new task"""
        tasks = self.load_tasks(username)
        task.order = len(tasks)
        task.id = task.name  # Use name as ID
        tasks.append(task)
        self.save_tasks(username, tasks)
        logger.info(f"Added task '{task.name}' for user {username}")
    
    def update_task(self, username: str, task_id: str, updates: Dict):
        """Update an existing task"""
        tasks = self.load_tasks(username)
        for task in tasks:
            if task.id == task_id:
                for key, value in updates.items():
                    setattr(task, key, value)
                break
        self.save_tasks(username, tasks)
        logger.info(f"Updated task '{task_id}' for user {username}")
    
    def delete_task(self, username: str, task_id: str):
        """Delete a task"""
        tasks = self.load_tasks(username)
        tasks = [t for t in tasks if t.id != task_id]
        # Reorder remaining tasks
        for idx, task in enumerate(tasks):
            task.order = idx
        self.save_tasks(username, tasks)
        logger.info(f"Deleted task '{task_id}' for user {username}")
    
    def reorder_tasks(self, username: str, task_ids: List[str]):
        """Reorder tasks within same priority group"""
        tasks = self.load_tasks(username)
        task_map = {t.id: t for t in tasks}
        
        # Validate all task_ids exist
        for tid in task_ids:
            if tid not in task_map:
                raise ValueError(f"Task ID not found: {tid}")
        
        # All tasks must have same priority
        group_colour = task_map[task_ids[0]].colour
        for tid in task_ids:
            if task_map[tid].colour != group_colour:
                raise ValueError("Cannot reorder tasks across different priority groups")
        
        # Rebuild task list with new order
        provided_set = set(task_ids)
        new_order_iter = iter(task_ids)
        new_tasks = []
        
        for t in tasks:
            if t.colour == group_colour and t.id in provided_set:
                next_id = next(new_order_iter)
                new_tasks.append(task_map[next_id])
            else:
                new_tasks.append(t)
        
        # Reassign order indexes
        for idx, task in enumerate(new_tasks):
            task.order = idx
        
        self.save_tasks(username, new_tasks)
        logger.info(f"Reordered tasks for user {username}")
