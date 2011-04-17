"""
* Copyright 2008 Google Inc.
*
* Licensed under the Apache License, Version 2.0 (the "License"); you may not
* use self file except in compliance with the License. You may obtain a copy of
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




class JSOStack:
    
    def __init__(self):
        self.clear()

    def clear(self):
        self.scratch = []
        self._minX = None
        self._minY = None
        self._maxX = None
        self._maxY = None

    def getMaxCoordX(self):
        return self._maxX

    def getMaxCoordY(self):
        return self._maxY

    def getMinCoordX(self):
        return self._minX

    def getMinCoordY(self):
        return self._minY

    def join(self):
        return "".join(self.scratch)

    def logCoordX(self, coordX):
        if self._minX is None :
            self._minX = coordX
            self._maxX = coordX
        else:
            if (self._minX > coordX):
                self._minX = coordX
            else:
                if (self._maxX < coordX):
                    self._maxX = coordX

    def logCoordY(self,coordY):
        if self._minY is None :
            self._minY = coordY
            self._maxY = coordY
        else:
            if (self._minY > coordY):
                self._minY = coordY
            else:
                if (self._maxY < coordY):
                    self._maxY = coordY

    def pop(self):
        return self.scratch.pop()

    def append(self, pathStr):
        self.scratch.append(pathStr)

    def __len__(self):
        return len(self.scratch)


