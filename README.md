# Task-Master

Task-Master is a desktop application built with Python and Tkinter GUI toolkit. It allows users to manage their tasks efficiently by providing features like adding tasks with deadlines, marking tasks as complete, to do, or in progress, deleting tasks, and prioritizing important tasks.

## Features

- **User Authentication**: The application requires users to log in with a username, which is stored in a configuration file.
- **Task Management**: Users can add tasks by specifying the task name, deadline date and time, and status (To Do, In Progress, or Complete).
- **Task Treeview**: All tasks are displayed in a treeview with columns for Task, Deadline, and Status.
- **Task Status Manipulation**: Users can mark tasks as complete, in progress, or to-do using dedicated buttons.
- **Task Deletion**: Users can delete selected tasks from the treeview.
- **Task Prioritisation**: Task prioritisation is now stored in the cloud database, ensuring it saves over sessions and devices.
- **Edit Existing Tasks**: Added support for editing existing tasks intuitively.
- **Input Validation**: Input validation has been implemented to improve data integrity.
- **Error Handling**: Implemented error handling for database operations to provide a smoother user experience.
- **Improved User Interface**: Improving the user interface and user experience with features such as resizable window and better layout.
- **Code Refactoring**: Refactored the code to follow best practices, including separating concerns and using functions/methods for better maintainability.

## Requirements

- Python 3.11.x
- tkcalendar (a calendar widget for Tkinter)
- firebase_admin (Python Firebase Admin SDK)

## Installation

1. Ensure you have Python 3.11.x installed on your system.
2. Install the required Python packages by running the following command: `pip install tkcalendar firebase_admin`
3. Follow the instructions inside `credentials.json` file to set up the database.

## Usage

1. Run the `Task-Master.py` script using Python.
2. If this is your first time using the application, enter a username in the provided field and click the "Login" button.
3. The main window of the Task Manager application will appear.
4. Enter the task details, including the task name, deadline date, deadline time, and status (To Do or In Progress).
5. Click on the "Add Task" button to add the task to the list.
6. Tasks will be displayed in the treeview with columns for Task, Deadline, and Status.
7. Right-click on a task to access the context menu with the option to prioritise the task.
8. Use the "Mark Complete," "Mark In Progress," and "Mark To Do" buttons to change the status of a task.
9. Use the "Delete Selected" button to delete selected tasks.

## Notes

- The application uses a graphical user interface (GUI) built with Tkinter.
- Task data is stored in a Firebase Realtime Database, ensuring data persistence across devices and sessions.
- The application logs activity to a file named `task_manager.log` in the same directory as the script.
- Tooltips are provided for input fields to guide users on their usage.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- The Firebase Realtime Database integration utilizes the Firebase Admin SDK for Python.
- The tkcalendar package provides the calendar widget used for selecting deadline dates.

## Authors

- Circuit
- Gelvey
