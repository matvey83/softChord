#!/usr/bin/env python
# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2007 Jan Alonzo <jmalonzo@unpluggable.com>
# Copyright (C) 2008, 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
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
"""
    pyjd.py is the loader for Pyjamas-Desktop applications.

    It takes as the first argument either the python module containing a class
    named after the module, with an onModuleLoad() function, or an HTML page
    containing one or more <meta name="pygwt:module" content="modulename" />
    tags.

    This is an example Hello.py module (which you would load with
    pyjd.py Hello.py):

        from pyjamas.ui import RootPanel, Button
        class Hello:
            def onModuleLoad(self):
                RootPanel().add(Button("Hello world"))

    This is an example HTML file which will load the above example
    (which you would load with pyjd.py Hello.html, and the application
     Hello.py will be automatically located, through the <meta /> tag):

        <html>
            <head> <meta name="pygwt:module" content="Hello" /> </head>
            <body />
        </html>

    pyjd.py will create a basic template HTML, based on the name of your
    application if you do not provide one, in order to load the application.
    The basic template does not contain any HTML, or any links to CSS
    stylesheets, and so your application will have to add everything,
    manually, by manipulating the DOM model.  The basic template does,
    however, include a "History" frame, which is essential for the Pyjamas
    History module to function correctly.

    You may find using an HTML page, even to just add a CSS stylesheet
    (in the usual way - <link rel='stylesheet' href='./Hello.css' /> or
    other location, even href="http://foo.org/style.css") to be more
    convenient.

    pyjd.py also takes a second argument (which the author has found
    to be convenient) which can be used to specify an alternative
    "root" location for loading of content from any "relative" URLs
    in your DOM document.  for example, equivalent to images with
    <img src="./images/test.png" />.  the author has found this to
    be convenient when running pyjamas applications
    http://code.google.com/p/pyjamas), which store the static content
    in a directory called "public".  Specifying this directory as the
    second argument to pyjd.py allows the same application being
    developed with Pyjamas to also be tested under Pyjamas-Desktop.

    However, you may find that you need to write a separate short
    http page for your Pyjamas-Desktop app, which is an identical
    copy of your Pyjamas HTML page in every respect but making
    absolutely sure that you remove the javascript "pygwt.js" script.
    You will still need to place the page on your Web Server,
    and then load it with pyjs.py as follows:

        pyjs.py http://127.0.0.1/jsonrpc/output/test.html

    This will ensure that pyjs.py - more specifically Webkit - knows
    the correct location for all relative URLS (of the form
    href="./images", stylesheet links, img src= references etc.)

    If you do not remove the "pygwt.js" script from the copy of
    the http loader page, pyjs.py, being effectively a web browser
    in its own right thanks to Webkit, will successfully run your
    Pyjamas-compiled application!  Unfortunately, however, the
    loader will also be activated, and you will end up running
    two conflicting versions of your application - one javascript
    based and one python based - simultaneously.  It's probably
    best to avoid this scenario.

    pyjd.py is based on the PyWebkitGTK "demobrowser.py".
"""

import os
import new
import sys
import logging
import time
from gettext import gettext as _
from traceback import print_stack

import gtk
import gobject
import webkit

def module_load(m):
    minst = None
    exec """\
from %(mod)s import %(mod)s
minst = %(mod)s()
""" % ({'mod': m})
    return minst

class WebToolbar(gtk.Toolbar):
    def __init__(self, browser):
        gtk.Toolbar.__init__(self)

        self._browser = browser

        # navigational buttons
        self._back = gtk.ToolButton(gtk.STOCK_GO_BACK)
        self._back.set_tooltip(gtk.Tooltips(),_('Back'))
        self._back.props.sensitive = False
        self._back.connect('clicked', self._go_back_cb)
        self.insert(self._back, -1)

        self._forward = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
        self._forward.set_tooltip(gtk.Tooltips(),_('Forward'))
        self._forward.props.sensitive = False
        self._forward.connect('clicked', self._go_forward_cb)
        self.insert(self._forward, -1)
        self._forward.show()

        self._stop_and_reload = gtk.ToolButton(gtk.STOCK_REFRESH)
        self._stop_and_reload.set_tooltip(gtk.Tooltips(),_('Stop and reload current page'))
        self._stop_and_reload.connect('clicked', self._stop_and_reload_cb)
        self.insert(self._stop_and_reload, -1)
        self._stop_and_reload.show()
        self._loading = False

        self.insert(gtk.SeparatorToolItem(), -1)

        # zoom buttons
        self._zoom_in = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
        self._zoom_in.set_tooltip(gtk.Tooltips(), _('Zoom in'))
        self._zoom_in.connect('clicked', self._zoom_in_cb)
        self.insert(self._zoom_in, -1)
        self._zoom_in.show()

        self._zoom_out = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
        self._zoom_out.set_tooltip(gtk.Tooltips(), _('Zoom out'))
        self._zoom_out.connect('clicked', self._zoom_out_cb)
        self.insert(self._zoom_out, -1)
        self._zoom_out.show()

        self._zoom_hundred = gtk.ToolButton(gtk.STOCK_ZOOM_100)
        self._zoom_hundred.set_tooltip(gtk.Tooltips(), _('100% zoom'))
        self._zoom_hundred.connect('clicked', self._zoom_hundred_cb)
        self.insert(self._zoom_hundred, -1)
        self._zoom_hundred.show()

        self.insert(gtk.SeparatorToolItem(), -1)

        # location entry
        self._entry = gtk.Entry()
        self._entry.connect('activate', self._entry_activate_cb)
        self._current_uri = None

        entry_item = gtk.ToolItem()
        entry_item.set_expand(True)
        entry_item.add(self._entry)
        self._entry.show()

        self.insert(entry_item, -1)
        entry_item.show()

        # scale other content besides from text as well
        self._browser.set_full_content_zoom(True)

        self._browser.connect("title-changed", self._title_changed_cb)

    def set_loading(self, loading):
        self._loading = loading

        if self._loading:
            self._show_stop_icon()
            self._stop_and_reload.set_tooltip(gtk.Tooltips(),_('Stop'))
        else:
            self._show_reload_icon()
            self._stop_and_reload.set_tooltip(gtk.Tooltips(),_('Reload'))
        self._update_navigation_buttons()

    def _set_address(self, address):
        self._entry.props.text = address
        self._current_uri = address

    def _update_navigation_buttons(self):
        can_go_back = self._browser.can_go_back()
        self._back.props.sensitive = can_go_back

        can_go_forward = self._browser.can_go_forward()
        self._forward.props.sensitive = can_go_forward

    def _entry_activate_cb(self, entry):
        self._browser.open(entry.props.text)

    def _go_back_cb(self, button):
        self._browser.go_back()

    def _go_forward_cb(self, button):
        self._browser.go_forward()

    def _title_changed_cb(self, widget, frame, title):
        self._set_address(frame.get_uri())

    def _stop_and_reload_cb(self, button):
        if self._loading:
            self._browser.stop_loading()
        else:
            self._browser.reload()

    def _show_stop_icon(self):
        self._stop_and_reload.set_stock_id(gtk.STOCK_CANCEL)

    def _show_reload_icon(self):
        self._stop_and_reload.set_stock_id(gtk.STOCK_REFRESH)

    def _zoom_in_cb (self, widget):
        """Zoom into the page"""
        self._browser.zoom_in()

    def _zoom_out_cb (self, widget):
        """Zoom out of the page"""
        self._browser.zoom_out()

    def _zoom_hundred_cb (self, widget):
        """Zoom 100%"""
        if not (self._browser.get_zoom_level() == 1.0):
            self._browser.set_zoom_level(1.0);

class WebStatusBar(gtk.Statusbar):
    def __init__(self):
        gtk.Statusbar.__init__(self)
        self.iconbox = gtk.EventBox()
        self.iconbox.add(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON))
        self.pack_start(self.iconbox, False, False, 6)
        self.iconbox.hide_all()

    def display(self, text, context=None):
        cid = self.get_context_id("pywebkitgtk")
        self.push(cid, str(text))

    def show_javascript_info(self):
        self.iconbox.show()

    def hide_javascript_info(self):
        self.iconbox.hide()

def mash_attrib(name, joiner='-'):
    res = ''
    for c in name:
        if c.isupper():
            res += joiner + c.lower()
        else:
            res += c
    return res

def _alert(self, msg):
    global wv
    wv._alert(msg)

def getDomDocument(self):
    return self.getWebkitDocument()

def addWindowEventListener(self, event_name, cb):
    #print self, event_name, cb
    if cb not in self._callbacks:
        self.connect("browser-event", cb)
        self._callbacks.append(cb)
    return self.addWindowEventListener(event_name, True)

def addXMLHttpRequestEventListener(element, event_name, cb):
    if not hasattr(element, "_callbacks"):
        element._callbacks = []
    if cb not in element._callbacks:
        element.connect("browser-event", cb)
        element._callbacks.append(cb)
    return element.addEventListener(event_name)

def addEventListener(element, event_name, cb):
    if not hasattr(element, "_callbacks"):
        element._callbacks = []
    if cb not in element._callbacks:
        element.connect("browser-event", cb)
        element._callbacks.append(cb)
    return element.addEventListener(event_name, True)

class Browser(gtk.Window):
    def __init__(self, application, appdir=None, width=800, height=600):
        gtk.Window.__init__(self)
        self.set_size_request(width, height)

        self.already_initialised = False

        logging.debug("initializing web browser window")

        self._loading = False
        self._browser= webkit.WebView()
        #self._browser.connect('load-started', self._loading_start_cb)
        #self._browser.connect('load-progress-changed', self._loading_progress_cb)
        self._browser.connect('load-finished', self._loading_stop_cb)
        self._browser.connect("title-changed", self._title_changed_cb)
        self._browser.connect("hovering-over-link", self._hover_link_cb)
        self._browser.connect("status-bar-text-changed", self._statusbar_text_changed_cb)
        self._browser.connect("icon-loaded", self._icon_loaded_cb)
        self._browser.connect("selection-changed", self._selection_changed_cb)
        self._browser.connect("set-scroll-adjustments", self._set_scroll_adjustments_cb)
        self._browser.connect("populate-popup", self._populate_popup)
#        self._browser.connect("navigation-requested", self._navigation_requested_cb)

        self._browser.connect("console-message",
                              self._javascript_console_message_cb)
        self._browser.connect("script-alert",
                              self._javascript_script_alert_cb)
        self._browser.connect("script-confirm",
                              self._javascript_script_confirm_cb)
        self._browser.connect("script-prompt",
                              self._javascript_script_prompt_cb)

        self._scrolled_window = gtk.ScrolledWindow()
        self._scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        self._scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        self._scrolled_window.add(self._browser)
        self._scrolled_window.show_all()

        self._toolbar = WebToolbar(self._browser)

        self._statusbar = WebStatusBar()

        vbox = gtk.VBox(spacing=4)
        vbox.pack_start(self._toolbar, expand=False, fill=False)
        vbox.pack_start(self._scrolled_window)
        vbox.pack_end(self._statusbar, expand=False, fill=False)

        self.add(vbox)
        self.set_default_size(600, 480)

        self.connect('destroy', gtk.main_quit)

        self.application = application
        self.appdir = appdir

        return

        if os.path.isfile(application):
            
            (pth, app) = os.path.split(application)
            if appdir:
                pth = os.path.abspath(appdir)
            sys.path.append(pth)

            m = None
            # first, pretend it's a module. if success, create fake template
            # otherwise, treat it as a URL
            if application[-3:] == ".py":

                try:
                    m = module_load(app[:-3])
                except ImportError, e:
                    print_stack()
                    print e
                    m = None

            if m is None:
                application = os.path.abspath(application)
                print application
                self._browser.open(application)
            else:
                # it's a python app.
                if application[-3:] != ".py":
                    print "Application %s must be a python file (.py)"
                    sys.exit(-1)
                # ok, we create a template with the app name in it:
                # pygwt_processMetas will pick up the app name
                # and do the load, there.  at least this way we
                # have a basic HTML page to start off with,
                # including a possible stylesheet.
                fqp = os.path.abspath(application[:-3])
                template = """
<html>
    <head>
        <meta name="pygwt:module" content="%(app)s" />
        <link rel="stylesheet" href="%(app)s.css" />
        <title>%(app)s</title>
    </head>
    <body bgcolor="white" color="white">
        <iframe id='__pygwt_historyFrame' style='width:0px;height:0px;border:0px;margin:0px;padding:0px;display:none;'></iframe>
    </body>
</html>
""" % {'app': app[:-3]}

                print template
                self._browser.load_string(template, "text/html", "iso-8859-15", fqp)
        else:
            # URL.
            
            sys.path.append(os.path.abspath(os.getcwd()))
            self._browser.open(application)


    def load_app(self):

        uri = self.application
        if uri.find("://") == -1:
            # assume file
            uri = 'file://'+os.path.abspath(uri)

        self._browser.open(uri)

    def getUri(self):
        return self.application

    def init_app(self):
        # TODO: ideally, this should be done by hooking body with an "onLoad".

        from __pyjamas__ import pygwt_processMetas, set_main_frame
        from __pyjamas__ import set_gtk_module
        set_gtk_module(gtk)

        main_frame = self._browser.getMainFrame()
        main_frame._callbacks = []
        main_frame.gobject_wrap = webkit.gobject_wrap
        main_frame.platform = 'webkit'
        main_frame.addEventListener = addEventListener
        main_frame.getUri = self.getUri
        main_frame.getDomDocument = new.instancemethod(getDomDocument, main_frame)
        main_frame._addXMLHttpRequestEventListener = addXMLHttpRequestEventListener
        main_frame._addWindowEventListener = new.instancemethod(addWindowEventListener, main_frame)
        main_frame._alert = new.instancemethod(_alert, main_frame)
        main_frame.mash_attrib = mash_attrib
        set_main_frame(main_frame)

        #for m in pygwt_processMetas():
        #    minst = module_load(m)
        #    minst.onModuleLoad()

    def _set_title(self, title):
        self.props.title = title

    def _loading_start_cb(self, view, frame):
        main_frame = self._browser.get_main_frame()
        if frame is main_frame:
            self._set_title(_("Loading %s - %s") % (frame.get_title(), frame.get_uri()))
        self._toolbar.set_loading(True)

    def _loading_stop_cb(self, view, frame):
        # FIXME: another frame may still be loading?
        self._toolbar.set_loading(False)

        if self.already_initialised:
            return
        self.already_initialised = True
        self.init_app()

    def _loading_progress_cb(self, view, progress):
        self._set_progress(_("%s%s loaded") % (progress, '%'))

    def _set_progress(self, progress):
        self._statusbar.display(progress)

    def _title_changed_cb(self, widget, frame, title):
        self._set_title(_("%s") % title)

    def _hover_link_cb(self, view, title, url):
        if view and url:
           self._statusbar.display(url)
        else:
           self._statusbar.display('')

    def _statusbar_text_changed_cb(self, view, text):
        #if text:
        self._statusbar.display(text)

    def _icon_loaded_cb(self):
        print "icon loaded"

    def _selection_changed_cb(self):
        print "selection changed"

    def _set_scroll_adjustments_cb(self, view, hadjustment, vadjustment):
        self._scrolled_window.props.hadjustment = hadjustment
        self._scrolled_window.props.vadjustment = vadjustment

    def _navigation_requested_cb(self, view, frame, networkRequest):
        return 1

    def _javascript_console_message_cb(self, view, message, line, sourceid):
        self._statusbar.show_javascript_info()

    def _javascript_script_alert_cb(self, view, frame, message):

        print "alert", message

        def close(w):
            dialog.destroy()
        dialog = gtk.Dialog("Alert", None, gtk.DIALOG_DESTROY_WITH_PARENT)
        #dialog.Modal = True;
        label = gtk.Label(message)
        dialog.vbox.add(label)
        label.show()
        button = gtk.Button("OK")
        dialog.action_area.pack_start (button, True, True, 0)
        button.connect("clicked", close)
        button.show()
        #dialog.Response += new ResponseHandler (on_dialog_response)
        dialog.run ()

    def _alert(self, msg):
        self._javascript_script_alert_cb(None, None, msg)

    def _javascript_script_confirm_cb(self, view, frame, message, isConfirmed):
        pass

    def _browser_event_cb(self, view, event, message, fromwindow):
        #print "event! wha-hey!", event, view, message
        #print event.get_event_type()
        #event.stop_propagation()
        return True

    def _javascript_script_prompt_cb(self, view, frame, message, default, text):
        pass

    def _populate_popup(self, view, menu):
        aboutitem = gtk.MenuItem(label="About PyWebKit")
        menu.append(aboutitem)
        aboutitem.connect('activate', self._about_pywebkitgtk_cb)
        menu.show_all()

    def _about_pywebkitgtk_cb(self, widget):
        self._browser.open("http://live.gnome.org/PyWebKitGtk")



def setup(application, appdir=None, width=800, height=600):

    gobject.threads_init()

    global wv

    wv = Browser(application, appdir, width, height)
    wv.load_app()
    wv.show_all()

    while 1:
        if is_loaded():
            return
        run(one_event=True)

def is_loaded():
    return wv.already_initialised

def run(one_event=False):
    if one_event:
        gtk.main_iteration()
    else:
        gtk.main()


