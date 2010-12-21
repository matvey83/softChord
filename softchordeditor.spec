# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'), os.path.join(HOMEPATH,'support/useUnicode.py'), 'src/softchordeditor_gui.py'],
             pathex=['/Users/adzhigir/softchordeditor'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/softchordeditor', 'softchordeditor'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )
coll = COLLECT( exe,
               a.binaries + [('softchordeditor.ui', 'src/softchordeditor.ui', 'DATA')] +
                            [('softchordeditor_chord_dialog.ui', 'src/softchordeditor_chord_dialog.ui', 'DATA')] +
                            [('softchordeditor_pdf_dialog.ui', 'src/softchordeditor_pdf_dialog.ui', 'DATA')] +
                            [('songdatabase.sqlite', 'src/song_database.sqlite', 'DATA')],
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=os.path.join('dist', 'softchordeditor'))

import sys
if sys.platform.startswith("darwin"):
    app = BUNDLE(exe, appname='softchordeditor.py', version=1)
    #app = BUNDLE(exe, appname='softChord Editor', version=1)
               
"""
a.binaries + [('softchordeditor.ui', 'src/softchordeditor.ui', 'DATA')] +
                            [('softchordeditor_chord_dialog.ui', 'src/softchordeditor_chord_dialog.ui', 'DATA')] +
                            [('softchordeditor_pdf_dialog.ui', 'src/softchordeditor_pdf_dialog.ui', 'DATA')] +
                            [('songdatabase.sqlite', 'src/song_database.sqlite', 'DATA')],
               a.zipfiles,
"""
