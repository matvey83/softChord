
"""
Script for compiling softChord on Mac OS X

To run:

python mac_compile.py
"""

import sys, os
import subprocess
import shutil

final_bundle_name = "softChord.app"

print('Backing up the original app bundle')

if os.path.isdir(final_bundle_name):
    bu_dir = "prev_softChord.app"
    if os.path.isdir(bu_dir):
        shutil.rmtree(bu_dir)
    os.rename(final_bundle_name, bu_dir)

dist_app = "dist/softchord.app"

print('Compiling the app...')
HOME = os.environ["HOME"]
# cmd = ["python3", os.path.join(HOME, "PyInstaller/Build.py"), "softchord.spec", "--noconfirm"]
cmd = ["pyinstaller", "softchord.spec", "--noconfirm"]
out = subprocess.call(cmd)
if out != 0:
    sys.exit(out)

cmd = ["cp", "src/Info.plist", dist_app + "/Contents/"]
print('CMD:', subprocess.list2cmdline(cmd))
out = subprocess.call(cmd)
if out != 0:
    print('ERROR: Copying Info.plist failed')
    sys.exit(out)


cmd = ["cp", "-rv", "dist/softchord/*", "softchord.app/Contents/MacOS/"]
# For some reason subprocess.call() does not work with "*":
#out = subprocess.call(cmd)
out = os.system( subprocess.list2cmdline(cmd) )
if out != 0:
    print('ERROR: Copying dist/softchord/* failed')
    sys.exit(out)

cmd = ["cp", "-rv", "/Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib", dist_app + "/Contents/Resources/"]
out = subprocess.call(cmd)
if out != 0:
    print('ERROR: Copying qt libraries failed')
    sys.exit(out)

print('Renaming the app package...')
os.rename(dist_app, final_bundle_name)
print('Done.')

#cp modified_Info.plist softchord.app/Contents/Info.plist
