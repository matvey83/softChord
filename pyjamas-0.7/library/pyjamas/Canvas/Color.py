"""
* Copyright 2008 Google Inc.
*
* Licensed under the Apache License, Version 2.0 (the "License"); you may not
* use this file except in compliance with the License. You may obtain a copy of
* the License at
*
* http:#www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
* License for the specific language governing permissions and limitations under
* the License.
"""


"""*
* Simple Wrapper specifying a color in RGB format.
* Provides various methods for converting to String representations
* of the specified color for easy compatibility with various APIs
"""
class Color:
    
    """*
    * Create a using a valid CSSString.
    * We do not do any validation so be careful!
    """
    """*
    * Create a object with the specified RGB
    * values.
    *
    * @param r red value 0-255
    * @param g green value 0-255
    * @param b blue value 0-255
    """
    """*
    * Create a object with the specified RGBA
    * values.
    *
    * @param r red value 0-255
    * @param g green value 0-255
    * @param b blue value 0-255
    * @param a alpha channel value 0-1
    """
    def __init__(self, r, g=None, b=None, a=None):
        if g is None and b is None and a is None:
            self.colorStr = r
        elif a is None:
            self.colorStr = "rgb(%d,%d,%d)" % (r, g, b)
        else:
            self.colorStr = "rgba(%d,%d,%d,%d)" % (r, g, b, a)
    
    def __str__(self):
        return self.colorStr
    


"""
* Some basic color strings that are often used for the web.
* Compiler should optimize these out if they are not used.
"""
ALPHA_GREY = Color("rgba(0,0,0,0.3)")
ALPHA_RED = Color("rgba(255,0,0,0.3)")
BLACK = Color("#000000")
BLUE = Color("#318ce0")
BLUEVIOLET = Color("#8a2be2")
CYAN = Color("#5fa2e0")
GREEN = Color("#23ef24")
GREY = Color("#a9a9a9")
LIGHTGREY = Color("#eeeeee")
ORANGE = Color("#f88247")
PEACH = Color("#ffd393")
PINK = Color("#ff00ff")
RED = Color("#ff0000")
SKY_BLUE = Color("#c6defa")
WHITE = Color("#ffffff")
YELLOW = Color("yellow")
DARK_ORANGE = Color("#c44607")
BRIGHT_ORANGE = Color("#fb5c0c")
DARK_BLUE = Color("#0c6ac1")

