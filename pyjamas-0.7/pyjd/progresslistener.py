# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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

import gobject
import xpcom
from xpcom.components import interfaces

class ProgressListener(gobject.GObject):
    _com_interfaces_ = interfaces.nsIWebProgressListener

    __gsignals__ = {
        'location-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([object])),
        'loading-start':    (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([])),
        'loading-stop':     (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([])),
        'loading-progress': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([float]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self.total_requests = 0
        self.completed_requests = 0

        self._wrapped_self = xpcom.server.WrapObject( \
                self, interfaces.nsIWebProgressListener)
        weak_ref = xpcom.client.WeakReference(self._wrapped_self)

        self._reset_requests_count()

    def setup(self, browser):
        mask = interfaces.nsIWebProgress.NOTIFY_STATE_NETWORK | \
               interfaces.nsIWebProgress.NOTIFY_STATE_REQUEST | \
               interfaces.nsIWebProgress.NOTIFY_LOCATION

        browser.web_progress.addProgressListener(self._wrapped_self, mask)
    
    def _reset_requests_count(self):
        self.total_requests = 0
        self.completed_requests = 0
    
    def onLocationChange(self, webProgress, request, location):
        self.emit('location-changed', location)
        
    def onProgressChange(self, webProgress, request, curSelfProgress,
                         maxSelfProgress, curTotalProgress, maxTotalProgress):
        pass
    
    def onSecurityChange(self, webProgress, request, state):
        pass
        
    def onStateChange(self, webProgress, request, stateFlags, status):
        if stateFlags & interfaces.nsIWebProgressListener.STATE_IS_REQUEST:
            if stateFlags & interfaces.nsIWebProgressListener.STATE_START:
                self.total_requests += 1
            elif stateFlags & interfaces.nsIWebProgressListener.STATE_STOP:
                self.completed_requests += 1

        if stateFlags & interfaces.nsIWebProgressListener.STATE_IS_NETWORK:
            if stateFlags & interfaces.nsIWebProgressListener.STATE_START:
                self.emit('loading-start')
                self._reset_requests_count()                
            elif stateFlags & interfaces.nsIWebProgressListener.STATE_STOP:
                self.emit('loading-stop')

        if self.total_requests < self.completed_requests:
            self.emit('loading-progress', 1.0)
        elif self.total_requests > 0:
            self.emit('loading-progress', float(self.completed_requests) /
                                          float(self.total_requests))
        else:
            self.emit('loading-progress', 0.0)

    def onStatusChange(self, webProgress, request, status, message):
        pass

