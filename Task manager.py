import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

class TaskManager:
    def __init__(self, master):
        self.master = master
        self.master.title("Task Manager")
        
        self.tasks = []
        
        self.task_label = ttk.Label(master, text="Task:")
        self.task_label.grid(row=0, column=0, padx=5, pady=5)
        
        self.task_entry = ttk.Entry(master, width=30)
        self.task_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.deadline_label = ttk.Label(master, text="Deadline Date:")
        self.deadline_label.grid(row=0, column=2, padx=5, pady=5)
        
        self.deadline_entry_date = DateEntry(master, width=20, date_pattern='yyyy-mm-dd')
        self.deadline_entry_date.grid(row=0, column=3, padx=5, pady=5)
        self.deadline_entry_date.set_date(datetime.today())  # Set initial date to today
        
        self.deadline_time_label = ttk.Label(master, text="Deadline Time:")
        self.deadline_time_label.grid(row=0, column=4, padx=5, pady=5)
        
        self.deadline_entry_time = ttk.Combobox(master, width=10)
        self.deadline_entry_time.grid(row=0, column=5, padx=5, pady=5)
        self.populate_time_combobox()  # Populate time combobox with future times
        
        self.status_label = ttk.Label(master, text="Status:")
        self.status_label.grid(row=0, column=6, padx=5, pady=5)
        
        self.status_combobox = ttk.Combobox(master, values=["To Do", "In Progress", "Complete"])
        self.status_combobox.grid(row=0, column=7, padx=5, pady=5)
        
        self.add_button = ttk.Button(master, text="Add Task", command=self.add_task)
        self.add_button.grid(row=0, column=8, padx=5, pady=5)
        
        self.task_tree = ttk.Treeview(master, columns=("Task", "Deadline", "Status"), show="headings")
        self.task_tree.heading("Task", text="Task")
        self.task_tree.heading("Deadline", text="Deadline")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.grid(row=1, column=0, columnspan=9, padx=5, pady=5)
        
        self.complete_button = ttk.Button(master, text="Mark Complete", command=self.mark_complete)
        self.complete_button.grid(row=2, column=0, padx=5, pady=5)
        
        self.in_progress_button = ttk.Button(master, text="Mark In Progress", command=self.mark_in_progress)
        self.in_progress_button.grid(row=2, column=1, padx=5, pady=5)
        
        self.delete_button = ttk.Button(master, text="Delete Selected", command=self.delete_selected)
        self.delete_button.grid(row=2, column=8, padx=5, pady=5)
        
        # Bind right-click event to the task treeview
        self.task_tree.bind("<Button-3>", self.right_click_menu)
        
    def populate_time_combobox(self):
        current_time = datetime.now().replace(second=0, microsecond=0)
        future_times = [current_time + timedelta(minutes=30 * i) for i in range(48)]  # Future times in half-hour intervals
        time_strings = [time.strftime('%H:%M') for time in future_times if time > current_time]
        self.deadline_entry_time['values'] = time_strings
    
    def add_task(self):
        task = self.task_entry.get()
        deadline_date = self.deadline_entry_date.get()
        deadline_time = self.deadline_entry_time.get()
        status = self.status_combobox.get()
        
        if task and deadline_date and deadline_time and status:
            deadline = f"{deadline_date} {deadline_time}"
            self.tasks.append((task, deadline, status))
            self.update_task_tree()
            self.task_entry.delete(0, tk.END)
            self.deadline_entry_date.delete(0, tk.END)
            self.deadline_entry_time.delete(0, tk.END)
            self.populate_time_combobox()  # Update time combobox with the  future times
        else:
            messagebox.showwarning("Warning", "Please enter task, deadline, and select status.")
    
    def mark_complete(self):
        selected_item = self.task_tree.selection()
        if selected_item:
            item = self.task_tree.item(selected_item)
            task = item['values'][0]
            deadline = item['values'][1]

            # Change status to "Complete"
            for i, (t, d, s) in enumerate(self.tasks):
                if t == task and d == deadline:
                    self.tasks[i] = (t, d, "Complete")
                    break

            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select a task to mark complete.")
    
    def mark_in_progress(self):
        selected_item = self.task_tree.selection()
        if selected_item:
            item = self.task_tree.item(selected_item)
            task = item['values'][0]
            deadline = item['values'][1]

            # Change status to "In Progress"
            for i, (t, d, s) in enumerate(self.tasks):
                if t == task and d == deadline:
                    self.tasks[i] = (t, d, "In Progress")
                    break

            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select a task to mark in progress.")
    
    def delete_selected(self):
        selected_items = self.task_tree.selection()
        if selected_items:
            for item in selected_items:
                task = self.task_tree.item(item)['values'][0]
                deadline = self.task_tree.item(item)['values'][1]
                for i, (t, d, s) in enumerate(self.tasks):
                    if t == task and d == deadline:
                        del self.tasks[i]
                        break
            self.update_task_tree()
        else:
            messagebox.showwarning("Warning", "Please select tasks to delete.")
    
    def update_task_tree(self):
        self.task_tree.delete(*self.task_tree.get_children())
        for task, deadline, status in self.tasks:
            self.task_tree.insert("", tk.END, values=(task, deadline, status))

    def right_click_menu(self, event):
        # Select the item under the cursor
        item_id = self.task_tree.identify_row(event.y)
        if item_id:
            # Create a right-click menu
            menu = tk.Menu(self.master, tearoff=0)
            menu.add_command(label="Prioritise Task", command=lambda: self.prioritise_task(item_id))
            menu.post(event.x_root, event.y_root)

    def prioritise_task(self, item_id):
        # Get the task details from the item ID
        task_details = self.task_tree.item(item_id)['values']
        task = task_details[0]
        deadline = task_details[1]
        status = task_details[2]

        # Remove the task from the list
        self.tasks.remove((task, deadline, status))

        # Insert the task at the beginning of the list
        self.tasks.insert(0, (task, deadline, status))

        # Update the task treeview
        self.update_task_tree()

def main():
    root = tk.Tk()
    app = TaskManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
