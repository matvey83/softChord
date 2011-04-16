"""
API for Flowplayer http://flowplayer.org

@license: Apache License Version 2.0
@copyright: 2009 Tobias Weber
@author: Tobias Weber
@contact: tobi-weber@gmx.de
"""

from pyjamas.ui.FlashPanel import FlashPanel
import DeferredHandler

from pyjamas.ui.Composite import Composite
from pyjamas.Timer import Timer
import urllib
from __pyjamas__ import wnd
from pyjamas import log

"""
Global variables called by Flash External Interface
"""
class PlayerEventCatcher:
    def fireEvent(self, *args):
        movieName = args[0]
        eventName = args[1]
        arguments = []
        for i in range(2, len(args)):
            if args[i] != None:
                arguments.append(args[i])
        wnd().players[args[0]].fireEvent(movieName, eventName, arguments)
        
def setInstanceGlobal(movieName, instance):
    wnd().players[movieName] = instance
    
wnd().players = {}
wnd().flowplayer = PlayerEventCatcher()
    
    
# Counter for Flash-movies
global movieCount
movieCount = 0

def getMovieCount():
    return movieCount


class Player(FlashPanel):
    """
    Embedding and api handling of Flowplayer 
    """
    
    clip_events = ['onBegin', 'onBeforeBegin', 'onFinish', 'onBeforeFinish', 'onLastSecond',
                   'onMetaData', 'onPause', 'onBeforePause', 'onResume', 'onBeforeResume',
                   'onSeek', 'onBeforeSeek', 'onStart', 'onStop', 'onBeforeStop', 'onUpdate',
                   'onBufferEmpty', 'onBufferFull', 'onBufferStop', 'onNetStreamEvent']

    def __init__(self, url, config=None):
        """
        @param url: The url to flowplayer.swf
        @param config: The Configuration-Object
        """
        FlashPanel.__init__(self)
        global movieCount
        
        self.api = None
        self.playlist = []
        self.plugins = {}
        self.activeIndex = 0
        self.listeners = []
        self.common_clip = None
        self.playlist = None
        self.curClip = None
        
        self.playerId = 'flowplayer'+str(movieCount)
        self.movieName = self.playerId+'_api'
        movieCount+=1
        setInstanceGlobal(self.movieName, self)
        
        #self.setObjectClass('flowplayer')
        self.setObjectID(self.movieName)
        self.setID(self.playerId)
        self.setHeight('300px')
        self.setWidth('400px')
        self.flash_url = url
        self.setObjectWidth('100%')
        self.setObjectHeight('100%')
        self.setAllowFullscreen(True)
        if not config:
            config = Configuration()
        self.common_clip = config.common_clip
        self.playlist = config.playlist
        for clip in self.playlist:
            clip.setPlayer(self)
        for plugin in config.plugins:
            plugin.setPlayer(self)
            if plugin.name:
                self.plugins[plugin.name] = plugin
        plugin = ScreenPlugin()
        plugin.setPlayer(self)
        self.plugins['screen'] = plugin
        self.flashvars = self.__createFlashVars(config)
        
    def loadApi(self):
        """
        Load the Flowplayer api
        """
        self.api = self.getMovieElement()
            
    def __getObjectAsString(self, obj):
        """
        @param obj: Object
        
        @return: String
        """
        obj_string = '{'
        i = 0
        for attr in obj.attrs:
            key = attr
            if hasattr(obj, key):
                value = getattr(obj, key)
                if not value == None:
                    if i > 0:
                        obj_string += ','
                    if str(value) == 'true' or str(value) == 'false':
                        value_string = value
                    else:
                        value_string = '"'+str(value)+'"'
                    key_string = '"'+key+'"'
                    obj_string += '%s:%s' % (key_string, value_string)
                    i+=1
        obj_string += '}'
        return obj_string
        
    def __createFlashVars(self, config):
        """
        @param config: Configuration Object
        
        @return: String
        
        Build Flashparams from Configuration
        """
        # Begin Config
        config_string = 'config={'
        
        # PlayerId
        config_string += '"playerId":"%s",' % self.movieName
        
        # Plugins
        if config.plugins:
            config_string += '"plugins":{'
            plugins = config.plugins
            controls = False
            for i in range(len(plugins)):
                plugin = plugins[i]
                if plugin.name == 'controls':
                    controls = True
                if i > 0:
                    config_string += ','
                config_string += '"%s":' % plugin.name
                config_string += self.__getObjectAsString(plugin)
            if not config.controls and not controls:
                config_string += ',"controls":null'
            config_string += '},'
        
        
        # Common Clip
        config_string += '"clip":'
        if config.common_clip:
            config_string += self.__getObjectAsString(config.common_clip)
            config_string += ','
        else:
            config_string += '{},'
        
        # Playlist
        config_string += '"playlist":['
        if config.playlist:
            i = 0
            for clip in config.playlist:
                i+=1
                config_string += self.__getObjectAsString(clip)
                if not i == len(config.playlist):
                    config_string += ','
        else:
            config_string += '{}'
        config_string += ']'
        
        # Debug
        if config.debug:
            config_string += ',"debug":true,"log":{"level":"%s","filter":"%s"}' % (config.logLevel, config.logFilter)
        
        # End Config
        config_string += '}'
        config_string = config_string.replace('%', 'pct')
        config_string = config_string.replace('&', '%26')
        config_string = config_string.replace('"', '&quot;')
        #config_string = config_string.replace('<', '&lt;')
        #config_string = config_string.replace('>', '&gt;')
        config_string = config_string.replace('\'', '\\\'')
        #log.writebr(config_string)
        return config_string
        
    def fireEvent(self, movieName, eventName, arguments):
        """
        @param args: Arguments given by Flowplayer
        
        Fire event
        """
        #log.writebr('FireEvent: %s/%s/%s' % (movieName, eventName, str(arguments)))
        if eventName == 'testFireEvent':
            log.writebr('fireEvent works')
            return
        if eventName == 'onLoad' and arguments[0] == 'player':
                self.loadApi()
        for listener in self.listeners:
            if eventName == 'onLoad':
                if arguments[0] == 'player':
                    if hasattr(listener, 'onLoadPlayer'):
                        eventMethod = getattr(listener, 'onLoadPlayer')
                        DeferredHandler.add(eventMethod)
                else:
                    if arguments[0] == 'play':
                        name = 'screen'
                    else:
                        name = arguments[0]
                    if self.plugins.has_key(name):
                        self.plugins[name].loaded = True
                    if hasattr(listener, 'onLoadPlugin'):
                        eventMethod = getattr(listener, 'onLoadPlugin')
                        DeferredHandler.add(eventMethod, arguments)
            elif eventName == 'onPluginEvent':
                plugin_name = arguments[0]
                plugin_eventName = arguments[1]
                if self.plugins.has_key(plugin_name):
                    self.plugins[plugin_name].fireEvent(plugin_eventName)
            elif eventName == 'onClipAdd':
                arguments[0] = self.playlist[int(arguments[1])]
                if hasattr(listener, eventName):
                    eventMethod = getattr(listener, eventName)
                    DeferredHandler.add(eventMethod, arguments)
            else:
                if eventName in self.clip_events:
                    clip_index = int(arguments[0])
                    clip = self.getClip(clip_index)
                    if clip_index == 0 and eventName == 'onBegin':
                        if hasattr(listener, 'onFirstPlaylistItem'):
                            eventMethod = getattr(listener, 'onFirstPlaylistItem')
                            DeferredHandler.add(eventMethod, [])
                    elif clip_index == len(self.playlist)-1 and eventName == 'onBegin':
                        if hasattr(listener, 'onLastPlaylistItem'):
                            eventMethod = getattr(listener, 'onLastPlaylistItem')
                            DeferredHandler.add(eventMethod, [])
                    clip.fireEvent(eventName, arguments[2:])
                else:
                    #log.writebr('[FP Event] %s / %s' % (eventName, arguments))
                    if hasattr(listener, eventName):
                        eventMethod = getattr(listener, eventName)
                        DeferredHandler.add(eventMethod, arguments)
        
    def addListener(self, listener):
        """
        @param listener: Object
        
        Add a listener
        """
        self.listeners.append(listener)
    
    def removeListener(self, listener):
        """
        @param listener: Object
        
        Remove a listener 
        """
        self.listeners.remove(listener)
    
    def isLoaded(self):
        """
        @return: Boolean, if the player is loaded
        """
        if self.api:
            return True
        else:
            return False
    
    # Flash ExternalInterface calls
    
    def addClip(self, clip, index=None):
        """
        @param clip: Clip Object
        @param index: specifies the position where clip is added in the playlist
        
        Add's a clip to the playlist. If the clip object contains a position
        property then the clip is added to an existing clip as an instream clip.
        The player's playlist is extended with the new clip and the onClipAdd event is fired.
        All common clip properties and event listeners are preserved. 
        """
        if self.isLoaded():
            if index:
                self.playlist.insert(index, clip)
                self.callFlash('fp_addClip', [clip.getProperties(), index])
            else:
                self.playlist.append(clip)
                self.callFlash('fp_addClip', [clip.getProperties()])
        
    def setClip(self, clip):
        """
        @param clip: Clip Object
        
        Replaces the current playlist with a playlist consisting of a single clip.
        All common clip properties and events are preserved.
        After this an onPlaylistReplace event fires. 
        """
        if self.isLoaded():
            self.setPlaylist([clip])
        
    def getClip(self, index=None):
        """
        @param index: Position in the playlist 
        
        @return: clip object from the playlist specified by index.
        
        For example getClip(0) returns the first clip from the playlist. 
        If called without an index the current clip will be returned.
        """
        if self.isLoaded():
            if index == None:
                clip = self.getCurrentClip()
                return clip
            else:
                return self.playlist[index]
        else:
            return None
    
    def getCurrentClip(self):
        # TODO
        return None
    
    def close(self):
        """
        Closes all connections between the player and the server. This method 
        is usually automatically called for you but in some cases you may
        want to do this yourself.
        """
        if self.isLoaded():
            self.callFlash('fp_close', [])
    
    def getTime(self):
        """
        @return: current time, in seconds, of the current clip. 
        """
        if self.isLoaded():
            return self.callFlash('fp_getTime', [])
        else:
            return None
    
    def getVersion(self):
        """
        @return: Flowplayer version
        """
        if self.isLoaded():
            return self.callFlash('fp_getVersion', [])
        else:
            return None
        
    def getPlugin(self, name):
        """
        @param name: Plugins name
        
        @return: plugin with the given name
        """
        if self.plugins.has_key(name):
            plugin = self.plugins[name]
            return plugin
        else:
            return None
        
    def loadPlugin(self, plugin):
        """
        @param plugin: Plugin object
        
        Loads a plugin in the player.
        """
        if self.isLoaded():
            properties = plugin.getProperties()
            plugin.setPlayer(self)
            self.plugins[plugin.name] = plugin
            self.callFlash('fp_loadPlugin', [plugin.name, plugin.url, properties])
    
    def getState(self):
        """
        @return: state of the player. Possible values are:
        -1   unloaded
        0    loaded
        1    unstarted
        2    buffering
        3    playing
        4    paused
        5    ended
        """
        if self.api:
            return self.callFlash('fp_getState', [])
        else:
            return -1
    
    def getVolume(self):
        """
        @return: player's current volume setting as an integer between 0-100.
        This returns the volume setting even if the player is muted.
        """
        if self.isLoaded():
            return self.callFlash('fp_getVolume', [])
        else:
            return None
    
    def setVolume(self, volume):
        """
        @param volume: Integer between 0-100
        
        Sets the volume. 0 is totally muted. 
        """
        if self.isLoaded():
            self.callFlash('fp_setVolume', [volume])
    
    def isFullscreen(self):
        """
        @return:  True if the player is in full screen mode and False otherwise. 
        """
        if self.isLoaded():
            return self.callFlash('fp_isFullscreen', [])
        else:
            return None
            
    def toggleFullscreen(self):
        """
        Toggles the state between fullscreen and normal mode. 
        
        @return:  True if the player is in full screen mode and False otherwise.
        """
        if self.isLoaded():
            return self.callFlash('fp_toggleFullscreen', [])
        else:
            return None
    
    def isPaused(self):
        """
        @return:  True if the player is paused and False otherwise. 
        """
        if self.isLoaded():
            return self.callFlash('fp_isPaused', [])
        else:
            return None
    
    def isPlaying(self):
        """
        @return:  True if the player is playing and False otherwise.
        """
        if self.isLoaded():
            return self.callFlash('fp_isPlaying', [])
        else:
            return None
    
    def mute(self):
        """
        Mutes the player. The difference between this and setVolume(0) is that the
        original volume level is remembered and resumed when unmute() is called. 
        """
        if self.isLoaded():
            self.callFlash('fp_mute', [])
    
    def unmute(self):
        """
        Resumes the volume level that was set before the player was muted. 
        """
        if self.isLoaded():
            self.callFlash('fp_unmute', [])
        
    def pause(self):
        """
        Pauses the currently playing clip.
        """
        if self.isLoaded():
            self.callFlash('fp_pause', [])
        
    def play(self):
        """
        starts playback of the current clip. 
        """
        if self.isLoaded():
            self.callFlash('fp_play', [])
    
    def playIndex(self, index):
        """
        @param index: the zero-based index of the clip in the Player's playlist array.
        
        Starts playback of the clip specified by index.
        """
        if self.isLoaded():
            self.callFlash('fp_play', [index])
        
    def playClip(self, clip):
        """
        @param clip: Clip object 
        
        Plays the clip. The player's playlist is replaced with a new playlist
        consisting of this single clip and the onPlaylistReplace event is fired.
        All common clip properties and event listeners are preserved. 
        """
        if self.isLoaded():
            self.playlist = [clip]
            self.callFlash('fp_play', [clip.getProperties()])
        
    def playClips(self, clips):
        """
        @param clips: List of clips
         
        Play the playlist specified by a List of clips. The player's playlist
        is replaced with a new playlist consisting of these clips and the
        onPlaylistReplace event is fired. All common clip properties and event
        listeners are preserved. 
        """
        if self.isLoaded():
            self.playlist = clips
            self.callFlash('fp_play', [self.playlist])
    
    def toggle(self):
        """
        Toggles the state between play and pause.
        """
        if self.isLoaded():
            self.callFlash('fp_toggle', [])
        
    def stop(self):
        """
        Stops the current clip.
        """
        if self.isLoaded():
            self.callFlash('fp_stop', [])
        
    def reset(self, pluginNames=None, speed=None):
        """
        If you have moved your screen or controlbar, this call moves them back to
        their original positions and size. You can optionally specify an list of
        plugin names (strings) that you also want to reset to their original state.
        """
        if self.isLoaded():
            if pluginNames:
                if speed:
                    self.callFlash('fp_reset', [pluginNames, speed])
                else:
                    self.callFlash('fp_reset', [pluginNames])
            else: # Reset Controls and Screens
                self.callFlash('fp_reset', [])
    
    def resume(self):
        """
        Resumes the currently paused clip.
        """
        if self.isLoaded():
            self.callFlash('fp_resume', [])
        
    def seek(self, seconds):
        """
        Seeks to the specified time of the current clip, in seconds. If using
        default URL-based streaming provider then the buffer must have loaded 
        to the point of seeking. When using streaming server this is not required.
        """
        if self.isLoaded():
            self.callFlash('fp_seek', [seconds])
    
    def startBuffering(self):
        """
        Starts downloading video data from the server. 
        """
        if self.isLoaded():
            self.callFlash('fp_startBuffering', [])
        
    def stopBuffering(self):
        """
        Stops downloading video data from the server. 
        """
        if self.isLoaded():
            self.callFlash('fp_stopBuffering', [])
            
    def getPlaylist(self):
        """
        Returns the playlist of the player as a list of Clip objects. 
        """
        return self.playlist
        
    def setPlaylist(self, clips):
        """
        @param clips: List of clips
        
        Replaces the current playlist with a new one. The playlist is given
        as a list of clips. All common clip properties are preserved.
        After this an onPlaylistReplace event fires. 
        """
        if self.isLoaded():
            self.playlist = clips
            self.callFlash('fp_setPlaylist', [self.playlist])
        
    def updateClip(self, clip):
        """
        @param clip: clip object
        
        Updates a clip, if the clip properties are changed
        """
        if self.isLoaded():
            index = self.playlist.index(clip)
            self.callFlash('fp_updateClip', [clip.getProperties(), index])
    
    def getScreen(self):
        """
        @return:  the screen plugin
        """
        return self.getPlugin('screen')
    
    def getControls(self):
        """
        @return:  the controls plugin
        """
        return self.getPlugin('controls')
        
        
class Configuration:
    """
    Defines the Startup Configuration of FlowPlayer
    @var controls: Boolean, if controls are enabled
    @var debug: Boolean, for debugging
    @var logLevel: String
    @var logFilter: String
    """
    def __init__(self):
        self.controls = True 
        """Boolean, if controls are enabled. Default: True"""
        self.debug = False
        """Boolean, for debugging"""
        self.logLevel = 'error'
        """ Loglevel """
        self.logFilter = '*'
        """ Logfilter """
        
        self.plugins = []
        self.common_clip = Clip()
        self.playlist = []
        
    def addPlugin(self, plugin):
        """
        @param plugin: Plugin object
        """
        self.plugins.append(plugin)
            
    def setCommonClip(self, clip):
        """
        @param clip: Clip object
        """
        self.common_clip = clip
    
    def setPlaylist(self, playlist):
        """
        @param playlist: List with Clips
        """
        self.playlist = playlist
    
    def disableControls(self):
        self.controls = False
    
class Clip:
    """
    Clip for the player
    """
    attrs = ['url', # String
             'accelerated', # Boolean
             'autoBuffering', # Boolean
             'autoPlay', # Boolean
             'baseUrl', # String
             'bufferLength', # Integer
             'connectionProvider', # String
             'cuepointMultiplier',
             'cuepoints', # Array
             'controls', # Object
             'duration', # Number
             'fadeInSpeed', # Integer
             'fadeOutSpeed', # Integer
             'image', # Boolean
             'linkUrl', # String
             'linkWindow', # String
             'live',# Boolean
             'metadata', # Boolean
             'originalUrl', # String
             'position', # Integer
             'playlist', # Array
             'provider', # String
             'scaling', # String
             'seekableOnBegin', # Boolean
             'start', # Integer
             'urlResolver' # String
             ]
    """ Possible Attributes for a Clip; Can be added with setAttr-Method """
    
    def __init__(self, url=None):
        self._player = None
        self.listeners = []
        if url:
            setattr(self, 'url', url)
    
    def setAttr(self, attr, value):
        """
        @param attr: Properties name
        @param value: Properties value
        
        Sets a Property to this Object
        """
        if attr in self.attrs:
            setattr(self, attr, value)
            self.update()
    
    def setPlayer(self, player):
        """
        @param player: Player Instance
        """
        self._player = player
    
    def getPlayer(self):
        """
        @return: The player instance
        """
        return self._player
        
    def update(self):
        """
        Updates this clip instance, if it is changed on runtime
        """
        if self._player:
            self._player.updateClip(self)
        
    def addListener(self, listener):
        """
        @param listener: Object
        
        Add a listener
        """
        self.listeners.append(listener)
    
    def removeListener(self, listener):
        """
        @param listener: Object
        
        Remove a listener
        """
        self.listeners.remove(listener)
                
    def fireEvent(self, eventName, arguments):
        for listener in self.listeners:
            if hasattr(listener, eventName):
                eventMethod = getattr(listener, eventName)
                arguments.insert(0, self)
                DeferredHandler.add(eventMethod, arguments)
        
    def getProperties(self):
        """
        @return:  Dictonary with Properties
        """
        properties = {}
        for attr in self.attrs:
            if hasattr(self, attr):
                properties[attr] = getattr(self, attr)
        return properties
         
class Plugin:
    """
    Base class for plugins
    """
    
    attrs = ['url',
             'bottom',
             'height',
             'left',
             'opacity',
             'right',
             'top',
             'width',
             'display',
             'zIndex',
             'border',
             'borderRadius',
             'borderColor',
             'background',
             'backgroundColor',
             'backgroundRepeat',
             'backgroundGradient',
             'backgroundImage']
    """ Possible Attributes for a Plugin; Can be added with setAttr-Method """
    
    def __init__(self, url=None, name=None):
        if url:
            self.url = url
        if name:
            self.name = name
        self._player = None
        self.listeners = []
        self.loaded = False
    
    def setAttr(self, attr, value):
        """
        @param attr: Properties name
        @param value: Properties value
        
        Sets a Property to this Object
        """
        if attr in self.attrs:
            setattr(self, attr, value)
    
    def setPlayer(self, player):
        """
        @param player: Player Instance
        """
        self._player = player
        
    def isLoaded(self):
        """
        Returns a Boolean, if the plugin is loaded
        """
        return self.loaded
    
    def animate(self, properties, speed=500):
        """
        @param properties: Dictonary;  the plugin's placement, 
        size and opacity properties that you want to animate
        
        @param speed: Integer; specifies the duration of the animation, in milliseconds.
        
        animate() lets you change a plugin's position, size and opacity in an animated way. 
        This can give very cool effects on your web page.
        You can also do relative animations by prepending a "+=" or "-=" to the property 
        value to animate relative to the property's current value.
        plugin.animate({width:'80%'})
        """
        if self.loaded and self._player:
            if self.name:
                callback = 'onAnimate'
                self._player.callFlash('fp_animate', [self.name, properties, speed, callback])
        
    def css(self, properties):
        """
        @param properties: Dictonary
        
        Changes the plugin's style and other properties immediately without animation.
        Change controlbar background color 
        controls.css({backgroundColor:'#cccccc'})
        """
        if self.loaded and self._player:
            if self.name:
                self._player.callFlash('fp_css', [self.name, properties])
    
    def fadeIn(self, speed=500):
        """
        @param speed: Integer; specifies the duration of the animation, in milliseconds.
        
        Makes the plugin visible in an animated way by adjusting its opacity
        from the initial opacity to 100%. In typical scenarios the initial 
        opacity is 0. This call will also set the plugin's display property 
        to "block", making it visible if it was hidden.
        """
        if self.loaded and self._player:
            callback = 'onAnimate'
            if self.name:
                self._player.callFlash('fp_fadeIn', [self.name, speed, callback])
        
    def fadeOut(self, speed=500):
        """
        @param speed: Integer; specifies the duration of the animation, in milliseconds.
        
        Hides the plugin in an animated manner by adjusting its opacity from 
        the initial opacity to 0%. This call will also set the plugin's display 
        property to "none", removing it completely from the canvas.
        """
        if self.loaded and self._player:
            callback = 'onAnimate'
            if self.name:
                self._player.callFlash('fp_fadeOut', [self.name, speed, callback])
    
    def fadeTo(self, opacity=100, speed=500):
        """
        @param opacity: specifies the end opacity of the animation (0 - 100).
        
        @param speed: Integer; specifies the duration of the animation, in milliseconds.
        
        Makes the plugin hidden in an animated manner by adjusting its opacity 
        from the initial opacity to the given opacity.
        """
        if self.loaded and self._player:
            callback = 'onAnimate'
            if self.name:
                self._player.callFlash('fp_fadeTo', [self.name, opacity, speed, callback])
        
    def hide(self):
        """
        Immediately hides the plugin and removes it from the canvas. 
        This is the same as setting the display property to "none". 
        This does not affect the plugin's opacity setting. 
        """
        if self.loaded and self._player:
            if self.name:
                self._player.callFlash('fp_hidePlugin', [self.name])
    
    def show(self):
        """
        Makes the plugin immediately visible. This does not affect the plugin's 
        opacity setting. This is the same as setting the display property to "block". 
        """
        if self.loaded and self._player:
            if self.name:
                self._player.callFlash('fp_showPlugin', [self.name])
    
    def toggle(self):
        """
        Toggles between the hidden and visible state. 
        """
        if self.loaded and self._player:
            if self.name:
                self._player.callFlash('fp_togglePlugin', [self.name])
        
    def addListener(self, listener):
        """
        @param listener: object
        
        Add a listener object
        """
        self.listeners.append(listener)
    
    def removeListener(self, listener):
        """
        @param listener: object
        
        Remove a listener object
        """
        self.listeners.remove(listener)
        
    def fireEvent(self, eventName):
        """
        @param eventName: Name of the event
        """
        eventName = eventName+'Plugin'
        for listener in self.listeners:
            if hasattr(listener, eventName):
                eventMethod = getattr(listener, eventName)
                DeferredHandler.add(eventMethod, [self])
    
    def getProperties(self):
        """
        @return:  Dictonary with properties of this instance
        """
        properties = {}
        for attr in self.attrs:
            if hasattr(self, attr):
                if not attr == 'url':
                    properties[attr] = getattr(self, attr)
        return properties
        
        
class ScreenPlugin(Plugin):
    """
    The main screen
    """
    
    def __init__(self):
        Plugin.__init__(self, name='screen')
    


class ContentPlugin(Plugin):
    """
    Provides an overlay for the player
    """
    content_attrs = ['html',
                     'textDecoration',
                     'stylesheet',
                     'style', 
                     'closeButton',
                     'closeImage']
    """ Additional Attributes for a ContentPlugin; Can be added with setAttr-Method """
    
    def __init__(self, url=None, name=None):
        Plugin.__init__(self, url, name)
        self.attrs += self.content_attrs
        """ Possible ContentPlugin Attributes """
        
    def setHtml(self, html):
        """
        @param html: Set the plugin's HTML content to the given string.
        """
        if self.loaded:
            if self.name:
                self._player.callFlash('fp_invoke', [self.name, 'setHtml', html])
    
    def append(self, html):
        """
        @param html: append more HTML content to the end of the existing HTML.
        """
        if self.loaded:
            if self.name:
                self._player.callFlash('fp_invoke', [self.name, 'append', html])
    
    def getHtml(self):
        """
        @return: the current HTML content.
        """
        html = None
        if self.loaded:
            if self.name:
                html = self._player.callFlash('fp_invoke', [self.name, 'getHtml'])
        return html
        
        
class ControlsPlugin(Plugin):
    """
    The controlbar for the player
    """
    
    control_attrs = ['timeColor',
                     'durationColor',
                     'progressColor',
                     'progressGradient',
                     'bufferColor',
                     'bufferGradient',
                     'sliderColor',
                     'sliderGradient',
                     'buttonColor',
                     'buttonOverColor',
                     'volumeSliderColor',
                     'volumeSliderGradient',
                     'timeBgColor',
                     'scrubberHeightRatio',
                     'scrubberBarHeightRatio',
                     'volumeSliderHeightRatio',
                     'timeBgHeightRatio',
                     'autoHide',
                     'hideDelay',
                     'all',
                     'play',
                     'volume',
                     'mute',
                     'time',
                     'stop',
                     'playlist',
                     'fullscreen',
                     'scrubber']
    """ Additional Attributes for a ControlsPlugin; Can be added with setAttr-Method """
    
    def __init__(self, url=None, name=None):
        name = 'controls'
        Plugin.__init__(self, url, name)
        self.attrs += self.control_attrs
        """ Possible ControlsPlugin Attributes """
    
    def getDefaultProperties(self):
        properties = {'autoHide': 'fullscreen', # never, always, fullscreen
                      'hideDelay': 4000,
                      'play': True,
                      'volume': True,
                      'mute': True,
                      'time': True,
                      'stop': False,
                      'playlist': False,
                      'fullscreen': True,
                      'scrubber': True
                      }
            
    def enable(self, properties):
        """
        @param properties: Dictionary
        
        Enables and/or disables the controlbar widgets. Disabled widgets are greyed out.
        For example, this can be useful when you want to force the user to watch a 
        video in the case of an advertisement. A value of all can be used to enable/disable 
        all widgets at the same time. For example, enable({all: False}) will disable all widgets. 
        Example: properties = {play: False}
        """
        if self.loaded:
            if self.name:
                self._player.callFlash('fp_invoke', [self.name, 'enable', properties])
    
    def widgets(self, properties):
        """
        @param properties: Dictionary
        
        Shows/hides the controlbar widgets. 
        all can be used to enable/disable all widgets at the same time, 
        for example, widgets({all: False}). 
        Example: properties = {scrubber: False}
        """
        if self.loaded:
            if self.name:
                self._player.callFlash('fp_invoke', [self.name, 'widgets', properties])
    
    def tooltips(self, properties):
        """
        @param properties: Dictionary
        
        Enables/disables tooltips. Use buttons:true or buttons:false to enable or disable all 
        buttons at the same time, respectively. Specifying the value null disables the tooltip. 
        If you want to enable the buttons remember to add the buttons: True property as one parameter.
        Example: properties = {buttons: True, play: 'Go'}
        """
        if self.loaded:
            if self.name:
                self._player.callFlash('fp_invoke', [self.name, 'tooltips', properties])
    
    
class PseudostreamingPlugin(Plugin):
    """
    Webserver video streaming plugin
    """
    attrs = ['url']
    """ Possible Attributes for a PseudostreamingPlugin """
    def __init__(self, url=None, name=None):
        if not name:
            name = 'pseudostreaming'
        if not url:
            url = 'flowplayer.pseudostreaming.swf'
        Plugin.__init__(self, url, name)
    
class AudioPlugin(Plugin):
    """
    Audio plugin
    """
    attrs = ['url']
    """ Possible Attributes for a AudioPlugin """
    def __init__(self, url=None):
        name = 'audio'
        if not url:
            url = 'flowplayer.audio.swf'
        Plugin.__init__(self, url, name)
        
        
class PlayerInterface:
    """
    Player Events Interface
    """
    def onBeforeClick(self): pass
    
    def onLoaded(self): pass

    def onBeforeLoaded(self): pass
    
    def onUnload(self): pass
    
    def onBeforeUnload(self): pass
    
    def onKeypress(self, keycode): pass
    
    def onBeforeKeypress(self, keycode): pass
    
    def onVolume(self, volume): pass
    
    def onBeforeVolume(self, volume): pass
    
    def onMute(self): pass
    
    def onBeforeMute(self): pass
    
    def onUnmute(self): pass
    
    def onBeforeUnmute(self): pass
    
    def onFullscreen(self): pass
    
    def onBeforeFullscreen(self): pass
    
    def onFullscreenExit(self): pass
    
    def onClipAdd(self, clip, index): pass
    
    def onPlaylistReplace(self, clips): pass
    
    def onError(self, code, message): pass
    
    def onMouseOver(self): pass
    
    def onMouseOut(self): pass
    
    def onFirstPlaylistItem(self): pass
    
    def onLastPlaylistItem(self): pass
        
     
class ClipInterface:
    """
    Clip Events Interface
    """
    def onBegin(self, clip): pass
    
    def onBeforeBegin(self, clip): pass
    
    def onFinish(self, clip): pass
    
    def onBeforeFinish(self, clip): pass
    
    def onLastSecond(self, clip): pass
    
    def onMetaData(self, clip): pass
    
    def onPause(self, clip): pass
    
    def onBeforePause(self, clip): pass
    
    def onResume(self, clip): pass
    
    def onBeforeResume(self, clip): pass
    
    def onSeek(self, clip, seconds): pass
    
    def onBeforeSeek(self, clip, seconds): pass
    
    def onStart(self, clip): pass
    
    def onStop(self, clip): pass
    
    def onBeforeStop(self, clip): pass
    
    def onUpdate(self, clip): pass
   
    def onBufferEmpty(self, clip): pass 
    
    def onBufferFull(self, clip): pass
    
    def onBufferStop(self, clip): pass
    
    def onNetStreamEvent(self, clip): pass
        
        
class PluginInterface:
    """
    Plugin Events Interface
    """
    
    def onMouseOverPlugin(self, plugin): pass
    
    def onMouseOutPlugin(self, plugin): pass
    
    def onAnimatePlugin(self, plugin): pass
    
    def onClickPlugin(self, plugin): pass
        