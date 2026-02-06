// Tasks page JavaScript

let tasks = [];
let currentFilter = 'all';
let editingTaskId = null;
let draggedPriority = null;

const PRIORITY_RANK = {
    'Important': 3,
    'Moderately Important': 2,
    'Not Important': 1,
    'default': 0
};

// DOM Elements
const taskForm = document.getElementById('taskForm');
const taskList = document.getElementById('taskList');
const hasDeadlineCheckbox = document.getElementById('hasDeadline');
const deadlineInputs = document.querySelectorAll('.deadline-inputs');
const taskModal = document.getElementById('taskModal');
const closeModal = document.querySelector('.close');
const cancelEditBtn = document.getElementById('cancelEdit');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadTasks();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Task form submission
    taskForm.addEventListener('submit', handleTaskSubmit);
    
    // Deadline checkbox toggle
    hasDeadlineCheckbox.addEventListener('change', function() {
        deadlineInputs.forEach(input => {
            input.style.display = this.checked ? 'flex' : 'none';
        });
    });
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.filter;
            renderTasks();
        });
    });
    
    // Modal close
    closeModal.addEventListener('click', () => {
        taskModal.classList.remove('show');
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === taskModal) {
            taskModal.classList.remove('show');
        }
    });
    
    // Cancel edit button
    cancelEditBtn.addEventListener('click', () => {
        editingTaskId = null;
        taskForm.reset();
        cancelEditBtn.style.display = 'none';
        document.querySelector('.task-form h2').textContent = 'Add New Task';
    });
}

// Load tasks from API
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();
        
        if (data.success) {
            tasks = data.tasks;
            renderTasks();
        } else {
            showError('Failed to load tasks: ' + data.error);
        }
    } catch (error) {
        showError('Error loading tasks: ' + error.message);
    }
}

// Render tasks in the list
function renderTasks() {
    const filteredTasks = currentFilter === 'all' 
        ? tasks 
        : tasks.filter(task => task.status === currentFilter);
    
    if (filteredTasks.length === 0) {
        taskList.innerHTML = '<p class="empty-state">No tasks found. Add your first task above!</p>';
        return;
    }
    
    // Sort by priority (highest first) then by order
    filteredTasks.sort((a, b) => {
        const pa = PRIORITY_RANK[a.colour] || 0;
        const pb = PRIORITY_RANK[b.colour] || 0;
        if (pa !== pb) return pb - pa; // higher priority first
        return (a.order || 0) - (b.order || 0);
    });

    taskList.innerHTML = filteredTasks.map(task => createTaskElement(task)).join('');
    
    // Add drag and drop
    setupDragAndDrop();
    
    // Add click listeners
    document.querySelectorAll('.task-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.task-actions')) {
                showTaskModal(item.dataset.taskId);
            }
        });
    });
}

// Create HTML for a single task
function createTaskElement(task) {
    const statusClass = task.status.toLowerCase().replace(' ', '');
    const priorityClass = colourOptions[task.colour]?.class || '';
    const deadline = formatDeadline(task.deadline);
    const isOverdue = isTaskOverdue(task);
    
    return `
        <div class="task-item ${priorityClass}" data-task-id="${task.id}" data-priority="${task.colour}" draggable="true">
            <div class="task-info">
                <div class="task-name">${escapeHtml(task.name)}</div>
                <div class="task-meta">
                    <span class="task-status status-${statusClass}">${task.status}</span>
                    ${deadline ? `<span class="task-deadline ${isOverdue ? 'overdue' : ''}">📅 ${deadline}</span>` : ''}
                    ${task.owner ? `<span>👤 ${escapeHtml(task.owner)}</span>` : ''}
                </div>
            </div>
            <div class="task-actions">
                <button class="btn btn-sm btn-success" onclick="updateTaskStatus('${task.id}', 'Complete'); event.stopPropagation();">✓</button>
                <button class="btn btn-sm btn-secondary" onclick="updateTaskStatus('${task.id}', 'In Progress'); event.stopPropagation();">▶</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTask('${task.id}'); event.stopPropagation();">✕</button>
            </div>
        </div>
    `;
}

// Format deadline for display
function formatDeadline(deadline) {
    if (!deadline) return null;
    
    try {
        const date = new Date(deadline);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return deadline;
    }
}

// Check if task is overdue
function isTaskOverdue(task) {
    if (!task.deadline) return false;
    return new Date(task.deadline) < new Date() && task.status !== 'Complete';
}

// Handle form submission (add or update task)
async function handleTaskSubmit(e) {
    e.preventDefault();
    
    const taskName = document.getElementById('taskName').value.trim();
    const taskStatus = document.getElementById('taskStatus').value;
    const taskColour = document.getElementById('taskColour').value;
    const taskOwner = document.getElementById('taskOwner')?.value || '';
    const taskDescription = document.getElementById('taskDescription').value.trim();
    const taskUrl = document.getElementById('taskUrl').value.trim();
    
    let deadline = null;
    if (hasDeadlineCheckbox.checked) {
        const deadlineDate = document.getElementById('deadlineDate').value;
        const deadlineTime = document.getElementById('deadlineTime').value;
        if (deadlineDate) {
            deadline = deadlineDate + (deadlineTime ? 'T' + deadlineTime : 'T00:00');
        }
    }
    
    const taskData = {
        name: taskName,
        status: taskStatus,
        colour: taskColour,
        owner: taskOwner,
        description: taskDescription,
        url: taskUrl,
        deadline: deadline
    };
    
    try {
        let response;
        if (editingTaskId) {
            // Update existing task
            response = await fetch(`/api/tasks/${editingTaskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
        } else {
            // Create new task
            response = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            await loadTasks();
            taskForm.reset();
            editingTaskId = null;
            cancelEditBtn.style.display = 'none';
            document.querySelector('.task-form h2').textContent = 'Add New Task';
        } else {
            showError('Failed to save task: ' + data.error);
        }
    } catch (error) {
        showError('Error saving task: ' + error.message);
    }
}

// Update task status
async function updateTaskStatus(taskId, newStatus) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadTasks();
        } else {
            showError('Failed to update task status: ' + data.error);
        }
    } catch (error) {
        showError('Error updating task status: ' + error.message);
    }
}

// Delete task
async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadTasks();
        } else {
            showError('Failed to delete task: ' + data.error);
        }
    } catch (error) {
        showError('Error deleting task: ' + error.message);
    }
}

// Show task details modal
function showTaskModal(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;
    
    document.getElementById('modalTaskName').textContent = task.name;
    document.getElementById('modalStatus').textContent = task.status;
    document.getElementById('modalDeadline').textContent = formatDeadline(task.deadline) || 'No deadline';
    document.getElementById('modalPriority').textContent = colourOptions[task.colour]?.label || 'Default';
    document.getElementById('modalOwner').textContent = task.owner || 'None';
    document.getElementById('modalDescription').textContent = task.description || 'No description';
    
    const urlLink = document.getElementById('modalUrl');
    if (task.url) {
        urlLink.href = task.url;
        urlLink.textContent = task.url;
        urlLink.style.display = 'inline';
    } else {
        urlLink.style.display = 'none';
    }
    
    // Edit button
    document.getElementById('editTaskBtn').onclick = () => {
        editTask(taskId);
        taskModal.classList.remove('show');
    };
    
    // Delete button
    document.getElementById('deleteTaskBtn').onclick = () => {
        deleteTask(taskId);
        taskModal.classList.remove('show');
    };
    
    taskModal.classList.add('show');
}

// Edit task - populate form with task data
function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;
    
    editingTaskId = taskId;
    
    document.getElementById('taskName').value = task.name;
    document.getElementById('taskStatus').value = task.status;
    document.getElementById('taskColour').value = task.colour || 'default';
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskUrl').value = task.url || '';
    
    if (document.getElementById('taskOwner')) {
        document.getElementById('taskOwner').value = task.owner || '';
    }
    
    if (task.deadline) {
        hasDeadlineCheckbox.checked = true;
        deadlineInputs.forEach(input => input.style.display = 'flex');
        
        const date = new Date(task.deadline);
        document.getElementById('deadlineDate').value = date.toISOString().split('T')[0];
        document.getElementById('deadlineTime').value = date.toTimeString().substring(0, 5);
    }
    
    cancelEditBtn.style.display = 'inline-block';
    document.querySelector('.task-form h2').textContent = 'Edit Task';
    
    // Scroll to form
    document.querySelector('.task-form').scrollIntoView({ behavior: 'smooth' });
}

// Drag and drop functionality
function setupDragAndDrop() {
    const taskItems = document.querySelectorAll('.task-item');
    
    taskItems.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragend', handleDragEnd);
    });
}

let draggedElement = null;

function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    draggedPriority = this.dataset.priority;
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (draggedElement !== this) {
        // Prevent moving between different priority groups
        if (draggedElement.dataset.priority !== this.dataset.priority) {
            alert('Tasks can only be moved within the same priority group.');
            return false;
        }
        // Get all visible task items
        const allItems = Array.from(document.querySelectorAll('.task-item'));
        const draggedIndex = allItems.indexOf(draggedElement);
        const targetIndex = allItems.indexOf(this);
        
        if (draggedIndex < targetIndex) {
            this.parentNode.insertBefore(draggedElement, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedElement, this);
        }
        
        // Update task order
        updateTaskOrder();
    }
    
    return false;
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    draggedPriority = null;
}

// Update task order after drag and drop
async function updateTaskOrder() {
    const taskItems = document.querySelectorAll('.task-item');
    // Only send the order for the priority group that was dragged
    let taskIds = Array.from(taskItems).map(item => item.dataset.taskId);
    if (draggedPriority) {
        taskIds = Array.from(taskItems).filter(item => item.dataset.priority === draggedPriority).map(item => item.dataset.taskId);
    }
    
    try {
        const response = await fetch('/api/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: taskIds })
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadTasks();
        } else {
            showError('Failed to reorder tasks: ' + data.error);
        }
    } catch (error) {
        showError('Error reordering tasks: ' + error.message);
    }
}

// Utility functions
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showError(message) {
    alert(message);
    console.error(message);
}
