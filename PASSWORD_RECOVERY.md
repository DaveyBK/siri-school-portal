# School Portal: password recovery

## If you are locked out

The portal shows "The portal is locked: the password file is missing or unreadable" when `data\credentials.json`
is missing, damaged, or still in the old plain-text form. It shows "bcrypt is not installed for ..." when the Python
that started the portal does not have bcrypt (the message names that Python). The portal never falls back to a
built-in password.

The portal runs under `C:\Python313\python.exe`. Use that Python for every command below, in a terminal opened in
the `school_portal` folder (the folder that holds `app.py`). Close the portal first.

1. Make sure bcrypt is installed for that Python:
   `C:\Python313\python.exe -c "import bcrypt"` should print nothing.
   If it fails, run `C:\Python313\python.exe -m pip install "bcrypt>=4.0.0"`, then run the first command again.
2. Run the recovery tool: `C:\Python313\python.exe scripts\set_portal_password.py`.
   It says which Python it is running under. If that is not `C:\Python313\python.exe`, stop and start again with
   the full path.
3. Type the username, then the login password twice and the admin password twice. Nothing is shown as you type.
   The login password and the admin password must be different.
4. Start the portal and log in.

If the tool says the password file could not be saved, check that `data\credentials.json` is not read-only and that
the portal is closed, then run it again. Nothing is changed when a save fails.

## Which password does what

The login password is asked at start-up. The two password-change dialogs (Settings on the login window, and
File > Change passwords) ask for both current passwords. Saving new passwords, in either dialog or with the tool,
always turns the start-up login on.

The admin password guards everything else that is protected: deleting, exporting, importing, renaming a student,
deleting a class, and the Admin Log and Dev Login tabs.

Anyone who can run the tool on this PC can reset both passwords; that is no weaker than before.
