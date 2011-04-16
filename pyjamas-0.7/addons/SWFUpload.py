"""
API for SWFUpload http://swfupload.org

@license: Apache License Version 2.0
@copyright: 2009 Tobias Weber
@author: Tobias Weber
@contact: tobi-weber@gmx.de
"""

from pyjamas.ui.FlashPanel import FlashPanel
import DeferredHandler

from pyjamas.Timer import Timer
from pyjamas import DOM
from urllib import quote
import sys
from __pyjamas__ import wnd, JS
from pyjamas import log


class SWFUploadInstances:
    
    def addInstance(self, movieName, instance):
        setattr(self, movieName, instance)
    
class SWFUploadEventCatcher:
    
    def __init__(self):
        self.instances = SWFUploadInstances()
    
    def addInstance(self, movieName, instance):
        self.instances.addInstance(movieName, instance)
        
# Global variable called by Flash External Interface 
wnd().SWFUpload = SWFUploadEventCatcher()
        
def setInstanceGlobal(movieName, instance):
    wnd().SWFUpload.addInstance(movieName, instance)
    
# Counter for Flash-movies
global movieCount
movieCount = 0

def getMovieCount():
    return movieCount


class SWFUpload(FlashPanel):
    """
    Embedding and api handling of SWFUpload
    """
    
    QUEUE_ERROR = {
        'QUEUE_LIMIT_EXCEEDED'              : -100,
        'FILE_EXCEEDS_SIZE_LIMIT'          : -110,
        'ZERO_BYTE_FILE'                      : -120,
        'INVALID_FILETYPE'                  : -130
    }
    UPLOAD_ERROR = {
        'HTTP_ERROR'                          : -200,
        'MISSING_UPLOAD_URL'                  : -210,
        'IO_ERROR'                          : -220,
        'SECURITY_ERROR'                      : -230,
        'UPLOAD_LIMIT_EXCEEDED'              : -240,
        'UPLOAD_FAILED'                      : -250,
        'SPECIFIED_FILE_ID_NOT_FOUND'        : -260,
        'FILE_VALIDATION_FAILED'              : -270,
        'FILE_CANCELLED'                      : -280,
        'UPLOAD_STOPPED'                    : -290
    }
    FILE_STATUS = {
        'QUEUED'         : -1,
        'IN_PROGRESS'     : -2,
        'ERROR'         : -3,
        'COMPLETE'     : -4,
        'CANCELLED'     : -5
    }
    BUTTON_ACTION = {
        'SELECT_FILE'  : -100,
        'SELECT_FILES' : -110,
        'START_UPLOAD' : -120
    }
    CURSOR = {
        'ARROW' : -1,
        'HAND' : -2
    }
    WINDOW_MODE = {
        'WINDOW' : "window",
        'TRANSPARENT' : "transparent",
        'OPAQUE' : "opaque"
    }
    
    def __init__(self):
        FlashPanel.__init__(self)
        global movieCount
        
        self.settings = None
        self.eventQueue = []
        self.setObjectClass('swfupload')
        self.movieName = 'SWFUpload_'+str(movieCount)
        movieCount+=1
        self.setObjectID(self.movieName)
        self.setWmode('window')
        self.setMenu(False)
        setInstanceGlobal(self.movieName, self)
        
    def getSettings(self):
        """
        @return: the settings instance
        """
        return self.settings
    
    def setSettings(self, settings):
        """
        @param settings: An instance of Settings
        """
        self.settings = settings
        self.flash_url = self.settings.getFlashURL()
        self.setObjectWidth(self.settings.getButtonWidth())
        self.setObjectHeight(self.settings.getButtonHeight())
        self.flashvars = self.__createFlashVars()
        
    def __createFlashVars(self):
        httpSuccessString = ','.join(self.settings.http_success)
        paramString = self.__buildParamString()
        vars = [  
                "movieName=", quote(self.object_id),
                "&amp;uploadURL=", quote(self.settings.upload_url),
                "&amp;useQueryString=", quote(self.settings.use_query_string),
                "&amp;requeueOnError=", quote(self.settings.requeue_on_error),
                "&amp;httpSuccess=", quote(httpSuccessString),
                "&amp;assumeSuccessTimeout=", quote(self.settings.assume_success_timeout),
                "&amp;params=", quote(paramString),
                "&amp;filePostName=", quote(self.settings.file_post_name),
                "&amp;fileTypes=", quote(self.settings.file_types),
                "&amp;fileTypesDescription=", quote(self.settings.file_types_description),
                "&amp;fileSizeLimit=", quote(self.settings.file_size_limit),
                "&amp;fileUploadLimit=", quote(self.settings.file_upload_limit),
                "&amp;fileQueueLimit=", quote(self.settings.file_queue_limit),
                "&amp;debugEnabled=", None,
                "&amp;buttonImageURL=", quote(self.settings.button_image_url),
                "&amp;buttonWidth=", quote(self.settings.button_width),
                "&amp;buttonHeight=", quote(self.settings.button_height),
                "&amp;buttonText=", quote(self.settings.button_text),
                "&amp;buttonTextTopPadding=", quote(self.settings.button_text_top_padding),
                "&amp;buttonTextLeftPadding=", quote(self.settings.button_text_left_padding),
                "&amp;buttonTextStyle=", quote(self.settings.button_text_style),
                "&amp;buttonAction=", quote(self.settings.button_action),
                "&amp;buttonDisabled=", quote(self.settings.button_disabled),
                "&amp;buttonCursor=", quote(self.settings.button_cursor)
                ]
        return ''.join(vars)
        
    def __buildParamString(self):
        postParams = self.settings.post_params
        paramStringPairs = []
        for k,v in postParams:
            paramStringPairs.append(quote(k) + "=" + quote(v))
        return '&amp;'.join(paramStringPairs)
    
    def callFlash(self, functionName, arguments=[]):
        """
        @param functionName: Methodname of ExternalInterface
        @param arguments: List with arguments of ExternalInterfaces method
        
        @return: the return value of ExternalInterfaces method.
        
        Extended method from FlashPanel.
        """
        returnValue = FlashPanel.callFlash(self, functionName, arguments)
        if str(returnValue) == '[object Object]':
            returnValue = File(returnValue)
        return returnValue
        
    def startUpload(self, file_id=None):
        """
        @param file_id: The file id
        
        startUpload causes the file specified by the file_id parameter to
        start the upload process. If the file_id parameter is omitted
        then the first file in the queue is uploaded.
        """
        if file_id:
            self.callFlash('StartUpload', [file_id])
        else:
            self.callFlash('StartUpload')
        
    def cancelUpload(self, file_id, triggerErrorEvent=True):
        """
        @param triggerErrorEvent: Boolean, Default: True
        
        cancelUpload cancels the file specified by the file_id parameter.
        The file is then removed from the queue.
        """
        self.callFlash('CancelUpload', [file_id, triggerErrorEvent])
    
    def stopUpload(self):
        """
        stopUpload stops and re-queues the file currently being uploaded.
        """
        self.callFlash('StopUpload')
        
    def getFileByIndex(self, index):
        """
        @param index: The file index in the queue
        
        @return: retrieve a File Object from the queue by the file index.
        """
        return self.callFlash('GetFileByIndex', [index])
        
    def getFile(self, file_id):
        """
        @param file_id: The file id
        
        @return: retrieve a File Object from the queue by the file id
        """
        return self.callFlash('GetFile', [file_id])
        
    def addFileParam(self, file_id, name, value):
        """
        @param file_id: The file id
        @param name: Name of the parameter
        @param value: Value of the parameter
         
        The addFileParam function adds a name/value pair that will be sent in the POST
        with the file specified by the file_id parameter.
        The name/value pair will only be sent with the file it is added to. 
        """
        self.callFlash('AddFileParam', [fileID, name, value])
        
    def removeFileParam(self, file_id, name):
        """
        @param file_id: The file id
        @param name: Name of the parameter
        
        The removeFileParam function removes a name/value pair from a file upload that
        was added using addFileParam.
        """
        self.callFlash('RemoveFileParam', [fileID, name])
    
    def setUploadURL(self, url):
        """
        @param url: The upload url
         
        Dynamically modifies the upload_url setting.
        """
        self.callFlash('SetUploadURL', [url])
        
    def setPostParams(self, paramsDict):
        """
        @param paramsDict: Dictonary with parameters
         
        Dynamically modifies the post_params setting.
        Any previous values are over-written. 
        """
        self.callFlash('SetPostParams', [paramsDict])
        
    def addPostParam(self, name, value):
        """
        @param name: Name of the parameter
        @param value: Value of the parameter
        
        The addPostParam function adds a name/value pair that will be
        sent in the POST for all files uploaded.
        """
        self.settings.addPostParam(name, value)
        self.setPostParams(self.settings.post_params)
        
    def removePostParam(self, name):
        """
        @param name: Name of the parameter
        
        The removePostParam function removes a name/value pair from the
        values sent with the POST for file uploads.
        """
        self.settings.removePostParam(name)
        self.setPostParams(self.settings.post_params)
        
    def setFileSizeLimit(self, fileSizeLimit):
        """
        @param fileSizeLimit: Limit of the size for files
         
        Dynamically modifies the file_size_limit setting. This applies to
        all future files that are queued. The file_size_limit parameter will
        accept a unit. Valid units are B, KB, MB, and GB. The default unit is KB.

        Examples: 2147483648 B, 2097152, 2097152KB, 2048 MB, 2 GB
        """
        self.settings.fiel_size_limit = fileSizeLimit
        self.callFlash('SetFileSizeLimit', [fileSizeLimit])
        
    def setFileUploadLimit(self, fileUploadLimit):
        """
        @param fileSizeLimit: Limit of the size for a upload
        
        Dynamically modifies the file_upload_limit setting. 
        The special value zero (0) indicates "no limit".
        """
        self.settings.file_upload_limit = fileUploadLimit
        self.callFlash('SetFileUploadLimit', [fileUploadLimit])
        
    def setFileQueueLimit(self, fileQueueLimit):
        """
        @param fileSizeLimit: Limit of the size for a queue
        
        Dynamically modifies the file_queue_limit setting.
        The special value zero (0) indicates "no limit".
        """
        self.settings.file_queue_limit = fileQueueLimit
        self.callFlash("SetFileQueueLimit", [fileQueueLimit])
    
    def setFilePostName(self, filePostName):
        """
        @param filePostName: The file post name
        
        Dynamically modifies the file_post_name setting.
        The Linux Flash Player ignores this setting.
        """
        self.settings.file_post_name = filePostName
        self.callFlash("SetFilePostName", [filePostName])
        
    def setButtonDisabled(self, isDisabled):
        """
        @param isDisable: Boolean to enable/disable the button
        
        When 'true' changes the Flash Button state to disabled and ignores any clicks.
        """
        self.settings.button_disabled = isDisabled
        self.callFlash("SetButtonDisabled", [isDisabled])
        
    def setButtonAction(self, buttonAction):
        """
        @param buttonAction: button action
         
        Sets the action taken when the Flash button is clicked.
        Valid action values are taken from the BUTTON_ACTION dict.
        """
        self.settings.button_action = buttonAction
        self.callFlash("SetButtonAction", [buttonAction])
        
    def setButtonCursor(self, cursor):
        """
        @param cursor: mouse cursor 
        
        Sets the mouse cursor shown when hovering over the Flash button.
        Valid cursor values are taken from the CURSOR dict.
        """
        self.settings.button_cursor = cursor
        self.callFlash("SetButtonCursor", [cursor])
        
    def setButtonText(self, html):
        """
        @param html: Html-text for the button
         
        Sets the text that should be displayed over the Flash button.
        Text that is too large and overflows the button size will be clipped.
        The text can be styled using HTML supported by the Flash Player.
        http://livedocs.adobe.com/flash/9.0/ActionScriptLangRefV3/flash/text/TextField.html#htmlText
        """
        self.settings.button_text = html
        self.callFlash("SetButtonText", [html])

    def setButtonTextPadding(self, left, top):
        """
        @param left: left padding
        @param top: top padding
         
        Sets the top and left padding of the Flash button text. The values may be negative.
        """
        self.settings.button_text_top_padding = top
        self.settings.button_text_left_padding = left
        self.callFlash("SetButtonTextPadding", [left, top])
    
    def setButtonTextStyle(self, css):
        """
        @param css: CSS styles for the button text
        
        Sets the CSS styles used to style the Flash Button Text.
        CSS should be formatted according to the Flash Player documentation (Adobe Documentation)
        Style classes defined here can then be referenced by HTML in the button_text setting.
        http://livedocs.adobe.com/flash/9.0/ActionScriptLangRefV3/flash/text/StyleSheet.html
        """
        self.settings.button_text_style = css
        self.callFlash("SetButtonTextStyle", [css])

    def setButtonDimensions(self, width, height):
        """
        @param width: The width of the button
        @param height: The height of the button
        
        Dynamically change the Flash button's width and height. The values should
        be numeric and should not include any units. The height value should be 1/4th
        of the total button image height so the button state sprite images can be
        displayed correctly
        """
        self.settings.button_width = width;
        self.settings.button_height = height;
        movie = self.getMovieElement()
        if movie:
            DOM.setStyleAttribute(movie, 'width', width + 'px')
            DOM.setStyleAttribute(movie, 'height', height + 'px')
        self.callFlash("SetButtonDimensions", [width, height])
        
    def setButtonImageURL(self,  buttonImageURL):
        """
        @param buttonImageURL: The image url for the button
        
        Dynamically change the image used in the Flash Button. The image url must be
        relative to the swfupload.swf file, an absolute path (e.g., starting with a /),
        or a fully qualified url. Any image format supported by Flash can be loaded.
        The most notable formats are jpg, gif, and png.
        The button image is expected to be a button sprite (or a single image file with
        several images stacked together). The image will be used to represent all the
        button states by moving the image up or down to only display the needed portion.
        These states include: normal, hover, click, disabled. 
        """
        self.settings.button_image_url = buttonImageURL
        self.callFlash("SetButtonImageURL", [buttonImageURL])

    # External Interface Methods
    def testExternalInterface(self):
        try:
            return self.callFlash("TestExternalInterface")
        except:
            return False
    
    def flashReady(self):
        """
        Event-Method called by swfupload
        """
        #log.writebr('Flash Ready')
        self.swfUploadLoaded()
    
    def swfUploadLoaded(self):
        """
        Event-Method called by swfupload
        """
        DeferredHandler.add(self.settings.swfupload_loaded_handler)
        
    def uploadProgress(self, file, bytesLoaded, totalBytes):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.upload_progress_handler, [file, bytesLoaded, totalBytes])
        
    def uploadError(self, file, errorCode, message):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.upload_error_handler, [file, errorCode, message])
        
    def uploadSuccess(self, file, receivedResponse, serverData):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.upload_success_handler, [file, receivedResponse, serverData])
        
    def uploadComplete(self, file):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.upload_complete_handler, [file])
        
    def fileDialogStart(self):
        """
        Event-Method called by swfupload
        """
        DeferredHandler.add(self.settings.file_dialog_start_handler)
        
    def fileQueued(self, file):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.file_queued_handler, [file])
        
    def fileQueueError(self, file, errorCode, message):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        DeferredHandler.add(self.settings.file_queue_error_handler, [file, errorCode, message])
        
    def fileDialogComplete(self, sel, qu, tqu):
        """
        Event-Method called by swfupload
        """
        DeferredHandler.add(self.settings.file_dialog_complete_handler, [sel, qu, tqu])
        
    def uploadStart(self, file):
        """
        Event-Method called by swfupload
        """
        file = File(file)
        status = self.settings.upload_start_handler(file)
        self.callFlash('ReturnUploadStart', [status])
        
                
class Settings:
    """
    
    """
    
    def __init__(self):
        # Upload backend settings
        self.upload_url = ""
        """
        The upload_url setting accepts a full, absolute, or relative target URL for the uploaded file.
        Relative URLs should be relative to document. The upload_url should be in the same domain as
        the Flash Control for best compatibility.

        If the preserve_relative_urls setting is false SWFUpload will convert the relative URL to an
        absolute URL to avoid the URL being interpreted differently by the Flash Player on different platforms.
        If you disable SWFUploads conversion of the URL relative URLs should be relative to the swfupload.swf file.
        """
        self.preserve_relative_urls = False
        """
        A boolean value that indicates whether SWFUpload should attempt to convert relative URLs used by the
        Flash Player to absolute URLs. If set to true SWFUpload will not modify any URLs. The default value is false.
        """
        self.file_post_name = 'Filedata'
        """
        The file_post_name allows you to set the value name used to post the file. This is not related
        to the file name. The default value is 'Filedata'. For maximum compatibility it is recommended
        that the default value is used.
        """
        self.post_params = {}
        """
        The post_params setting defines the name/value pairs that will be posted with each uploaded file.
        This setting accepts a Dictonary. Multiple post name/value pairs should be defined as demonstrated
        in the sample settings object. Values must be either strings or numbers.
        """
        self.use_query_string = False
        """
        The use_query_string setting may be true or false. This value indicates whether SWFUpload should
        send the post_params and file params on the query string or the post.
        """
        self.requeue_on_error = False
        """
        The requeue_on_error setting may be true or false. When this setting is true any files that has an
        uploadError (excluding fileQueue errors and the FILE_CANCELLED uploadError) is returned to the front
        of the queue rather than being discarded. The file can be uploaded again if needed. To remove the file
        from the queue the cancelUpload method must be called.

        All the events associated with a failed upload are still called and so the requeuing the failed upload
        can conflict with the Queue Plugin (or custom code that uploads the entire queue).
        Code that automatically uploads the next file in the queue will upload the failed file over and over
        again if care is not taken to allow the failing upload to be cancelled. 
        """
        self.http_success = []
        """
        A list that defines the HTTP Status Codes that will trigger success. 200 is always a success.
        Also, only the 200 status code provides the serverData.

        When returning and accepting an HTTP Status Code other than 200 it is not necessary for the server
        to return content. 
        """
        self.assume_success_timeout = 0
        """
         The number of seconds SWFUpload should wait for Flash to detect the server's response after the file
         has finished uploading. This setting allows you to work around the Flash Player bugs where long running
         server side scripts causes Flash to ignore the server response or the Mac Flash Player bug that ignores
         server responses with no content.

        Testing has shown that Flash will ignore server responses that take longer than 30 seconds after the last
        uploadProgress event.

        A timeout of zero (0) seconds disables this feature and is the default value. SWFUpload will wait indefinitely
        for the Flash Player to trigger the uploadSuccess event. 
        """
        
        # File Settings
        self.file_types =  '*.*'
        """
        The file_types setting accepts a semi-colon separated list of file extensions that are allowed to be
        selected by the user. Use '*.*' to allow all file types.
        """
        self.file_types_description =  'All Files'
        """
        A text description that is displayed to the user in the File Browser dialog. 
        """
        self.file_size_limit =  0
        """
        The file_size_limit setting defines the maximum allowed size of a file to be uploaded.
        This setting accepts a value and unit. Valid units are B, KB, MB and GB.
        If the unit is omitted default is KB. A value of 0 (zero) is interpreted as unlimited.

        Note: This setting only applies to the user's browser. It does not affect any settings or
        limits on the web server.
        """
        self.file_upload_limit = 0
        """
        Defines the number of files allowed to be uploaded by SWFUpload. This setting also sets the
        upper bound of the file_queue_limit setting. Once the user has uploaded or queued the maximum number
        of files she will no longer be able to queue additional files. The value of 0 (zero) is interpreted
        as unlimited. Only successful uploads (uploads the trigger the uploadSuccess event) are counted toward
        the upload limit. The setStats function can be used to modify the number of successful uploads.

        Note: This value is not tracked across pages and is reset when a page is refreshed.
        File quotas should be managed by the web server.
        """
        self.file_queue_limit = 0
        """
        Defines the number of unprocessed files allowed to be simultaneously queued. Once a file is uploaded,
        errored, or cancelled a new files can be queued in its place until the queue limit has been reached.
        If the upload limit (or remaining uploads allowed) is less than the queue limit then the lower number is used.
        """
    
        # Flash Settings
        self.flash_url = 'swfupload.swf'
        """
        The full, absolute, or relative URL to the Flash Control swf file. This setting cannot be changed once the
        SWFUpload has been instantiated. Relative URLs are relative to the page URL. 
        """
        self.prevent_swf_caching = True
        """
        This boolean setting indicates whether a random value should be added to the Flash URL in an attempt to
        prevent the browser from caching the SWF movie. This works around a bug in some IE-engine based browsers.

        Note: The algorithm for adding the random number to the URL is dumb and cannot handle URLs that already
        have some parameters.
        """
        
        # Button Settings
        self.button_image_url = ''
        """
        Fully qualified, absolute or relative URL to the image file to be used as the Flash button.
        Any Flash supported image file format can be used (another SWF file or gif, jpg, or png).

        This URL is affected by the preserve_relative_urls setting and should follow the same rules
        as the upload_url setting.

        The button image is treated as a sprite. There are 4 button states that must be represented
        by the button image.
        Each button state image should be stacked above the other in this order: normal, hover, down/click, disabled.
        """
        self.button_width = 1
        """
        A number defining the width of the Flash button.
        """
        self.button_height = 1
        """
        A number defining the height of the Flash button.
        This value should be 1/4th of the height or the button image.
        """
        self.button_text = ''
        """
        Plain or HTML text that is displayed over the Flash button.
        HTML text can be further styled using CSS classes and the button_text_style setting
        """
        self.button_text_style = 'color: #000000; font-size: 16pt;'
        """
        CSS style string that defines how the button_text is displayed.
        """
        self.button_text_top_padding = 0
        """
        Used to vertically position the Flash button text. Negative values may be used.
        """
        self.button_text_left_padding = 0
        """
        Used to horizontally position the Flash button text. Negative values may be used.
        """
        self.button_action = SWFUpload.BUTTON_ACTION['SELECT_FILES']
        """
        Defines the action taken when the Flash button is clicked.
        """
        self.button_disabled = False
        """
        A boolean value that sets whether the Flash button is in the disabled state.
        When in the disabled state the button will not execute any actions.
        """
        self.button_cursor = -2 #SWFUpload.CURSOR.ARROW
        """
        Used to define what type of mouse cursor is displayed when hovering over the Flash button.
        """
        self.button_window_mode = SWFUpload.WINDOW_MODE['WINDOW']
        """
        Sets the WMODE property of the Flash Movie.
        """
        
        # Event Handlers
        self.return_upload_start_handler = None
        self.swfupload_loaded_handler = None
        self.file_dialog_start_handler = None
        self.file_queued_handler = None
        self.file_queue_error_handler = None
        self.file_dialog_complete_handler = None
        
        self.upload_start_handler = None
        self.upload_progress_handler = None
        self.upload_error_handler = None
        self.upload_success_handler = None
        self.upload_complete_handler = None
        
        #self.debug_handler = self.debugMessage
    
        # Other settings
        self.custom_settings = {}
        self.customSettings = self.custom_settings
        
        # Update the flash url if needed
        if self.prevent_swf_caching:
            # TODO
            pass
            #self.flash_url = self.flash_url + self.flash_url.indexOf("?") < 0 ? "?" : "&") + "preventswfcaching=" + new Date().getTime()
    
    def setURL(self, url):
        """
        @param url: The upload url
        """
        self.upload_url = url
        
    def getURL(self):
        """
        @return: the upload url
        """
        return self.upload_url
    
    def setSuccessTimeout(self, assume_success_timeout):
        """
        @param assume_success_timeout: The success timeout
        """
        self.assume_success_timeout = assume_success_timeout
        
    def getSuccessTimeout(self):
        """
        @return: the success timeout
        """
        return self.assume_success_timeout
    
    def setFilePostName(self, file_post_name):
        """
        @param file_post_name: The file post name
        """
        self.file_post_name = file_post_name
        
    def getFilePostName(self):
        """
        @return: the  file post name
        """
        return self.file_post_name
    
    def setPostParams(self, post_params):
        """
        @param post_params: Dictonary with post parameters
        """
        self.post_params =  post_params
        
    def addPostParam(self, name, value):
        """
        @param name: Name of the parameter
        @param value: Value of the parameter
        """
        self.post_params[name] = value
        
    def removePostParam(self, name):
        pass # TODO
        
    def getPostParams(self):
        """
        @return: the post parameters
        """
        return self.post_params
    
    def setPreventSWFCaching(self, prevent_swf_caching):
        """
        @param prevent_swf_caching: Boolean if prevent swf caching
        """
        self.prevent_swf_caching = prevent_swf_caching
        
    def getPreventSWFCaching(self):
        """
        @return: if prevent swf caching
        """
        return self.prevent_swf_caching
    
    def useQueryString(self, use_query_string):
        """
        @param use_query_string: Boolean if to use a query string
        """
        self.use_query_string = use_query_string
        
    def isUseQueryString(self):
        """
        @return: if to use a query string
        """
        return self.use_query_string
        
    def setRequeueOnError(self, requeue_on_error):
        self.requeue_on_error = requeue_on_error
        
    def getRequeueOnError(self):
        return self.requeue_on_error
    
    def setHTTPSuccess(self, http_success):
        """
        @param http_success: List with http success codes
        """
        self.http_success = http_success
        
    def getHTTPSuccess(self):
        """
        @return: the http success codes
        """
        return self.http_success
    
    def setFileSizeLimit(self, file_size_limit):
        """
        @param file_size_limit: Fiel size limit
        """
        self.file_size_limit = file_size_limit
        
    def getFileSizeLimit(self):
        """
        @return: the file size limit
        """
        return self.file_types
        return self.file_size_limit
    
    def setFileType(self, file_types):
        """
        @param file_types: The type(s) of files
        """
        self.file_types = file_types
        
    def getFileType(self):
        """
        @return: the type(s) of files
        """
        return self.file_types
    
    def setFileTypeDescription(self, file_types_description):
        """
        @param file_types_description: File type description
        """
        self.file_types_description = file_types_description
        
    def getFileTypeDescription(self):
        """
        @return: the file type description
        """
        return self.file_types_description
    
    def setFileUploadLimit(self, file_upload_limit):
        """
        @param file_upload_limit: File upload limit
        """
        self.file_upload_limit = file_upload_limit
        
    def getFileUploadLimit(self):
        """
        @return: the file upload limit
        """
        return self.file_upload_limit
    
    def setFileQueueLimit(self, file_queue_limit):
        """
        @param file_queue_limit: File queue limit
        """
        self.file_queue_limit = file_queue_limit
        
    def getFileQueueLimit(self):
        """
        @return: the file queue limit
        """
        return self.file_queue_limit
        
    def setButtonImageURL(self, button_image_url):
        """
        @param button_image_url: Buttons image url
        """
        self.button_image_url = button_image_url
        
    def getButtonImageURL(self):
        """
        @return: the buttons image url
        """
        return self.button_image_url
    
    def setButtonWidth(self, button_width):
        """
        @param button_width: The width of the button
        """
        self.button_width = button_width
        
    def getButtonWidth(self):
        """
        @return: the width of the button
        """
        return self.button_width
        
    def setButtonHeight(self, button_height):
        """
        @param button_height: The height of the button
        """
        self.button_height = button_height
        
    def getButtonHeight(self):
        """
        @return: the the height of the button
        """
        return self.button_height
    
    def setButtonAction(self, button_action):
        """
        @param button_action: Button action
        """
        self.button_action = button_action
        
    def getButtonAction(self):
        """
        @return: thebutton action
        """
        return button_action
    
    def setButtonHTML(self, button_text):
        """
        @param button_text: Buttons html text
        """
        self.button_text = button_text
        
    def getButtonHTML(self):
        """
        @return: the  buttons html text
        """
        return self.button_text
    
    def setButtonCSS(self, button_text_style):
        """
        @param button_text_style: CSS Style for buttons text
        """
        self.button_text_style = button_text_style
        
    def getButtonCSS(self):
        """
        @return: the  buttons css style
        """
        return self.button_text_style
    
    def setButtonTopPadding(self, button_text_top_padding):
        """
        @param button_text_top_padding: Buttons top padding
        """
        self.button_text_top_padding = button_text_top_padding
        
    def getButtonTopPadding(self):
        """
        @return: the  buttons top padding
        """
        return self.button_text_top_padding
    
    def setButtonLeftPadding(self, button_text_left_padding):
        """
        @param button_text_left_padding: Buttons left padding
        """
        self.button_text_left_padding = button_text_left_padding
        
    def getButtonLeftPadding(self):
        """
        @return: the  buttons left padding
        """
        return self.button_text_left_padding
    
    def setFlashURL(self, flash_url):
        """
        @param flash_url: The flash url
        """
        self.flash_url = flash_url
        
    def getFlashURL(self):
        """
        @return: the flash url
        """
        return self.flash_url
        
    def setEventListener(self, listener):
        """
        @param listener: The listener object
        """
        self.swfupload_loaded_handler = getattr(listener, 'swfUploadLoaded')
        self.upload_progress_handler = getattr(listener, 'uploadProgress')
        self.upload_error_handler = getattr(listener, 'uploadError')
        self.upload_success_handler = getattr(listener, 'uploadSuccess')
        self.upload_complete_handler = getattr(listener, 'uploadComplete')
        self.file_dialog_start_handler = getattr(listener, 'fileDialogStart')
        self.file_queued_handler = getattr(listener, 'fileQueued')
        self.file_queue_error_handler = getattr(listener, 'fileQueueError')
        self.file_dialog_complete_handler = getattr(listener, 'fileDialogComplete')
        self.upload_start_handler = getattr(listener, 'uploadStart')
        

class File:
    """
    The file object is passed to several event handlers. It contains information about the file.
    Some operating systems do not fill in all the values (this is especially true
    for the createdate and modificationdate values).
    """
    
    def __init__(self, file):
        ### Workaround - otherwise name is undefined ###
        name = None
        JS("""
        name = file.name;
        """)
        #################################################
        
        self.id = file.id
        """
        SWFUpload file id, used for starting or cancelling and upload 
        """
        if name:
            self.name = name #file.name
        """
        The file name. The path is not included. 
        """
        self.creationdate = file.creationdate
        """
        The date the file was created 
        """
        self.modificationdate = file.modificationdate
        """
        The date the file was last modified 
        """
        self.type = file.type
        """
        The file type as reported by the client operating system 
        """
        self.index = file.index
        """
        The index of this file for use in getFile(i)
        """
        self.filestatus = file.filestatus
        """
        The file's current status. Use SWFUpload.FILE_STATUS to interpret the value. 
        """
        self.size = file.size
        """
        The file size in bytes 
        """

    def getId(self):
        """
        @return: the file id
        """
        return self.id

    def getName(self):
        """
        @return: the filename
        """
        return self.name

    def getCreationdate(self):
        """
        @return: the creationdate
        """
        return self.creationdate

    def getModificationdate(self):
        """
        @return: the modificationdate
        """
        return self.modificationdate

    def getType(self):
        """
        @return: the file type
        """
        return self.type

    def getIndex(self):
        """
        @return: the queue index of the file
        """
        return self.index

    def getFilestatus(self):
        """
        @return: the filestatus
        """
        return self.filestatus

    def getSize(self):
        """
        @return: the file size
        """
        return self.size
    
    
class SWFUploadInterface:
    """
    Interface for events fired by swfupload
    """
    
    def swfUploadLoaded(self):
        """
        The swfUploadLoaded event is fired by flashReady. It is settable.
        swfUploadLoaded is called to let you know that it is safe to call SWFUpload methods.
        """
        pass
        
    def uploadProgress(self, file, bytesLoaded, totalBytes):
        """
        The uploadProgress event is fired periodically by the Flash Control.
        This event is useful for providing UI updates on the page.

        Note: The Linux Flash Player fires a single uploadProgress event after
        the entire file has been uploaded
        This is a bug in the Linux Flash Player.
        """
        pass
        
    def uploadError(self, file, errorCode, message):
        """
        The uploadError event is fired any time an upload is interrupted or does not
        complete successfully. The error code parameter indicates the type of error that occurred.
        The error code parameter specifies in SWFUpload.UPLOAD_ERROR.

        Stopping, Cancelling or returning 'false' from uploadStart will cause uploadError to fire.
        Upload error will not fire for files that are cancelled but still waiting in the queue.
        """
        pass
        
    def uploadSuccess(self, file, receivedResponse, serverData): 
        """
        uploadSuccess is fired when the entire upload has been transmitted and the server returns a
        HTTP 200 status code. Any data outputted by the server is available in the server data parameter.

        Due to some bugs in the Flash Player the server response may not be acknowledged and no uploadSuccess
        event is fired by Flash. In this case the assume_success_timeout setting is checked to see if enough
        time has passed to fire uploadSuccess anyway. In this case the received response parameter will be false.

        The http_success setting allows uploadSuccess to be fired for HTTP status codes other than 200.
        In this case no server data is available from the Flash Player.

        At this point the upload is not yet complete. Another upload cannot be started from uploadSuccess.
        """
        pass
        
    def uploadComplete(self, file): 
        """
        uploadComplete is always fired at the end of an upload cycle (after uploadError or uploadSuccess).
        At this point the upload is complete and another upload can be started.

        If you want the next upload to start automatically this is a good place to call this.uploadStart().
        Use caution when calling uploadStart inside the uploadComplete event if you also have code that cancels
        all the uploads in a queue.
        """
        pass
        
    def fileDialogStart(self): 
        """
        fileDialogStart is fired after selectFile for selectFiles is called.
        This event is fired immediately before the File Selection Dialog window is displayed.
        However, the event may not execute until after the Dialog window is closed.
        """
        pass
        
    def fileQueued(self, file): 
        """
        The fileQueued event is fired for each file that is queued after the File
        Selection Dialog window is closed.
        """
        pass
        
    def fileQueueError(self, file, errorCode, message): 
        """
        The fileQueueError event is fired for each file that was not queued after the
        File Selection Dialog window is closed. A file may not be queued for several reasons
        such as, the file exceeds the file size, the file is empty or a file or queue limit has been exceeded.
        The reason for the queue error is specified by the error code parameter. The error code corresponds to a
        SWFUpload.QUEUE_ERROR dict.
        """
        pass
        
    def fileDialogComplete(self, sel, qu, tqu): 
        """
        The fileDialogComplete event fires after the File Selection Dialog window has been closed and all the selected
        files have been processed. The 'number of files queued' argument indicates the number of files that were
        queued from the dialog selection (as opposed to the number of files in the queue).

        If you want file uploading to begin automatically this is a good place to call 'startUpload()'
        """
        pass
        
    def uploadStart(self, file): 
        """
        uploadStart is called immediately before the file is uploaded. This event provides an opportunity
        to perform any last minute validation, add post params or do any other work before the file is uploaded.

        The upload can be cancelled by returning 'false' from uploadStart.
        If you return 'true' or do not return any value then the upload proceeds.
        Returning 'false' will cause an uploadError event to fired.
        """
        return True
    
    