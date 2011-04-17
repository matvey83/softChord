"""
Flash embedding Panel

@license: Apache License Version 2.0
@copyright: 2009 Tobias Weber
@author: Tobias Weber
@contact: tobi-weber@gmx.de
"""

from __javascript__ import Array, Object, eval

class FlashPanel(Panel):
    
    def callFlash(self, functionName, arguments=[]):
        """
        @param functionName: Methodname of ExternalInterface
        @param arguments: List with arguments of ExternalInterfaces method
        
        @return: return value of ExternalInterfaces method
        """
        movieElement = self.getMovieElement()
        if not movieElement:
            return None
        try:
            returnString = movieElement.CallFunction('<invoke name="%s" returntype="javascript">%s</invoke>' % (functionName, 
                                                                                                                self.flashArgumentsToXML(arguments, 0)))
            returnValue = ''
            if returnString:
                if returnString != 'undefined':
                    returnValue = eval(returnString)
        except:
            log.writebr('Call to '+functionName+' failed')
        return returnValue
    
    def toJS(self, list_or_dict):
        """
        @param list_or_dict: A List or a Dictonary
        
        Converting recrusive Dictonarys and Lists to Javascript Types.
        
        @return: javascript array or object
        """
        def toArray(self, list):
            array = Array()
            for obj in list:
                obj = self.toJS(obj)
                array.push(obj)
            return array
        def toObject(self, dict):
            object = Object()
            for key,obj in dict.iteritems():
                obj = self.toJS(obj)
                setattr(object, key, obj)
            return object
        obj = list_or_dict
        if hasattr(obj, 'keys'):
            obj = toObject(self, obj)
        elif hasattr(obj, 'append'):
            obj = toArray(self, obj)
        return obj
        
