

from distutils.core import setup  
import py2exe  

setup(name="softChord",  
      version="",  
      author="Matvey Adzhigirey",  
      author_email="",  
      url="",  
      license="GNU General Public License (GPL)",  
      scripts=["src/softchord_main.py"],
      data_files=["src/softchord_main_window.ui", "src/softchord_chord_dialog.ui", "src/softchord_pdf_dialog.ui", "src/zvuki_neba.songbook"],
      windows=[{"script": "src/softchord_main.py"}],  
      options={"py2exe": {"skip_archive": False, "includes": ["sip"]}}
      #options={"py2exe":{"includes":["sip"]}, "packages":["PyQt4"], "bundle_files":1, "compressed":False, "xref":True}
)

# Run as: python setup.py py2exe


