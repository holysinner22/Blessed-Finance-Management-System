# auth.py
import tkinter as tk
from tkinter import messagebox
from db import get_db_connection, init_db

class AuthWindow:
    def __init__(self, root):
        init_db()
        self.root = root
        self.root.withdraw()

        # ===== Login Window =====
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Blessed Finance Management - Login")
        self.login_window.state("zoomed")  # Fullscreen

        # ===== Gradient Background =====
        self.bg_canvas = tk.Canvas(self.login_window, width=self.login_window.winfo_screenwidth(),
                                   height=self.login_window.winfo_screenheight(), highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        self.draw_gradient(self.bg_canvas, "#1a1a2e", "#533483")

        # ===== Center Frame (Glass Style) =====
        container = tk.Frame(self.login_window, bg="#16213e", bd=2, relief="flat", highlightbackground="#e94560", highlightthickness=2)
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(container, text="Blessed Finance Management", 
                 bg="#16213e", fg="#e94560", font=("Helvetica", 28, "bold")).pack(pady=(10,20))

        # Username
        self.username_entry = self.create_entry(container, "Username")
        
        # Password
        self.password_entry = self.create_entry(container, "Password", show="*")

        # Toggle password visibility
        toggle_btn = tk.Button(container, text="👁", bg="#0f3460", fg="white", bd=0, cursor="hand2",
                               command=self.toggle_password)
        toggle_btn.pack(pady=(0,10))

        # Login button with hover effect
        login_btn = tk.Button(container, text="Login", font=("Helvetica", 14, "bold"),
                              bg="#e94560", fg="white", activebackground="#ff2e63",
                              activeforeground="white", cursor="hand2",
                              relief="flat", command=self.login)
        login_btn.pack(pady=15, ipadx=10, ipady=5)

        login_btn.bind("<Enter>", lambda e: login_btn.config(bg="#ff2e63"))
        login_btn.bind("<Leave>", lambda e: login_btn.config(bg="#e94560"))

        # Footer
        tk.Label(container, text="© 2025 Blessed Finance System", 
                 bg="#16213e", fg="gray", font=("Helvetica", 10)).pack(pady=(20,10))

    # ========= Helpers =========
    def draw_gradient(self, canvas, color1, color2):
        """Draw vertical gradient background"""
        width = self.login_window.winfo_screenwidth()
        height = self.login_window.winfo_screenheight()
        limit = height
        (r1,g1,b1) = self.login_window.winfo_rgb(color1)
        (r2,g2,b2) = self.login_window.winfo_rgb(color2)
        r_ratio = float(r2-r1) / limit
        g_ratio = float(g2-g1) / limit
        b_ratio = float(b2-b1) / limit

        for i in range(limit):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%04x%04x%04x" % (nr, ng, nb)
            canvas.create_line(0,i,width,i, tags=("gradient",), fill=color)
        canvas.lower("gradient")

    def create_entry(self, parent, placeholder, show=""):
        entry = tk.Entry(parent, font=("Helvetica", 13),
                         bg="#0f3460", fg="white", insertbackground="white",
                         relief="flat", show=show)
        entry.pack(fill="x", padx=20, pady=8, ipady=7)
        entry.insert(0, placeholder)
        entry.bind("<FocusIn>", lambda e, ent=entry, ph=placeholder: self._clear_placeholder(ent, ph))
        entry.bind("<FocusOut>", lambda e, ent=entry, ph=placeholder: self._add_placeholder(ent, ph))
        return entry

    def _clear_placeholder(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            if placeholder == "Password":
                entry.config(show="*")

    def _add_placeholder(self, entry, placeholder):
        if not entry.get():
            entry.insert(0, placeholder)
            if placeholder == "Password":
                entry.config(show="")

    def toggle_password(self):
        if self.password_entry.cget("show") == "*":
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if username in ["", "Username"] or password in ["", "Password"]:
            messagebox.showerror("Error", "All fields are required", parent=self.login_window)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
        result = cursor.fetchone()
        conn.close()

        if result:
            role = result[0]
            self.login_window.destroy()
            self.root.deiconify()
            from main import MainApp
            MainApp(self.root, role)
        else:
            messagebox.showerror("Error", "Invalid credentials", parent=self.login_window)
