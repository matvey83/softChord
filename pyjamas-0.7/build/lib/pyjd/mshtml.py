#import win32traceutil

import traceback
import sys
import os
import time
import new

# these three are required pre-imported, for pyjamas to work
# with the pyjd imputil etc.  awful, i know...
import threading
import encodings
import encodings.cp437


from windows import *
from ctypes import *
from ctypes.wintypes import *

import comtypes
from comtypes import IUnknown, GUID, COMMETHOD
from comtypes.automation import IDispatch, VARIANT
from comtypes.client import wrap, GetModule
from comtypes.client.dynamic import Dispatch

import comtypes.gen

if not hasattr(sys, 'frozen'):
    GetModule('atl.dll')
    GetModule('shdocvw.dll')
    try:
        GetModule('msxml2.dll')
    except:
        pass
    try:
        GetModule('msxml3.dll')
    except:
        pass
    try:
        GetModule('msxml6.dll')
    except:
        pass
    GetModule('mshtml.tlb') 
    #GetModule('progdlg.tlb') 

from comtypes.gen import SHDocVw
from comtypes.gen import MSHTML
try:
    from comtypes.gen import MSXML2
except:
    pass
try:
    from comtypes.gen import MSXML6
except:
    pass
try:
    from comtypes.gen import MSXML3
except:
    pass

atl = windll.atl                  # If this fails, you need atl.dll

# do this after gen stuff, above
import mshtmlevents 

SID_SShellBrowser = GUID("{000214E2-0000-0000-C000-000000000046}")

class IOleWindow(IUnknown):
    _case_insensitive_ = True
    u'IOleWindow Interface'
    _iid_ = GUID('{00000114-0000-0000-C000-000000000046}')
    _idlflags_ = []

    _methods_ = [
        COMMETHOD([], HRESULT, 'GetWindow',
                  ( ['in'], POINTER(c_void_p), 'pHwnd' ))
        ]

class IOleInPlaceActiveObject(IOleWindow):
    _iid_ = GUID("{00000117-0000-0000-C000-000000000046}")
    _idlflags_ = []
    _methods_ = IOleWindow._methods_ + [
        COMMETHOD([], HRESULT, 'TranslateAccelerator',
                  ( ['in'], POINTER(MSG), 'pMsg' ))
        ]
    

# http://www.mail-archive.com/comtypes-users@lists.sourceforge.net/msg00439.html
class IServiceProvider(IUnknown):
    _iid_ = GUID('{6D5140C1-7436-11CE-8034-00AA006009FA}')

    # Overridden QueryService to make it nicer to use (passing it an
    # interface and it returns a pointer to that interface)
    def QueryService(self, serviceIID, interface):
        p = POINTER(interface)()
        self._QueryService(byref(serviceIID), byref(interface._iid_), byref(p))
        return p

    _methods_ = [
        COMMETHOD([], HRESULT, 'QueryService',
                  ( ['in'], POINTER(GUID), 'guidService' ),
                  ( ['in'], POINTER(GUID), 'riid' ),
                  ( ['in'], POINTER(c_void_p), 'ppvObject' ))
        ]

#class IInputObject(IUnknown):
#    _iid_= GUID("{68284FAA-6A48-11D0-8C78-00C04FD918B4}")
#
#    _methods_= IUnknown._methods_ + [
#        (STDMETHOD (HRESULT, "UIActivateIO", BOOL, POINTER(MSG))),
#        (STDMETHOD (HRESULT, "HasFocusIO")),
#        (STDMETHOD (HRESULT, "TranslateAcceleratorIO", POINTER(MSG)))]

class EventSink(object):
    # some DWebBrowserEvents
    def OnVisible(self, this, *args):
        print "OnVisible", args

    def BeforeNavigate(self, this, *args):
        print "BeforeNavigate", args

    def NavigateComplete(self, this, *args):
        print "NavigateComplete", this, args
        return

    # some DWebBrowserEvents2
    def BeforeNavigate2(self, this, *args):
        print "BeforeNavigate2", args

    def NavigateComplete2(self, this, *args):
        print "NavigateComplete2", args

    def DocumentComplete(self, this, *args):
        print "DocumentComplete", args
        if self.workaround_ignore_first_doc_complete == False:
            # ignore first about:blank.  *sigh*...
            # TODO: work out how to parse *args byref VARIANT
            # in order to get at the URI.
            self.workaround_ignore_first_doc_complete = True
            return
            
        self._loaded()

    def NewWindow2(self, this, *args):
        print "NewWindow2", args
        return
        v = cast(args[1]._.c_void_p, POINTER(VARIANT))[0]
        v.value = True

    def NewWindow3(self, this, *args):
        print "NewWindow3", args
        return
        v = cast(args[1]._.c_void_p, POINTER(VARIANT))[0]
        v.value = True

fn_txt = """\
def event_fn(self, *args):
    #print "event %s", self, args
    #print "event callbacks", self._listeners
    callbacks = self._listeners.get('%s', [])
    for fn in callbacks:
        try:
            fn(self._sender, Dispatch(args[0]), True)
        except:
            traceback.print_exc()
            sys.stderr.flush()
"""

class EventCaller:
    def __init__(self, handler, name):
        self.handler = handler
        self.name = name
    def __call__(self, *args):
        callbacks = self.handler._listeners.get(self.name, [])
        #print "event", self.name, callbacks
        for fn in callbacks:
            try:
                fn(self.handler._sender, Dispatch(args[0]), True)
            except:
                sys.stderr.write( traceback.print_exc() )
                sys.stderr.flush()

class EventHandler(object):
    def __init__(self, sender):
        self._sender = sender
        self._listeners = {}
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        #print "EventHandler requested ", name
        if name.startswith('_') or name == 'addEventListener':
            return self.__dict__[name]
        idx = name.find('_on')
        if idx >= 0:
            if idx > 0:
                name = name[idx+1:]
            #return EventCaller(self, name)
            exec fn_txt % (name[2:], name[2:])
            #exec fn_txt % (name[2:])
            #print event_fn
            return new.instancemethod(event_fn, self)
        raise AttributeError(name)

    def addEventListener(self, name, fn):
        if not self._listeners.has_key(name):
            self._listeners[name] = []
        self._listeners[name].append(fn)

class Browser(EventSink):
    def __init__(self, application, appdir):
        EventSink.__init__(self)
        self.platform = 'mshtml'
        self.application = application
        self.appdir = appdir
        self.already_initialised = False
        self.workaround_ignore_first_doc_complete = False
        self.window_handler = None
        self.node_handlers = {}

        # Create an instance of IE via AtlAxWin.
        atl.AtlAxWinInit()
        hInstance = GetModuleHandle(None)

        self.hwnd = CreateWindowEx(0,
                              "AtlAxWin",
                              "about:blank",
                              WS_OVERLAPPEDWINDOW |
                              WS_VISIBLE | 
                              WS_HSCROLL | WS_VSCROLL,
                              CW_USEDEFAULT,
                              CW_USEDEFAULT,
                              CW_USEDEFAULT,
                              CW_USEDEFAULT,
                              NULL,
                              NULL,
                              hInstance,
                              NULL)

        # Get the IWebBrowser2 interface for the IE control.
        self.pBrowserUnk = POINTER(IUnknown)()
        atl.AtlAxGetControl(self.hwnd, byref(self.pBrowserUnk))
        # the wrap call querys for the default interface
        self.pBrowser = wrap(self.pBrowserUnk)
        self.pBrowser.RegisterAsBrowser = True
        self.pBrowser.AddRef()

        self.conn = mshtmlevents.GetEvents(self.pBrowser, sink=self,
                        interface=SHDocVw.DWebBrowserEvents2)

        #print "browser HWND", SetFocus(self.pBrowser.HWND)

    def _alert(self, txt):
        self.getDomWindow().alert(txt)

    def load_app(self):

        uri = self.application
        if uri.find(":") == -1:
            # assume file
            uri = 'file://'+os.path.abspath(uri)

        #print "load_app", uri

        self.application = uri
        v = byref(VARIANT())
        self.pBrowser.Navigate(uri, v, v, v, v)

        # Show Window
        cw = c_int(self.hwnd)
        ShowWindow(cw, c_int(SW_SHOW))
        UpdateWindow(cw)


        # http://msdn.microsoft.com/en-us/library/aa752126%28VS.85%29.aspx
        wba = self.pBrowser.QueryInterface(IServiceProvider)
        wn = wrap(wba.QueryService(SID_SShellBrowser, IOleWindow))

        hwnd = c_void_p(0)
        pHnd = byref(hwnd)
        wn.GetWindow(pHnd)

        #PostMessage(pHnd.value, WM_SETFOCUS,0,0)
        SetFocus(hwnd)
        #print self.hwnd, pHnd.value

    def getDomDocument(self):
        return Dispatch(self.pBrowser.Document)

    def getDomWindow(self):
        return self.getDomDocument().parentWindow

    def _addXMLHttpRequestEventListener(self, node, event_name, event_fn):
        
        #print "_addXMLHttpRequestEventListener", event_name

        rcvr = mshtmlevents._DispEventReceiver()
        rcvr.dispmap = {0: event_fn}

        #print rcvr
        rcvr.sender = node
        #print rcvr.sender
        ifc = rcvr.QueryInterface(IDispatch)
        #print ifc
        v = VARIANT(ifc)
        #print v
        setattr(node, event_name, v)
        return ifc

    def addEventListener(self, node, event_name, event_fn):
        
        rcvr = mshtmlevents._DispEventReceiver()
        rcvr.dispmap = {0: event_fn}

        rcvr.sender = node
        ifc = rcvr.QueryInterface(IDispatch)
        v = VARIANT(ifc)
        setattr(node, "on"+event_name, v)
        return ifc

        rcvr = mshtmlevents.GetDispEventReceiver(MSHTML.HTMLElementEvents2, event_fn, "on%s" % event_name)
        rcvr.sender = node
        ifc = rcvr.QueryInterface(IDispatch)
        node.attachEvent("on%s" % event_name, ifc)
        return ifc

    def mash_attrib(self, attrib_name):
        return attrib_name

    def _addWindowEventListener(self, event_name, event_fn):
        
        #print "_addWindowEventListener", event_name, event_fn
        #rcvr = mshtmlevents.GetDispEventReceiver(MSHTML.HTMLWindowEvents,
        #                   event_fn, "on%s" % event_name)
        #print rcvr
        #rcvr.sender = self.getDomWindow()
        #print rcvr.sender
        #ifc = rcvr.QueryInterface(IDispatch)
        #print ifc
        #v = VARIANT(ifc)
        #print v
        #setattr(self.getDomWindow(), "on%s" % event_name, v)
        #return ifc

        wnd = self.pBrowser.Document.parentWindow
        if self.window_handler is None:
            self.window_handler = EventHandler(self)
            self.window_conn = mshtmlevents.GetEvents(wnd,
                                        sink=self.window_handler,
                                    interface=MSHTML.HTMLWindowEvents2)
        self.window_handler.addEventListener(event_name, event_fn)
        return event_name # hmmm...

    def getXmlHttpRequest(self):
        #print "getXMLHttpRequest"
        o = comtypes.client.CreateObject('MSXML2.XMLHTTP.3.0')
        #print "getXMLHttpRequest", o
        return Dispatch(o)
        
    def getUri(self):
        return self.application

    def _loaded(self):

        #print "loaded"

        if self.already_initialised:
            return
        self.already_initialised = True

        self._addWindowEventListener("unload", self.on_unload_callback)

        from __pyjamas__ import pygwt_processMetas, set_main_frame
        set_main_frame(self)

        (pth, app) = os.path.split(self.application)
        if self.appdir:
            pth = os.path.abspath(self.appdir)
        sys.path.append(pth)
        
    def on_unload_callback(self, *args):
        PostQuitMessage(0)

global timer_q
timer_q = []

WM_USER_TIMER = RegisterWindowMessage("Timer Notify")

global wv
wv = None

def MainWin(one_event):

    # Pump Messages
    msg = MSG()
    pMsg = pointer(msg)
    
    while 1:
        res = GetMessage( pMsg, NULL, 0, 0)
        if res == -1:
            return 0
        if res == 0:
            break 

        if timer_q:
            fn = timer_q.pop()
            fn()

        if msg.message == WM_USER_TIMER:
            continue

        app = wv.pBrowser.Application
        ao = app.QueryInterface(IOleInPlaceActiveObject)
        if ao.TranslateAccelerator(pMsg):
        #if not TranslateAccelerator( 
        #                wv.hwnd,  #handle to receiving window 
        #                NULL,    #handle to active accelerator table 
        #                pMsg):     #message data 
            TranslateMessage(pMsg)
            DispatchMessage(pMsg)

        if one_event:
            break

    return msg.wParam
    
def add_timer_queue(fn):
    timer_q.append(fn)
    PostMessage(c_int(wv.hwnd), UINT(WM_USER_TIMER), WPARAM(0), LPARAM(0xffff))

def is_loaded():
    return wv.already_initialised

def run(one_event=False, block=True):
    try:
        MainWin(one_event) # TODO: ignore block arg for now
    except:
        sys.stderr.write( traceback.print_exc() )
        sys.stderr.flush()

def setup(application, appdir=None, width=800, height=600):

    global wv
    wv = Browser(application, appdir)

    wv.load_app()

    while 1:
        if is_loaded():
            return
        run(one_event=True)

