# students.py
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from db import get_db_connection
from datetime import datetime
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

class StudentManagement:
    @staticmethod
    def register_student(root, user_role):
        if user_role != "admin":
            messagebox.showerror("Access Denied", "Only admins can register students.")
            return
        reg_window = tk.Toplevel(root)
        reg_window.title("Register Student")
        reg_window.geometry("400x300")
        reg_window.configure(bg="#f0f0f0")

        style = ttk.Style(reg_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(reg_window, text="Name:").pack(anchor="w", padx=10, pady=5)
        name_entry = ttk.Entry(reg_window)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(name_entry, "Enter student's full name.")

        ttk.Label(reg_window, text="Parent Phone:").pack(anchor="w", padx=10, pady=5)
        phone_entry = ttk.Entry(reg_window)
        phone_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(phone_entry, "Phone number must be in the format 255XXXXXXXXX.")

        ttk.Label(reg_window, text="Class:").pack(anchor="w", padx=10, pady=5)
        classes = ["Pre Unit", "Baby Class", "Middle Class"] + [f"Grade {i}" for i in range(1, 7)]
        class_combo = ttk.Combobox(reg_window, values=classes, state="readonly")
        class_combo.set(classes[0])
        class_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(class_combo, "Select the student's class.")


        def save_student():
            name = name_entry.get()
            phone = phone_entry.get()
            cls = class_combo.get()

            if not name or not phone or not cls:
                messagebox.showerror("Error", "Please fill all fields.")
                return
            try:
                phone = str(phone).strip()
                if not phone.startswith("255") or len(phone) != 12 or not phone[3:].isdigit():
                    messagebox.showerror("Error", "Phone number must be in the format 255XXXXXXXXX.")
                    return

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO students (name, parent_phone, class) VALUES (?, ?, ?)", (name, phone, cls))
                student_id = cursor.lastrowid
                # Assign existing class-based fees to the new student
                cursor.execute("""
                    SELECT DISTINCT f.category_id, f.term, f.required_amount
                    FROM fees f
                    JOIN students s ON f.student_id = s.id
                    WHERE s.class = ? AND f.required_amount > 0
                """, (cls,))
                class_fees = cursor.fetchall()
                for category_id, term, required_amount in class_fees:
                    cursor.execute("""
                        INSERT OR IGNORE INTO fees (student_id, category_id, term, required_amount, paid_amount)
                        VALUES (?, ?, ?, ?, 0)
                    """, (student_id, category_id, term, required_amount))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"Student {name} registered and assigned {len(class_fees)} class fees!")
                reg_window.destroy()
                root.event_generate("<<DataChanged>>")
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to register student: {e}")

        ttk.Button(reg_window, text="Save", command=save_student).pack(pady=20)

    @staticmethod
    def bulk_import(root, user_role):
        if user_role != "admin":
            messagebox.showerror("Access Denied", "Only admins can import students.")
            return

        import_window = tk.Toplevel(root)
        import_window.title("Bulk Import Students")
        import_window.geometry("400x200")
        import_window.configure(bg="#f0f0f0")

        style = ttk.Style(import_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))

        ttk.Label(import_window, text="Select Excel File:").pack(anchor="w", padx=10, pady=5)
        file_entry = ttk.Entry(import_window)
        file_entry.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(file_entry, "Enter path to Excel file with columns: Name, Parent Phone, Class.")

        def browse_file():
            file_path = tk.filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
            if file_path:
                file_entry.delete(0, tk.END)
                file_entry.insert(0, file_path)

        ttk.Button(import_window, text="Browse", command=browse_file).pack(pady=5)

        def import_students():
            file_path = file_entry.get()
            if not file_path:
                messagebox.showerror("Error", "Please select a file.")
                return

            allowed_classes = ["Pre Unit", "Baby Class", "Middle Class",
                            "Grade 1", "Grade 2", "Grade 3",
                            "Grade 4", "Grade 5", "Grade 6"]

            # Create a mapping for case-insensitive matching
            class_mapping = {cls.lower(): cls for cls in allowed_classes}

            try:
                df = pd.read_excel(file_path)
                expected_columns = ["Name", "Parent Phone", "Class"]
                if not all(col in df.columns for col in expected_columns):
                    messagebox.showerror("Error", "Excel file must have columns: Name, Parent Phone, Class")
                    return

                conn = get_db_connection()
                cursor = conn.cursor()
                imported_count = 0
                skipped_rows = []

                for index, row in df.iterrows():
                    name = str(row["Name"]).strip()
                    phone = str(row["Parent Phone"]).strip()
                    cls_raw = str(row["Class"]).strip()

                    # Normalize class (case-insensitive)
                    cls_lower = cls_raw.lower()
                    if cls_lower in class_mapping:
                        cls = class_mapping[cls_lower]
                    else:
                        skipped_rows.append((index + 2, f"Invalid Class: {cls_raw}"))
                        continue

                    # Validate phone format (must be 255XXXXXXXXX)
                    if not (phone.startswith("255") and len(phone) == 12 and phone[3:].isdigit()):
                        skipped_rows.append((index + 2, f"Invalid Phone: {phone}"))
                        continue

                    if name and cls:
                        cursor.execute("INSERT OR IGNORE INTO students (name, parent_phone, class) VALUES (?, ?, ?)",
                                    (name, phone, cls))
                        if cursor.rowcount > 0:
                            student_id = cursor.lastrowid

                            # Assign existing class-based fees to the new student
                            cursor.execute("""
                                SELECT DISTINCT f.category_id, f.term, f.required_amount
                                FROM fees f
                                JOIN students s ON f.student_id = s.id
                                WHERE s.class = ? AND f.required_amount > 0
                            """, (cls,))
                            class_fees = cursor.fetchall()
                            for category_id, term, required_amount in class_fees:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO fees (student_id, category_id, term, required_amount, paid_amount)
                                    VALUES (?, ?, ?, ?, 0)
                                """, (student_id, category_id, term, required_amount))

                            imported_count += 1

                conn.commit()
                conn.close()

                summary_msg = f"{imported_count} students imported successfully with class fees!"
                if skipped_rows:
                    summary_msg += "\n\nSkipped Rows:\n" + "\n".join([f"Row {r[0]}: {r[1]}" for r in skipped_rows])

                messagebox.showinfo("Import Summary", summary_msg)
                import_window.destroy()
                root.event_generate("<<DataChanged>>")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to import students: {e}")


        ttk.Button(import_window, text="Import", command=import_students).pack(pady=20)


    @staticmethod
    def view_students(root, user_role):
        view_window = tk.Toplevel(root)
        view_window.title("View Students")
        view_window.geometry("1100x500")
        view_window.configure(bg="#f0f0f0")

        # ---------------- Styling ----------------
        style = ttk.Style(view_window)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 12, 'bold'))
        style.configure('TButton', background='#28a745', foreground='white', font=('Helvetica', 10, 'bold'))
        style.configure('Treeview', background='white', foreground='black', rowheight=25, fieldbackground='white')
        style.configure('Treeview.Heading', background='#007bff', foreground='white', font=('Helvetica', 10, 'bold'))

        # ---------------- Filters ----------------
        ttk.Label(view_window, text="Search Students:").pack(anchor="w", padx=10, pady=5)
        search_entry = ttk.Entry(view_window)
        search_entry.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(view_window, text="Select Class:").pack(anchor="w", padx=10, pady=5)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class FROM students")
        classes = ["All Classes"] + [r[0] for r in cursor.fetchall() if r[0]]
        class_combo = ttk.Combobox(view_window, values=classes)
        class_combo.set("All Classes")
        class_combo.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(view_window, text="Select Term (for Tuition):").pack(anchor="w", padx=10, pady=5)
        term_combo = ttk.Combobox(view_window, values=["All Terms", "Term 1", "Term 2", "Term 3", "Term 4"])
        term_combo.set("All Terms")
        term_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # ---------------- Delete All Button ----------------
        def delete_all_students():
            if user_role != "admin":
                messagebox.showerror("Access Denied", "Only admins can delete all students.")
                return
            if messagebox.askyesno("Confirm", "Are you sure you want to delete ALL students and their fees? This cannot be undone."):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM students")
                    cur.execute("DELETE FROM fees")
                    conn.commit()
                    conn.close()
                    load_students()
                    messagebox.showinfo("Success", "All students and their fees have been deleted.")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        ttk.Button(view_window, text="Delete All Students", command=delete_all_students).pack(pady=10)


        # ---------------- Treeview ----------------
        columns = ["Name", "Parent Phone", "Class", "Edit", "Delete"]
        tree = ttk.Treeview(view_window, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150 if col in ["Name", "Parent Phone"] else 80)
        tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # ---------------- CRUD Functions ----------------
        def edit_student(student_id):
            cursor.execute("SELECT name, parent_phone, class FROM students WHERE id=?", (student_id,))
            student = cursor.fetchone()
            if not student:
                messagebox.showerror("Error", "Student not found")
                return

            edit_window = tk.Toplevel(view_window)
            edit_window.title("Edit Student")
            edit_window.geometry("400x300")

            name_entry = ttk.Entry(edit_window)
            name_entry.pack(pady=5, fill=tk.X)
            name_entry.insert(0, student[0])

            phone_entry = ttk.Entry(edit_window)
            phone_entry.pack(pady=5, fill=tk.X)
            phone_entry.insert(0, student[1])

            classes_list = ["Pre Unit", "Baby Class", "Middle Class"] + [f"Grade {i}" for i in range(1, 7)]
            class_combo_edit = ttk.Combobox(edit_window, values=classes_list, state="readonly")
            class_combo_edit.set(student[2])
            class_combo_edit.pack(pady=5, fill=tk.X)

            def save_changes():
                new_name = name_entry.get().strip()
                new_phone = phone_entry.get().strip()
                new_class = class_combo_edit.get()
                if not new_name or not new_phone or not new_class:
                    messagebox.showerror("Error", "Please fill all fields.")
                    return
                if not (new_phone.startswith("255") and len(new_phone) == 12 and new_phone[3:].isdigit()):
                    messagebox.showerror("Error", "Phone number must be in the format 255XXXXXXXXX.")
                    return

                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT class FROM students WHERE id=?", (student_id,))
                    old_class = cur.fetchone()[0]

                    # Update student info
                    cur.execute("UPDATE students SET name=?, parent_phone=?, class=? WHERE id=?",
                                (new_name, new_phone, new_class, student_id))

                    # Update fees if class changed
                    if old_class != new_class:
                        cur.execute("DELETE FROM fees WHERE student_id=? AND paid_amount=0", (student_id,))
                        cur.execute("""
                            SELECT DISTINCT category_id, term, required_amount
                            FROM fees f
                            JOIN students s ON f.student_id = s.id
                            WHERE s.class=? AND required_amount>0
                        """, (new_class,))
                        fees = cur.fetchall()
                        for cat_id, term, req in fees:
                            cur.execute("""
                                INSERT OR IGNORE INTO fees (student_id, category_id, term, required_amount, paid_amount)
                                VALUES (?, ?, ?, ?, 0)
                            """, (student_id, cat_id, term, req))

                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Student updated successfully!")
                    edit_window.destroy()
                    load_students()

                except Exception as e:
                    messagebox.showerror("Error", str(e))

            ttk.Button(edit_window, text="Save", command=save_changes).pack(pady=10)

        def view_fee_details(student_id, student_name):
            fee_window = tk.Toplevel(view_window)
            fee_window.title(f"Fees for {student_name}")
            fee_window.geometry("600x400")
            fee_window.configure(bg="#f0f0f0")

            tree_fees = ttk.Treeview(fee_window, columns=["Category", "Term", "Required", "Paid", "Unpaid"], show="headings")
            for col in ["Category", "Term", "Required", "Paid", "Unpaid"]:
                tree_fees.heading(col, text=col)
                tree_fees.column(col, width=100)
            tree_fees.pack(fill=tk.BOTH, expand=True, pady=10)

            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT fc.name, f.term, f.required_amount, f.paid_amount
                    FROM fees f
                    JOIN fee_categories fc ON f.category_id = fc.id
                    WHERE f.student_id=?
                """, (student_id,))
                fees = cur.fetchall()
                conn.close()

                for category, term, required, paid in fees:
                    unpaid = (required or 0) - (paid or 0)
                    tree_fees.insert("", tk.END, values=(
                        category,
                        term or "",
                        f"TZS {required:,.2f}",
                        f"TZS {paid:,.2f}",
                        f"TZS {unpaid:,.2f}"
                    ))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load fees: {e}")


        def delete_student(student_id):
            if messagebox.askyesno("Confirm", "Are you sure you want to delete this student?"):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM students WHERE id=?", (student_id,))
                    cur.execute("DELETE FROM fees WHERE student_id=?", (student_id,))
                    conn.commit()
                    conn.close()
                    load_students()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        # ---------------- Load Students ----------------
        def load_students():
            for row in tree.get_children():
                tree.delete(row)

            keyword = search_entry.get().strip()
            selected_class = class_combo.get()
            selected_term = term_combo.get()

            query = "SELECT id, name, parent_phone, class FROM students"
            params = []
            if selected_class != "All Classes":
                query += " WHERE class=?"
                params.append(selected_class)
            if keyword:
                query += " AND" if "WHERE" in query else " WHERE"
                query += " (name LIKE ? OR class LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            query += " ORDER BY class, name"
            cursor.execute(query, params)
            students = cursor.fetchall()

            for student in students:
                student_id, name, phone, cls = student
                tree.insert("", tk.END, values=(name, phone, cls, "Edit", "Delete"))

            def item_clicked(event):
                region = tree.identify("region", event.x, event.y)
                if region != "cell":
                    return
                row_id = tree.identify_row(event.y)
                column = tree.identify_column(event.x)
                if not row_id:
                    return
                student_index = tree.index(row_id)
                # Get actual student ID for this row
                actual_id = students[student_index][0]
                if column == "#4":  # Edit
                    edit_student(actual_id)
                elif column == "#5":  # Delete
                    delete_student(actual_id)

            tree.bind("<Button-1>", item_clicked)
            
            def on_double_click(event):
                row_id = tree.identify_row(event.y)
                if not row_id:
                    return
                student_index = tree.index(row_id)
                actual_id, name, phone, cls = students[student_index]
                view_fee_details(actual_id, name)

            tree.bind("<Double-1>", on_double_click)


        search_entry.bind("<KeyRelease>", lambda e: load_students())
        class_combo.bind("<<ComboboxSelected>>", lambda e: load_students())
        term_combo.bind("<<ComboboxSelected>>", lambda e: load_students())
        load_students()
