# Interactive Tutorial System for Pear v2

## Overview
The Interactive Tutorial System provides step-by-step guided tutorials for non-tech-savvy users to learn how to use the Pear v2 School Inventory Management System.

## Features

### ✅ Available Tutorials
1. **Add a New Student** - Learn how to add students to the system
2. **Check Out a Book** - Learn the QR code book checkout process
3. **Take Daily Attendance** - Learn how to mark attendance
4. **Search for Students or Books** - Learn how to use the search feature
5. **Return a Book** - Learn how to process book returns
6. **Add a New Book or Item** - Learn how to add inventory items
7. **Generate QR Codes** - Learn how to create QR codes for students and books
8. **Load Class Schedule** - Learn how to load and view weekly schedules

### 🎨 Visual Features
- **Dark Overlay**: Dims the application background during tutorials
- **Spotlight Effect**: Highlights the active button/widget the user should interact with
- **Instruction Box**: Shows clear, step-by-step instructions
- **Arrows**: Points to the exact element the user needs to click
- **Progress Tracking**: Tracks completed tutorials with checkmarks

### 🌍 Multilingual Support
The tutorial system is designed to work with the app's existing English/Thai language toggle.

## How to Access Tutorials

### Method 1: Help Menu
1. Click on the **Help** menu in the menu bar
2. Select **📚 Interactive Tutorials**
3. Choose a tutorial from the list

### Method 2: Footer Button
1. Look at the bottom of the application
2. Click the purple **📚 Tutorials** button
3. Choose a tutorial from the list

## Using a Tutorial

### Starting a Tutorial
1. From the Tutorial Selector, click **▶ Start** on any tutorial
2. The tutorial will begin with step 1
3. A dark overlay will appear with a spotlight on the relevant button/area
4. Read the instruction in the blue instruction box

### During a Tutorial
- **Follow Instructions**: Each step tells you exactly what to do
- **Click Next**: After completing an action, click the **Next ➡️** button
- **Skip Tutorial**: Click **⏭️ Skip Tutorial** at any time to exit
- **Tab Switching**: Tutorials automatically switch to the correct tab

### Tutorial Completion
- When you finish a tutorial, it's marked with a ✓ **Completed** badge
- You can replay any tutorial at any time
- Progress is saved automatically

## For Administrators

### Tutorial Progress Tracking
- Tutorial completion is tracked per user
- Progress is saved to: `data/tutorial_progress.json`
- Click **Reset Progress** in the Tutorial Selector to clear all completion records

### Adding New Tutorials
To add a new tutorial, edit `ui/tutorial_system.py`:

```python
def _init_tutorials(self):
    # Create a new tutorial
    new_tutorial = Tutorial(
        "tutorial_id",           # Unique ID
        "Tutorial Name",         # Display name
        "Description text",      # Description shown in selector
        "🎓"                     # Icon emoji
    )
    
    # Add steps
    new_tutorial.add_step(TutorialStep(
        "step_id",              # Unique step ID
        "Step Title",           # Step title
        "Instruction text",     # What the user should do
        "widget_name",          # Widget to highlight (or None)
        "bottom",               # Position: bottom, top, left, right, center
        wait_for_action=True,   # Wait for user action or auto-advance
        tab_index=0             # Which tab to switch to (or None)
    ))
    
    # Register the tutorial
    self.tutorials["tutorial_id"] = new_tutorial
```

### Widget Names Reference
Map of widget names you can use in tutorials:
- `students_tab` - Students tab
- `items_tab` - Items tab
- `books_tab` - Books tab
- `attendance_tab` - Attendance tab
- `schedule_tab` - Schedule tab
- `students_tree` - Student list treeview
- `items_tree` - Items list treeview
- `assignments_tree` - Book assignments list
- `attendance_tree` - Attendance list
- `students_search` - Student search box

To add more widgets, update the `_find_widget()` method in `TutorialManager`.

## Technical Details

### Files
- `ui/tutorial_system.py` - Main tutorial system implementation
- `ui/main_window.py` - Integration into main application
- `data/tutorial_progress.json` - User progress tracking (auto-created)

### Classes
- **TutorialOverlay** - Creates the visual overlay and spotlight effect
- **TutorialStep** - Represents a single step in a tutorial
- **Tutorial** - Represents a complete tutorial with multiple steps
- **TutorialManager** - Manages all tutorials and execution
- **TutorialSelectorDialog** - UI for selecting which tutorial to run

### Dependencies
- tkinter (built-in)
- PIL/Pillow (for images, already required by main app)
- json (built-in)
- pathlib (built-in)

## Customization

### Changing Colors
Edit the color values in `tutorial_system.py`:
```python
# Instruction box title bar
bg='#3498db'  # Blue

# Spotlight border
outline='#3498db'  # Blue

# Tutorial button in footer (main_window.py)
bg='#9b59b6'  # Purple
```

### Changing Text
All instructional text is in the `_init_tutorials()` method in `tutorial_system.py`. Edit the instruction strings for each `TutorialStep`.

### Adding Translations
To add Thai translations:
1. Update each `TutorialStep` instruction text with a translation key
2. Modify the tutorial system to use the `t()` method from main_window
3. Add translation strings to the TRANSLATIONS dictionary in main_window.py

## Best Practices

### For Tutorial Creators
1. **Keep instructions short** - One clear action per step
2. **Use simple language** - Remember, users are non-tech-savvy
3. **Test thoroughly** - Walk through each tutorial to ensure widgets are found
4. **Provide context** - Explain WHY the user is doing something, not just WHAT
5. **Show outcomes** - Final steps should mention what happens after completion

### For Users
1. **Take your time** - Tutorials are designed to be followed at your own pace
2. **Try it yourself** - Tutorials use real actions, not simulations
3. **Repeat if needed** - You can replay any tutorial as many times as you want
4. **Ask for help** - If a tutorial is confusing, suggest improvements to admin

## Troubleshooting

### Tutorial button doesn't appear
- Ensure `tutorial_system.py` is in the `ui/` folder
- Check that the import statement is correct in `main_window.py`
- Verify Python can find the module

### Widgets not highlighting correctly
- Check widget names in `_find_widget()` method
- Ensure the widget exists and is created before tutorial starts
- Use `print()` statements to debug widget lookup

### Overlay doesn't show
- Make sure tkinter supports transparency on your system
- Try updating tkinter/Python version
- Check if other windows are blocking the overlay

### Progress not saving
- Verify write permissions for `data/` folder
- Check if `data/tutorial_progress.json` can be created
- Look for exceptions in console/logs

## Future Enhancements

Potential improvements for future versions:
- [ ] Voice narration support
- [ ] Video tutorials embedded in instruction boxes
- [ ] Practice mode with dummy data
- [ ] Tooltips that stay on screen after tutorial
- [ ] Tutorial playlists (sequential tutorials)
- [ ] Gamification (badges, points for completing tutorials)
- [ ] User feedback system for tutorials
- [ ] Admin dashboard for tutorial analytics

## Support

If you encounter issues or have suggestions for new tutorials:
1. Note the specific tutorial and step number
2. Describe what you expected vs. what happened
3. Check the console for error messages
4. Contact your system administrator

---

**Version**: 1.0  
**Last Updated**: November 2025  
**Compatible with**: Pear v2
