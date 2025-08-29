import tkinter as tk
from tkinter import ttk, messagebox
from db import get_db_connection
import requests, json, time
from datetime import datetime

# ==========================
# 🔒 Hidden API config
# ==========================
API_CONFIG = {
    "api_id": "API47589607091",
    "api_password": "Eugen@2025",
    "sender_id": "KADIYETU",
    "send_url": "https://api.sprintsmsservice.com/api/SendSMS",
    "status_url": "https://api.sprintsmsservice.com/api/GetDeliveryStatus"
}


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
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1
        )
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class NotificationManagement:
    @staticmethod
    def send_notifications(root, user_role):
        notify_window = tk.Toplevel(root)
        notify_window.title("Send Reminders - Blessed Finance Management System")
        notify_window.geometry("1000x600")
        notify_window.configure(bg="#f0f8ff")

        style = ttk.Style(notify_window)
        style.configure('TLabel', background='#f0f8ff', font=('Helvetica', 12, 'bold'))

        # Class filter
        ttk.Label(notify_window, text="Select Class:").pack(anchor="w", padx=10, pady=5)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class FROM students")
        classes = ["All Classes"] + [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()

        class_combo = ttk.Combobox(notify_window, values=classes)
        class_combo.set("All Classes")
        class_combo.pack(fill=tk.X, padx=10, pady=5)
        ToolTip(class_combo, "Select a class to filter unpaid fees.")

        # Treeview
        tree_frame = ttk.Frame(notify_window)
        tree_frame.pack(pady=10, padx=10, fill="both", expand=True)

        columns = ("Student", "Class", "Category", "Term", "Remaining", "Phone", "Last Reminder")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Load data function
        def load_data():
            for row in tree.get_children():
                tree.delete(row)

            conn = get_db_connection()
            cursor = conn.cursor()

            # Ensure reminders log table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders_log (
                    student_id INTEGER,
                    last_sent TIMESTAMP
                )
            """)

            query = """
                SELECT s.id, s.name, s.class, fc.name, f.term, 
                       (f.required_amount - f.paid_amount), s.parent_phone,
                       (SELECT last_sent FROM reminders_log rl WHERE rl.student_id = s.id ORDER BY last_sent DESC LIMIT 1)
                FROM fees f
                JOIN students s ON f.student_id = s.id
                JOIN fee_categories fc ON f.category_id = fc.id
                WHERE f.required_amount > f.paid_amount
            """
            params = []
            if class_combo.get() != "All Classes":
                query += " AND s.class = ?"
                params.append(class_combo.get())

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                last_sent = r[7].split(".")[0] if r[7] else "Never"
                tree.insert("", "end", values=(r[1], r[2], r[3], r[4] or "N/A",
                                               f"{r[5]:,.0f} TZS", r[6], last_sent))

        load_button = ttk.Button(notify_window, text="Load Records", command=load_data)
        load_button.pack(pady=5)

        # Send SMS
        def send_reminders():
            selection = tree.selection()
            records = []

            if selection:
                item = tree.item(selection[0])["values"]
                records.append(item)
            else:
                for row in tree.get_children():
                    records.append(tree.item(row)["values"])

            if not records:
                messagebox.showinfo("No Records", "No unpaid fees selected or loaded.")
                return

            prog = tk.Toplevel(notify_window)
            prog.title("Sending SMS")
            ttk.Label(prog, text="Sending reminders...").pack(pady=10)
            bar = ttk.Progressbar(prog, orient="horizontal", length=300, mode="determinate", maximum=len(records))
            bar.pack(pady=10)
            status = ttk.Label(prog, text="0/{} sent".format(len(records)))
            status.pack(pady=5)

            sent, failed = 0, []

            conn = get_db_connection()
            cursor = conn.cursor()

            # Ensure notifications table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    phone TEXT,
                    message TEXT,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            """)
            conn.commit()

            for i, r in enumerate(records):
                name, cls, category, term, remaining, phone, _ = r
                phone_num = NotificationManagement.format_phone_number(phone)
                amount = int(str(remaining).replace(" TZS", "").replace(",", ""))
                msg = NotificationManagement.create_message(name, cls, category, term, amount)

                try:
                    resp = NotificationManagement.send_sms_api(
                        phone_num, msg,
                        API_CONFIG["send_url"],
                        API_CONFIG["api_id"],
                        API_CONFIG["api_password"],
                        API_CONFIG["sender_id"]
                    )
                    if resp.get("status") == "success":
                        message_id = resp.get("message_id")
                        timestamp = NotificationManagement.get_delivery_status(message_id)

                        sent += 1
                        cursor.execute("SELECT id FROM students WHERE name=? AND class=?", (name, cls))
                        student = cursor.fetchone()
                        student_id = student[0] if student else None

                        if student_id:
                            cursor.execute(
                                "INSERT INTO reminders_log (student_id, last_sent) VALUES (?, ?)",
                                (student_id, timestamp)
                            )
                            cursor.execute(
                                "INSERT INTO notifications (student_id, phone, message, sent_at) VALUES (?, ?, ?, ?)",
                                (student_id, phone_num, msg, timestamp)
                            )
                        conn.commit()
                    else:
                        failed.append(f"{name} ({phone_num}) - {resp.get('error')}")
                except Exception as e:
                    failed.append(f"{name} ({phone_num}) - {str(e)}")

                bar["value"] = i + 1
                status.config(text=f"{i+1}/{len(records)} sent")
                prog.update()
                time.sleep(0.5)

            conn.close()
            prog.destroy()

            result = f"Sent {sent} reminders successfully."
            if failed:
                result += f"\nFailed: {len(failed)}\n" + "\n".join(failed[:5])
            messagebox.showinfo("Result", result)

            load_data()  # refresh timestamps

        ttk.Button(notify_window, text="Send SMS Reminders", command=send_reminders).pack(pady=20)

    @staticmethod
    def format_phone_number(phone):
        phone = str(phone).strip()
        digits = "".join(filter(str.isdigit, phone))
        if not digits.startswith("255") and len(digits) == 9:
            digits = "255" + digits
        return digits

    @staticmethod
    def create_message(name, cls, category, term, amount):
        return f"Mzazi wa {name} ({cls}), deni la shule ni {amount:,.0f} TZS kwa {category} (muhula {term}). Tafadhali lipa. Shule ya Blessed."

    @staticmethod
    def send_sms_api(phone, message, api_url, api_id, api_pass, sender_id):
        payload = {
            "api_id": api_id,
            "api_password": api_pass,
            "sms_type": "P",
            "encoding": "T",
            "sender_id": sender_id,
            "phonenumber": phone,
            "textmessage": message,
            "ValidityPeriodInSeconds": 60,
            "uid": "xyz"
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        r = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
        try:
            resp = r.json()
        except:
            return {"status": "error", "error": f"Invalid response: {r.text}"}

        if r.status_code == 200 and resp.get("status", "").upper() in ["S", "SUCCESS"]:
            return {"status": "success", "message_id": resp.get("message_id")}
        return {"status": "error", "error": resp.get("remarks", "Unknown error")}

    @staticmethod
    def get_delivery_status(message_id):
        try:
            params = {
                "api_id": API_CONFIG["api_id"],
                "api_password": API_CONFIG["api_password"],
                "message_id": message_id,
                "uid": "xyz"
            }
            r = requests.get(API_CONFIG["status_url"], params=params, timeout=30)
            resp = r.json()
            if r.status_code == 200 and resp.get("DLRStatus") == "Delivered":
                return resp.get("SentDateUTC", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except:
            pass
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
