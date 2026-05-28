
How to run the program (Development Setup):

1) Download or clone the source files.

2) Create and activate a Python virtual environment (recommended):

   python3 -m venv .venv
   source .venv/bin/activate     # macOS / Linux
   # .venv\Scripts\activate      # Windows

   Note: `.venv` is listed in `.gitignore`.

3) Install dependencies:

   pip install -r requirements.txt

   This will install PyQt6 (which includes the required Qt6 libraries).

4) (Optional) If you want to keep dependencies reproducible, the project now uses
   a virtual environment + requirements.txt instead of the old manual Qt SDK + PyQt
   installation.

5) Run the application:

   cd src
   python3 softchord.py






How to compile the program on Windows:

1) Install py2exe for the installed Python version and architecture.

2) CD into the "softChord" directory.

3) Run "python win_setup.py install"

4) Run "python win_setup.py py2exe"
   The compiled program will appear in "softChord\dist\"

NOTE: Only step 4 will need to be performed for subsequent builds.





How to compile on Mac OS X:

1) Make sure your virtual environment is activated:

   source .venv/bin/activate

2) Install PyInstaller inside the venv:

   pip install pyinstaller

3) From the project root, run:

   # pyinstaller src/softchord.py --onefile --windowed --noconfirm --name "softChord 0.10.0"
   pyinstaller softchord.spec

4) After building, update version numbers if needed and copy the Info.plist:

   # Example (adjust the app name/version as needed):
   cp src/Info.plist "dist/softChord 0.10.0.app/Contents/Info.plist"

5) (Optional) Copy the song database(s) into the `dist/` directory if you want
   them included with the built application.


See also:
http://tech.xster.net/tips/deploy-pyqt-applications-on-mac-os-x-with-pyinstaller/

