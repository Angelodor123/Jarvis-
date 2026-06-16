# Launching Jarvis

## Desktop Shortcut to start_jarvis.bat

1. Right-click `start_jarvis.bat` in the project folder and select **Send to → Desktop (create shortcut)**.
2. Optionally rename the shortcut to "Jarvis" and change its icon via **Properties → Change Icon**.

## Pin to Taskbar

1. Create the desktop shortcut as described above.
2. Right-click the shortcut on the desktop and select **Pin to taskbar**.

> Note: You cannot pin a `.bat` file directly — you must pin the desktop shortcut.

## Auto-launch on Login (Startup Folder)

To have Jarvis start silently (no console window) every time you log in:

1. Press **Win + R**, type `shell:startup`, and press Enter.
2. Copy `start_jarvis_silent.vbs` (or create a shortcut to it) into the Startup folder that opens.

From now on, `start_jarvis_silent.vbs` will run automatically at login, launching `main.py` in the background with no visible console window.
