"""
Task service layer for business logic
"""
import logging
from typing import List, Optional
from database.firebase_manager import DatabaseManager
from database.task_model import Task

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task operations"""
    
    def __init__(self):
        from config.settings import Settings
        self.db = DatabaseManager(use_firebase=not Settings.USE_LOCAL_STORAGE)
        self.username = Settings.TASKMASTER_USERNAME
    
    def get_all_tasks(self, owner: str = None) -> List[Task]:
        """Get all tasks (optionally filtered by owner)"""
        tasks = self.db.load_tasks(self.username)
        if owner:
            tasks = [t for t in tasks if t.owner == owner]
        return tasks
    
    async def get_task_by_name(self, task_name: str, owner: str = None) -> Optional[Task]:
        """Get a specific task by name (optionally filtered by owner)"""
        tasks = self.db.load_tasks(self.username)
        normalized_name = task_name.strip().lower()
        for task in tasks:
            if task.name.strip().lower() == normalized_name:
                if owner is None or task.owner == owner:
                    return task
        return None
    
    async def get_task_by_uuid(self, task_uuid: str) -> Optional[Task]:
        """Get a specific task by stable UUID"""
        tasks = self.db.load_tasks(self.username)
        for task in tasks:
            if task.uuid == task_uuid:
                return task
        return None
    
    async def add_task_from_modal(self, name: str, owner: str = "", deadline: Optional[str] = None,
                                   priority: str = "default", description: str = "",
                                   url: str = ""):
        """Add a new task from modal input"""
        task = Task(
            name=name,
            deadline=deadline,
            status="To Do",
            description=description,
            url=url,
            owner=owner,
            colour=priority
        )
        self.db.add_task(self.username, task)
        logger.info(f"Added task '{name}' assigned to '{owner}' for user {self.username}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_from_modal(self, task_id: str, name: str, owner: str = "",
                                     deadline: Optional[str] = None, priority: str = "default",
                                     description: str = "", url: str = ""):
        """Update a task from modal input"""
        updates = {
            'name': name,
            'deadline': deadline,
            'colour': priority,
            'description': description,
            'url': url,
            'owner': owner
        }
        self.db.update_task(self.username, task_id, updates)
        logger.info(f"Updated task '{task_id}' assigned to '{owner}' for user {self.username}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_status(self, task_name: str, new_status: str):
        """Update task status"""
        task = await self.get_task_by_name(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.update_task(self.username, task.id, {'status': new_status})
        logger.info(f"Updated task '{task_name}' status to {new_status} for user {self.username}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def delete_task(self, task_name: str):
        """Delete a task by name"""
        task = await self.get_task_by_name(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.delete_task(self.username, task.id)
        logger.info(f"Deleted task '{task_name}' for user {self.username}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_name_by_uuid(self, task_uuid: str, new_name: str):
        """Update task name by stable UUID"""
        tasks = self.db.load_tasks(self.username)
        task = next((t for t in tasks if t.uuid == task_uuid), None)
        if task is None:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")
        
        task.name = new_name
        task.id = new_name
        self.db.save_tasks(self.username, tasks)
        logger.info(f"Updated task name for UUID {task_uuid} to '{new_name}'")
    
    async def update_task_description_by_uuid(self, task_uuid: str, description: str):
        """Update task description by stable UUID"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")
        
        self.db.update_task(self.username, task.id, {'description': description or ""})
        logger.info(f"Updated task description for UUID {task_uuid}")
