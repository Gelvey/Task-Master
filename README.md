# Task-Master

## Overview
This Task Manager application allows users to manage their tasks by entering task details such as task name, deadline date and time, and status. Users can add tasks, mark them as complete or in progress, delete tasks, and prioritise them.

## Requirements
- Python 3.11.x 
- tkcalendar (a calendar widget for Tkinter)

## Installation
1. Ensure you have Python 3.11.x installed on your system.
2. Install tkcalendar by running `pip install tkcalendar` in your terminal.
3. Create a Firebase Realtime Database.

## Usage
1. Run the `task_manager.py` script using Python.
2. The main window of the Task Manager application will appear.
3. Enter the task details including task name, deadline date, deadline time, and status (To Do, In Progress, or Complete).
4. Click on the "Add Task" button to add the task to the list.
5. Tasks will be displayed in a treeview with columns for Task, Deadline, and Status.
6. Right-click on a task to access the context menu with options to prioritise the task.
7. Use the "Mark Complete" and "Mark In Progress" buttons to change the status of a task.
8. Use the "Delete Selected" button to delete selected tasks.

## Features
- Utilises Firebase Realtime Database
- Add tasks with deadline dates and times.
- Mark tasks as complete or in progress.
- Delete tasks.
- Prioritise tasks by right-clicking and selecting the "Prioritise Task" option.

## Notes
- Tasks are stored in memory and are not persisted between sessions.
- The application uses a graphical user interface (GUI) built with Tkinter.

## Author
Circuit & Gelvey
