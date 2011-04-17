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

import logging

import gobject
import xpcom
from xpcom.components import interfaces

class HistoryListener(gobject.GObject):
    _com_interfaces_ = interfaces.nsISHistoryListener

    __gsignals__ = {
        'session-history-changed': (gobject.SIGNAL_RUN_FIRST, 
                                    gobject.TYPE_NONE,
                                    ([int])),
        'session-link-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                    ([str]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._wrapped_self = xpcom.server.WrapObject( \
                self, interfaces.nsISHistoryListener)
        weak_ref = xpcom.client.WeakReference(self._wrapped_self)

    def setup(self, web_navigation):
        self._session_history = web_navigation.sessionHistory
        self._session_history.addSHistoryListener(self._wrapped_self)

    def OnHistoryGoBack(self, back_uri):
        logging.debug("OnHistoryGoBack: %s" % back_uri.spec)
        self.emit('session-link-changed', back_uri.spec)
        self.emit('session-history-changed', self._session_history.index - 1)
        return True

    def OnHistoryGoForward(self, forward_uri):
        logging.debug("OnHistoryGoForward: %s" % forward_uri.spec)
        self.emit('session-link-changed', forward_uri.spec)
        self.emit('session-history-changed', self._session_history.index + 1)
        return True

    def OnHistoryGotoIndex(self, index, goto_uri):
        logging.debug("OnHistoryGotoIndex: %i %s" % (index, goto_uri.spec))
        self.emit('session-link-changed', goto_uri.spec)
        self.emit('session-history-changed', index)
        return True

    def OnHistoryNewEntry(self, new_uri):
        logging.debug("OnHistoryNewEntry: %s" % new_uri.spec)
        self.emit('session-link-changed', new_uri.spec)
        self.emit('session-history-changed', self._session_history.index + 1)

    def OnHistoryPurge(self, num_entries):
        logging.debug("OnHistoryPurge: %i" % num_entries)
        #self.emit('session-history-changed')
        return True

    def OnHistoryReload(self, reload_uri, reload_flags):
        self.emit('session-link-changed', reload_uri.spec)
        logging.debug("OnHistoryReload: %s" % reload_uri.spec)
        return True
