"""
Task service layer for business logic
"""
import logging
from typing import List, Optional
from database.firebase_manager import DatabaseManager
from database.task_model import Task, normalize_subtasks

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
        logger.info(
            f"Added task '{name}' assigned to '{owner}' for user {self.username}")

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
        logger.info(
            f"Updated task '{task_id}' assigned to '{owner}' for user {self.username}")

    async def update_task_status(self, task_name: str, new_status: str):
        """Update task status"""
        task = await self.get_task_by_name(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")

        self.db.update_task(self.username, task.id, {'status': new_status})
        logger.info(
            f"Updated task '{task_name}' status to {new_status} for user {self.username}")

    async def delete_task(self, task_name: str):
        """Delete a task by name"""
        task = await self.get_task_by_name(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")

        self.db.delete_task(self.username, task.id)
        logger.info(f"Deleted task '{task_name}' for user {self.username}")

    async def update_task_name_by_uuid(self, task_uuid: str, new_name: str):
        """Update task name by stable UUID"""
        tasks = self.db.load_tasks(self.username)
        task = next((t for t in tasks if t.uuid == task_uuid), None)
        if task is None:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        task.name = new_name
        # Keep legacy key-by-name compatibility for web/desktop variants.
        task.id = new_name
        self.db.save_tasks(self.username, tasks)
        logger.info(f"Updated task name for UUID {task_uuid} to '{new_name}'")

    async def update_task_description_by_uuid(self, task_uuid: str, description: str):
        """Update task description by stable UUID"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        self.db.update_task(self.username, task.id, {
                            'description': description or ""})
        logger.info(f"Updated task description for UUID {task_uuid}")

    async def update_task_by_uuid(self, task_uuid: str, status: str, priority: str,
                                  owner: str, deadline: Optional[str],
                                  description: str, url: str):
        """Update task fields by stable UUID"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        updates = {
            'status': status,
            'colour': priority,
            'owner': owner,
            'deadline': deadline,
            'description': description or "",
            'url': url or "",
        }
        self.db.update_task(self.username, task.id, updates)
        logger.info(f"Updated task fields for UUID {task_uuid}")

    async def _trigger_forum_sync(self):
        """Legacy no-op: forum/dashboard sync is triggered by interaction handlers."""
        return

    def _normalize_and_save_subtasks_if_needed(self, task: Task) -> List[dict]:
        normalized = normalize_subtasks(task.subtasks)
        if task.subtasks != normalized:
            self.db.update_task(self.username, task.id, {
                                'subtasks': normalized})
        return normalized

    async def get_subtask_by_id(self, task_uuid: str, subtask_id: int) -> Optional[dict]:
        """Get subtask by stable numeric ID."""
        if subtask_id <= 0:
            return None

        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            return None

        subtasks = self._normalize_and_save_subtasks_if_needed(task)
        for subtask in subtasks:
            if subtask.get('id') == subtask_id:
                return subtask
        return None

    async def upsert_subtask_by_id(self, task_uuid: str, subtask_id: int, name: str,
                                   description: str = "", url: str = "") -> dict:
        """Create or update a subtask by stable numeric ID."""
        if subtask_id <= 0:
            raise ValueError("Sub-task ID must be a positive integer")

        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        subtasks = self._normalize_and_save_subtasks_if_needed(task)
        existing = next(
            (st for st in subtasks if st.get('id') == subtask_id), None)

        if existing:
            existing['name'] = name.strip()
            existing['description'] = description.strip()
            existing['url'] = url.strip()
            saved_subtask = existing
        else:
            saved_subtask = {
                'id': subtask_id,
                'name': name.strip(),
                'description': description.strip(),
                'url': url.strip(),
                'completed': False,
            }
            subtasks.append(saved_subtask)

        subtasks = normalize_subtasks(subtasks)
        self.db.update_task(self.username, task.id, {'subtasks': subtasks})
        logger.info(
            f"Upserted subtask #{subtask_id} for task UUID {task_uuid}")

        await self._trigger_forum_sync()
        return next((st for st in subtasks if st.get('id') == subtask_id), saved_subtask)

    async def toggle_subtask_by_id(self, task_uuid: str, subtask_id: int) -> dict:
        """Toggle completion state for a subtask by stable numeric ID."""
        if subtask_id <= 0:
            raise ValueError("Sub-task ID must be a positive integer")

        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        subtasks = self._normalize_and_save_subtasks_if_needed(task)
        target = next(
            (st for st in subtasks if st.get('id') == subtask_id), None)
        if not target:
            raise ValueError(f"Sub-task #{subtask_id} not found")

        target['completed'] = not bool(target.get('completed', False))
        subtasks = normalize_subtasks(subtasks)
        self.db.update_task(self.username, task.id, {'subtasks': subtasks})
        logger.info(f"Toggled subtask #{subtask_id} for task UUID {task_uuid}")

        await self._trigger_forum_sync()
        return next((st for st in subtasks if st.get('id') == subtask_id), target)

    async def delete_subtask_by_id(self, task_uuid: str, subtask_id: int) -> dict:
        """Delete a subtask by stable numeric ID."""
        if subtask_id <= 0:
            raise ValueError("Sub-task ID must be a positive integer")

        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        subtasks = self._normalize_and_save_subtasks_if_needed(task)
        existing = next(
            (st for st in subtasks if st.get('id') == subtask_id), None)
        if not existing:
            raise ValueError(f"Sub-task #{subtask_id} not found")

        remaining = [st for st in subtasks if st.get('id') != subtask_id]
        remaining = normalize_subtasks(remaining)
        self.db.update_task(self.username, task.id, {'subtasks': remaining})
        logger.info(
            f"Deleted subtask #{subtask_id} from task UUID {task_uuid}")

        await self._trigger_forum_sync()
        return existing

    async def add_subtask(self, task_uuid: str, subtask_name: str, description: str = "", url: str = ""):
        """Add a subtask to a task"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        subtasks = self._normalize_and_save_subtasks_if_needed(task)
        next_id = max([st.get('id', 0) for st in subtasks], default=0) + 1

        new_subtask = {
            "id": next_id,
            "name": subtask_name.strip(),
            "description": description.strip() if description else "",
            "url": url.strip() if url else "",
            "completed": False
        }
        task.subtasks.append(new_subtask)

        normalized = normalize_subtasks(task.subtasks)
        self.db.update_task(self.username, task.id, {'subtasks': normalized})
        logger.info(
            f"Added subtask '{subtask_name}' (#{next_id}) to task UUID {task_uuid}")

        await self._trigger_forum_sync()

    async def toggle_subtask(self, task_uuid: str, subtask_index: int):
        """Toggle the completion status of a subtask"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        task.subtasks = self._normalize_and_save_subtasks_if_needed(task)

        if subtask_index < 0 or subtask_index >= len(task.subtasks):
            raise ValueError(f"Invalid subtask index: {subtask_index}")

        # Toggle completion status
        task.subtasks[subtask_index]['completed'] = not task.subtasks[subtask_index].get(
            'completed', False)

        self.db.update_task(self.username, task.id, {
                            'subtasks': task.subtasks})
        logger.info(
            f"Toggled subtask {subtask_index} for task UUID {task_uuid}")

        await self._trigger_forum_sync()

    async def delete_subtask(self, task_uuid: str, subtask_index: int):
        """Delete a subtask from a task"""
        task = await self.get_task_by_uuid(task_uuid)
        if not task:
            raise ValueError(f"Task with UUID '{task_uuid}' not found")

        task.subtasks = self._normalize_and_save_subtasks_if_needed(task)

        if subtask_index < 0 or subtask_index >= len(task.subtasks):
            raise ValueError(f"Invalid subtask index: {subtask_index}")

        # Delete subtask
        removed = task.subtasks.pop(subtask_index)

        self.db.update_task(self.username, task.id, {
                            'subtasks': task.subtasks})
        logger.info(
            f"Deleted subtask '{removed.get('name')}' from task UUID {task_uuid}")

        await self._trigger_forum_sync()
