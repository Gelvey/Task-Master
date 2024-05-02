import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import logging
import firebase_admin
from firebase_admin import credentials, db
import configparser

# Initialize Firebase app with credentials
cred = credentials.Certificate('credentials.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://login-2-600a7-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Configure logging
logging.basicConfig(filename='task_manager.log', level=logging.INFO)

def read_username_from_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        username = config.get('user', 'username')
        return username
    except configparser.Error:
        return ''

def write_username_to_config(username):
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Create the [user] section if it doesn't exist
    if not config.has_section('user'):
        config.add_section('user')

    config.set('user', 'username', username)
    with open('config.ini', 'w') as config_file:
        config.write(config_file)

class Task:
    def __init__(self, name, deadline, status):
        self.name = name
        self.deadline = deadline
        self.status = status
        
class LoginScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Task-Master - Login")
        self.geometry("300x150")

        self.username = read_username_from_config()
        if self.username:
            self.open_task_manager()
        else:
            self.setup_login_ui()

    def setup_login_ui(self):
        self.username_label = ttk.Label(self, text="Username:")
        self.username_label.pack(pady=10)

        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(pady=5)

        self.login_button = ttk.Button(self, text="Login", command=self.login)
        self.login_button.pack(pady=10)

    def login(self):
        username = self.username_entry.get()
        if username:
            write_username_to_config(username)
            self.open_task_manager()
        else:
            messagebox.showerror("Error", "Please enter a username.")

    def open_task_manager(self):
        self.destroy()
        root = tk.Tk()
        app = TaskManager(root, self.username)
        root.mainloop()

class TaskManager:
    def __init__(self, master, username):
        self.master = master
        self.master.title("Task-Master")
        self.username = username
        self.tasks = self.load_tasks_from_database()
        self.setup_ui()

    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.master, padding=(10, 10))
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Create task entry widgets
        task_frame = ttk.LabelFrame(main_frame, text="Add Task")
        task_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.task_label = ttk.Label(task_frame, text="Task:")
        self.task_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.task_entry = ttk.Entry(task_frame, width=30)
        self.task_entry.grid(row=0, column=1, padx=5, pady=5)

        self.deadline_label = ttk.Label(task_frame, text="Deadline Date:")
        self.deadline_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.deadline_entry_date = DateEntry(task_frame, width=20, date_pattern='yyyy-mm-dd')
        self.deadline_entry_date.grid(row=0, column=3, padx=5, pady=5)
        self.deadline_entry_date.set_date(datetime.today())  # Set initial date to today

        self.deadline_time_label = ttk.Label(task_frame, text="Deadline Time:")
        self.deadline_time_label.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.deadline_entry_time = ttk.Combobox(task_frame, width=10)
        self.deadline_entry_time.grid(row=0, column=5, padx=5, pady=5)
        self.populate_time_combobox()  # Populate time combobox with future times

        self.status_label = ttk.Label(task_frame, text="Status:")
        self.status_label.grid(row=0, column=6, padx=5, pady=5, sticky="w")

        self.status_combobox = ttk.Combobox(task_frame, values=["To Do", "In Progress", "Complete"])
        self.status_combobox.grid(row=0, column=7, padx=5, pady=5)

        self.add_button = ttk.Button(task_frame, text="Add Task", command=self.add_task)
        self.add_button.grid(row=0, column=8, padx=5, pady=5)

        # Create task treeview
        self.task_tree = ttk.Treeview(main_frame, columns=("Task", "Deadline", "Status"), show="headings")
        self.task_tree.heading("Task", text="Task")
        self.task_tree.heading("Deadline", text="Deadline")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Add tooltips
        self.create_tooltip(self.task_entry, "Enter task name")
        self.create_tooltip(self.deadline_entry_date, "Select deadline date")
        self.create_tooltip(self.deadline_entry_time, "Select deadline time")
        self.create_tooltip(self.status_combobox, "Select task status")

        # Create button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        self.complete_button = ttk.Button(button_frame, text="Mark Complete", command=self.mark_complete)
        self.complete_button.grid(row=0, column=0, padx=5, pady=5)

        self.in_progress_button = ttk.Button(button_frame, text="Mark In Progress", command=self.mark_in_progress)
        self.in_progress_button.grid(row=0, column=1, padx=5, pady=5)

        self.to_do_button = ttk.Button(button_frame, text="Mark To Do", command=self.mark_to_do)
        self.to_do_button.grid(row=0, column=2, padx=5, pady=5)

        self.delete_button = ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected)
        self.delete_button.grid(row=0, column=3, padx=5, pady=5)

        # Bind right-click event to the task treeview
        self.task_tree.bind("<Button-3>", self.right_click_menu)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Load tasks into the treeview
        self.update_task_tree()

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip = ToolTip(widget, text)
        widget.bind("<Enter>", lambda _: tooltip.showtip())
        widget.bind("<Leave>", lambda _: tooltip.hidetip())

    def populate_time_combobox(self):
        current_time = datetime.now().replace(second=0, microsecond=0)
        future_times = [current_time + timedelta(minutes=30 * i) for i in range(48)]  # Future times in half-hour intervals
        time_strings = [time.strftime('%H:%M') for time in future_times if time > current_time]
        self.deadline_entry_time['values'] = time_strings

    def add_task(self):
        task_name = self.task_entry.get()
        deadline_date = self.deadline_entry_date.get()
        deadline_time = self.deadline_entry_time.get()
        status = self.status_combobox.get()

        if task_name and deadline_date and deadline_time and status:
            deadline = f"{deadline_date} {deadline_time}"
            task = Task(task_name, deadline, status)
            self.tasks.append(task)
            self.save_tasks_to_database()  # Save tasks to the database
            self.update_task_tree()
            self.task_entry.delete(0, tk.END)
            self.deadline_entry_date.delete(0, tk.END)
            self.deadline_entry_time.delete(0, tk.END)
            self.populate_time_combobox()  # Update time combobox with future times
        else:
            messagebox.showwarning("Warning", "Please enter task, deadline, and select status.")

    def mark_complete(self):
        selected_item = self.task_tree.selection()
        if selected_item:
            item = self.task_tree.item(selected_item)
            task_name = item['values'][0]
            deadline = item['values'][1]

            # Change status to "Complete"
            for task in self.tasks:
                if task.name == task_name and task.deadline == deadline:
                    task.status = "Complete"
                    break

            self.save_tasks_to_database()  # Save updated tasks to the database
            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select a task to mark complete.")

    def mark_in_progress(self):
        selected_item = self.task_tree.selection()
        if selected_item:
            item = self.task_tree.item(selected_item)
            task_name = item['values'][0]
            deadline = item['values'][1]

            # Change status to "In Progress"
            for task in self.tasks:
                if task.name == task_name and task.deadline == deadline:
                    task.status = "In Progress"
                    break

            self.save_tasks_to_database()  # Save updated tasks to the database
            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select a task to mark in progress.")

    def mark_to_do(self):
        selected_item = self.task_tree.selection()
        if selected_item:
            item = self.task_tree.item(selected_item)
            task_name = item['values'][0]
            deadline = item['values'][1]

            # Change status to "To Do"
            for task in self.tasks:
                if task.name == task_name and task.deadline == deadline:
                    task.status = "To Do"
                    break

            self.save_tasks_to_database()  # Save updated tasks to the database
            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select a task to mark to do.")

    def delete_selected(self):
        selected_items = self.task_tree.selection()
        if selected_items:
            for item in selected_items:
                task_name = self.task_tree.item(item)['values'][0]
                deadline = self.task_tree.item(item)['values'][1]
                for task in self.tasks:
                    if task.name == task_name and task.deadline == deadline:
                        self.tasks.remove(task)
                        break
            self.save_tasks_to_database()  # Save updated tasks to the database
            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select tasks to delete.")

    def update_task_tree(self):
        self.task_tree.delete(*self.task_tree.get_children())
        for task in self.tasks:
            self.task_tree.insert("", tk.END, values=(task.name, task.deadline, task.status))

    def right_click_menu(self, event):
        # Select the item under the cursor
        item_id = self.task_tree.identify_row(event.y)
        if item_id:
            # Create a right-click menu
            menu = tk.Menu(self.master, tearoff=0)
            menu.add_command(label="Prioritize Task", command=lambda: self.prioritize_task(item_id))
            menu.post(event.x_root, event.y_root)

    def prioritize_task(self, item_id):
        # Get the task details from the item ID
        task_details = self.task_tree.item(item_id)['values']
        task_name = task_details[0]
        deadline = task_details[1]
        status = task_details[2]

        # Find the task object
        task = next((t for t in self.tasks if t.name == task_name and t.deadline == deadline and t.status == status), None)

        if task:
            # Remove the task from the list
            self.tasks.remove(task)

            # Insert the task at the beginning of the list
            self.tasks.insert(0, task)

            # Save updated tasks to the database
            self.save_tasks_to_database()

            # Update the task treeview
            self.update_task_tree()

    def load_tasks_from_database(self):
        # Fetch tasks from the user-specific directory
        tasks_ref = db.reference(f'users/{self.username}/tasks')
        tasks_data = tasks_ref.get()

        tasks = []
        if tasks_data:
            for task_id, task_data in tasks_data.items():
                name = task_data['name']
                deadline = task_data['deadline']
                status = task_data['status']
                task = Task(name, deadline, status)
                tasks.append(task)

        return tasks

    def save_tasks_to_database(self):
        # Save tasks to the user-specific directory
        tasks_ref = db.reference(f'users/{self.username}/tasks')
        tasks_data = {task.name: {'name': task.name, 'deadline': task.deadline, 'status': task.status} for task in self.tasks}
        tasks_ref.set(tasks_data)

        logging.info(f"Tasks saved to the database for user {self.username}")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

    def showtip(self):
        if not self.tooltip_window:
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry("+%d+%d" % (x, y))
            label = tk.Label(tw, text=self.text, justify='left', bg='yellow', relief='solid', borderwidth=1, font=("Helvetica", 10, "normal"))
            label.pack(ipadx=1)

    def hidetip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def main():
    login_screen = LoginScreen()
    login_screen.mainloop()

if __name__ == "__main__":
    main()
