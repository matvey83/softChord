
How to run the program:

1) Download the source files

2) Install Python (if not installed).

3) Install the Qt SDK

4) Install PyQt for the above Python and Qt versions

NOTE: Make sure all of the above are for the same architecture (32-bit vs 64-bit).

5) CD into the "src" directory and run: "python softchord.py"





How to compile the program on Windows:

1) Install py2exe for the installed Python version and architecture.

2) CD into the "softchord" directory.

3) Run "python win_setup.py install"

4) Run "python win_setup.py py2exe"
   The compiled program will appear in "softchord\dist\"

NOTE: Only step 4 will need to be performed for subsequent builds.





How to compile on Mac OS X:

1) pip install pyinstaller

2) CD into the "softchord" directory.

3) Copy the newly installed "pyinstaller" directory into the softchord
directory

4) python pyinstaller/pyinstaller.py src/softchord.py --onefile --windowed --noconfirm --name "softChord X.Y.Z"

5) cp src/Info.plist dist/softChord\ 0.9.1.app/Contents/Info.plist 

6) Copy the database into the dir dist/ directory


See:
http://tech.xster.net/tips/deploy-pyqt-applications-on-mac-os-x-with-pyinstaller/

