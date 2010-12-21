python ~/PyInstaller/Build.py softchordeditor.spec --noconfirm

cp Info.plist Macsoftchordeditor.app/Contents/

cp -rv dist/softchordeditor/* Macsoftchordeditor.app/Contents/MacOS/

cp -rv /Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib Macsoftchordeditor.app/Contents/Resources/

cp modified_Info.plist Macsoftchordeditor.app/Contents/Info.plist
