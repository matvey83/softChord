# Copyright 2006 James Tauber and contributors
# Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    This module contains flags and integer values used by the event system.
"""

BUTTON_LEFT   = 1
BUTTON_MIDDLE = 4
BUTTON_RIGHT  = 2

ONBLUR        = 0x01000
ONCHANGE      = 0x00400
ONCLICK       = 0x00001
ONCONTEXTMENU = 0x20000
ONDBLCLICK    = 0x00002
ONERROR       = 0x10000
ONFOCUS       = 0x00800
ONKEYDOWN     = 0x00080
ONKEYPRESS    = 0x00100
ONKEYUP       = 0x00200
ONLOAD        = 0x08000
ONLOSECAPTURE = 0x02000
ONMOUSEDOWN   = 0x00004
ONMOUSEMOVE   = 0x00040
ONMOUSEOUT    = 0x00020
ONMOUSEOVER   = 0x00010
ONMOUSEUP     = 0x00008
ONSCROLL      = 0x04000

FOCUSEVENTS   = 0x01800 # ONFOCUS | ONBLUR
KEYEVENTS     = 0x00380 # ONKEYDOWN | ONKEYPRESS | ONKEYUP
MOUSEEVENTS   = 0x0007C # ONMOUSEDOWN | ONMOUSEUP | ONMOUSEMOVE | ONMOUSEOVER | ONMOUSEOUT


