
import os, sys
from distutils.core import setup  
import py2exe  
# import PyQt4



setup(name="softChord",  
      version="",  
      author="Matvey Adzhigirey",  
      author_email="",  
      url="",  
      license="GNU General Public License (GPL)",  
      scripts=["softchord.py"], #, "softchord_main_window_ui.py", "softchord_chord_dialog_ui.py", "softchord_pdf_dialog_ui.py"],
      data_files=[
        #"softchord_main_window.ui", 
        #"softchord_chord_dialog.ui", 
        #"softchord_pdf_dialog.ui", 
        "zvuki_neba.songbook",
        #('sqldrivers', [os.path.join(os.path.dirname(PyQt4.__file__), 
        #                            'plugins', 
        #                          'sqldrivers', 
        #                          'qsqlite4.dll')
        #                        ]),
      ],
      windows=[{"script": "softchord.py"}],  
      options={
          "py2exe": {
                "bundle_files":1, # Bundle everything, including the Python interpreter
                "compressed":True,
                #"skip_archive": False, 
                "includes": ["sip"]
                #"packages":["PyQt4"],
                #"xref":True,
            }
      },
      zipfile = None, # Include the libraries in the executable itself instead of creating a separate archive file.

      #options={"py2exe":{"includes":["sip"]}, "packages":["PyQt4"], "bundle_files":1, "compressed":False, "xref":True}
      #options={"py2exe": {"bundle_files":1, "compressed":True, "includes": ["sip"]}}
)

# Run as: python setup.py py2exe


