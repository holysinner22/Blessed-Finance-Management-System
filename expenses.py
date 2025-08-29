import tkinter as tk
from tkinter import ttk, messagebox
from db import get_db_connection, reorder_expense_ids
from datetime import date
import sqlite3

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ExpenseManagement:
    @staticmethod
    def add_expense(root, user_role):
        if user_role != "admin":
            messagebox.showerror("Access Denied", "Only admins can add expenses.")
            return
        expense_window = tk.Toplevel(root)
        expense_window.title("Add Expense")
        expense_window.geometry("400x300")
        expense_window.configure(bg="#f0f0f0")

        style = ttk.Style(expense_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(expense_window, text="Item:").pack(anchor="w", padx=10, pady=5)
        item_entry = ttk.Entry(expense_window)
        item_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(item_entry, "Enter expense item (e.g., Books).")

        ttk.Label(expense_window, text="Quantity:").pack(anchor="w", padx=10, pady=5)
        quantity_entry = ttk.Entry(expense_window)
        quantity_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(quantity_entry, "Enter quantity (e.g., 10).")

        ttk.Label(expense_window, text="Cost per Unit (TZS):").pack(anchor="w", padx=10, pady=5)
        cost_entry = ttk.Entry(expense_window)
        cost_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(cost_entry, "Enter cost per unit in TZS (e.g., 5000).")

        ttk.Label(expense_window, text="Date (YYYY-MM-DD):").pack(anchor="w", padx=10, pady=5)
        date_entry = ttk.Entry(expense_window)
        date_entry.insert(0, date.today().isoformat())
        date_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(date_entry, "Enter date (e.g., 2025-08-25) or use today's date.")

        def save_expense():
            item = item_entry.get()
            quantity = quantity_entry.get()
            cost = cost_entry.get()
            expense_date = date_entry.get()
            if not item or not quantity or not cost or not expense_date:
                messagebox.showerror("Error", "Please fill all fields.")
                return
            try:
                quantity = int(quantity)
                cost = float(cost)
                if quantity <= 0 or cost <= 0:
                    messagebox.showerror("Error", "Quantity and cost must be positive.")
                    return
                try:
                    date.fromisoformat(expense_date)
                except ValueError:
                    messagebox.showerror("Error", "Date must be in YYYY-MM-DD format.")
                    return
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (item, quantity, cost, date) VALUES (?, ?, ?, ?)",
                               (item, quantity, cost, expense_date))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Expense recorded!")
                expense_window.destroy()
                # Trigger refresh in Manage Expenses window
                root.event_generate("<<DataChanged>>")
            except ValueError:
                messagebox.showerror("Error", "Quantity must be an integer, cost must be a number.")
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to record expense: {e}")

        ttk.Button(expense_window, text="Save", command=save_expense).pack(pady=20)

    @staticmethod
    def view_expenses(root, user_role):
        expense_window = tk.Toplevel(root)
        expense_window.title("Manage Expenses")
        expense_window.geometry("700x500")
        expense_window.configure(bg="#f0f0f0")

        style = ttk.Style(expense_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))
        style.configure('Treeview', background='white', foreground='black', rowheight=25, fieldbackground='white')
        style.configure('Treeview.Heading', background='#007bff', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(expense_window, text="Search Expenses:").pack(anchor="w", padx=10, pady=5)
        search_entry = ttk.Entry(expense_window)
        search_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(search_entry, "Enter item name to search expenses.")

        tree = ttk.Treeview(expense_window, columns=("ID", "Item", "Quantity", "Cost", "Total", "Date"), show="headings")
        tree.heading("ID", text="ID")
        tree.heading("Item", text="Item")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Cost", text="Cost per Unit (TZS)")
        tree.heading("Total", text="Total Cost (TZS)")
        tree.heading("Date", text="Date")
        tree.column("ID", width=40)
        tree.column("Item", width=150)
        tree.column("Quantity", width=100)
        tree.column("Cost", width=100)
        tree.column("Total", width=120)
        tree.column("Date", width=100)
        tree.pack(fill=tk.BOTH, expand=True, pady=10)

        def perform_search():
            keyword = search_entry.get()
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT id, item, quantity, cost, (quantity * cost), date FROM expenses"
            params = []
            if keyword:
                query += " WHERE item LIKE ?"
                params.append(f"%{keyword}%")
            query += " ORDER BY date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                formatted_row = (
                    row[0], row[1], row[2], f"TZS {row[3]:,.2f}", f"TZS {row[4]:,.2f}", row[5]
                )
                tree.insert("", tk.END, values=formatted_row)
            conn.close()

        def delete_expense():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select an expense to delete.")
                return
            expense_id = tree.item(selected[0])["values"][0]
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this expense?"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
                conn.commit()
                conn.close()
                # Reorder IDs and refresh
                reorder_expense_ids()
                perform_search()
                messagebox.showinfo("Deleted", "Expense deleted and IDs adjusted!")

        def edit_expense():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select an expense to edit.")
                return
            row = tree.item(selected[0])["values"]
            expense_id, item, quantity, cost, total, expense_date = row

            edit_win = tk.Toplevel(expense_window)
            edit_win.title("Edit Expense")
            edit_win.geometry("400x300")

            ttk.Label(edit_win, text="Item:").pack(anchor="w", padx=10, pady=5)
            item_entry = ttk.Entry(edit_win)
            item_entry.insert(0, item)
            item_entry.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(edit_win, text="Quantity:").pack(anchor="w", padx=10, pady=5)
            quantity_entry = ttk.Entry(edit_win)
            quantity_entry.insert(0, quantity)
            quantity_entry.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(edit_win, text="Cost per Unit (TZS):").pack(anchor="w", padx=10, pady=5)
            cost_entry = ttk.Entry(edit_win)
            cost_entry.insert(0, cost.replace("TZS ", "").replace(",", ""))
            cost_entry.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(edit_win, text="Date (YYYY-MM-DD):").pack(anchor="w", padx=10, pady=5)
            date_entry = ttk.Entry(edit_win)
            date_entry.insert(0, expense_date)
            date_entry.pack(fill=tk.X, padx=10, pady=5)

            def update_expense():
                try:
                    new_item = item_entry.get()
                    new_quantity = int(quantity_entry.get())
                    new_cost = float(cost_entry.get())
                    new_date = date_entry.get()
                    date.fromisoformat(new_date)

                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE expenses SET item=?, quantity=?, cost=?, date=? WHERE id=?",
                        (new_item, new_quantity, new_cost, new_date, expense_id)
                    )
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Expense updated!")
                    edit_win.destroy()
                    perform_search()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update expense: {e}")

            ttk.Button(edit_win, text="Update", command=update_expense).pack(pady=20)

        # Bind search and live refresh
        search_entry.bind("<KeyRelease>", lambda e: perform_search())
        root.bind("<<DataChanged>>", lambda e: perform_search())
        perform_search()

        # Buttons for CRUD
        btn_frame = ttk.Frame(expense_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Refresh", command=perform_search).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=edit_expense).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=delete_expense).grid(row=0, column=2, padx=5)
