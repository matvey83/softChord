# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import os
import sys
import hulahop
# this is for storing the gecko stuff (cache, cookies, plugins etc.)
gecko_path = os.environ.get('HOME', '.') 
gecko_path = os.path.join(gecko_path, ".pyjd")
hulahop.startup(gecko_path)

from hulahop.webview import WebView

import gtk
import gtk.gdk
import gobject
import xpcom

from xpcom.nsError import *
from xpcom import components
from xpcom.components import interfaces

from progresslistener import ProgressListener


class ContentInvoker:
    _com_interfaces_ = interfaces.nsIDOMEventListener

    def __init__(self, node, event_fn):
        self._node = node
        self._event_fn = event_fn

    def handleEvent(self, event):
        self._event_fn(self._node, event, False)

class Browser(WebView):
    def __init__(self, application, appdir):
        WebView.__init__(self)
        self.platform = 'hulahop'
        self.progress = ProgressListener()
        self.application = application
        self.appdir = appdir
        self.already_initialised = False

        io_service_class = components.classes[ \
        "@mozilla.org/network/io-service;1"]
        io_service = io_service_class.getService(interfaces.nsIIOService)

        # Use xpcom to turn off "offline mode" detection, which disables
        # access to localhost for no good reason.  (Trac #6250.)
        io_service2 = io_service_class.getService(interfaces.nsIIOService2)
        io_service2.manageOfflineStatus = False

        self.progress.connect('loading-stop', self._loaded)
        self.progress.connect('loading-progress', self._loading)

    def _alert(self, txt):
        print "_alert", txt
        #self.get_prompt_svc().alert(None, "Alert", txt)

        def close(w):
            dialog.destroy()
        dialog = gtk.Dialog("Alert", None, gtk.DIALOG_DESTROY_WITH_PARENT)
        label = gtk.Label(txt)
        dialog.vbox.add(label)
        label.show()
        button = gtk.Button("OK")
        dialog.action_area.pack_start (button, True, True, 0)
        button.connect("clicked", close)
        button.show()
        dialog.run ()

    def get_prompt_svc(self):

        prompt_svc_cls = components.classes[ \
            "@mozilla.org/embedcomp/prompt-service;1"]
        return prompt_svc_cls.createInstance(interfaces.nsIPromptService)

    def load_app(self):

        uri = self.application
        if uri.find(":") == -1:
            # assume file
            uri = 'file://'+os.path.abspath(uri)

        self.application = uri
        self.load_uri(uri)

    def do_setup(self):
        WebView.do_setup(self)
        self.progress.setup(self)
        
    def _addXMLHttpRequestEventListener(self, node, event_name, event_fn):
        
        listener = xpcom.server.WrapObject(ContentInvoker(node, event_fn),
                                            interfaces.nsIDOMEventListener)
        print event_name, listener
        node.addEventListener(event_name, listener, False)
        return listener

    def addEventListener(self, node, event_name, event_fn):
        
        listener = xpcom.server.WrapObject(ContentInvoker(node, event_fn),
                                            interfaces.nsIDOMEventListener)
        node.addEventListener(event_name, listener, True)
        return listener

    def mash_attrib(self, attrib_name):
        return attrib_name

    def _addWindowEventListener(self, event_name, event_fn, win=None):
        
        if win is None:
            win = self.window_root
        listener = xpcom.server.WrapObject(ContentInvoker(win, event_fn),
                                            interfaces.nsIDOMEventListener)
        win.addEventListener(event_name, listener, True)
        return listener

    def getDOMParser(self):
        xml_svc_cls = components.classes[ \
            "@mozilla.org/xmlextras/domparser;1"]
        return xml_svc_cls.createInstance(interfaces.nsIDOMParser)
        
    def getXmlHttpRequest(self):
        xml_svc_cls = components.classes[ \
            "@mozilla.org/xmlextras/xmlhttprequest;1"]
        return xml_svc_cls.createInstance(interfaces.nsIXMLHttpRequest)
        
    def getUri(self):
        return self.application

    def getDomWindow(self):
        return self.get_dom_window()

    def getDomDocument(self):
        return self.get_dom_window().document

    def _loaded(self, progress_listener):

        print "loaded"

        if self.already_initialised:
            return
        self.already_initialised = True

        dw = self.get_dom_window()
        doc = dw.document

        from __pyjamas__ import pygwt_processMetas, set_main_frame
        from __pyjamas__ import set_gtk_module
        set_main_frame(self)
        set_gtk_module(gtk)

        (pth, app) = os.path.split(self.application)
        if self.appdir:
            pth = os.path.abspath(self.appdir)
        sys.path.append(pth)

        #for m in pygwt_processMetas():
        #    minst = module_load(m)
        #    minst.onModuleLoad()

    def _loading(self, progress_listener, progress):
        pass
        #print "loading", progress, self.getDomWindow().location.href

    def _trigger_fake_button(self):
        doc = self.getDomDocument()
        wnd = self.getDomWindow()
        element = self._hack_timer_workaround_bug_button
        evt = doc.createEvent('MouseEvents')
        evt.initMouseEvent("click", True, True, wnd, 1, 0, 0, 0, 0, False,
                                    False, False, False, 0, element)
        element.dispatchEvent(evt)

    def _timer_callback_workaround(self, *args):

        global timer_q
        while timer_q:
            fn = timer_q.pop()
            fn()

def is_loaded():
    return wv.already_initialised

global timer_q
timer_q = []

def add_timer_queue(fn):
    timer_q.append(fn)
    wv._trigger_fake_button()

    #DOM.buttonClick(self.b.getElement())

    # hope and pray that an event occurs!
    #event = gtk.gdk.new()
    #gtk.gdk.push(event)

def run(one_event=False, block=True):
    if one_event:
        if block or gtk.events_pending():
            gtk.main_iteration()
            sys.stdout.flush()
    else:
        while 1:
            gtk.main_iteration()
            sys.stdout.flush()

        #gtk.main()

def setup(application, appdir=None, width=800, height=600):

    gtk.gdk.threads_init()

    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.set_size_request(width, height)
    win.connect('destroy', gtk.main_quit)

    global wv
    wv = Browser(application, appdir)

    wv.show()
    win.add(wv)
    win.show()

    wv.load_app()

    while 1:
        if is_loaded() and not gtk.events_pending():
            return
        run(one_event=True)

def module_load(m):
    minst = None
    exec """\
from %(mod)s import %(mod)s
minst = %(mod)s()
""" % ({'mod': m})
    return minst

