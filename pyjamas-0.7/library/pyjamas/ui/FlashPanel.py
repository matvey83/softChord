"""
Flash embedding Panel

@license: Apache License Version 2.0
@copyright: 2009 Tobias Weber
@author: Tobias Weber
@contact: tobi-weber@gmx.de
"""

from pyjamas import DOM
from pyjamas.ui.Panel import Panel
from pyjamas import log
from __pyjamas__ import wnd


def browser():
    return 'w3c'

class FlashPanel(Panel):
    
    def __init__(self, **kwargs):
        element = DOM.createDiv()
        self.setElement(element)
        Panel.__init__(self, **kwargs)
        
        self.object_id = 'FlashObject'
        """ id of the object-tag. Default: FlashObject """
        self.object_class = None
        """ The class-name of the object-tag. Default: None"""
        self.object_width = None
        """ The width-parameter of the object-tag. Default: None"""
        self.object_height = None
        """ The height-parameter of the object-tag. Default: None"""
        self.flash_url = None
        """ The Flash-Movie url. Default: None"""
        self.wmode = None #'window'
        """ The flashmovie wmode parameter. Default: None"""
        self.quality = 'high'
        """ The flashmovie quality parameter. Default: high"""
        self.menu = None # 'false'
        """ The flashmovie wmode parameter. Default: None"""
        self.allowScriptAccess = 'always'
        """ The flashmovie allowscriptaccess parameter. Default: always"""
        self.allowFullscreen = 'false'
        """ The flashmovie allowfullscreen parameter. Default: False"""
        self.bgColor = '#FFFFFF'
        """ The flashmovie bgcolor parameter. Default: #FFFFFF (white)"""
        self.flashvars = ''
        self.browser = browser()
        #log.writebr('FlashPanel loaded on %s' % self.browser)
        
    def onLoad(self):
        DOM.setInnerHTML(self.element, self.__getFlashHTML())
    
    def getObjectID(self):
        """
        @return: id of the object-tag
        """
        return self.object_id
         
    def setObjectID(self, object_id):
        """
        @param object_id: The id of the object-tag
        """
        self.object_id = object_id
    
    def getObjectClass(self):
        """
        @return: class-name of the object-tag
        """
        return self.object_class
    
    def setObjectClass(self, object_class):
        """
        @param object_class: The class-name of the object-tag
        """
        self.object_class = object_class
    
    def getObjectWidth(self):
        """
        @return: width parameter of the object-tag
        """
        return self.object_width
    
    def setObjectWidth(self, width):
        """
        @param object_class: The width parameter of the object-tag
        """
        self.object_width = str(width)
    
    def getObjectHeight(self):
        """
        @return: height parameter of the object-tag
        """
        return self.object_height
    
    def setObjectHeight(self, height):
        """
        @param object_class: The height parameter of the object-tag
        """
        self.object_height = str(height)
        
    def getFlashUrl(self):
        """
        @return: url of the flashmovie
        """
        return self.flash_url

    def setFlashUrl(self, flash_url):
        """
        @param flash_url: The url of the flash_movie
        """
        self.flash_url = flash_url
    
    def getWmode(self):
        """
        @return: flash parameter wmode
        """
        return self.wmode
    
    def setWmode(self, wmode):
        """
        @param wmode: The flash parameter wmode
        """
        self.wmode = wmode
        
    def getQuality(self):
        """
        @return: flash parameter quality
        """
        return self.quality
    
    def setQuality(self, quality):
        """
        @param quality: The flash parameter quality
        """
        self.quality = quality
        
    def getMenu(self):
        """
        @return: flash parameter menu
        """
        if self.menu == 'true':
            return True
        else:
            return False
    
    def setMenu(self, menu):
        """
        @param menu: The flash parameter menu
        """
        if menu:
            self.menu = 'true'
        else:
            self.menu = 'false'
            
    def getAllowFullscreen(self):
        """
        @return: flash parameter allowfullscreen
        """
        if self.allowFullscreen == 'true':
            return True
        else:
            return False
    
    def setAllowFullscreen(self, allowFullscreen):
        """
        @param allowFullscreen: The flash parameter allowfullscreen
        """
        if allowFullscreen:
            self.allowFullscreen = 'true'
        else:
            self.allowFullscreen = 'false'
        
    def getBGColor(self):
        """
        @return: flash parameter bgcolor
        """
        return self.bgColor
    
    def setBGColor(self, bgcolor):
        """
        @param bgcolor: The flash parameter bgcolor
        """
        self.bgColor = bgcolor
        
    def getFlashVars(self):
        """
        @return: flash parameter flashvars
        """
        return self.flashvars
    
    def setFlashVars(self, flashvars):
        """
        @param flashvars: The flash parameter flashvars
        """
        self.flashvars = flashvars
        
    def __getFlashHTML(self):
        object = 'id="'+self.object_id+'"'
        if self.object_width:
            object += ' width="'+self.object_width+'"'
        if self.object_height:
            object += ' height="'+self.object_height+'"'
        if self.object_class:
            object += ' class="'+self.object_class+'"'
        if self.browser == 'ie':
            object += ' classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000"'
        else:
            object += ' type="application/x-shockwave-flash"' 
            object += ' data="'+self.flash_url+'"'
        html =  ['<object %s>' % object]
        if self.flash_url:
            html.append('<param name="movie" value="'+self.flash_url+'" />')
        if self.quality:
            html.append('<param name="quality" value="'+self.quality+'" />')
        if self.allowScriptAccess != None:
            html.append('<param name="allowscriptaccess" value="'+self.allowScriptAccess+'" />')
        if self.allowFullscreen != None:
            html.append('<param name="allowfullscreen" value="'+self.allowFullscreen+'" />')
        if self.bgColor:
            html.append('<param name="bgcolor" value="'+self.bgColor+'"/>')
        if self.wmode != None:
            html.append('<param name="wmode" value="'+self.wmode+'" />')
        if self.menu != None:
            html.append('<param name="menu" value="'+self.menu+'" />')
        html.append('<param name="flashvars" value="'+self.getFlashVars()+'" />')
        # If Flash is not installed
        html.append("""
        <div class="noflash">
            <h3>You have no flash plugin installed</h3>
            <p>Click here to download latest version</p>
            <p>Download latest version from <a href='http://www.adobe.com/go/getflashplayer'>here</a></p>
        </div>
        """)
        html.append('</object>')
        
        flashvars = ''.join(html)
        return flashvars
            
    def getMovieElement(self):
        """
        @return: element DOM-Object of the object-tag
        """ 
        element = DOM.getElementById(self.object_id)
        return element
    
    def callFlash(self, functionName, arguments=[]):
        """
        @param functionName: Methodname of ExternalInterface
        @param arguments: List with arguments of ExternalInterfaces method
        
        @return: return value of ExternalInterfaces method
        """
        raise NotImplemented("calling of javascript and conversion of javascript parameters is required")
    
    def toJS(self, list_or_dict):
        """
        @param list_or_dict: A List or a Dictonary
        
        Converting recrusive Dictonarys and Lists to Javascript Types.
        
        @return: javascript array or object
        """
        raise NotImplemented("conversion of javascript parameters is required")

    def flashArgumentsToXML(self, arguments, num):
        """
        @return: result of flashs build in function __flash__argumentsToXML
        """
        arguments = self.toJS(arguments)
        return wnd().__flash__argumentsToXML(arguments, num);
        
        
