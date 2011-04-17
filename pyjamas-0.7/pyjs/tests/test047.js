    var x = 5;
    x += 1;
    while ((x > 0)) {
pyjslib_printFunc([ x ], 1 );
    x -= 1;
    }
    try {
pyjslib_printFunc([ 5 ], 1 );
    } catch(err) {
pyjslib_printFunc([ 2 ], 1 );
    }
    if ((__name__ == '__main__')) {
pyjslib_printFunc([ x ], 1 );
    }
pyjslib_printFunc([ 5 ], 1 );

        var __x = pyjslib_range(10).__iter__();
        try {
            while (true) {
                var x = __x.next();
                
        
pyjslib_printFunc([ x ], 1 );

            }
        } catch (e) {
            if (e != StopIteration) {
                throw e;
            }
        }
        
