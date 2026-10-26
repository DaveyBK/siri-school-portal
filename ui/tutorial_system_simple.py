"""
Simple Tutorial System for Pear v2
Uses direct widget highlighting and tooltip-style instruction boxes
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List
import json
from pathlib import Path

from inventory import runmode
from ui import theme


def progress_file_path() -> Path:
    """Where tutorial progress is kept: the user's home folder, as always; inside the sandbox in test mode."""
    if runmode.TEST_MODE:
        return Path(__file__).resolve().parent.parent / "data" / "tutorial_progress.json"
    return Path.home() / ".pear_library" / "tutorial_progress.json"


# D3 (b), decided 2 Oct: these five describe controls the portal does not have, so they are not offered. Their
# progress, if any, stays in tutorial_progress.json, unused.
_NOT_OFFERED = {"checkout_book", "take_attendance", "add_book", "manual_checkin", "load_schedule"}


class SimpleTutorialStep:
    """A single tutorial step with simple highlighting"""
    
    def __init__(self, title: str, instruction: str, widget_getter=None, tab_index=None, highlight_duration=0):
        self.title = title
        self.instruction = instruction
        self.widget_getter = widget_getter  # Function that returns the widget
        self.tab_index = tab_index
        self.highlight_duration = highlight_duration  # How long to highlight in ms (0 = until next step)


class SimpleTutorial:
    """A tutorial with multiple steps"""
    
    def __init__(self, tutorial_id: str, name: str, description: str, icon: str = "📖"):
        self.tutorial_id = tutorial_id
        self.name = name
        self.description = description
        self.icon = icon
        self.steps: List[SimpleTutorialStep] = []
    
    def add_step(self, step: SimpleTutorialStep):
        self.steps.append(step)
        return self


class SimpleTutorialManager:
    """Manages tutorials with a simpler approach"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.tutorials: Dict[str, SimpleTutorial] = {}
        self.current_tutorial: Optional[SimpleTutorial] = None
        self.current_step_index: int = 0
        self.is_active: bool = False
        
        # UI elements
        self.instruction_window: Optional[tk.Toplevel] = None
        self.selection_window: Optional[tk.Toplevel] = None  # Add selection window
        self.highlight_widgets: List[tk.Widget] = []  # Track highlighted widgets
        self.original_configs: Dict[tk.Widget, Dict] = {}  # Store original widget configs
        
        # Progress tracking
        self.completed_tutorials = self._load_progress()
        
        # Initialize tutorials
        self._init_tutorials()
    
    def _load_progress(self) -> set:
        """Load completed tutorials"""
        try:
            # Use home directory for reliability (inside the sandbox in test mode)
            progress_file = progress_file_path()
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('completed', []))
        except Exception as e:
            print(f"Could not load progress: {e}")
        return set()
    
    def _save_progress(self):
        """Save completed tutorials"""
        try:
            progress_file = progress_file_path()
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(progress_file, 'w') as f:
                json.dump({'completed': list(self.completed_tutorials)}, f)
        except Exception as e:
            print(f"Could not save progress: {e}")
    
    def _init_tutorials(self):
        """Initialize all tutorials"""
        
        # Tutorial 1: Add a Student
        t1 = SimpleTutorial("add_student", "Add a New Student", 
                           "Learn how to add a new student to the system", "👤")
        t1.add_step(SimpleTutorialStep(
            "Navigate to Students Tab",
            "First, click on the 'Students' tab at the top to view the student list.",
            lambda: self._get_tab_widget(0),
            tab_index=0
        ))
        t1.add_step(SimpleTutorialStep(
            "Click Add Button",
            "Now click the green '➕ Add' button in the toolbar to add a new student.",
            lambda: self._find_button_by_text("Add"),
            tab_index=0
        ))
        t1.add_step(SimpleTutorialStep(
            "Fill in Student Details",
            "A dialog will appear. Fill in:\n• Student ID (unique number)\n• First Name\n• Last Name\n• Level (grade or class)\n\nThen click OK to save the student.",
            None
        ))
        t1.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Great! The new student is now in the system and will appear in the student list.",
            None
        ))
        self.tutorials["add_student"] = t1
        
        # Tutorial 2: Checkout a Book
        t2 = SimpleTutorial("checkout_book", "Check Out a Book",
                           "Learn how to check out a book to a student", "📚")
        t2.add_step(SimpleTutorialStep(
            "Go to Books Tab",
            "Click on the 'Books' tab to see all available books.",
            lambda: self._get_tab_widget(2),
            tab_index=2
        ))
        t2.add_step(SimpleTutorialStep(
            "Select a Book",
            "Click on a book from the list that you want to check out.",
            None,
            tab_index=2
        ))
        t2.add_step(SimpleTutorialStep(
            "Click Checkout Button",
            "Click the 'Checkout' button in the toolbar at the top.",
            None,
            tab_index=2
        ))
        t2.add_step(SimpleTutorialStep(
            "Enter Student ID",
            "A dialog will appear asking for the Student ID. Enter the ID of the student borrowing the book and click OK.",
            None
        ))
        t2.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Done! The book is now checked out to that student. You can see the assignment in the student's record.",
            None
        ))
        self.tutorials["checkout_book"] = t2
        
        # Tutorial 3: Return a Book
        t3 = SimpleTutorial("return_book", "Return a Book",
                           "Learn how to mark a book as returned", "↩️")
        t3.add_step(SimpleTutorialStep(
            "Go to Students Tab",
            "Click on the 'Students' tab to view all students.",
            lambda: self._get_tab_widget(0),
            tab_index=0
        ))
        t3.add_step(SimpleTutorialStep(
            "Select the Student",
            "Click on the student who is returning a book. You'll see their borrowed items in the bottom section.",
            None,
            tab_index=0
        ))
        t3.add_step(SimpleTutorialStep(
            "Select the Item",
            "In the '📖 Books Out' section, click on the book being returned.",
            None,
            tab_index=0
        ))
        t3.add_step(SimpleTutorialStep(
            "Click Return Button",
            "Click the '↩ Return Book' button to mark the book as returned.",
            None,
            tab_index=0
        ))
        t3.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Perfect! The book is now marked as returned and is available for checkout again.",
            None
        ))
        self.tutorials["return_book"] = t3
        
        # Tutorial 4: Search
        t4 = SimpleTutorial("search", "Search for Students or Books",
                           "Learn how to quickly find records", "🔍")
        t4.add_step(SimpleTutorialStep(
            "Go to Students Tab",
            "Let's start by going to the Students tab to search for a student.",
            lambda: self._get_tab_widget(0),
            tab_index=0
        ))
        t4.add_step(SimpleTutorialStep(
            "Use Search Box",
            "Look for the search box in the toolbar. Type a student's name, ID, or level, then press Enter or click the Search button.",
            None,
            tab_index=0
        ))
        t4.add_step(SimpleTutorialStep(
            "View Results",
            "The list will filter to show only matching students. Press Refresh to see everyone again.",
            None,
            tab_index=0
        ))
        t4.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Great! The Items tab searches items the same way, and the Books tab's search finds students.",
            None
        ))
        self.tutorials["search"] = t4
        
        # Tutorial 5: Take Attendance
        t5 = SimpleTutorial("take_attendance", "Take Daily Attendance",
                           "Learn how to mark students present or absent", "✅")
        t5.add_step(SimpleTutorialStep(
            "Navigate to Attendance",
            "Click on the 'Attendance' tab to see today's attendance list.",
            lambda: self._get_tab_widget(3),
            tab_index=3
        ))
        t5.add_step(SimpleTutorialStep(
            "Select a Student",
            "Click on a student in the attendance list to select them.",
            None,
            tab_index=3
        ))
        t5.add_step(SimpleTutorialStep(
            "Mark Attendance",
            "Use the buttons at the bottom to mark the student as:\n• Present (green)\n• Absent (red)\n• Late (yellow)",
            None,
            tab_index=3
        ))
        t5.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Excellent! The attendance is saved automatically. Repeat for all students in the class.",
            None
        ))
        self.tutorials["take_attendance"] = t5
        
        # Tutorial 6: Add an Item
        t6 = SimpleTutorial("add_item", "Add a New Item",
                           "Learn how to add items like calculators, tablets, etc.", "📦")
        t6.add_step(SimpleTutorialStep(
            "Go to Items Tab",
            "Click on the 'Items' tab to view all non-book items.",
            lambda: self._get_tab_widget(1),
            tab_index=1
        ))
        t6.add_step(SimpleTutorialStep(
            "Click Add Button",
            "Click the green '➕ Add' button in the toolbar.",
            None,
            tab_index=1
        ))
        t6.add_step(SimpleTutorialStep(
            "Fill in Item Details",
            "A dialog will appear. Fill in:\n• Item ID (unique identifier)\n• Name (e.g., 'Calculator', 'iPad')\n• Category (optional)\n\nThen click OK to save.",
            None
        ))
        t6.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Done! The item is now in the system and can be checked out to students.",
            None
        ))
        self.tutorials["add_item"] = t6
        
        # Tutorial 7: Add a Book Manually
        t7 = SimpleTutorial("add_book", "Add a New Book",
                           "Learn how to manually add a book to the library", "📖")
        t7.add_step(SimpleTutorialStep(
            "Go to Books Tab",
            "Click on the 'Books' tab to view all books in the system.",
            lambda: self._get_tab_widget(2),
            tab_index=2
        ))
        t7.add_step(SimpleTutorialStep(
            "Click Add Button",
            "Click the green '➕ Add' button in the toolbar.",
            None,
            tab_index=2
        ))
        t7.add_step(SimpleTutorialStep(
            "Fill in Book Details",
            "A dialog will appear. Fill in:\n• Book ID (unique identifier, can be ISBN)\n• Title\n• Author\n• Genre (optional)\n\nThen click OK to save.",
            None
        ))
        t7.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Perfect! The book is now in the library system and can be checked out to students.",
            None
        ))
        self.tutorials["add_book"] = t7
        
        # Tutorial 8: Manual Student Check-in
        t8 = SimpleTutorial("manual_checkin", "Manually Check In a Student",
                           "Learn how to mark attendance without QR scanner", "✋")
        t8.add_step(SimpleTutorialStep(
            "Go to Attendance Tab",
            "Click on the 'Attendance' tab to see today's attendance.",
            lambda: self._get_tab_widget(3),
            tab_index=3
        ))
        t8.add_step(SimpleTutorialStep(
            "Find the Student",
            "Look through the list or use the search box to find the student who is checking in.",
            None,
            tab_index=3
        ))
        t8.add_step(SimpleTutorialStep(
            "Click on Student",
            "Click on the student's name in the attendance list to select them.",
            None,
            tab_index=3
        ))
        t8.add_step(SimpleTutorialStep(
            "Mark Present",
            "Click the 'Present' button (green) at the bottom to mark them as checked in.",
            None,
            tab_index=3
        ))
        t8.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Done! The student is now marked as present. This works when the QR scanner is offline or unavailable.",
            None
        ))
        self.tutorials["manual_checkin"] = t8
        
        # Tutorial 9: Generate QR Codes
        t9 = SimpleTutorial("generate_qr", "Generate QR Codes",
                           "Learn how to create QR codes for items and students", "📱")
        t9.add_step(SimpleTutorialStep(
            "Open QR Menu",
            "At the top of the window, click on the 'QR' menu.",
            None
        ))
        t9.add_step(SimpleTutorialStep(
            "Choose What to Generate",
            "Select either:\n• 'Generate QR for All Items' - creates QR codes for all items\n• 'Generate QR for All Students' - creates QR codes for all students",
            None
        ))
        t9.add_step(SimpleTutorialStep(
            "Save QR Codes",
            "No folder is asked for: the QR code images are saved in data\\qr\\items and data\\qr\\students.",
            None
        ))
        t9.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Perfect! You can now print these QR codes and attach them to physical items or student ID cards for quick scanning.",
            None
        ))
        self.tutorials["generate_qr"] = t9
        
        # Tutorial 10: Load Schedule
        t10 = SimpleTutorial("load_schedule", "Load Class Schedule",
                           "Learn how to automatically load students for today's class", "📅")
        t10.add_step(SimpleTutorialStep(
            "Go to Attendance Tab",
            "Click on the 'Attendance' tab.",
            lambda: self._get_tab_widget(3),
            tab_index=3
        ))
        t10.add_step(SimpleTutorialStep(
            "Click Load Schedule",
            "Click the 'Load Schedule' button at the bottom of the attendance section.",
            None,
            tab_index=3
        ))
        t10.add_step(SimpleTutorialStep(
            "Select Schedule File",
            "Choose your CSV schedule file. The file should have columns for:\n• Day of week\n• Time\n• Level/Class\n• Room (optional)",
            None
        ))
        t10.add_step(SimpleTutorialStep(
            "Tutorial Complete!",
            "Great! The system automatically loaded all students who have class today at this time. Now you can quickly mark their attendance.",
            None
        ))
        self.tutorials["load_schedule"] = t10
    
    def _get_tab_widget(self, index):
        """Get a tab frame by index"""
        try:
            if hasattr(self.main_window, 'notebook'):
                tab_id = self.main_window.notebook.tabs()[index]
                return self.main_window.nametowidget(tab_id)
        except Exception as e:
            print(f"Could not get tab: {e}")
        return None
    
    def _find_button_by_text(self, text):
        """Find a button containing specific text"""
        try:
            # Search through all children of main window
            for widget in self.main_window.winfo_children():
                if self._search_widget_tree(widget, text, tk.Button):
                    return widget
            
            # Also search in notebook tabs
            if hasattr(self.main_window, 'notebook'):
                for tab_id in self.main_window.notebook.tabs():
                    tab = self.main_window.nametowidget(tab_id)
                    result = self._search_widget_tree(tab, text, tk.Button)
                    if result:
                        return result
        except Exception as e:
            print(f"Could not find button: {e}")
        return None
    
    def _search_widget_tree(self, widget, text, widget_type):
        """Recursively search widget tree for a button with specific text"""
        try:
            if isinstance(widget, widget_type):
                button_text = widget.cget('text')
                if text.lower() in button_text.lower():
                    return widget
            
            for child in widget.winfo_children():
                result = self._search_widget_tree(child, text, widget_type)
                if result:
                    return result
        except:
            pass
        return None
    
    def get_tutorial_list(self) -> List[SimpleTutorial]:
        """Get the tutorials that are offered (all but _NOT_OFFERED)"""
        return [t for k, t in self.tutorials.items() if k not in _NOT_OFFERED]
    
    def start_tutorial(self, tutorial_id: str):
        """Start a tutorial"""
        if tutorial_id not in self.tutorials:
            return False
        
        if self.is_active:
            self.stop_tutorial()
        
        self.current_tutorial = self.tutorials[tutorial_id]
        self.current_step_index = 0
        self.is_active = True
        
        self._show_current_step()
        return True
    
    def _show_current_step(self):
        """Show the current tutorial step"""
        if not self.current_tutorial or self.current_step_index >= len(self.current_tutorial.steps):
            self._complete_tutorial()
            return
        
        # Clear any previous highlights
        self._clear_highlights()
        
        step = self.current_tutorial.steps[self.current_step_index]
        
        # Switch to correct tab if specified
        if step.tab_index is not None:
            try:
                self.main_window.notebook.select(step.tab_index)
                self.main_window.update_idletasks()
                # Small delay to let tab switch complete
                self.main_window.after(100, lambda: self._continue_step(step))
            except Exception as e:
                print(f"Could not switch tab: {e}")
                self._continue_step(step)
        else:
            self._continue_step(step)
    
    def _continue_step(self, step: SimpleTutorialStep):
        """Continue showing step after tab switch"""
        # Highlight widget if specified
        if step.widget_getter:
            try:
                widget = step.widget_getter()
                if widget:
                    self._highlight_widget(widget)
            except Exception as e:
                print(f"Could not highlight widget: {e}")
        
        # Show instruction window
        self._show_instruction_window(step)
    
    def _highlight_widget(self, widget):
        """Highlight a widget with a colored border"""
        try:
            # Store original configuration
            self.original_configs[widget] = {
                'highlightthickness': widget.cget('highlightthickness'),
                'highlightbackground': widget.cget('highlightbackground'),
                'highlightcolor': widget.cget('highlightcolor')
            }
            
            # Apply highlight
            widget.configure(
                highlightthickness=3,
                highlightbackground=theme.colour('accent', '#3498db'),
                highlightcolor=theme.colour('accent', '#3498db')
            )
            
            self.highlight_widgets.append(widget)
        except Exception as e:
            print(f"Could not highlight widget: {e}")
    
    def _clear_highlights(self):
        """Remove all highlights"""
        for widget in self.highlight_widgets:
            try:
                if widget.winfo_exists() and widget in self.original_configs:
                    widget.configure(**self.original_configs[widget])
            except:
                pass
        
        self.highlight_widgets.clear()
        self.original_configs.clear()
    
    def _show_instruction_window(self, step: SimpleTutorialStep):
        """Show instruction window as a small floating dialog"""
        if self.instruction_window and self.instruction_window.winfo_exists():
            self.instruction_window.destroy()
        
        self.instruction_window = tk.Toplevel(self.main_window)
        self.instruction_window.title("📚 Tutorial")
        self.instruction_window.protocol("WM_DELETE_WINDOW", self.stop_tutorial)
        self.instruction_window.configure(bg=theme.colour('side', '#2c3e50'))
        
        # Make it a small window, not fullscreen
        window_width = 450
        window_height = 300
        
        # Header with progress bar
        header = tk.Frame(self.instruction_window, bg=theme.colour('primary', '#3498db'), height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_text = f"Step {self.current_step_index + 1} of {len(self.current_tutorial.steps)}: {step.title}"
        tk.Label(header, text=title_text, bg=theme.colour('primary', '#3498db'), fg='white',
                font=('Arial', 10, 'bold'), padx=15).pack(side=tk.LEFT, pady=10)
        
        # Progress indicator
        progress_frame = tk.Frame(self.instruction_window, bg=theme.colour('side', '#2c3e50'), height=8)
        progress_frame.pack(fill=tk.X)
        progress_frame.pack_propagate(False)
        
        progress_percent = (self.current_step_index + 1) / len(self.current_tutorial.steps)
        progress_width = int(window_width * progress_percent)
        
        progress_bar = tk.Frame(progress_frame, bg=theme.colour('accent', '#27ae60'), width=progress_width, height=8)
        progress_bar.pack(side=tk.LEFT)
        
        # Content
        content = tk.Frame(self.instruction_window, bg=theme.colour('side', '#2c3e50'))
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(content, text=step.instruction, bg=theme.colour('side', '#2c3e50'), fg='white',
                font=('Arial', 11), wraplength=400, justify='left').pack(pady=(0, 20))
        
        # Buttons
        btn_frame = tk.Frame(content, bg=theme.colour('side', '#2c3e50'))
        btn_frame.pack(fill=tk.X)
        
        theme.flat_button(btn_frame, 'danger', text="⏭️ Skip Tutorial", bg='#e74c3c', fg='white',
                 font=('Arial', 9, 'bold'), padx=12, pady=6,
                 command=self.stop_tutorial).pack(side=tk.LEFT)
        
        if self.current_step_index < len(self.current_tutorial.steps) - 1:
            theme.flat_button(btn_frame, 'primary', text="Next ➡️", bg='#27ae60', fg='white',
                     font=('Arial', 9, 'bold'), padx=15, pady=6,
                     command=self._next_step).pack(side=tk.RIGHT)
        else:
            theme.flat_button(btn_frame, 'primary', text="Finish ✓", bg='#27ae60', fg='white',
                     font=('Arial', 9, 'bold'), padx=15, pady=6,
                     command=self._complete_tutorial).pack(side=tk.RIGHT)
        
        # Position in bottom-right corner
        self.instruction_window.update_idletasks()
        
        screen_width = self.instruction_window.winfo_screenwidth()
        screen_height = self.instruction_window.winfo_screenheight()
        
        x = screen_width - window_width - 50
        y = screen_height - window_height - 100
        
        self.instruction_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.instruction_window.attributes('-topmost', True)
        self.instruction_window.lift()

    def _next_step(self):
        """Move to next step"""
        self.current_step_index += 1
        self._show_current_step()
    
    def _complete_tutorial(self):
        """Complete the tutorial"""
        if self.current_tutorial:
            self.completed_tutorials.add(self.current_tutorial.tutorial_id)
            self._save_progress()
        
        self.stop_tutorial()
        
        # Show completion message
        from tkinter import messagebox
        messagebox.showinfo("Tutorial Complete! 🎉",
                          "Great job! You've completed the tutorial.\n\n"
                          "You can replay any tutorial at any time from the Tutorials menu.")
    
    def stop_tutorial(self):
        """Stop the current tutorial"""
        self._clear_highlights()
        
        if self.instruction_window and self.instruction_window.winfo_exists():
            self.instruction_window.destroy()
        
        self.current_tutorial = None
        self.current_step_index = 0
        self.is_active = False
    
    def is_tutorial_completed(self, tutorial_id: str) -> bool:
        """Check if tutorial is completed"""
        return tutorial_id in self.completed_tutorials
    
    def reset_progress(self):
        """Reset all progress"""
        self.completed_tutorials.clear()
        self._save_progress()
    
    def show_tutorial_selection(self):
        """Show a large tutorial selection dialog with tutorials in a grid"""
        if self.selection_window and self.selection_window.winfo_exists():
            self.selection_window.lift()
            return
        
        self.selection_window = tk.Toplevel(self.main_window)
        self.selection_window.title("📚 Tutorial Center - Choose a Tutorial")
        self.selection_window.configure(bg=theme.colour('ground', '#ecf0f1'))
        
        # Make it a large window (80% of screen)
        screen_width = self.selection_window.winfo_screenwidth()
        screen_height = self.selection_window.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.selection_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Header
        header = tk.Frame(self.selection_window, bg=theme.colour('side', '#2c3e50'), height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📚 Tutorial Center", bg=theme.colour('side', '#2c3e50'), fg='white',
                font=('Arial', 24, 'bold')).pack(pady=25)
        
        # Scrollable content area
        canvas = tk.Canvas(self.selection_window, bg=theme.colour('ground', '#ecf0f1'), highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.selection_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=theme.colour('ground', '#ecf0f1'))
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Make canvas window fill the canvas width
        def _configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        # Enable mouse wheel scrolling - bind to canvas only, not bind_all
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        # Bind mousewheel only when mouse enters the canvas
        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)
        
        # Unbind when window closes to prevent conflicts
        def _on_close():
            canvas.unbind_all("<MouseWheel>")
            self.selection_window.destroy()
        
        self.selection_window.protocol("WM_DELETE_WINDOW", _on_close)
        
        # Add some padding
        content = tk.Frame(scrollable_frame, bg=theme.colour('ground', '#ecf0f1'))
        content.pack(padx=40, pady=30, fill=tk.BOTH, expand=True)
        
        # Create tutorial cards in a grid (3 columns)
        tutorials = self.get_tutorial_list()
        columns = 3
        
        # Configure all columns to have equal weight
        for col in range(columns):
            content.grid_columnconfigure(col, weight=1, uniform='col')
        
        for idx, tutorial in enumerate(tutorials):
            row = idx // columns
            col = idx % columns
            
            self._create_tutorial_card(content, tutorial, row, col)
        
        # Bottom bar with close button, packed before the canvas so the canvas cannot take its room (B5b-15)
        bottom_bar = tk.Frame(self.selection_window, bg=theme.colour('side', '#34495e'), height=60)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        bottom_bar.pack_propagate(False)
        
        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update close button to use the new close function
        theme.flat_button(bottom_bar, 'secondary', text="✖ Close", bg='#e74c3c', fg='white',
                 font=('Arial', 11, 'bold'), padx=20, pady=8,
                 command=_on_close).pack(side=tk.RIGHT, padx=20, pady=12)
        
        theme.flat_button(bottom_bar, 'warning', text="🔄 Reset Progress", bg='#95a5a6', fg='white',
                 font=('Arial', 11, 'bold'), padx=20, pady=8,
                 command=self._reset_and_refresh).pack(side=tk.LEFT, padx=20, pady=12)
    
    def _create_tutorial_card(self, parent, tutorial: SimpleTutorial, row: int, col: int):
        """Create a single tutorial card"""
        is_completed = self.is_tutorial_completed(tutorial.tutorial_id)
        
        # Card frame
        card = tk.Frame(parent, bg=theme.colour('card', 'white'), relief=tk.RAISED, borderwidth=2)
        card.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')
        
        # Don't configure grid weights here - it's done in show_tutorial_selection
        
        # Inner padding
        inner = tk.Frame(card, bg=theme.colour('card', 'white'))
        inner.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Icon and title
        header_frame = tk.Frame(inner, bg=theme.colour('card', 'white'))
        header_frame.pack(fill=tk.X)
        
        icon_label = tk.Label(header_frame, text=tutorial.icon, bg=theme.colour('card', 'white'),
                             font=('Arial', 36))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_frame = tk.Frame(header_frame, bg=theme.colour('card', 'white'))
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(title_frame, text=tutorial.name, bg=theme.colour('card', 'white'),
                font=('Arial', 14, 'bold'), anchor='w', justify='left').pack(anchor='w')
        
        # Completion badge
        if is_completed:
            badge = tk.Label(title_frame, text="✓ Completed", bg=theme.colour('primary', '#27ae60'), fg='white',
                           font=('Arial', 9, 'bold'), padx=8, pady=2)
            badge.pack(anchor='w', pady=(5, 0))
        
        # Description
        tk.Label(inner, text=tutorial.description, bg=theme.colour('card', 'white'), fg=theme.colour('ink_muted', '#7f8c8d'),
                font=('Arial', 10), wraplength=220, justify='left', anchor='w').pack(pady=(15, 0), anchor='w')
        
        # Step count
        tk.Label(inner, text=f"{len(tutorial.steps)} steps", bg=theme.colour('card', 'white'), fg=theme.colour('ink_muted', '#95a5a6'),
                font=('Arial', 9, 'italic')).pack(pady=(10, 15), anchor='w')
        
        # Start button
        btn_text = "▶ Start Tutorial" if not is_completed else "🔄 Replay Tutorial"
        btn_color = '#3498db' if not is_completed else '#9b59b6'
        
        start_btn = theme.flat_button(inner, 'primary', text=btn_text, bg=btn_color, fg='white',
                             font=('Arial', 11, 'bold'), padx=15, pady=8,
                             cursor='hand2',
                             command=lambda t=tutorial: self._start_from_selection(t))
        start_btn.pack(fill=tk.X)
        
        # Hover effects
        def on_enter(e):
            card.configure(relief=tk.RAISED, borderwidth=3)
            start_btn.configure(bg=theme.colour('primary_dark', self._darken_color(btn_color)))
        
        def on_leave(e):
            card.configure(relief=tk.RAISED, borderwidth=2)
            start_btn.configure(bg=theme.colour('primary', btn_color))
        
        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        start_btn.bind('<Enter>', on_enter)
        start_btn.bind('<Leave>', on_leave)
    
    def _darken_color(self, hex_color):
        """Darken a hex color slightly for hover effect"""
        # Simple darkening by reducing RGB values
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _start_from_selection(self, tutorial: SimpleTutorial):
        """Start a tutorial from the selection window"""
        if self.selection_window and self.selection_window.winfo_exists():
            self.selection_window.destroy()
        self.start_tutorial(tutorial.tutorial_id)
    
    def _reset_and_refresh(self):
        """Reset progress and refresh the selection window"""
        from tkinter import messagebox
        if messagebox.askyesno("Reset Progress", 
                              "Are you sure you want to reset all tutorial progress?"):
            self.reset_progress()
            # Refresh the window
            if self.selection_window and self.selection_window.winfo_exists():
                self.selection_window.destroy()
            self.show_tutorial_selection()
