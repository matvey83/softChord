
import pyjd # dummy for pyjs
from pyjamas.ui.Label import Label
from pyjamas.ui.Button import Button
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.TextBox import TextBox
from pyjamas.ui.ListBox import ListBox
from pyjamas.ui import KeyboardListener

from pyjamas.JSONService import JSONProxy

import songs


class SoftChordApp:
    def onModuleLoad(self):
        """
        Gets run when the page is first loaded.
        Creates the widgets.
        """

        self.remote = DataService()
        panel = VerticalPanel()

        self.newSongTextBox = TextBox()
        self.newSongTextBox.addKeyboardListener(self)
        self.songListBox = ListBox()
        self.songListBox.setVisibleItemCount(7)
        self.songListBox.setWidth("300px")
        self.songListBox.setHeight("400px")
        self.songListBox.addClickListener(self)
        
        panel.add(Label("Add New Song:"))
        panel.add(self.newSongTextBox)
        panel.add(Label("Click to Remove:"))
        panel.add(self.songListBox)

        self.deleteSongButton = Button("Delete")
        self.deleteSongButton.addClickListener(self)
        panel.add(self.deleteSongButton)
        
        self.status = Label()
        panel.add(self.status)

        RootPanel().add(panel)
    

    def onKeyUp(self, sender, keyCode, modifiers):
        pass

    def onKeyDown(self, sender, keyCode, modifiers):
        pass

    def onKeyPress(self, sender, keyCode, modifiers):
        """
        This functon handles the onKeyPress event
        """
        if keyCode == KeyboardListener.KEY_ENTER and sender == self.newSongTextBox:
            id = self.remote.addSong(sender.getText(), self)
            sender.setText("")

            if id<0:
                self.status.setText("Server Error or Invalid Response")

    def onClick(self, sender):
        """
        Gets called when a user clicked in the <sender> widget.
        Currently deletes the song on which the user clicked.
        """
        if sender == self.songListBox:
            pass
            #song_id = sender.getValue(sender.getSelectedIndex())
            #self.status.setText("song_id: %s" % song_id)
            #id = self.remote.deleteSong(song_id, self)
            #if id<0:
            #    self.status.setText("Server Error or Invalid Response")

        elif sender == self.deleteSongButton:
            # Figure out what song is selected in the table:
            song_id = self.songListBox.getValue(self.songListBox.getSelectedIndex())
            self.status.setText("song_id: %s" % song_id)
            id = self.remote.deleteSong(song_id, self)
            if id<0:
                self.status.setText("Server Error or Invalid Response")
    
    def onRemoteResponse(self, response, request_info):
        """
        Gets called when the backend (django) sends a packet to us.
        Populates the song table with all songs in the database.
        """
        self.status.setText("response received")
        if request_info.method == 'getAllSongs' or request_info.method == 'addSong' or request_info.method == 'deleteSong':
            self.status.setText(self.status.getText() + "HERE!")
            self.songListBox.clear()
            for song_dict in response:
                # FIXME we should not send the song text at this point, to save on bandwidth
                song_obj = songs.Song(song_dict)
                title = song_obj.title
                song_id = song_obj.id
                
                self.songListBox.addItem(title)
                self.songListBox.setValue(self.songListBox.getItemCount()-1, song_id)
        else:
            self.status.setText(self.status.getText() + "none!")
    
    def onRemoteError(self, code, errobj, request_info):
        message = errobj['message']
        self.status.setText("Server Error or Invalid Response: ERROR %s - %s" % (code, message))

class DataService(JSONProxy):
    def __init__(self):
        JSONProxy.__init__(self, "/services/", ["getAllSongs", "addSong", "deleteSong"])

if __name__ == "__main__":
    """
    For running Pyjamas-Desktop.
    """
    pyjd.setup("public/softrchordapp.html")
    #pyjd.setup("http://127.0.0.1:8000/site_media/output/softchordapp.html")
    app = SoftChordApp()
    app.onModuleLoad()
    pyjd.run()

