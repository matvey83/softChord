"""
* Copyright 2007 Fred Sauer
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



from pyjamas import Command
from pyjamas import DeferredCommand

"""*
* Used by {@link MouseDragHandler} to improve drag performance on slower
* platforms.
"""
class DeferredMoveCommand implements Command:
    int PERFORMANCE_THRESHOLD_MILLIS = 80
    
    long mostRecentTotalTime
    MouseDragHandler mouseDragHandler
    long scheduledTimeMillis
    int x
    int y
    
    def __init__(self, mouseDragHandler):
        self.mouseDragHandler = mouseDragHandler
    
    
    def execute(self):
        if scheduledTimeMillis == 0:
            return
        
        mouseDragHandler.actualMove(x, y)
        mostRecentTotalTime = System.currentTimeMillis() - scheduledTimeMillis
        scheduledTimeMillis = 0
    
    
    """*
    * Either execute {@link MouseDragHandler#actualMove(int, int)} immediately or
    * schedule via {@link DeferredCommand#add(Command)}. This is done as a
    * work-around for slow otherwise slow performance on Firefox/Linux
    * (discovered on Ubuntu). The decision is made as follows:
    * <ul>
    * <li>In Hosted Mode, always execute immediately.</li>
    * <li>In Web Mode execute immediately, unless most recent processing time
    * exceeded {@link #PERFORMANCE_THRESHOLD_MILLIS} ({@value #PERFORMANCE_THRESHOLD_MILLIS}
    * milliseconds).</li>
    * </ul>
    *
    * @param x the left mouse move position
    * @param y the top mouse move position
    """
    def scheduleOrExecute(self, x, y):
        self.x = x
        self.y = y
        if scheduledTimeMillis == 0:
            scheduledTimeMillis = System.currentTimeMillis()
        
        # Select method to perform move:
        #
        # Hosted Mode:
        # execute immediately
        # Web Mode
        if GWT.isScript()  and  mostRecentTotalTime > PERFORMANCE_THRESHOLD_MILLIS:
            DeferredCommand.addCommand(this)
         else:
            execute()
        
    


