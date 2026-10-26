# 🚀 Quick Start - Tutorial System

## For End Users (Non-Tech-Savvy)

### How to Learn Using Tutorials

**Step 1**: Open the App  
Launch Pear v2 as normal

**Step 2**: Find the Tutorial Button  
Look at the **bottom** of the screen for a **purple button** that says **"📚 Tutorials"**

**Step 3**: Choose What to Learn  
A window will pop up showing different lessons:
- Adding students
- Checking out books
- Taking attendance
- And more!

**Step 4**: Start Learning  
Click the **"▶ Start"** button next to any lesson

**Step 5**: Follow Along  
- The screen will get dark
- A blue box will show you instructions
- An arrow will point to what to click
- Read the instructions carefully
- Do what it says!

**Step 6**: Move to Next Step  
After you do the action, click the green **"Next ➡️"** button

**Step 7**: Exit Anytime  
Don't understand? No problem!  
Click the red **"⏭️ Skip Tutorial"** button at any time

### Tips for Learning
- 📖 **Read carefully** - Each instruction tells you exactly what to do
- 🐢 **Go slow** - Take your time, there's no rush
- 🔁 **Repeat** - You can do the same tutorial multiple times
- ✅ **Check off** - Completed tutorials get a green checkmark
- 💡 **Try it out** - After the tutorial, practice on your own

---

## For Teachers/Admins

### Quick Setup Checklist

- [x] Files already added to project
- [x] Menu item added (Help → Interactive Tutorials)
- [x] Footer button added (purple button)
- [x] 8 tutorials pre-configured
- [ ] Test all tutorials work correctly
- [ ] Train staff on how to use tutorials
- [ ] Optional: Customize tutorial text
- [ ] Optional: Add Thai translations

### How to Test

1. Run the application
2. Click the purple **"📚 Tutorials"** button (bottom of screen)
3. Start the "Add a New Student" tutorial
4. Verify:
   - Dark overlay appears
   - Students tab is highlighted
   - Instruction box shows
   - Arrow points to button
   - Can click "Next"
   - Can click "Skip"

### Recommended Training Order

For new staff, recommend completing tutorials in this order:

**Day 1 - Basics:**
1. Search for Students or Books (easiest)
2. Add a New Student
3. Take Daily Attendance

**Day 2 - Library Functions:**
4. Check Out a Book
5. Return a Book
6. Add a New Book/Item

**Day 3 - Advanced:**
7. Load Class Schedule
8. Generate QR Codes

### Common Questions

**Q: Can tutorials break anything?**  
A: No! Tutorials guide users through real actions, but they can skip at any time without consequences.

**Q: Do users need to complete all tutorials?**  
A: No. Users can pick and choose which ones they need.

**Q: Can we customize the tutorial text?**  
A: Yes! Edit `ui/tutorial_system.py` in the `_init_tutorials()` method.

**Q: How do we reset someone's progress?**  
A: Click "Reset Progress" in the tutorial selector, or delete `data/tutorial_progress.json`.

**Q: Can we add our own tutorials?**  
A: Yes! See `TUTORIAL_SYSTEM_README.md` for instructions.

---

## Troubleshooting

### Button Not Showing?
1. Check `ui/tutorial_system.py` file exists
2. Restart the application
3. Check Python console for errors

### Tutorial Not Working?
1. Try clicking "Skip" and restarting it
2. Make sure you're on the latest version
3. Check if the feature exists (some tutorials require certain features)

### Overlay Stuck on Screen?
1. Press Escape key
2. Click "Skip Tutorial"
3. Restart application if needed

---

## Success Metrics

Track tutorial effectiveness by monitoring:
- ✅ Number of tutorials completed
- ✅ Which tutorials are most popular
- ✅ User feedback on clarity
- ✅ Reduction in support questions

---

## Contact Support

If you have issues or suggestions:
1. Note which tutorial you were using
2. Note which step number
3. Describe what you expected vs. what happened
4. Contact your IT admin or system developer

---

**Remember**: The tutorials are here to help! Take your time and learn at your own pace. 🎓

Happy Learning! 📚✨
