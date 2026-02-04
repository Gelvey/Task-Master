const taskList = document.getElementById("task-list");
const taskForm = document.getElementById("task-form");
const taskName = document.getElementById("task-name");
const taskDeadline = document.getElementById("task-deadline");
const taskStatus = document.getElementById("task-status");
const taskOwner = document.getElementById("task-owner");
const configText = document.getElementById("runtime-config");

const renderTask = (task) => {
  const item = document.createElement("li");
  item.className = "task-item";
  const title = document.createElement("h3");
  title.textContent = task.name;

  const status = document.createElement("p");
  status.textContent = `Status: ${task.status || "To Do"}`;

  const owner = document.createElement("p");
  owner.textContent = `Owner: ${task.owner || ""}`;

  const deadline = document.createElement("p");
  deadline.textContent = `Deadline: ${task.deadline || "None"}`;

  item.append(title, status, owner, deadline);
  taskList.appendChild(item);
};

const loadTasks = async () => {
  const response = await fetch("/api/tasks");
  const tasks = await response.json();
  taskList.innerHTML = "";
  tasks.forEach(renderTask);
};

const addTask = async (event) => {
  event.preventDefault();
  const payload = {
    name: taskName.value.trim(),
    deadline: taskDeadline.value.trim(),
    status: taskStatus.value,
    owner: taskOwner.value.trim(),
  };

  if (!payload.name) {
    alert("Task name is required.");
    return;
  }

  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    alert(error.error || "Unable to add task.");
    return;
  }

  taskForm.reset();
  await loadTasks();
};

const loadRuntimeConfig = async () => {
  try {
    const response = await fetch("/runtime-config.json");
    if (!response.ok) {
      if (configText) {
        configText.textContent = "Configuration not available.";
      }
      return;
    }
    const data = await response.json();
    if (configText) {
      configText.textContent = JSON.stringify(data, null, 2);
    }
  } catch (error) {
    console.warn("Runtime config not available.");
    if (configText) {
      configText.textContent = "Configuration not available.";
    }
  }
};

taskForm.addEventListener("submit", addTask);

loadTasks();
loadRuntimeConfig();
