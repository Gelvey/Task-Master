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
    
    def get_all_tasks(self, owner: str) -> List[Task]:
        """Get all tasks for an owner"""
        return self.db.load_tasks(owner)
    
    async def get_task_by_name(self, owner: str, task_name: str) -> Optional[Task]:
        """Get a specific task by name"""
        tasks = self.db.load_tasks(owner)
        for task in tasks:
            if task.name == task_name:
                return task
        return None
    
    async def add_task_from_modal(self, owner: str, name: str, deadline: Optional[str] = None,
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
        self.db.add_task(owner, task)
        logger.info(f"Added task '{name}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_from_modal(self, owner: str, task_id: str, name: str,
                                     deadline: Optional[str] = None, priority: str = "default",
                                     description: str = "", url: str = ""):
        """Update a task from modal input"""
        updates = {
            'name': name,
            'deadline': deadline,
            'colour': priority,
            'description': description,
            'url': url
        }
        self.db.update_task(owner, task_id, updates)
        logger.info(f"Updated task '{task_id}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_status(self, owner: str, task_name: str, new_status: str):
        """Update task status"""
        task = await self.get_task_by_name(owner, task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.update_task(owner, task.id, {'status': new_status})
        logger.info(f"Updated task '{task_name}' status to {new_status}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def delete_task(self, owner: str, task_name: str):
        """Delete a task by name"""
        task = await self.get_task_by_name(owner, task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.delete_task(owner, task.id)
        logger.info(f"Deleted task '{task_name}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
