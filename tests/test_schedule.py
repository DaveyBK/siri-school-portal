from ui.main_window import MainWindow
import tkinter as tk

# Create main window
root = MainWindow()
root.after(100, lambda: print(f'Schedule highlighted column: {root.schedule_highlighted_column}'))
root.after(200, lambda: print(f'Schedule tree has children: {len(root.schedule_tree.get_children())}'))
root.after(300, lambda: print(f'Saturday classes: {root.schedule_classes_by_day.get("saturday", [])}'))
root.after(400, lambda: root.quit())
root.mainloop()
print('Done')
