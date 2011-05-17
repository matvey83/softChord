import pyjd # dummy in pyjs

from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.TextArea import TextArea
from pyjamas.ui.Label import Label
from pyjamas.ui.Button import Button
from pyjamas.ui.HTML import HTML
#from pyjamas.ui.TextBox import TextBox
#from pyjamas.ui import KeyboardListener
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.ListBox import ListBox
from pyjamas.JSONService import JSONProxy

# For generating HTML from the song text and chords:
import songs

TEXT_WAITING = "Waiting for response..."


class DataService(JSONProxy):
    """
    Class for handling RPC requests to the server. An instance of this class is saved
    to SoftChordWeb.remote. When methods of this class are invoked, the corresponding
    methods on the server are invoked using JSON-RPC.
    """
    def __init__(self):
        # Initialize with a list of available functions on the server:
        remote_procedures=["echo", "getAllSongs", "getSong", "addSong", "deleteSong"]
        JSONProxy.__init__(self, "/songs/index.py/rpc/", remote_procedures)


class SoftChordWeb:
    def onModuleLoad(self):
        """
        Gets run when the page is first loaded.
        Creates the widgets.
        """

        # For managing JSON-RPC (communicaiton with the server):
        self.remote = DataService()
        
        root_panel = RootPanel()
        
        root_panel.add(HTML("<h2>softChord Web</h2>"))
        
        self.status=Label()
        self.text_area = TextArea()
        self.text_area.setText("Enter some text here, and watch it get sent to the server and echoed back.")
        self.text_area.setCharacterWidth(80)
        self.text_area.setVisibleLines(3)
        
        # For testing the server connection:
        test_panel = VerticalPanel()
        test_panel.add(HTML("Test the server connection:"))
        test_panel.add(self.text_area)
        self.test_button = Button("Test Connection", self)
        test_panel.add(self.test_button)
        test_panel.add(self.status)
        #root_panel.add(test_panel)
        
        # Label for displaying status from the server:
        self.status = Label()
        root_panel.add(self.status)
        
        
        main_layout = VerticalPanel()
        
        h_layout = HorizontalPanel()
        h_layout.setPadding(10)
        
        songlist_layout = VerticalPanel()
        
        songlist_layout.add(Label('Songs from songbook "Звуки Неба":'))
        
        #self.newSongTextBox = TextBox()
        #self.newSongTextBox.addKeyboardListener(self)
        #songlist_layout.add(self.newSongTextBox)
        
        #songlist_layout.add(Label("Click to Remove:"))

        self.songListBox = ListBox()
        self.songListBox.setVisibleItemCount(7)
        self.songListBox.setWidth("300px")
        self.songListBox.setHeight("400px")
        self.songListBox.addChangeListener(self)
        songlist_layout.add(self.songListBox)
        
        # Currently not possible to delete a song (otherwise anyone could delete any song):
        self.deleteSongButton = Button("Delete")
        self.deleteSongButton.addClickListener(self)
        #songlist_layout.add(self.deleteSongButton)
         
        
        h_layout.add(songlist_layout)
        
        self.songHtml = HTML("<b>Please select a song in the left table</b>")
        h_layout.add(self.songHtml)
        
        main_layout.add(h_layout)
        
        root_panel.add(main_layout)
        
        # The currently selected song:
        self.current_song = None
        
        # Populate the song table:
        self.remote.getAllSongs(self)
    
    
    '''
    def onKeyUp(self, sender, keyCode, modifiers):
        pass

    def onKeyDown(self, sender, keyCode, modifiers):
        pass

    def onKeyPress(self, sender, keyCode, modifiers):
        """
        This functon handles the onKeyPress event
        NOTE USED currently (previously it would add a new song)
        """
        if keyCode == KeyboardListener.KEY_ENTER and sender == self.newSongTextBox:
            id = self.remote.addSong(self.newSongTextBox.getText(), self)
            self.newSongTextBox.setText("")

            if id<0:
                self.status.setText("Server Error or Invalid Response")
    '''

    def onChange(self, sender):
        """
        Called when a new song is selected in the song list
        """
        if sender == self.songListBox:
            song_id = self.songListBox.getValue(self.songListBox.getSelectedIndex())
            self.status.setText("selected song_id: %s" % song_id)
            id = self.remote.getSong(song_id, self)
            if id<0:
                self.status.setText("Server Error or Invalid Response")
    
    def onClick(self, sender):
        """
        Gets called when a user clicked in the <sender> widget.
        Currently deletes the song on which the user clicked.
        """

        self.status.setText(TEXT_WAITING)
        text = self.text_area.getText()

        if sender == self.test_button:
            # Test the remote connection
            id = self.remote.echo(text, self)
        
        elif sender == self.deleteSongButton:
            # NOT USED (can only read the database currently)
            # Figure out what song is selected in the table:
            song_id = self.songListBox.getValue(self.songListBox.getSelectedIndex())
            self.status.setText("delete song_id: %s" % song_id)
            id = self.remote.deleteSong(song_id, self)
            if id<0:
                self.status.setText("Server Error or Invalid Response")
    

    def onRemoteResponse(self, response, request_info):
        """
        Gets called when the backend script sends a packet to us.
        Populates the song table with all songs in the database.
        """
        self.status.setText("response received")
        if request_info.method == 'getAllSongs' or request_info.method == 'addSong' or request_info.method == 'deleteSong':
            self.status.setText(self.status.getText() + " - song list received")
            self.songListBox.clear()
            for item in response:
                song_id, song_num, song_title = item
                if song_num:
                    song_title = "%i %s" % (song_num, song_title)
                self.songListBox.addItem(song_title)
                self.songListBox.setValue(self.songListBox.getItemCount()-1, song_id)
        
        elif request_info.method == 'getSong':
            self.status.setText("Song received, parsing JSON...")
            
            # Convert the JSON respose (from the server) into a Song object:
            song = songs.Song(response)
            self.status.setText("Received song: id: %i; num-chords: %i" % (song.id, len(song.chords) ) )
            self.current_song = song
            self.displayCurrentSong()
            
            # Transpose the song up by half step before showing:
            # (for demonstration of the transpose method for Serge):
            self.transposeCurrentSong(1)
        else:
            # Unknown response received form the server
            self.status.setText(response)
    
    def transposeCurrentSong(self, up_steps):
        if not self.current_song:
            pass # error, no song selected
        self.current_song.transpose(up_steps)
        self.displayCurrentSong()
    
    def displayCurrentSong(self):
        self.songHtml.setHTML(self.current_song.getHtml())
    
    def onRemoteError(self, code, errobj, request_info):
        # onRemoteError gets the HTTP error code or 0 and
        # errobj is an jsonrpc 2.0 error dict:
        #     {
        #       'code': jsonrpc-error-code (integer) ,
        #       'message': jsonrpc-error-message (string) ,
        #       'data' : extra-error-data
        #     }
        message = errobj['message']
        if code != 0:
            self.status.setText("HTTP error %d: %s" % 
                                (code, message))
        else:
            code = errobj['code']
            self.status.setText("JSONRPC Error %s: %s" %
                                (code, message))

        # 
        #message = errobj['message']
        #self.status.setText("Server Error or Invalid Response: ERROR %s - %s" % (code, message))



if __name__ == '__main__':
    """
    For running Pyjamas-Desktop.
    """
    # for pyjd, set up a web server and load the HTML from there:
    # this convinces the browser engine that the AJAX will be loaded
    # from the same URI base as the URL, it's all a bit messy...
    pyjd.setup("http://127.0.0.1/<change to path of static-slash-output>/SoftChordWeb.html")
    app = SoftChordWeb()
    app.onModuleLoad()
    pyjd.run()

