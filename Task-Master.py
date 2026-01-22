import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import logging
import time
import firebase_admin
from firebase_admin import credentials, db
import json
import configparser
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Parse owners from environment variable OWNERS (space-separated), optional
OWNERS = os.getenv("OWNERS", "").split()

# Configure logging early so initialization messages are recorded
logging.basicConfig(filename="Task-Master.log", level=logging.INFO, filemode="a")

# Firebase configuration with local fallback
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
USE_FIREBASE = False
try:
    cred_path = "credentials.json"
    if FIREBASE_DATABASE_URL and os.path.isfile(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
        USE_FIREBASE = True
        logging.info("Initialized Firebase backend")
    else:
        logging.warning("Firebase not configured or credentials.json missing; using local storage.")
except Exception as e:
    logging.error(f"Failed to initialize Firebase: {e}")
    USE_FIREBASE = False


def read_username_from_config():
    config = configparser.ConfigParser()
    config_file = "config.ini"
    if os.path.isfile(config_file):
        config.read(config_file)
        try:
            username = config.get("user", "username")
            return username
        except configparser.Error:
            return ""
    else:
        return ""


def write_username_to_config(username):
    config = configparser.ConfigParser()
    config_file = "config.ini"
    config.read(config_file)

    # Create the [user] section if it doesn't exist
    if not config.has_section("user"):
        config.add_section("user")

    config.set("user", "username", username)
    with open(config_file, "w") as file:
        config.write(file)

def validate_url(url):
    """Validate URL format"""
    if not url:
        return True  # Empty URL is valid

    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(url_pattern.match(url))

class Task:
    def __init__(
        self,
        name,
        deadline=None,
        status="To Do",
        order=0,
        description="",
        url="",
        owner="",
        colour="default",
    ):
        self.name = name
        self.deadline = deadline  # Can be None
        self.status = status
        self.order = order
        self.description = description
        self.url = url
        self.owner = owner
        self.colour = colour


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
        username = (
            self.username_entry.get().strip()
        )  # Remove leading/trailing whitespaces
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

        # Define colour options before loading tasks
        # Priority options (internal name "colour" retained for minimal changes)
        self.colour_options = {
            "default": {"bg": "white", "fg": "black"},
            "Important": {"bg": "#ffcdd2", "fg": "black"},  # Light red
            "Moderately Important": {"bg": "#fff9c4", "fg": "black"},  # Light yellow
            "Not Important": {"bg": "#c8e6c9", "fg": "black"},  # Light green
            # removed Personal & Work as requested
        }

        # Drag-and-drop tracking data (Treeview created in UI setup)
        self.drag_data = {"item": None, "initial_index": None}

        self.tasks = self.load_tasks_from_database()

        # Make the window dynamically resizable
        self.master.resizable(True, True)

        # Configure grid weights for dynamic resizing
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=0)  # Task frame doesn't expand
        self.master.grid_rowconfigure(1, weight=1)  # Tree view expands

        self.setup_ui()
        self.start_auto_refresh()

    def populate_time_combobox(self):
        """Populate the time combobox with 30-minute intervals"""
        time_strings = [
            "00:00",
            "00:30",
            "01:00",
            "01:30",
            "02:00",
            "02:30",
            "03:00",
            "03:30",
            "04:00",
            "04:30",
            "05:00",
            "05:30",
            "06:00",
            "06:30",
            "07:00",
            "07:30",
            "08:00",
            "08:30",
            "09:00",
            "09:30",
            "10:00",
            "10:30",
            "11:00",
            "11:30",
            "12:00",
            "12:30",
            "13:00",
            "13:30",
            "14:00",
            "14:30",
            "15:00",
            "15:30",
            "16:00",
            "16:30",
            "17:00",
            "17:30",
            "18:00",
            "18:30",
            "19:00",
            "19:30",
            "20:00",
            "20:30",
            "21:00",
            "21:30",
            "22:00",
            "22:30",
            "23:00",
            "23:30",
        ]
        self.deadline_entry_time["values"] = time_strings
        self.deadline_entry_time.set("")  # Set empty default value

    def load_tasks_from_database(self):
        """
        Load tasks from Firebase database with proper error handling for missing fields
        """
        tasks = []
        tasks_data = None

        if USE_FIREBASE:
            try:
                tasks_ref = db.reference(f"users/{self.username}/tasks")
                tasks_data = tasks_ref.get()
            except Exception as e:
                logging.error(f"Failed to load tasks from Firebase: {e}")
                tasks_data = None
        else:
            # Local JSON fallback
            local_file = f"tasks_{self.username}.json"
            if os.path.isfile(local_file):
                try:
                    with open(local_file, "r", encoding="utf-8") as f:
                        tasks_data = json.load(f)
                except Exception as e:
                    logging.error(f"Failed to read local tasks file: {e}")
                    tasks_data = None

        if tasks_data:
            for task_id, task_data in tasks_data.items():
                task = Task(
                    name=task_data.get("name", task_id),
                    deadline=task_data.get("deadline"),
                    status=task_data.get("status", "To Do"),
                    order=int(task_data.get("order", 0)),
                    description=task_data.get("description", ""),
                    url=task_data.get("url", ""),
                    owner=task_data.get("owner", ""),
                    colour=task_data.get("colour", "default"),
                )
                tasks.append(task)

        # Sort tasks by order if present
        tasks.sort(key=lambda x: x.order)
        return tasks

    def save_tasks_to_database(self, task_to_update=None):
        """
        Save tasks to Firebase or local JSON. If task_to_update is provided, update only that task's entry.
        This ensures the URL/description saved from the description window is persisted immediately.
        """

        def make_task_data(task):
            return {
                "name": task.name,
                "deadline": task.deadline if hasattr(task, "deadline") else None,
                "status": task.status if hasattr(task, "status") else "To Do",
                "order": task.order if hasattr(task, "order") else 0,
                "description": getattr(task, "description", ""),
                "url": getattr(task, "url", ""),
                "colour": getattr(task, "colour", "default"),
                "owner": getattr(task, "owner", ""),
            }

        if task_to_update is not None:
            # Update single task entry
            task_data = make_task_data(task_to_update)
            if USE_FIREBASE:
                try:
                    task_ref = db.reference(f"users/{self.username}/tasks/{task_to_update.name}")
                    task_ref.update(task_data)
                    logging.info(f"Updated task '{task_to_update.name}' in Firebase for user {self.username}")
                except Exception as e:
                    logging.error(f"Failed to update task in Firebase: {e}")
                    raise
            else:
                local_file = f"tasks_{self.username}.json"
                try:
                    tasks_data = {}
                    if os.path.isfile(local_file):
                        with open(local_file, "r", encoding="utf-8") as f:
                            tasks_data = json.load(f) or {}
                    tasks_data[task_to_update.name] = task_data
                    with open(local_file, "w", encoding="utf-8") as f:
                        json.dump(tasks_data, f, indent=2)
                    logging.info(f"Updated task '{task_to_update.name}' locally for user {self.username} to {local_file}")
                except Exception as e:
                    logging.error(f"Failed to update local tasks file: {e}")
                    raise
            return

        # Otherwise save full list (existing behavior)
        tasks_data = {}
        for task in self.tasks:
            tasks_data[task.name] = make_task_data(task)

        if USE_FIREBASE:
            try:
                tasks_ref = db.reference(f"users/{self.username}/tasks")
                tasks_ref.set(tasks_data)
                logging.info(f"Tasks saved to Firebase for user {self.username}")
            except Exception as e:
                logging.error(f"Failed to save tasks to Firebase: {e}")
                raise
        else:
            # Write to local JSON file as fallback
            local_file = f"tasks_{self.username}.json"
            try:
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(tasks_data, f, indent=2)
                logging.info(f"Tasks saved locally for user {self.username} to {local_file}")
            except Exception as e:
                logging.error(f"Failed to save local tasks file: {e}")
                raise

    def clear_task_entry(self):
        self.task_entry.delete(0, tk.END)
        self.deadline_var.set(False)
        self.toggle_deadline_entries()
        self.deadline_entry_date.set_date(datetime.today())
        self.deadline_entry_time.set("")
        self.status_combobox.set("")
        self.colour_combobox.set("default")
        # clear owner selection
        try:
            self.owner_var.set("")
        except Exception:
            pass

    def on_click(self, event):
        """Handle mouse click on task tree"""
        item = self.task_tree.identify_row(event.y)
        if item:
            # Store the clicked item and its index
            self.drag_data["item"] = item
            self.drag_data["initial_index"] = self.task_tree.index(item)

    def on_drag(self, event):
        """Handle drag operation"""
        if self.drag_data["item"]:
            # Get the item under current mouse position
            target = self.task_tree.identify_row(event.y)
            if target:
                # Move the item to new position
                self.task_tree.move(
                    self.drag_data["item"], "", self.task_tree.index(target)
                )

    def on_drop(self, event):
        """Handle drop operation"""
        if self.drag_data["item"]:
            # Get final position
            final_index = self.task_tree.index(self.drag_data["item"])

            # Update task orders in the list
            if final_index != self.drag_data["initial_index"]:
                task_name = self.task_tree.item(self.drag_data["item"])["values"][0]
                moved_task = next((t for t in self.tasks if t.name == task_name), None)

                if moved_task:
                    # Remove task from current position
                    self.tasks.remove(moved_task)
                    # Insert at new position
                    self.tasks.insert(final_index, moved_task)
                    # Update all task orders
                    for i, task in enumerate(self.tasks):
                        task.order = i

                    # Save to database
                    self.save_tasks_to_database()

            # Reset drag data
            self.drag_data = {"item": None, "initial_index": None}

    def show_context_menu(self, event):
        """Show context menu on right click"""
        # Select the item under cursor
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)

            # Create context menu
            menu = tk.Menu(self.master, tearoff=0)
            menu.add_command(
                label="View/Edit Description",
                command=lambda: self.show_task_details(event),
            )
            menu.add_command(label="Bump to Top", command=lambda: self.bump_task(item))
            menu.add_command(
                label="Delete Task", command=lambda: self.delete_task(item)
            )

            # Display menu at mouse position
            menu.post(event.x_root, event.y_root)

    def bump_task(self, item):
        """Move selected task to the top of the list"""
        task_name = self.task_tree.item(item)["values"][0]
        task = next((t for t in self.tasks if t.name == task_name), None)

        if task:
            # Remove task from current position
            self.tasks.remove(task)
            # Insert at beginning
            self.tasks.insert(0, task)
            # Update all task orders
            for i, t in enumerate(self.tasks):
                t.order = i

            # Save to database and update display
            self.save_tasks_to_database()
            self.update_task_tree()

    def delete_task(self, item):
        """Delete selected task"""
        if messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this task?"
        ):
            task_name = self.task_tree.item(item)["values"][0]
            task = next((t for t in self.tasks if t.name == task_name), None)

            if task:
                self.tasks.remove(task)
                # Update remaining task orders
                for i, t in enumerate(self.tasks):
                    t.order = i

                # Save to database and update display
                self.save_tasks_to_database()
                self.update_task_tree()

    def add_task(self):
        if self.validate_input():
            task_name = self.task_entry.get().strip()
            deadline = None
            if self.deadline_var.get():
                deadline_date = self.deadline_entry_date.get()
                deadline_time = self.deadline_entry_time.get()
                deadline = f"{deadline_date} {deadline_time}"

            status = self.status_combobox.get()
            colour = self.colour_combobox.get() or "default"
            owner = self.owner_var.get() or ""

            task = Task(
                name=task_name,
                deadline=deadline,
                status=status,
                colour=colour,
                owner=owner,
                order=len(self.tasks),
            )
            self.tasks.append(task)

            try:
                self.save_tasks_to_database()
                self.update_task_tree()
                self.clear_task_entry()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save tasks: {e}")

    def edit_task(self):
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a task to edit.")
            return

        selected_item = selected_items[0]  # Edit the first selected item
        item_values = self.task_tree.item(selected_item)["values"]
        task_name = item_values[0]
        task = next((t for t in self.tasks if t.name == task_name), None)

        if task:
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, task.name)

            if task.deadline:
                self.deadline_var.set(True)
                date_time = task.deadline.split()
                self.deadline_entry_date.set_date(
                    datetime.strptime(date_time[0], "%Y-%m-%d")
                )
                self.deadline_entry_time.set(date_time[1])
            else:
                self.deadline_var.set(False)

            self.toggle_deadline_entries()
            self.status_combobox.set(task.status)
            self.colour_combobox.set(task.colour or "default")
            # set owner into combobox
            try:
                self.owner_var.set(getattr(task, "owner", "") or "")
            except Exception:
                pass

            # Change the Add Task button to Save Changes
            self.add_button.configure(
                text="Save Changes", command=lambda: self.save_edited_task(task)
            )

    def save_edited_task(self, original_task):
        if self.validate_input():
            # Update the task with new values
            original_task.name = self.task_entry.get().strip()
            original_task.deadline = None
            if self.deadline_var.get():
                deadline_date = self.deadline_entry_date.get()
                deadline_time = self.deadline_entry_time.get()
                original_task.deadline = f"{deadline_date} {deadline_time}"

            original_task.status = self.status_combobox.get()
            original_task.colour = self.colour_combobox.get() or "default"
            original_task.owner = self.owner_var.get() or ""

            try:
                self.save_tasks_to_database()
                self.update_task_tree()
                self.clear_task_entry()
                # Reset the Add Task button
                self.add_button.configure(text="Add Task", command=self.add_task)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save tasks: {e}")

    def setup_ui(self):
        # Create main frame with grid configuration
        main_frame = ttk.Frame(self.master, padding=(10, 10))
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        # allow master window to be reasonably resizable
        try:
            self.master.minsize(700, 400)
        except Exception:
            pass

        # Improve treeview appearance (row height & fonts)
        style = ttk.Style()
        try:
            style.configure("Treeview", rowheight=24, font=("Arial", 11))
            style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        except Exception:
            pass

        # Create task entry widgets
        task_frame = ttk.LabelFrame(main_frame, text="Add/Edit Task")
        task_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Configure task_frame grid
        task_frame.grid_columnconfigure(1, weight=1)  # Make task entry expandable
        task_frame.grid_columnconfigure(3, weight=0)  # Deadline frame doesn't expand

        # Task name entry
        self.task_label = ttk.Label(task_frame, text="Task:")
        self.task_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.task_entry = ttk.Entry(task_frame, width=30)
        self.task_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Deadline checkbox and entries
        self.deadline_var = tk.BooleanVar()
        self.deadline_check = ttk.Checkbutton(
            task_frame,
            text="Set Deadline",
            variable=self.deadline_var,
            command=self.toggle_deadline_entries,
        )
        self.deadline_check.grid(row=0, column=2, padx=5, pady=5)

        self.deadline_frame = ttk.Frame(task_frame)
        self.deadline_frame.grid(row=0, column=3, columnspan=2, padx=5, pady=5)

        self.deadline_entry_date = DateEntry(
            self.deadline_frame, width=20, date_pattern="yyyy-mm-dd"
        )
        self.deadline_entry_time = ttk.Combobox(self.deadline_frame, width=10)
        self.populate_time_combobox()

        # Priority selection (label changed from "Colour" to "Priority")
        self.colour_label = ttk.Label(task_frame, text="Priority:")
        self.colour_label.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        self.colour_combobox = ttk.Combobox(
            task_frame, values=list(self.colour_options.keys())
        )
        self.colour_combobox.grid(row=0, column=6, padx=5, pady=5)
        self.colour_combobox.set("default")
        # make comboboxes wider so long names are readable
        try:
            self.colour_combobox.config(width=22)
        except Exception:
            pass

        # Status selection
        self.status_label = ttk.Label(task_frame, text="Status:")
        self.status_label.grid(row=0, column=7, padx=5, pady=5, sticky="w")
        self.status_combobox = ttk.Combobox(task_frame, values=["To Do", "In Progress"])
        self.status_combobox.grid(row=0, column=8, padx=5, pady=5)
        try:
            self.status_combobox.config(width=14)
            self.task_entry.config(width=48)
        except Exception:
            pass

        # Owner selection (added)
        self.owner_var = tk.StringVar(value="")
        owner_choices = [""] + OWNERS
        self.owner_label = ttk.Label(task_frame, text="Owner:")
        self.owner_label.grid(row=0, column=9, padx=5, pady=5, sticky="w")
        self.owner_combobox = ttk.Combobox(
            task_frame,
            textvariable=self.owner_var,
            values=owner_choices,
            state="readonly",
            width=14,
        )
        self.owner_combobox.grid(row=0, column=10, padx=5, pady=5)
        self.owner_combobox.set("")

        # Buttons
        button_frame = ttk.Frame(task_frame)
        # moved buttons to column 11 to accommodate Owner combobox
        button_frame.grid(row=0, column=11, columnspan=3, padx=5, pady=5, sticky="e")

        self.add_button = ttk.Button(
            button_frame, text="Add Task", command=self.add_task
        )
        self.add_button.pack(side=tk.LEFT, padx=2)

        self.edit_button = ttk.Button(
            button_frame, text="Edit Task", command=self.edit_task
        )
        self.edit_button.pack(side=tk.LEFT, padx=2)

        self.refresh_button = ttk.Button(
            button_frame, text="↻", width=3, command=self.refresh_tasks
        )
        self.refresh_button.pack(side=tk.LEFT, padx=2)

        # Create task treeview (column "Colour" renamed to "Priority" for UI) and include Owner
        self.task_tree = ttk.Treeview(
            main_frame,
            columns=("Task", "Deadline", "Status", "Owner", "Priority"),
            show="headings",
        )
        self.task_tree.heading("Task", text="Task")
        self.task_tree.heading("Deadline", text="Deadline")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.heading("Owner", text="Owner")
        self.task_tree.heading("Priority", text="Priority")
        self.task_tree.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Set sensible initial column widths and allow key columns to stretch
        self.task_tree.column("Task", anchor="w", width=340, stretch=True)
        self.task_tree.column("Deadline", anchor="center", width=160, stretch=True)
        self.task_tree.column("Status", anchor="center", width=120, stretch=False)
        self.task_tree.column("Owner", anchor="center", width=140, stretch=False)
        self.task_tree.column("Priority", anchor="center", width=220, stretch=True)

        # Recompute column widths proportionally on resize
        main_frame.bind("<Configure>", self._resize_columns)
        # small delayed call to ensure initial sizing after layout
        self.master.after(100, lambda: self._resize_columns())

        # Configure tag colours for the treeview
        for colour_name, colour_values in self.colour_options.items():
            self.task_tree.tag_configure(
                colour_name,
                background=colour_values["bg"],
                foreground=colour_values["fg"],
            )

        # Add scrollbar for treeview
        scrollbar = ttk.Scrollbar(
            main_frame, orient="vertical", command=self.task_tree.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.task_tree.configure(yscrollcommand=scrollbar.set)

        # Configure selection and bind drag/drop + right-click context menu
        self.task_tree.configure(selectmode="browse")
        self.task_tree.bind("<Button-1>", self.on_click)
        self.task_tree.bind("<B1-Motion>", self.on_drag)
        self.task_tree.bind("<ButtonRelease-1>", self.on_drop)
        self.task_tree.bind("<Button-3>", self.show_context_menu)

        self.toggle_deadline_entries()  # Initialize deadline entries state
        self.update_task_tree()

    def toggle_deadline_entries(self):
        if self.deadline_var.get():
            self.deadline_entry_date.grid(row=0, column=0, padx=5, pady=5)
            self.deadline_entry_time.grid(row=0, column=1, padx=5, pady=5)
            self.deadline_frame.grid(row=0, column=3, columnspan=2, padx=5, pady=5)
        else:
            self.deadline_entry_date.grid_remove()
            self.deadline_entry_time.grid_remove()
            self.deadline_frame.grid_remove()

        # Force complete geometry recalculation
        self.master.update_idletasks()

        # Get current window position
        x = self.master.winfo_x()
        y = self.master.winfo_y()

        # Temporarily set minimum size to 1x1 to allow full shrinking
        self.master.minsize(1, 1)

        # Force window to resize to fit content
        self.master.grid_propagate(True)
        self.master.pack_propagate(True)

        # Update all geometry managers
        for widget in self.master.winfo_children():
            widget.update_idletasks()

        # Get the actual required size
        required_width = self.master.winfo_reqwidth()
        required_height = self.master.winfo_reqheight()

        # Set the window size and position
        self.master.geometry(f"{required_width}x{required_height}+{x}+{y}")

        # Reset minimum size constraints
        self.master.update_idletasks()
        self.master.minsize(required_width, required_height)

        def update_window_size(self):
            # Force geometry update
            self.master.update_idletasks()
            # Get the required size for all widgets
            min_width = self.master.winfo_reqwidth()
            min_height = self.master.winfo_reqheight()

            # Get current window size
            current_width = self.master.winfo_width()
            current_height = self.master.winfo_height()

            # Only shrink if needed, don't expand
            new_width = min(current_width, min_width)
            new_height = min(current_height, min_height)

            # Update window size
            self.master.geometry(f"{new_width}x{new_height}")

    def show_task_details(self, event):
        item_id = self.task_tree.identify_row(event.y)
        if item_id:
            item = self.task_tree.item(item_id)
            task_name = item["values"][0]
            task = next((t for t in self.tasks if t.name == task_name), None)

            if task:
                self.open_description_window(task)

    def open_description_window(self, task):
        # Pass a per-task save callback so updates to the URL/description are guaranteed persisted
        description_window = TaskDescriptionWindow(
            self.master,
            task,
            lambda: self.save_tasks_to_database(task),
            getattr(task, "description", ""),
        )

    def start_auto_refresh(self):
        """Start auto-refresh every 10 seconds"""
        self.refresh_tasks()
        self.master.after(10000, self.start_auto_refresh)

    def refresh_tasks(self):
        """Refresh tasks from the database"""
        # Preserve selected task names (IDs change after repopulating)
        try:
            selected_items = self.task_tree.selection()
            selected_names = []
            for iid in selected_items:
                vals = self.task_tree.item(iid).get("values") or []
                if vals:
                    selected_names.append(vals[0])
        except Exception:
            selected_names = []

        self.tasks = self.load_tasks_from_database()
        self.update_task_tree()

        # Restore selection by matching task names and ensure visible
        try:
            for child in self.task_tree.get_children():
                vals = self.task_tree.item(child).get("values") or []
                if vals and vals[0] in selected_names:
                    self.task_tree.selection_add(child)
                    self.task_tree.see(child)
        except Exception:
            pass

    def validate_input(self):
        task_name = self.task_entry.get().strip()
        if not task_name:
            messagebox.showerror("Error", "Please enter a task name.")
            return False

        if self.deadline_var.get():
            if not self.deadline_entry_date.get() or not self.deadline_entry_time.get():
                messagebox.showerror(
                    "Error", "Please enter both deadline date and time."
                )
                return False

        if not self.status_combobox.get():
            messagebox.showerror("Error", "Please select a status.")
            return False

        return True

    def update_task_tree(self):
        self.task_tree.delete(*self.task_tree.get_children())
        for task in self.tasks:
            deadline_display = task.deadline if task.deadline else "No deadline"
            values = (task.name, deadline_display, task.status, task.owner or "", task.colour)
            item = self.task_tree.insert("", tk.END, values=values)
            self.task_tree.item(item, tags=(task.colour,))
        # ensure columns are adjusted after repopulating
        self._resize_columns()

    def _resize_columns(self, event=None):
        """Adjust column widths proportionally to available treeview width."""
        try:
            total = self.task_tree.winfo_width()
            if total <= 10:
                return
            # allocate approximate proportions
            task_w = int(total * 0.44)
            deadline_w = int(total * 0.22)
            status_w = int(total * 0.12)
            owner_w = int(total * 0.12)
            # increase minimum for Priority so long labels are not truncated
            priority_w = max(int(total - (task_w + deadline_w + status_w + owner_w)), 180)
            self.task_tree.column("Task", width=task_w)
            self.task_tree.column("Deadline", width=deadline_w)
            self.task_tree.column("Status", width=status_w)
            self.task_tree.column("Owner", width=owner_w)
            self.task_tree.column("Priority", width=priority_w)
        except Exception:
            pass


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
            label = tk.Label(
                tw,
                text=self.text,
                justify="left",
                bg="white",
                relief="solid",
                borderwidth=1,
                font=("Helvetica", 10, "normal"),
            )
            label.pack(ipadx=1)

    def hidetip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class TaskDescriptionWindow:
    def __init__(self, master, task, save_callback, task_description):
        """
        Initialize the task description window.

        Args:
            master: The parent window
            task: The task object to edit
            save_callback: Callback function to save changes to database
            task_description: The current task description
        """
        self.window = tk.Toplevel(master)
        self.window.title("Task Description")
        self.window.geometry("400x400")

        # Store original values for comparison
        self.original_description = task_description or ""
        self.original_url = getattr(task, "url", "")

        # Main container frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.task = task
        self.save_callback = save_callback

        # Add a status bar for feedback
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5)

        # Description frame
        description_frame = ttk.LabelFrame(main_frame, text="Description", padding=10)
        description_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Description text area
        self.description_text = tk.Text(description_frame, wrap=tk.WORD, height=10)
        self.description_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # If there's an existing description, insert it
        if task_description:
            self.description_text.insert("1.0", task_description)

        # URL frame
        url_frame = ttk.LabelFrame(main_frame, text="Related URL", padding=10)
        url_frame.pack(fill=tk.X, padx=5, pady=5)

        # URL entry
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(fill=tk.X, padx=5, pady=5)

        # If there's an existing URL in the task object, insert it
        if hasattr(task, "url"):
            self.url_entry.insert(0, task.url)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10, side=tk.BOTTOM)

        # Save button
        self.save_button = ttk.Button(
            button_frame, text="Save (Ctrl+S)", command=self.save_with_verification
        )
        self.save_button.pack(side=tk.RIGHT, padx=5)

        # Cancel button
        self.cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self.confirm_close
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        # Bind keyboard shortcuts
        self.window.bind("<Control-s>", lambda e: self.save_with_verification())
        self.window.bind("<Escape>", lambda e: self.confirm_close())

        # Bind window close event
        self.window.protocol("WM_DELETE_WINDOW", self.confirm_close)

        # Center the window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        # Set minimum window size
        self.window.minsize(400, 300)

        # Set focus to description text area
        self.description_text.focus_set()

        # Flag to track save status
        self.changes_saved = True

        # Bind text changes to track modifications
        self.description_text.bind("<<Modified>>", self.on_modify)
        self.url_entry.bind("<Key>", self.on_modify)

    def on_modify(self, event=None):
        """Track when changes are made to the form"""
        self.changes_saved = False
        self.status_var.set("Unsaved changes")

    def has_changes(self):
        """Check if there are unsaved changes"""
        current_description = self.description_text.get("1.0", "end-1c")
        current_url = self.url_entry.get().strip()
        return (
            current_description != self.original_description
            or current_url != self.original_url
        )

    def confirm_close(self):
        """Confirm before closing if there are unsaved changes"""
        if not self.changes_saved and self.has_changes():
            if messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
            ):
                self.save_with_verification()
            elif messagebox.askyesno(
                "Confirm Close", "Are you sure you want to close without saving?"
            ):
                self.window.destroy()
        else:
            self.window.destroy()

    def save_with_verification(self):
        """Save with verification and retry logic"""
        if not self.has_changes():
            self.status_var.set("No changes to save")
            return

        self.status_var.set("Saving...")
        self.save_button.config(state="disabled")

        try:
            # Get the current values
            description = self.description_text.get("1.0", "end-1c")
            url = self.url_entry.get().strip()

            # Validate URL if provided
            if url:
                if not validate_url(url):
                    messagebox.showerror(
                        "Invalid URL",
                        "Please enter a valid URL starting with 'http://' or 'https://'",
                    )
                    self.status_var.set("Invalid URL")
                    self.save_button.config(state="normal")
                    return

            # Update the task object
            self.task.description = description
            self.task.url = url

            # Attempt to save with retry logic
            max_retries = 3
            retry_count = 0
            save_successful = False

            while not save_successful and retry_count < max_retries:
                try:
                    self.save_callback()
                    save_successful = True
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.status_var.set(f"Retry attempt {retry_count}...")
                        time.sleep(1)  # Wait before retrying
                    else:
                        raise e

            # Update status and enable save button
            self.status_var.set("Changes saved successfully")
            self.changes_saved = True

            # Update original values
            self.original_description = description
            self.original_url = url

            # Log successful save
            logging.info(
                f"Task description saved successfully for task: {self.task.name}"
            )

            # Show success message and destroy window
            messagebox.showinfo("Success", "Task details saved successfully!")

            # Re-enable the save button before destroying the window
            self.save_button.config(state="normal")

            # Destroy the window
            self.window.destroy()

        except Exception as e:
            error_msg = f"Failed to save task details: {str(e)}"
            self.status_var.set("Error saving changes")
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)
            self.save_button.config(state="normal")


def main():
    login_screen = LoginScreen()
    login_screen.mainloop()


if __name__ == "__main__":
    main()
