import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from inventory import auth, runmode
from inventory.validation import validate_username, validate_password
from ui import theme

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Siri English — PRACTICE" if runmode.PRACTICE_MODE else "School Portal Login")
        # Both Tk roots get the theme, so the login window matches the portal.
        self.style = theme.init_root(self)
        strip_height = 0
        if runmode.PRACTICE_MODE:
            strip_height = self._build_practice_banner()
        if theme.CLASSIC:
            self.geometry(f"400x{290 + strip_height}")
        self.resizable(False, False)
        
        # The password file decides everything; if it cannot be used the window only says so.
        self.locked_message = None
        self.valid_username = None
        try:
            self.valid_username = auth.load()["username"]
        except auth.CredentialsError as e:
            self.locked_message = e.user_message
        
        if theme.CLASSIC:
            # Center window (original behaviour, preserved exactly)
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.authenticated = False
        self._build_login_form()
        self._build_footer()
        
        if not theme.CLASSIC:
            # Size to content once the form exists, then centre. The old fixed
            # 400x290 could not grow, and the window is not resizable, so a
            # larger font or a scaled display used to clip it.
            self.update_idletasks()
            width = self.winfo_reqwidth()
            height = self.winfo_reqheight()
            self.minsize(width, height)
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Prevent closing without login
        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)
    
    def _build_practice_banner(self):
        """Practice copy only: the same red strip as the main window. Returns its height."""
        self._practice_banner = tk.Label(
            self, text="PRACTICE MODE — nothing here is real. Use the real portal for real students.",
            bg="#c62828", fg="white", font=("Arial", 11, "bold"), pady=4, wraplength=380)
        self._practice_banner.pack(side=tk.TOP, fill=tk.X)
        self.update_idletasks()
        return self._practice_banner.winfo_reqheight()

    def on_close_attempt(self):
        """Prevent window close without authentication."""
        if self.locked_message:
            messagebox.showwarning("Portal locked", "The portal is locked, so there is nothing to log in to. "
                                                    "Use Exit to close this window.")
        elif not self.authenticated:
            messagebox.showwarning("Login Required", "You must login to continue.")
        else:
            self.destroy()
    
    def _build_login_form(self):
        """Build the login form UI."""
        if self.locked_message:
            frame = ttk.Frame(self, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(frame, text="School Portal Login", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 20))
            ttk.Label(frame, text=self.locked_message, wraplength=340, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 20))
            ttk.Button(frame, text="Exit", command=self.on_exit).pack(anchor="w")
            return
        # Main form frame
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title with settings button
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = ttk.Label(title_frame, text="School Portal Login", font=("Arial", 16, "bold"))
        title.pack(side=tk.LEFT)
        
        settings_btn = ttk.Button(title_frame, text="⚙ Settings", command=self.open_settings)
        settings_btn.pack(side=tk.RIGHT)
        
        # Username
        ttk.Label(frame, text="Username:").pack(anchor="w", pady=(0, 5))
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(frame, textvariable=self.username_var, width=30)
        username_entry.pack(fill=tk.X, pady=(0, 15))
        username_entry.focus()
        
        # Password
        ttk.Label(frame, text="Password:").pack(anchor="w", pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=self.password_var, width=30, show="•")
        password_entry.pack(fill=tk.X, pady=(0, 20))
        password_entry.bind("<Return>", lambda e: self.on_login())
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        login_btn = ttk.Button(button_frame, text="Login", command=self.on_login)
        login_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        exit_btn = ttk.Button(button_frame, text="Exit", command=self.on_exit)
        exit_btn.pack(side=tk.LEFT)
    
    def _build_footer(self):
        """Build footer with pear icon."""
        footer_frame = ttk.Frame(self)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))
        
        footer_label = ttk.Label(footer_frame, text="NestMind Portal", font=("Arial", 9), justify=tk.CENTER)
        footer_label.pack()
    
    def on_login(self):
        """Validate credentials and authenticate."""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing", "Please enter both username and password.")
            return

        try:
            password_valid = username == auth.load()["username"] and auth.verify("login", password)
        except auth.CredentialsError as e:
            messagebox.showerror("Locked", e.user_message)
            self.password_var.set("")
            return

        if password_valid:
            self.authenticated = True
            self.destroy()
        else:
            messagebox.showerror("Invalid", "Incorrect username or password.")
            self.password_var.set("")
    
    def on_exit(self):
        """Exit application."""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.authenticated = False
            self.destroy()
    
    def open_settings(self):
        """Open settings dialog to change credentials."""
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("350x490")
        settings_window.resizable(False, False)
        
        # Center on parent
        settings_window.transient(self)
        settings_window.grab_set()
        
        frame = ttk.Frame(settings_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        ttk.Label(frame, text="Change Login Credentials", font=("Arial", 12, "bold")).pack(pady=(0, 20))
        
        # Both current passwords (for verification), like File > Change passwords
        ttk.Label(frame, text="Current Login Password:").pack(anchor="w", pady=(0, 5))
        current_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=current_password_var, width=35, show="•").pack(fill=tk.X, pady=(0, 15))

        ttk.Label(frame, text="Current Admin Password:").pack(anchor="w", pady=(0, 5))
        current_admin_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=current_admin_password_var, width=35, show="•").pack(fill=tk.X, pady=(0, 15))
        
        # New Username
        ttk.Label(frame, text="New Username:").pack(anchor="w", pady=(0, 5))
        new_username_var = tk.StringVar(value=self.valid_username)
        ttk.Entry(frame, textvariable=new_username_var, width=35).pack(fill=tk.X, pady=(0, 15))
        
        # New Password
        ttk.Label(frame, text="New Login Password:").pack(anchor="w", pady=(0, 5))
        new_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=new_password_var, width=35, show="•").pack(fill=tk.X, pady=(0, 15))
        
        # Admin Logs Password
        ttk.Label(frame, text="Admin Password (leave empty to keep it):").pack(anchor="w", pady=(0, 5))
        admin_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=admin_password_var, width=35, show="•").pack(fill=tk.X, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_and_close():
            current_password = current_password_var.get().strip()
            current_admin_password = current_admin_password_var.get().strip()
            new_username = new_username_var.get().strip()
            new_password = new_password_var.get().strip()
            admin_password = admin_password_var.get().strip()

            if not current_password or not current_admin_password or not new_username or not new_password:
                messagebox.showwarning("Missing", "Fill in both current passwords, the username and the new login password. "
                                                  "Leave the new admin password empty to keep the current one.")
                return

            # Validate new username
            valid_user, error_msg = validate_username(new_username)
            if not valid_user:
                messagebox.showerror("Invalid Username", error_msg)
                return

            # Validate new password
            valid_pass, error_msg = validate_password(new_password, min_length=6)
            if not valid_pass:
                messagebox.showerror("Invalid Password", error_msg)
                return

            # Validate admin password
            if admin_password:
                valid_admin, error_msg = validate_password(admin_password, min_length=6)
                if not valid_admin:
                    messagebox.showerror("Invalid Admin Password", error_msg)
                    return

            try:
                login_ok = auth.verify("login", current_password)
                admin_ok = auth.verify("admin", current_admin_password)
            except auth.CredentialsError as e:
                messagebox.showerror("Locked", e.user_message)
                return
            if not login_ok:
                messagebox.showerror("Error", "Current login password is incorrect!")
                current_password_var.set("")
                return
            if not admin_ok:
                messagebox.showerror("Error", "Current admin password is incorrect!")
                current_admin_password_var.set("")
                return

            try:
                auth.set_passwords(new_password, admin_password or None, username=new_username)
            except (ValueError, auth.CredentialsError) as e:
                messagebox.showerror("Error", f"Could not save credentials: {e}")
                return
            except OSError as e:
                messagebox.showerror("Error", f"Could not save passwords: {e.strerror or e}")
                return
            self.valid_username = new_username
            messagebox.showinfo("Success", f"Credentials updated for user '{new_username}'. Start-up login is on.")
            settings_window.destroy()
        
        save_btn = ttk.Button(button_frame, text="Save", command=save_and_close)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=settings_window.destroy)
        cancel_btn.pack(side=tk.LEFT)
