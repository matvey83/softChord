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
* Exception class indicating a Gears database-related error.
"""
class DatabaseException(GearsException):
    """*
    * Constructor taking a message.
    *
    * @param message error message for this exception
    """
    def __init__(self, message):
        super(message)
    
    
    """*
    * Constructor taking a message and root cause.
    *
    * @param message error message for this exception
    * @param cause the {@link Throwable} that caused this exception
    """
    def __init__(self, message, cause):
        super(message, cause)
    


