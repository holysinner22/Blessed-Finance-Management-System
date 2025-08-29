# fees.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from fpdf import FPDF
from db import get_db_connection

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

class FeeManagement:
    @staticmethod
    def manage_fees(root, user_role):
        if user_role != "admin":
            messagebox.showerror("Access Denied", "Only admins can manage fees.")
            return
        fee_window = tk.Toplevel(root)
        fee_window.title("Manage Fees - Assign to Class")
        fee_window.geometry("600x600")
        fee_window.configure(bg="#f0f0f0")

        style = ttk.Style(fee_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))

        def on_data_changed(event):
            fee_window.destroy()
            FeeManagement.manage_fees(root, user_role)

        root.bind("<<DataChanged>>", on_data_changed)

        ttk.Label(fee_window, text="Add New Fee Category", font=("Helvetica", 14, "bold")).pack(pady=10)

        cat_frame = ttk.Frame(fee_window)
        cat_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(cat_frame, text="Category Name:").pack(anchor="w")
        cat_name_entry = ttk.Entry(cat_frame)
        cat_name_entry.insert(0, "e.g., Library Fee")
        cat_name_entry.pack(fill=tk.X, pady=5)
        ToolTip(cat_name_entry, "Enter a unique name for the fee category (e.g., Library Fee, Sports Fee).")

        def clear_placeholder(event):
            if cat_name_entry.get() == "e.g., Library Fee":
                cat_name_entry.delete(0, tk.END)

        cat_name_entry.bind("<FocusIn>", clear_placeholder)

        def add_category():
            name = cat_name_entry.get()
            if name and name != "e.g., Library Fee":
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT OR IGNORE INTO fee_categories (name) VALUES (?)", (name,))
                    conn.commit()
                    if cursor.rowcount == 0:
                        messagebox.showwarning("Warning", "Category already exists!")
                    else:
                        messagebox.showinfo("Success", "Category added!")
                        fee_window.destroy()
                        FeeManagement.manage_fees(root, user_role)
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"Failed to add category: {e}")
                finally:
                    conn.close()
            else:
                messagebox.showerror("Error", "Please enter a valid category name.")

        ttk.Button(cat_frame, text="Add Category", command=add_category).pack(pady=10)

        ttk.Label(fee_window, text="Assign Fee to Class", font=("Helvetica", 14, "bold")).pack(pady=10)

        assign_frame = ttk.Frame(fee_window)
        assign_frame.pack(pady=10, padx=10, fill=tk.X)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT class FROM students")
        classes = [r[0] for r in cursor.fetchall() if r[0]] or ["No classes available"]

        cursor.execute("SELECT id, name FROM fee_categories")
        categories = cursor.fetchall()
        cat_dict = {name: id for id, name in categories}
        cat_names = list(cat_dict.keys()) or ["No categories available"]

        conn.close()

        ttk.Label(assign_frame, text="Select Class:").pack(anchor="w")
        class_combo = ttk.Combobox(assign_frame, values=classes)
        class_combo.pack(fill=tk.X, pady=5)
        ToolTip(class_combo, "Select a class to assign the fee to all students in that class.")

        ttk.Label(assign_frame, text="Select Fee Category:").pack(anchor="w")
        cat_combo = ttk.Combobox(assign_frame, values=cat_names)
        cat_combo.pack(fill=tk.X, pady=5)
        ToolTip(cat_combo, "Select the fee category (e.g., Tuition, Uniforms).")

        ttk.Label(assign_frame, text="Term (for Tuition only):").pack(anchor="w")
        term_combo = ttk.Combobox(assign_frame, values=["Term 1", "Term 2", "Term 3", "Term 4"], state="disabled")
        term_combo.pack(fill=tk.X, pady=5)
        ToolTip(term_combo, "Select a term for Tuition fees; disabled for other categories.")

        def update_term(*args):
            if cat_combo.get() == "Tuition":
                term_combo.config(state="normal")
                if not term_combo.get():
                    term_combo.set("Term 1")
            else:
                term_combo.config(state="disabled")
                term_combo.set("")

        cat_combo.bind("<<ComboboxSelected>>", update_term)

        ttk.Label(assign_frame, text="Required Amount (TZS):").pack(anchor="w")
        amount_entry = ttk.Entry(assign_frame)
        amount_entry.insert(0, "e.g., 500000")
        amount_entry.pack(fill=tk.X, pady=5)
        ToolTip(amount_entry, "Enter the required amount in TZS (e.g., 500000).")

        def clear_amount_placeholder(event):
            if amount_entry.get() == "e.g., 500000":
                amount_entry.delete(0, tk.END)

        amount_entry.bind("<FocusIn>", clear_amount_placeholder)

        def assign_fee():
            selected_class = class_combo.get()
            cat_name = cat_combo.get()
            term = term_combo.get()
            amount = amount_entry.get()
            if not selected_class or selected_class == "No classes available":
                messagebox.showerror("Error", "Please select a valid class.")
                return
            if not cat_name or cat_name == "No categories available":
                messagebox.showerror("Error", "Please select a valid fee category.")
                return
            if cat_name == "Tuition" and not term:
                messagebox.showerror("Error", "Please select a term for Tuition.")
                return
            if not amount or amount == "e.g., 500000":
                messagebox.showerror("Error", "Please enter a valid amount.")
                return
            try:
                amount = float(amount)
                if amount <= 0:
                    messagebox.showerror("Error", "Amount must be positive.")
                    return
                cat_id = cat_dict[cat_name]
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM students WHERE class=?", (selected_class,))
                student_ids = [r[0] for r in cursor.fetchall()]
                if not student_ids:
                    messagebox.showerror("Error", "No students in selected class.")
                    conn.close()
                    return
                for student_id in student_ids:
                    cursor.execute("INSERT OR IGNORE INTO fees (student_id, category_id, term, required_amount, paid_amount, timestamp) VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)",
                                   (student_id, cat_id, term, amount))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"Fee assigned to {len(student_ids)} students in {selected_class}!")
                fee_window.destroy()
                root.event_generate("<<DataChanged>>")
            except ValueError:
                messagebox.showerror("Error", "Amount must be a number.")
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to assign fee: {e}")

        ttk.Button(assign_frame, text="Assign Fee to Class", command=assign_fee).pack(pady=10)

    @staticmethod
    def add_payment(root, user_role):
        print("DEBUG: add_payment called")
        if user_role != "admin":
            messagebox.showerror("Access Denied", "Only admins can add or edit payments.")
            return
        payment_window = tk.Toplevel(root)
        payment_window.title("Add/Edit Payment")
        payment_window.geometry("500x500")
        payment_window.configure(bg="#f0f0f0")

        style = ttk.Style(payment_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))

        def load_dropdowns():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT class FROM students")
            classes = [r[0] for r in cursor.fetchall() if r[0]] or ["No classes available"]
            cursor.execute("SELECT id, name FROM fee_categories")
            categories = cursor.fetchall()
            conn.close()
            cat_dict = {name: id for id, name in categories}
            cat_names = list(cat_dict.keys()) or ["No categories available"]
            return classes, cat_dict, cat_names

        classes, cat_dict, cat_names = load_dropdowns()

        ttk.Label(payment_window, text="Select Class:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        class_combo = ttk.Combobox(payment_window, values=classes)
        class_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(class_combo, "Select a class to view students.")

        ttk.Label(payment_window, text="Select Student:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        student_combo = ttk.Combobox(payment_window, values=[])
        student_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(student_combo, "Select a student from the class.")

        ttk.Label(payment_window, text="Select Fee Category:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        cat_combo = ttk.Combobox(payment_window, values=cat_names)
        cat_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(cat_combo, "Select the fee category (e.g., Tuition, Uniforms).")

        ttk.Label(payment_window, text="Term (for Tuition only):", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        term_combo = ttk.Combobox(payment_window, values=["Term 1", "Term 2", "Term 3", "Term 4"], state="disabled")
        term_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(term_combo, "Select a term for Tuition payments. Enabled only for Tuition.")

        ttk.Label(payment_window, text="Payment Amount (TZS):", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        amount_entry = ttk.Entry(payment_window)
        amount_entry.insert(0, "e.g., 100000")
        amount_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(amount_entry, "Enter the payment amount in TZS (e.g., 100000).")

        remaining_label = ttk.Label(payment_window, text="Remaining: TZS 0.00", font=("Helvetica", 12))
        remaining_label.pack(pady=5, padx=10)

        def clear_amount_placeholder(event):
            if amount_entry.get() == "e.g., 100000":
                amount_entry.delete(0, tk.END)

        def update_term(*args):
            if cat_combo.get() == "Tuition":
                term_combo.config(state="normal")
                if not term_combo.get():
                    term_combo.set("Term 1")
            else:
                term_combo.config(state="disabled")
                term_combo.set("")
            update_remaining()

        def update_students(*args):
            selected_class = class_combo.get()
            if selected_class and selected_class != "No classes available":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM students WHERE class=?", (selected_class,))
                students = [r[0] for r in cursor.fetchall()]
                student_combo['values'] = students or ["No students in class"]
                student_combo.set("")
                conn.close()
            else:
                student_combo['values'] = []
                student_combo.set("")
            update_remaining()

        def update_remaining(*args):
            student_name = student_combo.get()
            cat_name = cat_combo.get()
            term = term_combo.get()
            if student_name and student_name != "No students in class" and cat_name and cat_name != "No categories available":
                if cat_name == "Tuition" and not term:
                    remaining_label.config(text="Remaining: Select a term for Tuition")
                    return
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM students WHERE name=?", (student_name,))
                    student_id = cursor.fetchone()
                    if student_id:
                        student_id = student_id[0]
                        cat_id = cat_dict.get(cat_name)
                        if cat_id:
                            where_clause = "student_id=? AND category_id=?"
                            params = (student_id, cat_id)
                            if cat_name == "Tuition" and term:
                                where_clause += " AND term=?"
                                params += (term,)
                            cursor.execute(f"SELECT required_amount, paid_amount FROM fees WHERE {where_clause}", params)
                            fee = cursor.fetchone()
                            if fee:
                                remaining = fee[0] - fee[1]
                                remaining_label.config(text=f"Remaining: TZS {remaining:,.2f}")
                            else:
                                remaining_label.config(text=f"Remaining: No fee assigned for {cat_name}{', ' + term if term else ''}")
                        else:
                            remaining_label.config(text="Remaining: Invalid category")
                    else:
                        remaining_label.config(text="Remaining: Invalid student")
                    conn.close()
                except sqlite3.Error as e:
                    remaining_label.config(text=f"Error: {e}")
            else:
                remaining_label.config(text="Remaining: TZS 0.00")

        def reset_form():
            class_combo.set(classes[0] if classes and classes[0] != "No classes available" else "")
            student_combo.set("")
            cat_combo.set(cat_names[0] if cat_names and cat_names[0] != "No categories available" else "")
            term_combo.set("")
            term_combo.config(state="disabled")
            amount_entry.delete(0, tk.END)
            amount_entry.insert(0, "e.g., 100000")
            update_term()
            update_students()
            update_remaining()

        def record_payment():
            student_name = student_combo.get()
            cat_name = cat_combo.get()
            term = term_combo.get()
            amount = amount_entry.get()
            if not student_name or student_name == "No students in class":
                messagebox.showerror("Error", "Please select a valid student.")
                return
            if not cat_name or cat_name == "No categories available":
                messagebox.showerror("Error", "Please select a valid fee category.")
                return
            if cat_name == "Tuition" and not term:
                messagebox.showerror("Error", "Please select a term for Tuition.")
                return
            if not amount or amount == "e.g., 100000":
                messagebox.showerror("Error", "Please enter a valid payment amount.")
                return
            try:
                amount = float(amount)
                if amount <= 0:
                    messagebox.showerror("Error", "Payment amount must be positive.")
                    return
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM students WHERE name=?", (student_name,))
                student_id = cursor.fetchone()
                if not student_id:
                    messagebox.showerror("Error", "Student not found.")
                    conn.close()
                    return
                student_id = student_id[0]
                cat_id = cat_dict.get(cat_name)
                where_clause = "student_id=? AND category_id=?"
                params = (student_id, cat_id)
                update_params = (amount, student_id, cat_id)
                if cat_name == "Tuition" and term:
                    where_clause += " AND term=?"
                    params += (term,)
                    update_params += (term,)
                cursor.execute(f"SELECT required_amount, paid_amount FROM fees WHERE {where_clause}", params)
                fee = cursor.fetchone()
                if not fee:
                    messagebox.showerror("Error", f"No fee assigned for {student_name} ({cat_name}{', ' + term if term else ''}).")
                    conn.close()
                    return
                remaining = fee[0] - fee[1]
                if amount > remaining:
                    messagebox.showerror("Error", f"Payment (TZS {amount:,.2f}) exceeds remaining balance (TZS {remaining:,.2f}).")
                    conn.close()
                    return
                cursor.execute(f"UPDATE fees SET paid_amount = paid_amount + ? WHERE {where_clause}", update_params)
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"Payment of TZS {amount:,.2f} recorded for {student_name} ({cat_name}{', ' + term if term else ''})!")
                payment_window.destroy()
                root.event_generate("<<DataChanged>>")
            except ValueError:
                messagebox.showerror("Error", "Payment amount must be a valid number.")
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to record payment: {e}")

        class_combo.bind("<<ComboboxSelected>>", update_students)
        cat_combo.bind("<<ComboboxSelected>>", lambda e: [update_term(), update_remaining()])
        student_combo.bind("<<ComboboxSelected>>", update_remaining)
        term_combo.bind("<<ComboboxSelected>>", update_remaining)
        amount_entry.bind("<FocusIn>", clear_amount_placeholder)

        ttk.Button(payment_window, text="Record Payment", command=record_payment).pack(pady=10)
        ttk.Button(payment_window, text="Reset Form", command=reset_form).pack(pady=5)
        ttk.Button(payment_window, text="Refresh Dropdowns", command=lambda: [setattr(class_combo, 'values', load_dropdowns()[0]), reset_form()]).pack(pady=5)

        reset_form()

    @staticmethod
    def view_payments(root, user_role):
        payment_window = tk.Toplevel(root)
        payment_window.title("View Payments")
        payment_window.geometry("800x500")
        payment_window.configure(bg="#f0f0f0")

        style = ttk.Style(payment_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))
        style.configure('Treeview', background='white', foreground='black', rowheight=25, fieldbackground='white')
        style.configure('Treeview.Heading', background='#007bff', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(payment_window, text="Search Payments:").pack(anchor="w", padx=10, pady=5)
        search_entry = ttk.Entry(payment_window)
        search_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(search_entry, "Enter student name or class to search payments.")

        ttk.Label(payment_window, text="Sort by:").pack(anchor="w", padx=10, pady=5)
        sort_combo = ttk.Combobox(payment_window, values=["Class (Ascending)", "Class (Descending)", "Student Name", "Category", "Term"])
        sort_combo.set("Class (Ascending)")
        sort_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(sort_combo, "Select sorting criteria for the payment table.")

        tree = ttk.Treeview(payment_window, columns=("Student", "Class", "Category", "Term", "Required", "Paid", "Remaining"), show="headings")
        tree.heading("Student", text="Student Name")
        tree.heading("Class", text="Class")
        tree.heading("Category", text="Fee Category")
        tree.heading("Term", text="Term")
        tree.heading("Required", text="Required (TZS)")
        tree.heading("Paid", text="Paid (TZS)")
        tree.heading("Remaining", text="Remaining (TZS)")
        tree.column("Student", width=150)
        tree.column("Class", width=100)
        tree.column("Category", width=100)
        tree.column("Term", width=100)
        tree.column("Required", width=100)
        tree.column("Paid", width=100)
        tree.column("Remaining", width=100)
        tree.pack(fill=tk.BOTH, expand=True, pady=10)

        def perform_search():
            keyword = search_entry.get()
            sort_option = sort_combo.get()
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                SELECT s.name, s.class, fc.name, f.term, f.required_amount, f.paid_amount, (f.required_amount - f.paid_amount)
                FROM fees f
                JOIN students s ON f.student_id = s.id
                JOIN fee_categories fc ON f.category_id = fc.id
                WHERE s.name LIKE ? OR s.class LIKE ?
            """
            params = (f"%{keyword}%", f"%{keyword}%")
            sort_field = {
                "Class (Ascending)": "s.class ASC",
                "Class (Descending)": "s.class DESC",
                "Student Name": "s.name ASC",
                "Category": "fc.name ASC",
                "Term": "f.term ASC"
            }.get(sort_option, "s.class ASC")
            query += f" ORDER BY {sort_field}"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                formatted_row = (
                    row[0], row[1], row[2], row[3] or "N/A",
                    f"TZS {row[4]:,.2f}", f"TZS {row[5]:,.2f}", f"TZS {row[6]:,.2f}"
                )
                tree.insert("", tk.END, values=formatted_row)
            conn.close()

        def delete_all_payments():
            if user_role != "admin":
                messagebox.showerror("Access Denied", "Only admins can delete all payments.")
                return

            confirm = messagebox.askyesno("Confirm Delete All", "Are you sure you want to delete ALL payment records? This action cannot be undone.")
            if not confirm:
                return

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM fees")
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "All payment records have been deleted.")
                perform_search()  # Refresh Treeview
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to delete all payments: {e}")



        def generate_single_report():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Please select a payment record.")
                return
            item = tree.item(selected[0])
            values = item['values']
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Payment Receipt", ln=True, align="C")
            pdf.ln(10)
            pdf.set_font("Arial", size=10)
            fields = ["Student Name", "Class", "Fee Category", "Term", "Required (TZS)", "Paid (TZS)", "Remaining (TZS)"]
            for field, value in zip(fields, values):
                pdf.cell(100, 10, f"{field}: {value}", ln=True)
            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if file_path:
                pdf.output(file_path)
                messagebox.showinfo("Success", "Payment receipt generated!")

        def export_to_csv():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.name, s.class, fc.name, f.term, f.required_amount, f.paid_amount, (f.required_amount - f.paid_amount)
                FROM fees f
                JOIN students s ON f.student_id = s.id
                JOIN fee_categories fc ON f.category_id = fc.id
                ORDER BY s.class, s.name
            """)
            rows = cursor.fetchall()
            conn.close()
            df = pd.DataFrame(rows, columns=["Student Name", "Class", "Fee Category", "Term", "Required (TZS)", "Paid (TZS)", "Remaining (TZS)"])
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if file_path:
                df.to_csv(file_path, index=False)
                messagebox.showinfo("Success", "Payments exported to CSV!")
                
                
        def delete_selected_payment():
            if user_role != "admin":
                messagebox.showerror("Access Denied", "Only admins can delete payments.")
                return

            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Please select a payment record to delete.")
                return

            confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected payment record?")
            if not confirm:
                return

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                for item in selected:
                    values = tree.item(item)['values']
                    student_name, class_name, cat_name, term = values[0], values[1], values[2], values[3] if values[3] != "N/A" else None

            # Get student ID and category ID
                    cursor.execute("SELECT id FROM students WHERE name=? AND class=?", (student_name, class_name))
                    student_id = cursor.fetchone()
                    cursor.execute("SELECT id FROM fee_categories WHERE name=?", (cat_name,))
                    cat_id = cursor.fetchone()
                    if student_id and cat_id:
                        student_id = student_id[0]
                        cat_id = cat_id[0]
                # Build query depending on whether term is set
                        if term:
                            cursor.execute("DELETE FROM fees WHERE student_id=? AND category_id=? AND term=?", (student_id, cat_id, term))
                        else:
                            cursor.execute("DELETE FROM fees WHERE student_id=? AND category_id=? AND term IS NULL", (student_id, cat_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Selected payment record(s) deleted.")
                perform_search()  # Refresh Treeview
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to delete payment: {e}")

        def export_to_pdf():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.name, s.class, fc.name, f.term, f.required_amount, f.paid_amount, (f.required_amount - f.paid_amount)
                FROM fees f
                JOIN students s ON f.student_id = s.id
                JOIN fee_categories fc ON f.category_id = fc.id
                ORDER BY s.class, s.name
            """)
            rows = cursor.fetchall()
            conn.close()
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Payment Report", ln=True, align="C")
            pdf.ln(10)
            pdf.set_font("Arial", size=10)
            headers = ["Student Name", "Class", "Fee Category", "Term", "Required (TZS)", "Paid (TZS)", "Remaining (TZS)"]
            for i, header in enumerate(headers):
                pdf.cell(30, 10, header, border=1)
            pdf.ln()
            for row in rows:
                formatted_row = (
                    row[0], row[1], row[2], row[3] or "N/A",
                    f"TZS {row[4]:,.2f}", f"TZS {row[5]:,.2f}", f"TZS {row[6]:,.2f}"
                )
                for item in formatted_row:
                    pdf.cell(30, 10, str(item), border=1)
                pdf.ln()
            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if file_path:
                pdf.output(file_path)
                messagebox.showinfo("Success", "Payments exported to PDF!")

        search_entry.bind("<KeyRelease>", lambda e: perform_search())
        sort_combo.bind("<<ComboboxSelected>>", lambda e: perform_search())
        perform_search()

        button_frame = ttk.Frame(payment_window)
        button_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Button(button_frame, text="Refresh", command=perform_search).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Generate Selected Receipt", command=generate_single_report).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Export to CSV", command=export_to_csv).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="Export to PDF", command=export_to_pdf).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(button_frame, text="Delete Selected Payment", command=delete_selected_payment).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Delete All Payments", command=delete_all_payments).grid(row=1, column=1, padx=5, pady=5)



    @staticmethod
    def view_fee_assignments(root, user_role):
        assignment_window = tk.Toplevel(root)
        assignment_window.title("View Fee Assignments")
        assignment_window.geometry("800x500")
        assignment_window.configure(bg="#f0f0f0")

        style = ttk.Style(assignment_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))
        style.configure('Treeview', background='white', foreground='black', rowheight=25, fieldbackground='white')
        style.configure('Treeview.Heading', background='#007bff', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(assignment_window, text="Select Class:").pack(anchor="w", padx=10, pady=5)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class FROM students")
        classes = ["All Classes"] + [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()
        class_combo = ttk.Combobox(assignment_window, values=classes)
        class_combo.set("All Classes")
        class_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(class_combo, "Select a class to view assigned fees.")

        tree = ttk.Treeview(assignment_window, columns=("Class", "Category", "Term", "Required Amount", "Timestamp"), show="headings")
        tree.heading("Class", text="Class")
        tree.heading("Category", text="Fee Category")
        tree.heading("Term", text="Term")
        tree.heading("Required Amount", text="Required Amount (TZS)")
        tree.heading("Timestamp", text="Assigned On")
        tree.column("Class", width=100)
        tree.column("Category", width=150)
        tree.column("Term", width=100)
        tree.column("Required Amount", width=150)
        tree.column("Timestamp", width=150)
        tree.pack(fill=tk.BOTH, expand=True, pady=10)

        def perform_search():
            selected_class = class_combo.get()
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT s.class, fc.name, f.term, f.required_amount, f.timestamp
                FROM fees f
                JOIN students s ON f.student_id = s.id
                JOIN fee_categories fc ON f.category_id = fc.id
            """
            params = []
            if selected_class != "All Classes":
                query += " WHERE s.class = ?"
                params = [selected_class]
            query += " ORDER BY s.class, f.timestamp DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                formatted_row = (
                    row[0], row[1], row[2] or "N/A", f"TZS {row[3]:,.2f}", row[4]
                )
                tree.insert("", tk.END, values=formatted_row)
            conn.close()

        class_combo.bind("<<ComboboxSelected>>", lambda e: perform_search())
        perform_search()

        ttk.Button(assignment_window, text="Refresh", command=perform_search).pack(pady=10)