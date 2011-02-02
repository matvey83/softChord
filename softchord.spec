# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'), os.path.join(HOMEPATH,'support/useUnicode.py'), 'src/softchord_main.py'],
             pathex=['/Users/adzhigir/softchord'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/softchord', 'softchord'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )
coll = COLLECT( exe,
               a.binaries + [('softchord_main_window.ui', 'src/softchord_main_window.ui', 'DATA')] +
                            [('softchord_chord_dialog.ui', 'src/softchord_chord_dialog.ui', 'DATA')] +
                            [('softchord_pdf_dialog.ui', 'src/softchord_pdf_dialog.ui', 'DATA')] +
                            [('zvuki_neba.songbook', 'src/zvuki_neba.songbook', 'DATA')],
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=os.path.join('dist', 'softchordr'))

import sys
if sys.platform.startswith("darwin"):
    app = BUNDLE(exe, appname='softchord.py', version=1)
    #app = BUNDLE(exe, appname='softChord', version=1)
               
