# Tutorial System - Visual Guide

## What Users Will See

### 1. Tutorial Selector (Main Screen)
```
┌────────────────────────────────────────────────────────┐
│ 📚 Interactive Tutorials                    [Help]     │
├────────────────────────────────────────────────────────┤
│ Choose a tutorial to learn how to use the system      │
├────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │ 👤 Add a New Student                  ✓ Completed│   │
│ │ Learn how to add a new student to the system     │   │
│ │ 3 steps                             [▶ Start]    │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │ 📚 Check Out a Book                              │   │
│ │ Learn how to check out a book using QR codes     │   │
│ │ 4 steps                             [▶ Start]    │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │ ✅ Take Daily Attendance                         │   │
│ │ Learn how to mark students present or absent     │   │
│ │ 3 steps                             [▶ Start]    │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ [more tutorials...]                                    │
│                                                         │
│ [Reset Progress]                           [Close]     │
└────────────────────────────────────────────────────────┘
```

### 2. Tutorial In Progress
```
┌────────────────────────────────────────────────────────┐
│                                                         │
│    [Dark semi-transparent overlay covering screen]     │
│                                                         │
│      ┌──────────────────────────────────┐              │
│      │ 📚 Tutorial                      │              │
│      ├──────────────────────────────────┤              │
│      │                                  │              │
│      │ Now click the green '➕ Add'     │              │
│      │ button to add a new student.    │              │
│      │                                  │              │
│      │ [⏭️ Skip Tutorial]  [Next ➡️]   │              │
│      └──────────────────────────────────┘              │
│                  ↓ [Arrow pointing down]               │
│                                                         │
│      ┌──────────────────────────────────┐              │
│      │  [➕ Add]  [✏️ Edit]  [🗑️ Delete] │  ← Highlighted
│      └──────────────────────────────────┘              │
│                                                         │
│    [Rest of screen is dimmed]                          │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 3. Entry Points

#### A. Footer Button (Always Visible)
```
┌────────────────────────────────────────────────────────┐
│                                                         │
│  [Main Application Content]                            │
│                                                         │
├────────────────────────────────────────────────────────┤
│ Pear v2    [📚 Tutorials]                    [⚙ Settings] │
└────────────────────────────────────────────────────────┘
```

#### B. Help Menu
```
┌────────────────────────────────────────────────────────┐
│ File  Data  QR  View  Help                             │
│                        │                                │
│                        ├─ 📚 Interactive Tutorials      │
│                        ├────────────────                │
│                        └─ About Pear v2                 │
│                                                         │
└────────────────────────────────────────────────────────┘
```

## Color Scheme

### Tutorial Selector
- **Header Background**: Blue (#3498db)
- **Completed Badge**: Green (#27ae60)
- **Start Buttons**: Blue (#3498db)
- **Reset Button**: Red (#e74c3c)
- **Card Background**: Light Gray (#ecf0f1)

### Tutorial Overlay
- **Overlay**: Semi-transparent Black (85% opacity)
- **Spotlight**: White with Blue Border (#3498db, 3px)
- **Instruction Box**:
  - Title Bar: Blue (#3498db)
  - Background: Dark Gray (#2c3e50)
  - Text: White
- **Buttons**:
  - Skip: Red (#e74c3c)
  - Next: Green (#27ae60)
- **Arrow**: Blue (#3498db, 4px width)

### Footer Tutorial Button
- **Background**: Purple (#9b59b6)
- **Text**: White, Bold

## User Flow

```
User Opens App
     │
     ├─→ Clicks "📚 Tutorials" (Footer)
     │         │
     │         └─→ Tutorial Selector Opens
     │                    │
     │                    ├─→ User Clicks "▶ Start" on Tutorial
     │                    │          │
     │                    │          └─→ Tutorial Begins
     │                    │                    │
     │                    │                    ├─→ Step 1: Overlay Shows
     │                    │                    │         │
     │                    │                    │         ├─→ User Follows Instruction
     │                    │                    │         │         │
     │                    │                    │         │         └─→ Clicks "Next"
     │                    │                    │         │
     │                    │                    ├─→ Step 2: Next Overlay
     │                    │                    │         │
     │                    │                    │         └─→ [Repeat]
     │                    │                    │
     │                    │                    └─→ Final Step: Completion Message
     │                    │                              │
     │                    │                              └─→ Tutorial Marked Complete
     │                    │
     │                    └─→ OR User Clicks "⏭️ Skip Tutorial"
     │                              │
     │                              └─→ Tutorial Exits
     │
     └─→ OR Clicks Help Menu → "📚 Interactive Tutorials"
               │
               └─→ [Same flow as above]
```

## Keyboard Shortcuts

During tutorial selector:
- **Escape**: Close selector

During tutorial:
- **Escape**: Skip tutorial (if implemented)

## Responsive Design

- Tutorial selector is fixed size (700x550px)
- Instruction boxes are 400x200px
- Overlay covers entire main window
- Spotlight padding: 10px around target widget
- Arrow length: 20-30px

## Tutorial Step Types

### 1. Action Steps
- User must click/interact with highlighted element
- "Next" button is hidden
- Tutorial advances automatically when action is detected

### 2. Information Steps
- No action required
- "Next" button is visible
- User clicks "Next" to proceed

### 3. Tab Navigation Steps
- Automatically switches to correct tab
- Highlights tab at top of screen
- User clicks tab to proceed

### 4. Completion Steps
- Final step showing success message
- "Next" button or auto-close after delay
- Saves tutorial as completed

## Animation (Future Enhancement)

Potential animations to add:
- Fade in/out for overlay
- Pulse effect on highlighted widget
- Arrow bounce animation
- Confetti on tutorial completion
- Smooth transitions between steps

## Accessibility

- High contrast colors
- Large, readable fonts
- Clear, simple language
- Keyboard navigation support (future)
- Screen reader compatibility (future)

---

This visual guide helps understand how users will experience the tutorial system!
