# main.py
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
import shutil
from datetime import date
from auth import AuthWindow
from db import init_db, get_db_connection
from students import StudentManagement
from fees import FeeManagement
from expenses import ExpenseManagement
from reports import ReportManagement
from notifications import NotificationManagement

class MainApp:
    def __init__(self, root, user_role):
        self.root = root
        self.user_role = user_role
        self.root.title("Blessed School Finance Management System")

        # ✅ Open full screen
        self.root.state("zoomed")  # Works on Windows/Linux
        # self.root.attributes("-fullscreen", True)  # Uncomment for true fullscreen (no borders, ESC exits)

        self.root.configure(bg="#e6f2ff")


        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'), padding=6)
        self.style.map('TButton', background=[('active', '#218838')])
        self.style.configure('TLabel', background='#e6f2ff', font=('Helvetica', 10, 'bold'), foreground='#212529')
        self.style.configure('TEntry', font=('Helvetica', 10), padding=4, foreground='#212529')
        self.style.configure('Treeview', background='white', foreground='black', rowheight=25, fieldbackground='white')
        self.style.configure('Treeview.Heading', background='#007bff', foreground='white', font=('Helvetica', 10, 'bold'))
        self.style.map('Treeview.Heading', background=[('active', '#0056b3')])
        self.style.configure('Dashboard.TFrame', background='#ffffff', relief='solid', borderwidth=1, padding=10)
        self.style.configure('Dashboard.TLabel', font=('Helvetica', 14, 'bold'), foreground='#343a40')
        self.style.configure('Dashboard.Value.TLabel', font=('Helvetica', 18, 'bold'), foreground='#17a2b8')

        init_db()

        self.menu = tk.Menu(self.root, bg="#007bff", fg="white", font=('Helvetica', 10))
        self.root.config(menu=self.menu)

        dashboard_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Dashboard", menu=dashboard_menu)
        dashboard_menu.add_command(label="View Dashboard", command=self.show_dashboard)

        students_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Students", menu=students_menu)
        students_menu.add_command(label="Register Student", command=self.register_student)
        students_menu.add_command(label="Bulk Import", command=self.bulk_import_students)
        students_menu.add_command(label="View/Search Students", command=self.view_students)

        fees_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Fees & Payments", menu=fees_menu)
        fees_menu.add_command(label="Manage Fees (Assign)", command=self.manage_fees)
        fees_menu.add_command(label="Add/Edit Payment", command=self.add_payment)
        fees_menu.add_command(label="View Payments", command=self.view_payments)
        fees_menu.add_command(label="View Fee Assignments", command=self.view_fee_assignments)

        expenses_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Expenses", menu=expenses_menu)
        expenses_menu.add_command(label="Add Expense", command=self.add_expense)
        expenses_menu.add_command(label="View Expenses", command=self.view_expenses)

        notifications_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Notifications", menu=notifications_menu)
        notifications_menu.add_command(label="Send Reminders", command=self.send_notifications)

        reports_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Generate Report", command=self.generate_report)

        backup_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Data Management", menu=backup_menu)
        backup_menu.add_command(label="Backup Data", command=self.backup_data)
        backup_menu.add_command(label="Restore Data", command=self.restore_data)
        
        account_menu = tk.Menu(self.menu, tearoff=0, bg="#007bff", fg="white")
        self.menu.add_cascade(label="Account", menu=account_menu)
        account_menu.add_command(label="Logout", command=self.logout)
        account_menu.add_command(label="Exit", command=self.root.quit)

        if self.user_role == 'staff':
            students_menu.entryconfig("Register Student", state="disabled")
            students_menu.entryconfig("Bulk Import", state="disabled")
            fees_menu.entryconfig("Manage Fees (Assign)", state="disabled")
            expenses_menu.entryconfig("Add Expense", state="disabled")
            backup_menu.entryconfig("Backup Data", state="disabled")
            backup_menu.entryconfig("Restore Data", state="disabled")

        self.root.bind("<<DataChanged>>", self.on_data_changed)

        self.show_dashboard()

    def on_data_changed(self, event=None):
        print("DEBUG: DataChanged event triggered")  # Debug log
        self.show_dashboard()

    def clear_frame(self):
        for widget in self.root.winfo_children():
            if not isinstance(widget, tk.Menu):
                widget.destroy()

    def show_dashboard(self):
        self.clear_frame()
        dashboard_frame = ttk.Frame(self.root, padding=20)
        dashboard_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = tk.Frame(dashboard_frame, bg="#007bff")
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 20))

        tk.Label(header_frame, text="📊 School Finance Dashboard", font=("Helvetica", 20, "bold"),
         fg="white", bg="#007bff", pady=10).pack(side="left", padx=20)

        # Refresh button
        ttk.Button(header_frame, text="🔄 Refresh Dashboard", command=self.show_dashboard).pack(side="right", padx=10, pady=10)

        # Logout button
        ttk.Button(header_frame, text="🚪 Logout", command=self.logout).pack(side="right", padx=10, pady=10)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT SUM(paid_amount) FROM fees")
        total_collected = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(required_amount - paid_amount) FROM fees WHERE required_amount > paid_amount")
        outstanding = cursor.fetchone()[0] or 0

        today = date.today().isoformat()
        cursor.execute("SELECT SUM(cost * quantity) FROM expenses WHERE date=?", (today,))
        daily_expenses = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT id) FROM fees")
        total_fees_assigned = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM fee_categories")
        total_categories = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT class) FROM students")
        total_classes = cursor.fetchone()[0] or 0

        conn.close()

        # Stat cards (label, value, bg color, emoji)
        stats = [
            ("Total Collected", f"TZS {total_collected:,.2f}", "#28a745", "💰"),
            ("Total Pending", f"TZS {outstanding:,.2f}", "#dc3545", "⏳"),
            ("Daily Expenses", f"TZS {daily_expenses:,.2f}", "#17a2b8", "📉"),
            ("Total Students", f"{total_students}", "#ffc107", "👩‍🎓"),
            ("Fees Assigned", f"{total_fees_assigned}", "#6f42c1", "📝"),
            ("Fee Categories", f"{total_categories}", "#fd7e14", "📂"),
            ("Classes", f"{total_classes}", "#e83e8c", "🏫"),
        ]

        for i, (label_text, value, color, emoji) in enumerate(stats):
            row = (i // 3) + 1
            col = i % 3

            card = tk.Frame(dashboard_frame, bg=color, bd=0, relief="ridge")
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            card.configure(highlightbackground=color, highlightthickness=2)

            tk.Label(card, text=f"{emoji} {label_text}", font=("Helvetica", 14, "bold"),
                     bg=color, fg="white").pack(pady=(15, 5))
            tk.Label(card, text=value, font=("Helvetica", 18, "bold"),
                     bg=color, fg="white").pack(pady=(0, 15))

        for i in range(3):
            dashboard_frame.columnconfigure(i, weight=1)

    def logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to logout?"):
            self.root.destroy()  # Close current main window
            root = tk.Tk()       # Open a new Tk window for login
            AuthWindow(root)     # Show login window
            root.mainloop()


    def register_student(self):
        StudentManagement.register_student(self.root, self.user_role)

    def bulk_import_students(self):
        StudentManagement.bulk_import(self.root, self.user_role)

    def view_students(self):
        StudentManagement.view_students(self.root, self.user_role)

    def manage_fees(self):
        FeeManagement.manage_fees(self.root, self.user_role)

    def add_payment(self):
        FeeManagement.add_payment(self.root, self.user_role)

    def view_payments(self):
        FeeManagement.view_payments(self.root, self.user_role)

    def view_fee_assignments(self):
        FeeManagement.view_fee_assignments(self.root, self.user_role)

    def add_expense(self):
        ExpenseManagement.add_expense(self.root, self.user_role)

    def view_expenses(self):
        ExpenseManagement.view_expenses(self.root, self.user_role)

    def generate_report(self):
        ReportManagement.generate_report(self.root, self.user_role)

    def send_notifications(self):
        NotificationManagement.send_notifications(self.root, self.user_role)

    def backup_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")])
        if file_path:
            shutil.copy("school_finance.db", file_path)
            messagebox.showinfo("Success", "Backup created!")

    def restore_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")])
        if file_path:
            shutil.copy(file_path, "school_finance.db")
            messagebox.showinfo("Success", "Data restored! Restart the app.")

if __name__ == "__main__":
    root = tk.Tk()
    auth = AuthWindow(root)
    root.mainloop()