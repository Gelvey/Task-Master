// Tasks page JavaScript

let tasks = [];
let currentFilter = 'all';
let editingTaskId = null;
let currentSubtasks = []; // Track subtasks in the form

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

function normalizeSubtaskList(subtasks) {
    if (!Array.isArray(subtasks)) {
        return [];
    }

    const usedIds = new Set();
    let nextId = 1;

    const normalized = subtasks.map((raw) => {
        const subtask = (raw && typeof raw === 'object') ? { ...raw } : { name: String(raw ?? '') };

        let id = subtask.id;
        if (typeof id === 'string' && /^\d+$/.test(id)) {
            id = parseInt(id, 10);
        }
        if (!Number.isInteger(id) || id <= 0 || usedIds.has(id)) {
            while (usedIds.has(nextId)) {
                nextId += 1;
            }
            id = nextId;
        }

        usedIds.add(id);
        nextId = Math.max(nextId, id + 1);

        return {
            id,
            name: (subtask.name || '').trim(),
            description: (subtask.description || '').trim(),
            url: (subtask.url || '').trim(),
            completed: Boolean(subtask.completed)
        };
    });

    return normalized.sort((a, b) => a.id - b.id);
}

function getNextSubtaskId(subtasks) {
    const ids = normalizeSubtaskList(subtasks).map(st => st.id || 0);
    return (ids.length ? Math.max(...ids) : 0) + 1;
}

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    loadTasks();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Task form submission
    taskForm.addEventListener('submit', handleTaskSubmit);

    // Deadline checkbox toggle
    hasDeadlineCheckbox.addEventListener('change', function () {
        deadlineInputs.forEach(input => {
            input.style.display = this.checked ? 'flex' : 'none';
        });
    });

    // Subtask management
    document.getElementById('addSubtaskBtn').addEventListener('click', addSubtaskToForm);
    document.getElementById('newSubtask').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSubtaskToForm();
        }
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function () {
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
        currentSubtasks = [];
        renderSubtasksList();
        cancelEditBtn.style.display = 'none';
        document.querySelector('.task-form h2').textContent = 'Add New Task';
    });
}

// Subtask management functions
function addSubtaskToForm() {
    const input = document.getElementById('newSubtask');
    const descriptionInput = document.getElementById('newSubtaskDescription');
    const urlInput = document.getElementById('newSubtaskUrl');
    const subtaskName = input.value.trim();
    if (subtaskName) {
        currentSubtasks = normalizeSubtaskList(currentSubtasks);
        currentSubtasks.push({
            id: getNextSubtaskId(currentSubtasks),
            name: subtaskName,
            description: descriptionInput ? descriptionInput.value.trim() : '',
            url: urlInput ? urlInput.value.trim() : '',
            completed: false
        });
        input.value = '';
        if (descriptionInput) descriptionInput.value = '';
        if (urlInput) urlInput.value = '';
        renderSubtasksList();
    }
}

function renderSubtasksList() {
    currentSubtasks = normalizeSubtaskList(currentSubtasks);
    const container = document.getElementById('subtasksList');
    if (currentSubtasks.length === 0) {
        container.innerHTML = '<p class="empty-subtasks">No sub-tasks added yet.</p>';
        return;
    }

    let html = '<ul class="subtasks-form-list">';
    currentSubtasks.forEach((st, idx) => {
        const checkbox = st.completed ? '☑' : '☐';
        const hasExtras = Boolean(st.description || st.url);
        html += `
            <li>
                <span class="subtask-checkbox" onclick="toggleSubtaskInForm(${idx})">${checkbox}</span>
                <span class="subtask-name">#${st.id} ${escapeHtml(st.name)}</span>
                ${hasExtras ? '<span class="subtask-extra"> • details</span>' : ''}
                <button type="button" class="btn btn-sm btn-secondary" onclick="editSubtaskInForm(${idx})">Edit</button>
                <button type="button" class="btn-subtask-delete" onclick="deleteSubtaskFromForm(${idx})">✕</button>
            </li>
        `;
    });
    html += '</ul>';
    container.innerHTML = html;
}

function toggleSubtaskInForm(index) {
    currentSubtasks = normalizeSubtaskList(currentSubtasks);
    currentSubtasks[index].completed = !currentSubtasks[index].completed;
    renderSubtasksList();
}

function deleteSubtaskFromForm(index) {
    currentSubtasks = normalizeSubtaskList(currentSubtasks);
    currentSubtasks.splice(index, 1);
    renderSubtasksList();
}

function editSubtaskInForm(index) {
    currentSubtasks = normalizeSubtaskList(currentSubtasks);
    const subtask = currentSubtasks[index];
    if (!subtask) return;

    const updatedName = prompt(`Edit name for sub-task #${subtask.id}:`, subtask.name || '');
    if (updatedName === null) return;
    const name = updatedName.trim();
    if (!name) {
        alert('Sub-task name is required.');
        return;
    }

    const updatedDescription = prompt(`Edit description for sub-task #${subtask.id}:`, subtask.description || '');
    if (updatedDescription === null) return;

    const updatedUrl = prompt(`Edit URL for sub-task #${subtask.id}:`, subtask.url || '');
    if (updatedUrl === null) return;

    currentSubtasks[index] = {
        ...subtask,
        name,
        description: updatedDescription.trim(),
        url: updatedUrl.trim(),
    };
    renderSubtasksList();
}

// Load tasks from API
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();

        if (data.success) {
            tasks = data.tasks.map(task => ({
                ...task,
                subtasks: normalizeSubtaskList(task.subtasks || [])
            }));
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
    // Clean up any active drag state before rendering
    DragManager.cleanup();

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

    // Group tasks by priority
    const priorityGroups = {};
    filteredTasks.forEach(task => {
        const priority = task.colour || 'default';
        if (!priorityGroups[priority]) {
            priorityGroups[priority] = [];
        }
        priorityGroups[priority].push(task);
    });

    // Render priority sections in order
    const priorityOrder = ['Important', 'Moderately Important', 'Not Important', 'default'];
    let html = '';

    priorityOrder.forEach(priority => {
        if (priorityGroups[priority] && priorityGroups[priority].length > 0) {
            const priorityLabel = priority === 'default' ? 'Other' : priority;
            html += `
                <div class="priority-section" data-priority="${priority}">
                    <h3 class="priority-header">${priorityLabel}</h3>
                    <div class="priority-tasks">
                        ${priorityGroups[priority].map(task => createTaskElement(task)).join('')}
                    </div>
                </div>
            `;
        }
    });

    taskList.innerHTML = html;

    // Setup drag and drop with event delegation
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

    // Calculate progress if subtasks exist
    let progressHtml = '';
    if (task.subtasks && task.subtasks.length > 0) {
        const completed = task.subtasks.filter(st => st.completed).length;
        const total = task.subtasks.length;
        const percentage = Math.round((completed / total) * 100);
        progressHtml = `
            <div class="task-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: ${percentage}%"></div>
                </div>
                <span class="progress-text">${completed}/${total} sub-tasks (${percentage}%)</span>
            </div>
        `;
    }

    return `
        <div class="task-item ${priorityClass}" data-task-id="${task.id}" data-priority="${task.colour}" draggable="true">
            <div class="task-info">
                <div class="task-name">${escapeHtml(task.name)}</div>
                ${progressHtml}
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
        deadline: deadline,
        subtasks: normalizeSubtaskList(currentSubtasks)
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
            currentSubtasks = [];
            renderSubtasksList();
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

    // Render subtasks if available
    const subtasksContainer = document.getElementById('modalSubtasks');
    if (task.subtasks && task.subtasks.length > 0) {
        let subtasksHtml = '<ul class="subtasks-list">';
        task.subtasks.forEach((st, idx) => {
            const checkbox = st.completed ? '☑' : '☐';
            const subtaskId = st.id || (idx + 1);
            subtasksHtml += `<li>${checkbox} #${subtaskId} ${escapeHtml(st.name)}</li>`;
            if (st.description) {
                subtasksHtml += `<li class="subtask-meta">📝 ${escapeHtml(st.description)}</li>`;
            }
            if (st.url) {
                subtasksHtml += `<li class="subtask-meta">🔗 <a href="${escapeHtml(st.url)}" target="_blank">${escapeHtml(st.url)}</a></li>`;
            }
        });
        subtasksHtml += '</ul>';
        subtasksContainer.innerHTML = subtasksHtml;
        subtasksContainer.style.display = 'block';
    } else {
        subtasksContainer.style.display = 'none';
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

    // Load subtasks (use deep copy for true independence)
    currentSubtasks = normalizeSubtaskList((task.subtasks || []).map(st => JSON.parse(JSON.stringify(st))));
    renderSubtasksList();

    cancelEditBtn.style.display = 'inline-block';
    document.querySelector('.task-form h2').textContent = 'Edit Task';

    // Scroll to form
    document.querySelector('.task-form').scrollIntoView({ behavior: 'smooth' });
}

// Drag and Drop Manager - Encapsulated state management
const DragManager = (() => {
    let draggedElement = null;
    let draggedPriority = null;
    let sourceSection = null;
    let placeholder = null;
    let dragOverTask = null;

    return {
        start(element, priority, section) {
            draggedElement = element;
            draggedPriority = priority;
            sourceSection = section;

            element.classList.add('dragging');
            section.classList.add('drag-active');

            // Lock other sections
            document.querySelectorAll('.priority-section').forEach(sec => {
                if (sec !== section) {
                    sec.classList.add('drag-locked');
                }
            });

            // Create placeholder
            placeholder = document.createElement('div');
            placeholder.className = 'drop-placeholder';
            placeholder.style.height = element.offsetHeight + 'px';
        },

        getDraggedElement() {
            return draggedElement;
        },

        getPriority() {
            return draggedPriority;
        },

        getSection() {
            return sourceSection;
        },

        updateDropTarget(target) {
            if (dragOverTask && dragOverTask !== target) {
                dragOverTask.classList.remove('drop-target');
            }
            dragOverTask = target;
            if (target) {
                target.classList.add('drop-target');
            }
        },

        showPlaceholder(beforeElement, container) {
            if (placeholder && placeholder.parentNode !== container) {
                if (beforeElement) {
                    container.insertBefore(placeholder, beforeElement);
                } else {
                    container.appendChild(placeholder);
                }
            }
        },

        removePlaceholder() {
            if (placeholder && placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
            }
        },

        cleanup() {
            if (draggedElement) {
                draggedElement.classList.remove('dragging');
            }
            if (sourceSection) {
                sourceSection.classList.remove('drag-active');
            }
            if (dragOverTask) {
                dragOverTask.classList.remove('drop-target');
            }

            document.querySelectorAll('.priority-section').forEach(sec => {
                sec.classList.remove('drag-locked');
            });

            this.removePlaceholder();

            draggedElement = null;
            draggedPriority = null;
            sourceSection = null;
            dragOverTask = null;
            placeholder = null;
        },

        isActive() {
            return draggedElement !== null;
        }
    };
})();

// Drag and drop functionality with event delegation
let dragAndDropInitialized = false;

function setupDragAndDrop() {
    if (dragAndDropInitialized) return;

    // Use event delegation on task list
    taskList.addEventListener('dragstart', handleDragStart);
    taskList.addEventListener('dragover', handleDragOver);
    taskList.addEventListener('drop', handleDrop);
    taskList.addEventListener('dragend', handleDragEnd);
    taskList.addEventListener('dragleave', handleDragLeave);

    // Clean up on window blur (tab switching)
    window.addEventListener('blur', () => {
        if (DragManager.isActive()) {
            DragManager.cleanup();
        }
    });

    dragAndDropInitialized = true;
}

function handleDragStart(e) {
    const taskItem = e.target.closest('.task-item');
    if (!taskItem) return;

    const section = taskItem.closest('.priority-section');
    const priority = section.dataset.priority;

    DragManager.start(taskItem, priority, section);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', taskItem.innerHTML);
}

function handleDragOver(e) {
    if (!DragManager.isActive()) return;

    e.preventDefault();

    const taskItem = e.target.closest('.task-item');
    const section = e.target.closest('.priority-section');
    const draggedElement = DragManager.getDraggedElement();

    // Check if we're in the correct section
    if (!section || section !== DragManager.getSection()) {
        e.dataTransfer.dropEffect = 'none';
        DragManager.updateDropTarget(null);
        DragManager.removePlaceholder();
        return;
    }

    e.dataTransfer.dropEffect = 'move';

    // If over a task item (not the dragged one)
    if (taskItem && taskItem !== draggedElement) {
        DragManager.updateDropTarget(taskItem);

        const container = taskItem.parentNode;
        const allItems = Array.from(container.querySelectorAll('.task-item:not(.dragging)'));
        const targetIndex = allItems.indexOf(taskItem);

        // Determine if we should insert before or after
        const rect = taskItem.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;

        if (e.clientY < midpoint) {
            DragManager.showPlaceholder(taskItem, container);
        } else {
            DragManager.showPlaceholder(taskItem.nextSibling, container);
        }
    } else if (section && !taskItem) {
        // Over the section but not over a specific task
        const container = section.querySelector('.priority-tasks');
        if (container) {
            DragManager.updateDropTarget(null);
            DragManager.showPlaceholder(null, container);
        }
    }

    return false;
}

function handleDrop(e) {
    e.stopPropagation();
    e.preventDefault();

    if (!DragManager.isActive()) return;

    const taskItem = e.target.closest('.task-item');
    const section = e.target.closest('.priority-section');
    const draggedElement = DragManager.getDraggedElement();

    // Only allow drops within the same section
    if (!section || section !== DragManager.getSection()) {
        DragManager.cleanup();
        return false;
    }

    const container = section.querySelector('.priority-tasks');

    if (taskItem && taskItem !== draggedElement) {
        // Determine insertion point
        const rect = taskItem.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;

        if (e.clientY < midpoint) {
            container.insertBefore(draggedElement, taskItem);
        } else {
            container.insertBefore(draggedElement, taskItem.nextSibling);
        }
    } else if (!taskItem) {
        // Dropped in empty space within section
        container.appendChild(draggedElement);
    }

    // Update task order
    updateTaskOrder(DragManager.getPriority());

    DragManager.cleanup();
    return false;
}

function handleDragEnd(e) {
    DragManager.cleanup();
}

function handleDragLeave(e) {
    // Only handle if we're leaving the task list entirely
    if (!e.relatedTarget || !taskList.contains(e.relatedTarget)) {
        if (DragManager.isActive()) {
            DragManager.removePlaceholder();
        }
    }
}

// Update task order after drag and drop
async function updateTaskOrder(priority) {
    const section = document.querySelector(`.priority-section[data-priority="${priority}"]`);
    if (!section) return;

    const taskItems = section.querySelectorAll('.task-item');
    const taskIds = Array.from(taskItems).map(item => item.dataset.taskId);

    try {
        const response = await fetch('/api/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: taskIds })
        });

        const data = await response.json();

        if (data.success) {
            // Refresh tasks data without full re-render
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
