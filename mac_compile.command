python ~/PyInstaller/Build.py softchord.spec --noconfirm

cp Info.plist Macsoftchord.app/Contents/

cp -rv dist/softchord/* Macsoftchord.app/Contents/MacOS/

cp -rv /Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib Macsoftchord.app/Contents/Resources/

cp modified_Info.plist Macsoftchord.app/Contents/Info.plist
