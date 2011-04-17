# Copyright 2006 James Tauber and contributors
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

# iteration from Bob Ippolito's Iteration in JavaScript

# must declare import _before_ importing sys

from __pyjamas__ import INT, JS, setCompilerOptions, debugger

setCompilerOptions("noDebug", "noBoundMethods", "noDescriptors", "noAttributeChecking", "noSourceTracking", "noLineTracking", "noStoreSource")

platform = JS("$pyjs.platform")
sys = None
dynamic = None
JS("""
var $max_float_int = 1;
for (var i = 0; i < 1000; i++) {
    $max_float_int *= 2;
    if ($max_float_int + 1 == $max_float_int) {
        break;
    }
}
$max_int = 0x7fffffff;
$min_int = -0x80000000;
""")

class object:
    pass

def op_is(a,b):
    JS("""
    if (a === b) return true;
    if (a !== null && b !== null) {
        switch ((a.__number__ << 8) | b.__number__) {
            case 0x0101:
                return a == b;
            case 0x0202:
                return a.__v == b.__v;
            case 0x0404:
                return a.__cmp__(b) == 0;
        }
    }
    return false;
""")

def op_eq(a,b):
    # All 'python' classes and types are implemented as objects/functions.
    # So, for speed, do a typeof X / X.__cmp__  on a/b.
    # Checking for the existance of .__cmp__ is expensive when it doesn't exist
    #setCompilerOptions("InlineEq")
    #return a == b
    JS("""
    if (a === null) {
        if (b === null) return true;
        return false;
    }
    if (b === null) {
        return false;
    }
    switch ((a.__number__ << 8) | b.__number__) {
        case 0x0101:
        case 0x0401:
            return a == b;
        case 0x0102:
            return a == b.__v;
        case 0x0201:
            return a.__v == b;
        case 0x0202:
            return a.__v == b.__v;
        case 0x0104:
        case 0x0204:
            a = new pyjslib['long'](a.valueOf());
        case 0x0404:
            return a.__cmp__(b) == 0;
        case 0x0402:
            return a.__cmp__(new pyjslib['long'](b.valueOf())) == 0;
    }
    if ((typeof a == 'object' || typeof a == 'function') && typeof a.__cmp__ == 'function') {
        if (typeof b.__cmp__ != 'function') {
            return false;
        }
        if (a.__cmp__ === b.__cmp__) {
            return a.__cmp__(b) == 0;
        }
        if (pyjslib['_isinstance'](a, b)) {
            return a.__cmp__(b) == 0;
        }
        return false;
    } else if ((typeof b == 'object' || typeof b == 'function') && typeof b.__cmp__ == 'function') {
        // typeof b.__cmp__ != 'function'
        // a.__cmp__ !== b.__cmp__
        if (pyjslib['_isinstance'](a, b)) {
            return b.__cmp__(a) == 0;
        }
        return false;
    }
    return a == b;
    """)

def op_uadd(v):
    JS("""
    switch (v.__number__) {
        case 0x01:
        case 0x02:
        case 0x04:
            return v;
    }
    if (v !== null) {
        if (typeof v['__pos__'] == 'function') return v.__pos__();
    }
""")
    raise TypeError("bad operand type for unary +: '%r'" % v)

def op_usub(v):
    JS("""
    switch (v.__number__) {
        case 0x01:
            return -v;
        case 0x02:
            return new pyjslib['int'](-v);
    }
    if (v !== null) {
        if (typeof v['__neg__'] == 'function') return v.__neg__();
    }
""")
    raise TypeError("bad operand type for unary -: '%r'" % v)

def op_add(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                return x + y;
            case 0x0102:
                return x + y.__v;
            case 0x0201:
                return x.__v + y;
            case 0x0202:
                return new pyjslib['int'](x.__v + y.__v);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__add(y);
            case 0x0402:
                return x.__add(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__add(y);
        }
        if (!x.__number__) {
            if (typeof x == 'string' && typeof y == 'string') return x + y;
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__add__'] == 'function')
                return y.__add__(x);
            if (typeof x['__add__'] == 'function') return x.__add__(y);
        }
        if (!y.__number__ && typeof y['__radd__'] == 'function') return y.__radd__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for +: '%r', '%r'" % (x, y))

def op_sub(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                return x - y;
            case 0x0102:
                return x - y.__v;
            case 0x0201:
                return x.__v - y;
            case 0x0202:
                return new pyjslib['int'](x.__v - y.__v);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__sub(y);
            case 0x0402:
                return x.__sub(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__sub(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__sub__'] == 'function')
                return y.__sub__(x);
            if (typeof x['__sub__'] == 'function') return x.__sub__(y);
        }
        if (!y.__number__ && typeof y['__rsub__'] == 'function') return y.__rsub__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for -: '%r', '%r'" % (x, y))

def op_floordiv(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.floor(x / y);
            case 0x0102:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.floor(x / y.__v);
            case 0x0201:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.floor(x.__v / y);
            case 0x0202:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
                return new pyjslib['int'](Math.floor(x.__v / y.__v));
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__floordiv(y);
            case 0x0402:
                return x.__floordiv(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__floordiv(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__floordiv__'] == 'function')
                return y.__floordiv__(x);
            if (typeof x['__floordiv__'] == 'function') return x.__floordiv__(y);
        }
        if (!y.__number__ && typeof y['__rfloordiv__'] == 'function') return y.__rfloordiv__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for //: '%r', '%r'" % (x, y))

def op_div(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x / y;
            case 0x0102:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x / y.__v;
            case 0x0201:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x.__v / y;
            case 0x0202:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return new pyjslib['int'](x.__v / y.__v);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__div(y);
            case 0x0402:
                return x.__div(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__div(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__div__'] == 'function')
                return y.__div__(x);
            if (typeof x['__div__'] == 'function') return x.__div__(y);
        }
        if (!y.__number__ && typeof y['__rdiv__'] == 'function') return y.__rdiv__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for /: '%r', '%r'" % (x, y))

def op_mul(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                return x * y;
            case 0x0102:
                return x * y.__v;
            case 0x0201:
                return x.__v * y;
            case 0x0202:
                return new pyjslib['int'](x.__v * y.__v);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__mul(y);
            case 0x0402:
                return x.__mul(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__mul(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__mul__'] == 'function')
                return y.__mul__(x);
            if (typeof x['__mul__'] == 'function') return x.__mul__(y);
        }
        if (!y.__number__ && typeof y['__rmul__'] == 'function') return y.__rmul__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for *: '%r', '%r'" % (x, y))

def op_mod(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x % y;
            case 0x0102:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x % y.__v;
            case 0x0201:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return x.__v % y;
            case 0x0202:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
                return new pyjslib['int'](x.__v % y.__v);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__mod(y);
            case 0x0402:
                return x.__mod(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__mod(y);
        }
        if (typeof x == 'string') {
            return pyjslib.sprintf(x, y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__mod__'] == 'function')
                return y.__mod__(x);
            if (typeof x['__mod__'] == 'function') return x.__mod__(y);
        }
        if (!y.__number__ && typeof y['__rmod__'] == 'function') return y.__rmod__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for %: '%r', '%r'" % (x, y))

def op_pow(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.pow(x, y);
            case 0x0102:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.pow(x,y.__v);
            case 0x0201:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                return Math.pow(x.__v,y);
            case 0x0202:
                return x.__pow__(y);
            case 0x0204:
                return (new pyjslib['long'](x.__v)).__pow(y);
            case 0x0402:
                return x.__pow(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__pow(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__pow__'] == 'function')
                return y.__pow__(x);
            if (typeof x['__pow__'] == 'function') return x.__pow__(y);
        }
        if (!y.__number__ && typeof y['__rpow__'] == 'function') return y.__rpow__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for %: '%r', '%r'" % (x, y))

def op_invert(v):
    JS("""
    if (v !== null) {
        if (typeof v['__invert__'] == 'function') return v.__invert__();
    }
""")
    raise TypeError("bad operand type for unary -: '%r'" % v)

def op_bitshiftleft(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0202:
                return x.__lshift__(y);
            case 0x0204:
                return y.__rlshift__(x);
            case 0x0402:
                return x.__lshift(y.__v);
            case 0x0404:
                return x.__lshift(y.valueOf());
        }
        if (typeof x['__lshift__'] == 'function') {
            var v = x.__lshift__(y);
            if (v !== pyjslib['NotImplemented']) return v;
        }
        if (typeof y['__rlshift__'] != 'undefined') return y.__rlshift__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for <<: '%r', '%r'" % (x, y))

def op_bitshiftright(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0202:
                return x.__rshift__(y);
            case 0x0204:
                return y.__rrshift__(x);
            case 0x0402:
                return x.__rshift(y.__v);
            case 0x0404:
                return x.__rshift(y.valueOf());
        }
        if (typeof x['__rshift__'] == 'function') {
            var v = x.__rshift__(y);
            if (v !== pyjslib['NotImplemented']) return v;
        }
        if (typeof y['__rrshift__'] != 'undefined') return y.__rrshift__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for >>: '%r', '%r'" % (x, y))

def op_bitand2(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0202:
                return x.__and__(y);
            case 0x0204:
                return y.__and(new pyjslib['long'](x));
            case 0x0402:
                return x.__and(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__and(y);
        }
        if (typeof x['__and__'] == 'function') {
            var v = x.__and__(y);
            if (v !== pyjslib['NotImplemented']) return v;
        }
        if (typeof y['__rand__'] != 'undefined') return y.__rand__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for &: '%r', '%r'" % (x, y))

op_bitand = JS("""function (args) {
    var a;
    if (args[0] !== null && args[1] !== null && args.length > 1) {
        var res, r;
        res = args[0];
        for (i = 1; i < args.length; i++) {
            if (typeof res['__and__'] == 'function') {
                r = res;
                res = res.__and__(args[i]);
                if (res === pyjslib['NotImplemented'] && typeof args[i]['__rand__'] == 'function') {
                    res = args[i].__rand__(r);
                }
            } else if (typeof args[i]['__rand__'] == 'function') {
                res = args[i].__rand__(res);
            } else {
                res = null;
                break;
            }
            if (res === pyjslib['NotImplemented']) {
                res = null;
                break;
            }
        }
        if (res !== null) {
            return res;
        }
    }
""")
raise TypeError("unsupported operand type(s) for &: " + ', '.join([repr(a) for a in list(args)]))
JS("""
};
""")

def op_bitxor2(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0202:
                return x.__xor__(y);
            case 0x0204:
                return y.__xor(new pyjslib['long'](x));
            case 0x0402:
                return x.__xor(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__xor(y);
        }
        if (typeof x['__xor__'] == 'function') {
            var v = x.__xor__(y);
            if (v !== pyjslib['NotImplemented']) return v;
        }
        if (typeof y['__rxor__'] != 'undefined') return y.__rxor__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for &: '%r', '%r'" % (x, y))

op_bitxor = JS("""function (args) {
    var a;
    if (args[0] !== null && args[1] !== null && args.length > 1) {
        var res, r;
        res = args[0];
        for (i = 1; i < args.length; i++) {
            if (typeof res['__xor__'] == 'function') {
                r = res;
                res = res.__xor__(args[i]);
                if (res === pyjslib['NotImplemented'] && typeof args[i]['__rxor__'] == 'function') {
                    res = args[i].__rxor__(r);
                }
            } else if (typeof args[i]['__rxor__'] == 'function') {
                res = args[i].__rxor__(res);
            } else {
                res = null;
                break;
            }
            if (res === pyjslib['NotImplemented']) {
                res = null;
                break;
            }
        }
        if (res !== null) {
            return res;
        }
    }
""")
raise TypeError("unsupported operand type(s) for ^: " + ', '.join([repr(a) for a in args]))
JS("""
};
""")

def op_bitor2(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0202:
                return x.__or__(y);
            case 0x0204:
                return y.__or(new pyjslib['long'](x));
            case 0x0402:
                return x.__or(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__or(y);
        }
        if (typeof x['__or__'] == 'function') {
            var v = x.__or__(y);
            if (v !== pyjslib['NotImplemented']) return v;
        }
        if (typeof y['__ror__'] != 'undefined') return y.__ror__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for &: '%r', '%r'" % (x, y))

op_bitor = JS("""function (args) {
    var a;
    if (args[0] !== null && args[1] !== null && args.length > 1) {
        var res, r;
        res = args[0];
        for (i = 1; i < args.length; i++) {
            if (typeof res['__or__'] == 'function') {
                r = res;
                res = res.__or__(args[i]);
                if (res === pyjslib['NotImplemented'] && typeof args[i]['__ror__'] == 'function') {
                    res = args[i].__ror__(r);
                }
            } else if (typeof args[i]['__ror__'] == 'function') {
                res = args[i].__ror__(res);
            } else {
                res = null;
                break;
            }
            if (res === pyjslib['NotImplemented']) {
                res = null;
                break;
            }
        }
        if (res !== null) {
            return res;
        }
    }
""")
raise TypeError("unsupported operand type(s) for |: " + ', '.join([repr(a) for a in args]))
JS("""
};
""")


# All modules (do and should) take care of checking their parent:
#   - If the parent is not loaded and initialized, call ___import___(parent, null)
# All modules are placed in sys.modules dict
# The module is first tried within the context
# If the depth > 1 (i.e. one or more dots in the path) then:
#     Try the parent if it has an object that resolves to [context.]path
# If the module doesn't exist and dynamic loading is enabled, try dynamic loading
def ___import___(path, context, module_name=None, get_base=True):
    save_track_module = JS("$pyjs.track.module")
    sys = JS("$pyjs.loaded_modules['sys']")
    if JS("sys.__was_initialized__ != true"):
        module = JS("$pyjs.loaded_modules[path]")
        module()
        JS("$pyjs.track.module = save_track_module;")
        if path == 'sys':
            module.modules = dict({'pyjslib': pyjslib, 'sys': module})
        return module
    importName = path
    is_module_object = False
    path_parts = path.__split('.') # make a javascript Array
    depth = path_parts.length
    topName = JS("path_parts[0]")
    objName = JS("path_parts[path_parts.length-1]")
    parentName = path_parts.slice(0, path_parts.length-1).join('.')
    if context is None:
        in_context = False
    else:
        in_context = True
        inContextImportName = context + '.' + importName
        if not parentName:
            inContextParentName = context
        else:
            inContextParentName = context + '.' + parentName
        inContextTopName = context + '.' + topName
        contextTopName = JS("context.__split('.')[0]")

        # Check if we already have imported this module in this context
        if depth > 1 and sys.modules.has_key(inContextParentName):
            module = sys.modules[inContextParentName]
            if JS("typeof module[objName] != 'undefined'"):
                if get_base:
                    return JS("$pyjs.loaded_modules[inContextTopName]")
                return JS("module[objName]")
        elif sys.modules.has_key(inContextImportName):
            if get_base:
                return JS("$pyjs.loaded_modules[inContextTopName]")
            return sys.modules[inContextImportName]
        elif depth > 1 and JS("typeof (module = $pyjs.loaded_modules[inContextParentName]) != 'undefined'"):
            sys.modules[inContextParentName] = module
            JS("module.__was_initialized__ = false;")
            module(None)
            JS("$pyjs.track.module = save_track_module;")
            if JS("typeof module[objName] != 'undefined'"):
                if get_base:
                    return JS("$pyjs.loaded_modules[inContextTopName]")
                return JS("module[objName]")
        if sys.modules.has_key(inContextImportName):
            if get_base:
                return JS("$pyjs.loaded_modules[inContextTopName]")
            return sys.modules[inContextImportName]
        if JS("typeof (module = $pyjs.loaded_modules[inContextImportName]) != 'undefined'"):
            sys.modules[inContextImportName] = module
            JS("module.__was_initialized__ = false;")
            module(module_name)
            JS("$pyjs.track.module = save_track_module;")
            if get_base:
                return JS("$pyjs.loaded_modules[inContextTopName]")
            return module
        # Check if the topName is a valid module, if so, we stay in_context
        if not sys.modules.has_key(inContextTopName):
            if JS("typeof (module = $pyjs.loaded_modules[inContextTopName]) != 'function'"):
                in_context = False
                if JS("$pyjs.options.dynamic_loading"):
                    module = __dynamic_load__(inContextTopName)
                    if JS("""typeof module == 'function'"""):
                        in_context = True
                        if depth == 1:
                            module(module_name)
                            JS("$pyjs.track.module = save_track_module;")
                            return module
                        else:
                            module(None)
                            if depth == 2 and JS("typeof module[objName] != 'undefined'"):
                                if get_base:
                                    return JS("$pyjs.loaded_modules[inContextTopName]")
                                return JS("module[objName]")
        if in_context:
            importName = inContextImportName
            parentName = inContextParentName
            topName = inContextTopName
    if not in_context:
        if parentName and sys.modules.has_key(parentName):
            module = sys.modules[parentName]
            if JS("typeof module[objName] != 'undefined'"):
                if get_base:
                    return JS("$pyjs.loaded_modules[topName]")
                return JS("module[objName]")
        elif sys.modules.has_key(importName):
            if get_base:
                return JS("$pyjs.loaded_modules[topName]")
            return sys.modules[importName]
        elif parentName and JS("typeof (module = $pyjs.loaded_modules[parentName]) != 'undefined'"):
            sys.modules[parentName] = module
            JS("module.__was_initialized__ = false;")
            module(None)
            JS("$pyjs.track.module = save_track_module;")
            if JS("typeof module[objName] != 'undefined'"):
                if get_base:
                    return JS("$pyjs.loaded_modules[topName]")
                return JS("module[objName]")
        if sys.modules.has_key(importName):
            if get_base:
                return JS("$pyjs.loaded_modules[topName]")
            return sys.modules[importName]
        if JS("typeof (module = $pyjs.loaded_modules[importName]) != 'undefined'"):
            sys.modules[importName] = module
            if importName != 'pyjslib' and importName != 'sys':
                JS("module.__was_initialized__ = false;")
            module(module_name)
            JS("$pyjs.track.module = save_track_module;")
            if get_base:
                return JS("$pyjs.loaded_modules[topName]")
            return module

    # If we are here, the module is not loaded (yet).
    if JS("$pyjs.options.dynamic_loading"):
        module = __dynamic_load__(importName)
        if JS("""typeof module == 'function'"""):
            module(module_name)
            JS("$pyjs.track.module = save_track_module;")
            if get_base:
                return JS("$pyjs.loaded_modules[topName]")
            return module

    raise ImportError(
        "No module named %s, %s in context %s" % (importName, path, context))

def __dynamic_load__(importName):
    global __nondynamic_modules__
    setCompilerOptions("noDebug")
    module = JS("""$pyjs.loaded_modules[importName]""")
    if sys is None or dynamic is None or __nondynamic_modules__.has_key(importName):
        return module
    if JS("""typeof module == 'undefined'"""):
        try:
            dynamic.ajax_import("lib/" + importName + ".__" + platform + "__.js")
            module = JS("""$pyjs.loaded_modules[importName]""")
        except:
            pass
    if JS("""typeof module == 'undefined'"""):
        try:
            dynamic.ajax_import("lib/" + importName + ".js")
            module = JS("""$pyjs.loaded_modules[importName]""")
        except:
            pass
        if JS("""typeof module == 'undefined'"""):
            __nondynamic_modules__[importName] = 1.0
    return module

class BaseException:

    def __init__(self, *args):
        self.args = args

    def __getitem__(self, index):
        return self.args.__getitem__(index)

    def toString(self):
        return self.__str__()

    def __str__(self):
        if len(self.args) is 0:
            return ''
        elif len(self.args) is 1:
            return str(self.args[0])
        return repr(self.args)

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        return self.__name__ + repr(self.args)

class Exception(BaseException):
    pass

class StandardError(Exception):
    pass

class AssertionError(Exception):
    pass

class GeneratorExit(Exception):
    pass

class TypeError(StandardError):
    pass

class AttributeError(StandardError):
    pass

class NameError(StandardError):
    pass

class ValueError(StandardError):
    pass

class ImportError(StandardError):
    pass

class LookupError(StandardError):
    pass

class RuntimeError(StandardError):
    pass

class ArithmeticError(StandardError):
    pass

class KeyError(LookupError):

    def __str__(self):
        if len(self.args) is 0:
            return ''
        elif len(self.args) is 1:
            return repr(self.args[0])
        return repr(self.args)

class IndexError(LookupError):
    pass

class NotImplementedError(RuntimeError):
    pass

class ZeroDivisionError(ArithmeticError):
    pass

class OverflowError(ArithmeticError):
    pass

class UndefinedValueError(ValueError):
    pass

def init():

    # There seems to be an bug in Chrome with accessing the message
    # property, on which an error is thrown
    # Hence the declaration of 'var message' and the wrapping in try..catch
    JS("""
pyjslib._errorMapping = function(err) {
    if (err instanceof(ReferenceError) || err instanceof(TypeError)) {
        var message = '';
        try {
            message = err.message;
        } catch ( e) {
        }
        return pyjslib.AttributeError(message);
    }
    return err;
};
""")
    # The TryElse 'error' is used to implement the else in try-except-else
    # (to raise an exception when there wasn't any)
    JS("""
pyjslib.TryElse = function () { };
pyjslib.TryElse.prototype = new Error();
pyjslib.TryElse.__name__ = 'TryElse';
""")
    # StopIteration is used to get out of an iteration loop
    JS("""
pyjslib.StopIteration = function () { };
pyjslib.StopIteration.prototype = new Error();
pyjslib.StopIteration.__name__ = 'StopIteration';
""")

    # Patching of the standard javascript String object
    JS("""
String.prototype.rfind = function(sub, start, end) {
    var pos;
    if (typeof start != 'undefined') {
        /* *sigh* - python rfind goes *RIGHT*, NOT left */
        pos = this.substring(start).lastIndexOf(sub);
        if (pos == -1) {
            return -1;
        }
        pos += start;
    }
    else {
        pos=this.lastIndexOf(sub, start);
    }
    if (typeof end == 'undefined') return pos;

    if (pos + sub.length>end) return -1;
    return pos;
};

String.prototype.find = function(sub, start, end) {
    var pos=this.indexOf(sub, start);
    if (typeof end == 'undefined') return pos;

    if (pos + sub.length>end) return -1;
    return pos;
};

String.prototype.join = function(data) {
    var text="";

    if (data.constructor === Array) {
        return data.join(this);
    } else if (typeof data.__iter__ == 'function') {
        if (typeof data.__array == 'object') {
            return data.__array.join(this);
        }
        var iter=data.__iter__();
        if (typeof iter.__array == 'object') {
            return iter.__array.join(this);
        }
        data = [];
        var item, i = 0;
        if (typeof iter.$genfunc == 'function') {
            while (typeof (item=iter.next(true)) != 'undefined') {
                data[i++] = item;
            }
        } else {
            try {
                while (true) {
                    data[i++] = iter.next();
                }
            }
            catch (e) {
                if (e.__name__ != 'StopIteration') throw e;
            }
        }
        return data.join(this);
    }

    return text;
};

String.prototype.isdigit = function() {
    return (this.match(/^\d+$/g) !== null);
};

String.prototype.isalpha = function() {
    return (this.match(/^[a-zA-Z]+$/g) !== null);
};

String.prototype.isupper = function() {
    return (this.match(/^[A-Z]+$/g) !== null);
};

String.prototype.__replace=String.prototype.replace;

String.prototype.$$replace = function(old, replace, count) {
    var do_max=false;
    var start=0;
    var new_str="";
    var pos=0;

    if (typeof old != 'string') return this.__replace(old, replace);
    if (typeof count != 'undefined') do_max=true;

    while (start<this.length) {
        if (do_max && !count--) break;

        pos=this.indexOf(old, start);
        if (pos<0) break;

        new_str+=this.substring(start, pos) + replace;
        start=pos+old.length;
    }
    if (start<this.length) new_str+=this.substring(start);

    return new_str;
};

String.prototype.__contains__ = function(s){
    return this.indexOf(s)>=0;
};

String.prototype.__split = String.prototype.split;

String.prototype.$$split = function(sep, maxsplit) {
    var items=pyjslib.list();
    var do_max=false;
    var subject=this;
    var start=0;
    var pos=0;

    if (sep === null || typeof sep == 'undefined') {
        sep=" ";
        if (subject.length == 0) {
            return items;
        }
        subject=subject.strip();
        subject=subject.$$replace(/\s+/g, sep);
    }
    else if (typeof maxsplit != 'undefined') do_max=true;

    if (subject.length == 0) {
        items.__array.push('');
        return items;
    }

    while (start<subject.length) {
        if (do_max && !maxsplit--) break;

        pos=subject.indexOf(sep, start);
        if (pos<0) break;

        items.__array.push(subject.substring(start, pos));
        start=pos+sep.length;
    }
    if (start<=subject.length) items.__array.push(subject.substring(start));

    return items;
};

if (typeof "a"[0] == 'undefined' ) {
    // IE: cannot do "abc"[idx]
    String.prototype.__iter__ = function() {
        var i = 0;
        var s = this;
        return {
            'next': function(noStop) {
                if (i >= s.length) {
                    if (noStop === true) {
                        return;
                    }
                    throw pyjslib.StopIteration;
                }
                return s.charAt(i++);
            },
            '__iter__': function() {
                return this;
            }
        };
    };
} else {
    String.prototype.__iter__ = function() {
        var i = 0;
        var s = this;
        return {
            '__array': this,
            'next': function(noStop) {
                if (i >= s.length) {
                    if (noStop === true) {
                        return;
                    }
                    throw pyjslib.StopIteration;
                }
                return s.charAt(i++);
            },
            '__iter__': function() {
                return this;
            }
        };
    };
}

String.prototype.strip = function(chars) {
    return this.lstrip(chars).rstrip(chars);
};

String.prototype.lstrip = function(chars) {
    if (typeof chars == 'undefined') return this.$$replace(/^\s+/, "");
    if (chars.length == 0) return this;
    return this.$$replace(new RegExp("^[" + chars + "]+"), "");
};

String.prototype.rstrip = function(chars) {
    if (typeof chars == 'undefined') return this.$$replace(/\s+$/, "");
    if (chars.length == 0) return this;
    return this.$$replace(new RegExp("[" + chars + "]+$"), "");
};

String.prototype.startswith = function(prefix, start, end) {
    // FIXME: accept tuples as suffix (since 2.5)
    if (typeof start == 'undefined') start = 0;
    if (typeof end == 'undefined') end = this.length;

    if ((end - start) < prefix.length) return false;
    if (this.substr(start, prefix.length) == prefix) return true;
    return false;
};

String.prototype.endswith = function(suffix, start, end) {
    // FIXME: accept tuples as suffix (since 2.5)
    if (typeof start == 'undefined') start = 0;
    if (typeof end == 'undefined') end = this.length;

    if ((end - start) < suffix.length) return false;
    if (this.substr(end - suffix.length, suffix.length) == suffix) return true;
    return false;
};

String.prototype.ljust = function(width, fillchar) {
    switch (width.__number__) {
        case 0x02:
        case 0x04:
            width = width.valueOf();
            break;
        case 0x01:
            if (Math.floor(width) == width) break;
        default:
            throw pyjslib.TypeError("an integer is required (got '" + width + "')");
    }
    if (typeof fillchar == 'undefined') fillchar = ' ';
    if (typeof(fillchar) != 'string' ||
        fillchar.length != 1) {
        throw pyjslib.TypeError("ljust() argument 2 must be char, not " + typeof(fillchar));
    }
    if (this.length >= width) return this;
    return this + new Array(width+1 - this.length).join(fillchar);
};

String.prototype.rjust = function(width, fillchar) {
    switch (width.__number__) {
        case 0x02:
        case 0x04:
            width = width.valueOf();
            break;
        case 0x01:
            if (Math.floor(width) == width) break;
        default:
            throw pyjslib.TypeError("an integer is required (got '" + width + "')");
    }
    if (typeof fillchar == 'undefined') fillchar = ' ';
    if (typeof(fillchar) != 'string' ||
        fillchar.length != 1) {
        throw pyjslib.TypeError("rjust() argument 2 must be char, not " + typeof(fillchar));
    }
    if (this.length >= width) return this;
    return new Array(width + 1 - this.length).join(fillchar) + this;
};

String.prototype.center = function(width, fillchar) {
    switch (width.__number__) {
        case 0x02:
        case 0x04:
            width = width.valueOf();
            break;
        case 0x01:
            if (Math.floor(width) == width) break;
        default:
            throw pyjslib.TypeError("an integer is required (got '" + width + "')");
    }
    if (typeof fillchar == 'undefined') fillchar = ' ';
    if (typeof(fillchar) != 'string' ||
        fillchar.length != 1) {
        throw pyjslib.TypeError("center() argument 2 must be char, not " + typeof(fillchar));
    }
    if (this.length >= width) return this;
    padlen = width - this.length;
    right = Math.ceil(padlen / 2);
    left = padlen - right;
    return new Array(left+1).join(fillchar) + this + new Array(right+1).join(fillchar);
};

String.prototype.__getslice__ = function(lower, upper) {
    if (lower === null) {
        lower = 0;
    } else if (lower < 0) {
        lower = this.length + lower;
    }
    if (upper === null) {
        upper=this.length;
    } else if (upper < 0) {
       upper = this.length + upper;
    }
    return this.substring(lower, upper);
};

String.prototype.__getitem__ = function(idx) {
    if (idx < 0) idx += this.length;
    if (idx < 0 || idx > this.length) {
        throw pyjslib.IndexError("string index out of range");
    }
    return this.charAt(idx);
};

String.prototype.__setitem__ = function(idx, val) {
    throw pyjslib.TypeError("'str' object does not support item assignment");
};

String.prototype.upper = String.prototype.toUpperCase;
String.prototype.lower = String.prototype.toLowerCase;

String.prototype.zfill = function(width) {
    return this.rjust(width, '0');
};

String.prototype.__add__ = function(y) {
    if (typeof y != "string") {
        throw pyjslib.TypeError("cannot concatenate 'str' and non-str objects");
    }
    return this + y;
};

String.prototype.__mul__ = function(y) {
    switch (y.__number__) {
        case 0x02:
        case 0x04:
            y = y.valueOf();
            break;
        case 0x01:
            if (Math.floor(y) == y) break;
        default:
            throw pyjslib.TypeError("can't multiply sequence by non-int of type 'str'");
    }
    var s = '';
    while (y-- > 0) {
        s += this;
    }
    return s;
};
String.prototype.__rmul__ = String.prototype.__mul__;
String.prototype.__number__ = null;
String.prototype.__name__ = 'str';
String.prototype.__class__ = String.prototype;
String.prototype.__is_instance__ = null;
String.prototype.__str__ = function () {
    if (typeof this == 'string') return this.toString();
    return "<type 'str'>";
};
String.prototype.__repr__ = function () {
    if (typeof this == 'string') return "'" + this.toString() + "'";
    return "<type 'str'>";
};

""")

    # Patching of the standard javascript Boolean object
    JS("""
Boolean.prototype.__number__ = 0x01;
Boolean.prototype.__name__ = 'bool';
Boolean.prototype.__class__ = Boolean.prototype;
Boolean.prototype.__is_instance__ = null;
Boolean.prototype.__str__= function () {
    if (typeof this == 'string') {
     	if (this === true) return "True";
    	return "False";
    }
    return "<type 'bool'>";
};
Boolean.prototype.__repr__ = Boolean.prototype.__str__;
Boolean.prototype.__and__ = function (y) {
    return this & y.valueOf();
}
Boolean.prototype.__or__ = function (y) {
    return this | y.valueOf();
}
Boolean.prototype.__xor__ = function (y) {
    return this ^ y.valueOf();
}

""")

    # Patching of the standard javascript Array object
    # This makes it imposible to use for (k in Array())
    JS("""
if (typeof Array.prototype.indexOf != 'function') {
    Array.prototype.indexOf = function(elt /*, from*/) {
        var len = this.length >>> 0;

        var from = Number(arguments[1]) || 0;
        from = (from < 0)
                ? Math.ceil(from)
                : Math.floor(from);
        if (from < 0)
            from += len;

        for (; from < len; from++) {
            if (from in this &&
                this[from] === elt)
                return from;
        }
        return -1;
    };
};
""")

    # Patching of the standard javascript RegExp
    JS("""
RegExp.prototype.Exec = RegExp.prototype.exec;
""")
    JS("""
pyjslib.abs = Math.abs;
""")

class Class:
    def __init__(self, name):
        self.name = name

    def __str___(self):
        return self.name

def open(fname, mode='r'):
    raise NotImplementedError("open is not implemented in browsers")

def cmp(a,b):
    JS("""
    if (typeof a == typeof b) {
        switch (typeof a) {
            case 'number':
            case 'string':
            case 'boolean':
                return a == b ? 0 : (a < b ? -1 : 1);
        }
        if (a === b) return 0;
    }
    if (a === null) {
        if (b === null) return 0;
        return -1;
    }
    if (b === null) {
        return 1;
    }

    switch ((a.__number__ << 8)|b.__number__) {
        case 0x0202:
            a = a.__v;
            b = b.__v;
        case 0x0101:
            return a == b ? 0 : (a < b ? -1 : 1);
        case 0x0100:
        case 0x0200:
        case 0x0400:
            if (typeof b.__cmp__ == 'function') {
                return -b.__cmp__(a);
            }
            return -1;
        case 0x0001:
        case 0x0002:
        case 0x0004:
            if (typeof a.__cmp__ == 'function') {
                return a.__cmp__(b);
            }
            return 1;
        case 0x0102:
            return -b.__cmp__(new pyjslib['int'](a));
        case 0x0104:
            return -b.__cmp__(new pyjslib['long'](a));
        case 0x0201:
            return a.__cmp__(new pyjslib['int'](b));
        case 0x0401:
            return a.__cmp__(new pyjslib['long'](b));
        case 0x0204:
            return -b.__cmp__(new pyjslib['long'](a));
        case 0x0402:
            return a.__cmp__(new pyjslib['long'](b));
        case 0x0404:
            return a.__cmp__(b);
    }

    if (typeof a.__class__ == typeof b.__class__ && typeof a.__class__ == 'function') {
        if (a.__class__.__name__ < b.__class__.__name__) {
            return -1;
        }
        if (a.__class__.__name__ > b.__class__.__name__) {
            return 1;
        }
    }

    if ((typeof a == 'object' || typeof a == 'function') && typeof a.__cmp__ == 'function') {
        return a.__cmp__(b);
    } else if ((typeof b == 'object' || typeof b == 'function') && typeof b.__cmp__ == 'function') {
        return -b.__cmp__(a);
    }
    if (a == b) return 0;
    if (a > b) return 1;
    return -1;
    """)

# for list.sort()
__cmp = cmp

def bool(v):
    # this needs to stay in native code without any dependencies here,
    # because this is used by if and while, we need to prevent
    # recursion
    #setCompilerOptions("InlineBool")
    #if v:
    #    return True
    #return False
    JS("""
    switch (v) {
        case null:
        case false:
        case 0:
        case '':
            return false;
    }
    if (typeof v == 'object') {
        if (typeof v.__nonzero__ == 'function'){
            return v.__nonzero__();
        } else if (typeof v.__len__ == 'function'){
            return v.__len__() > 0;
        }
    }
    return true;
    """)

class float:
    __number__ = JS("0x01")
    def __new__(self, args):
        JS("""
        var v = Number(args[0]);
        if (isNaN(v)) {
            throw pyjslib.ValueError("invalid literal for float(): " + args[0]);
        }
        return v;
""")
# Patching of the standard javascript Number
# which is in principle the python 'float'
JS("""
Number.prototype.__number__ = 0x01;
Number.prototype.__name__ = 'float';
Number.prototype.__init__ = function (value, radix) {
    return null;
};

Number.prototype.__str__ = function () {
    if (typeof this == 'number') return this.toString();
    return "<type 'float'>";
};

Number.prototype.__repr__ = function () {
    if (typeof this == 'number') return this.toString();
    return "<type 'float'>";
};

Number.prototype.__nonzero__ = function () {
    return this != 0;
};

Number.prototype.__cmp__ = function (y) {
    return this < y? -1 : (this == y ? 0 : 1);
};

Number.prototype.__hash__ = function () {
    return this;
};

Number.prototype.__oct__ = function () {
    return '0'+this.toString(8);
};

Number.prototype.__hex__ = function () {
    return '0x'+this.toString(16);
};

Number.prototype.__pos__ = function () {
    return this;
};

Number.prototype.__neg__ = function () {
    return -this;
};

Number.prototype.__abs__ = function () {
    if (this >= 0) return this;
    return -this;
};

Number.prototype.__add__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return this + y;
};

Number.prototype.__radd__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return y + this;
};

Number.prototype.__sub__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return this - y;
};

Number.prototype.__rsub__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return y - this;
};

Number.prototype.__floordiv__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
    return Math.floor(this / y);
};

Number.prototype.__rfloordiv__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (this == 0) throw pyjslib['ZeroDivisionError']('float divmod');
    return Math.floor(y / this);
};

Number.prototype.__div__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (y == 0) throw pyjslib['ZeroDivisionError']('float division');
    return this / y;
};

Number.prototype.__rdiv__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (this == 0) throw pyjslib['ZeroDivisionError']('float division');
    return y / this;
};

Number.prototype.__mul__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return this * y;
};

Number.prototype.__rmul__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    return y * this;
};

Number.prototype.__mod__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (y == 0) throw pyjslib['ZeroDivisionError']('float modulo');
    return this % y;
};

Number.prototype.__rmod__ = function (y) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (this == 0) throw pyjslib['ZeroDivisionError']('float modulo');
    return y % this;
};

Number.prototype.__pow__ = function (y, z) {
    if (!y.__number__ || isNaN(y = y.valueOf())) return pyjslib['NotImplemented'];
    if (typeof z == 'undefined' || z == null) {
        return Math.pow(this, y);
    }
    if (!z.__number__ || isNaN(z = z.valueOf())) return pyjslib['NotImplemented'];
    return Math.pow(this, y) % z;
};

""")

def float_int(value, radix=None):
    JS("""
    var v;
    if (value.__number__) {
        if (radix !== null) {
            throw pyjslib.TypeError("int() can't convert non-string with explicit base");
        }
        v = value.valueOf();
        if (v > 0) {
            v = Math.floor(v);
        } else {
            v = Math.ceil(v);
        }
    } else if (typeof value == 'string') {
        if (radix === null) {
            radix = 10;
        }
        switch (value[value.length-1]) {
            case 'l':
            case 'L':
                v = value.slice(0, value.length-2);
                break;
            default:
                v = value;
        }
        v = parseInt(v, radix);
    } else {
        throw pyjslib.TypeError("TypeError: int() argument must be a string or a number");
    }
    if (isNaN(v) || !isFinite(v)) {
        throw pyjslib.ValueError("invalid literal for int() with base " + radix + ": '" + value + "'");
    }
    return v;
""")

JS("""
(function(){
    var $int = pyjslib['int'] = function (value, radix) {
        var v, i;
        if (typeof radix == 'undefined' || radix === null) {
            if (typeof value == 'undefined') {
                throw pyjslib.TypeError("int() takes at least 1 argument");
            }
            switch (value.__number__) {
                case 0x01:
                    value = value > 0 ? Math.floor(value) : Math.ceil(value);
                    break;
                case 0x02:
                    return value;
                case 0x04:
                    v = value.valueOf();
                    if (!($min_int <= v && v <= $max_int))
                        return value;
            }
            radix = null;
        }
        if (typeof this != 'object' || this.__number__ != 0x02) return new $int(value, radix);
        if (value.__number__) {
            if (radix !== null) throw pyjslib.TypeError("int() can't convert non-string with explicit base");
            v = value.valueOf();
        } else if (typeof value == 'string') {
            if (radix === null) {
                radix = 10;
            }
            v = parseInt(value, radix);
        } else {
            throw pyjslib.TypeError("TypeError: int() argument must be a string or a number");
        }
        if (isNaN(v) || !isFinite(v)) {
            throw pyjslib.ValueError("invalid literal for int() with base " + radix + ": '" + value + "'");
        }
        if ($min_int <= v && v <= $max_int) {
            this.__v = v;
            return this;
        }
        return new pyjslib['long'](v);
    };
    $int.__init__ = function () {};
    $int.__number__ = 0x02;
    $int.__v = 0;
    $int.__name__ = 'int';
    $int.prototype = $int;
    $int.__class__ = $int;

    $int.toExponential = function (fractionDigits) {
        return (typeof fractionDigits == 'undefined' || fractionDigits === null) ? this.__v.toExponential() : this.__v.toExponential(fractionDigits);
    };

    $int.toFixed = function (digits) {
        return (typeof digits == 'undefined' || digits === null) ? this.__v.toFixed() : this.__v.toFixed(digits);
    };

    $int.toLocaleString = function () {
        return this.__v.toLocaleString();
    };

    $int.toPrecision = function (precision) {
        return (typeof precision == 'undefined' || precision === null) ? this.__v.toPrecision() : this.__v.toPrecision(precision);
    };

    $int.toString = function (radix) {
        return (typeof radix == 'undefined' || radix === null) ? this.__v.toString() : this.__v.toString(radix);
    };

    $int.valueOf = function () {
        return this.__v.valueOf();
    };

    $int.__str__ = function () {
        if (typeof this == 'object' && this.__number__ == 0x02) return this.__v.toString();
        return "<type 'int'>";
    };

    $int.__repr__ = function () {
        if (typeof this == 'object' && this.__number__ == 0x02) return this.__v.toString();
        return "<type 'int'>";
    };

    $int.__nonzero__ = function () {
        return this.__v != 0;
    };

    $int.__cmp__ = function (y) {
        return this.__v < y? -1 : (this.__v == y ? 0 : 1);
    };

    $int.__hash__ = function () {
        return this.__v;
    };

    $int.__invert__ = function () {
        return new $int(~this.__v);
    };

    $int.__lshift__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (y < 32) {
            var v = this.__v << y;
            if (v > this.__v) {
                return new $int(v);
            }
        }
        return new pyjslib['long'](this.__v).__lshift__(y);
    };

    $int.__rlshift__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (this.__v < 32) {
            var v = y << this.__v;
            if (v > this.__v) {
                return new $int(v);
            }
        }
        return new pyjslib['long'](y).__lshift__(this.__v);
    };

    $int.__rshift__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(this.__v >> y);
    };

    $int.__rrshift__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(y >> this.__v);
    };

    $int.__and__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(this.__v & y);
    };

    $int.__rand__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(y & this.__v);
    };

    $int.__xor__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(this.__v ^ y);
    };

    $int.__rxor__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(y ^ this.__v);
    };

    $int.__or__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(this.__v | y);
    };

    $int.__ror__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        return new $int(y | this.__v);
    };

    $int.__oct__ = function () {
        return '0x'+this.__v.toString(8);
    };

    $int.__hex__ = function () {
        return '0x'+this.__v.toString(16);
    };

    $int.__pos__ = function () {
        return this;
    };

    $int.__neg__ = function () {
        return new $int(-this.__v);
    };

    $int.__abs__ = function () {
        if (this.__v >= 0) return this;
        return new $int(-this.__v);
    };

    $int.__add__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        var v = this.__v + y;
        if ($min_int <= v && v <= $max_int) {
            return new $int(v);
        }
        if (-$max_float_int < v && v < $max_float_int) {
            return new pyjslib['long'](v);
        }
        return new pyjslib['long'](this.__v).__add__(new pyjslib['long'](y));
    };

    $int.__radd__ = $int.__add__;

    $int.__sub__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        var v = this.__v - y;
        if ($min_int <= v && v <= $max_int) {
            return new $int(v);
        }
        if (-$max_float_int < v && v < $max_float_int) {
            return new pyjslib['long'](v);
        }
        return new pyjslib['long'](this.__v).__sub__(new pyjslib['long'](y));
    };

    $int.__rsub__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        var v = y -this.__v;
        if ($min_int <= v && v <= $max_int) {
            return new $int(v);
        }
        if (-$max_float_int < v && v < $max_float_int) {
            return new pyjslib['long'](v);
        }
        return new pyjslib['long'](y).__sub__(new pyjslib['long'](this.__v));
    };

    $int.__floordiv__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (y == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(Math.floor(this.__v / y));
    };

    $int.__rfloordiv__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (this.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(Math.floor(y / this.__v));
    };

    $int.__div__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (y == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(this.__v / y);
    };

    $int.__rdiv__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (this.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(y / this.__v);
    };

    $int.__mul__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        var v = this.__v * y;
        if ($min_int <= v && v <= $max_int) {
            return new $int(v);
        }
        if (-$max_float_int < v && v < $max_float_int) {
            return new pyjslib['long'](v);
        }
        return new pyjslib['long'](this.__v).__mul__(new pyjslib['long'](y));
    };

    $int.__rmul__ = $int.__mul__;

    $int.__mod__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (y == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(this.__v % y);
    };

    $int.__rmod__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        if (this.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
        return new $int(y % this.__v);
    };

    $int.__pow__ = function (y) {
        if (y.__number__ != 0x02) return pyjslib['NotImplemented'];
        y = y.__v;
        var v = Math.pow(this.__v, y);
        if ($min_int <= v && v <= $max_int) {
            return new $int(v);
        }
        if (-$max_float_int < v && v < $max_float_int) {
            return new pyjslib['long'](v);
        }
        return new pyjslib['long'](this.__v).__pow__(new pyjslib['long'](y));
    };
})();
""")

# This is the python long implementation. See:
#  - Include/longintrepr.h
#  - Include/longobject.h
#  - Objects/longobject.c
JS("""
(function(){

    var $log2 = Math.log(2);
    var $DigitValue = [
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  37, 37, 37, 37, 37, 37,
            37, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
            25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 37, 37, 37, 37,
            37, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
            25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37,
            37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37, 37
    ];
    var $log_base_PyLong_BASE = new Array();
    var $convwidth_base = new Array();
    var $convmultmax_base = new Array();
    for (var i = 0; i < 37; i++) {
        $log_base_PyLong_BASE[i] = $convwidth_base[i] = $convmultmax_base[i] = 0;
    }
    var $cdigit = '0123456789abcdefghijklmnopqrstuvwxyz';


    var PyLong_SHIFT = 15;
    var PyLong_MASK = 0x7fff;
    var PyLong_BASE = 0x8000;

    var KARATSUBA_CUTOFF = 70;
    var KARATSUBA_SQUARE_CUTOFF = (2 * KARATSUBA_CUTOFF);

    var FIVEARY_CUTOFF = 8;

    function array_eq(a, b, n) {
        for (var i = 0 ; i < n; i++) {
            if (a[i] != b[i])
                return false;
        }
        return true;
    }

    function long_normalize(v) {
        var j = v.ob_size < 0 ? -v.ob_size:v.ob_size;
        var i = j;
        while (i > 0 && v.ob_digit[i-1] == 0) {
            i--;
        }
        if (i != j) {
            v.ob_size = v.ob_size < 0 ? -i:i;
        }
        return v;
    }

    function AsScaledDouble(vv) {
        var multiplier = PyLong_BASE; // 1L << PyLong_SHIFT == 1 << 15
        var neg, i, x, nbitsneeded;

        if (vv.ob_size < 0) {
            i = -vv.ob_size;
            neg = true;
        } else if (vv.ob_size > 0) {
            i = vv.ob_size;
            neg = false;
        } else {
            return [0.0, 0];
        }
        --i;
        x = vv.ob_digit[i];
        nbitsneeded = 56;
        while (i > 0 && nbitsneeded > 0) {
            --i;
            x = x * multiplier + vv.ob_digit[i];
            nbitsneeded -= PyLong_SHIFT;
        }
        if (neg) {
            return [-x, i];
        }
        return [x, i];
    }

    function v_iadd(x, m, y, n) {
        var i, carry = 0;
        for (i = 0; i < n; ++i) {
                carry += x[i] + y[i];
                x[i] = carry & PyLong_MASK;
                carry >>= PyLong_SHIFT;
        }
        for (; carry && i < m; ++i) {
                carry += x[i];
                x[i] = carry & PyLong_MASK;
                carry >>= PyLong_SHIFT;
        }
        return carry;
    }

    function v_isub(x, m, y, n) {
        var i, borrow = 0;
        for (i = 0; i < n; ++i) {
                borrow = x[i] - y[i] - borrow;
                x[i] = borrow & PyLong_MASK;
                borrow >>= PyLong_SHIFT;
                borrow &= 1;
        }
        for (; borrow && i < m; ++i) {
                borrow = x[i] - borrow;
                x[i] = borrow & PyLong_MASK;
                borrow >>= PyLong_SHIFT;
                borrow &= 1;
        }
        return borrow;
    }

    //function mul1(a, n) {
    //    return muladd1(a, n, 0);
    //}

    function muladd1(z, a, n, extra) {
        var size_a = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var carry = extra, i;

        for (i = 0; i < size_a; ++i) {
                carry += a.ob_digit[i] * n;
                z.ob_digit[i] = carry & PyLong_MASK;
                carry >>= PyLong_SHIFT;
        }
        z.ob_digit[i] = carry;
        z.ob_size = i + 1;
        return long_normalize(z);
    }

    function inplace_divrem1(pout, pin, pout_idx, pin_idx, size, n) {
        var rem = 0, hi = 0;
        pin_idx += size;
        pout_idx += size;
        while (pin_idx > pin.length) {
            --size;
            --pin_idx;
            pout[--pout_idx] = 0;
        }
        while (--size >= 0) {
            rem = (rem << PyLong_SHIFT) + pin[--pin_idx];
            pout[--pout_idx] = hi = Math.floor(rem / n);
            rem -= hi * n;
        }
        return [rem, pout_idx, pin_idx];
    }

    function divrem1(a, n, prem) {
        var size = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var z = new $long(0);

        prem[0] = inplace_divrem1(z.ob_digit, a.ob_digit, 0, 0, size, n)[0];
        z.ob_size = size;
        return long_normalize(z);
    }

    function Format(aa, base, addL, newstyle, noBase) {
        var text, str, p, i, bits, sz, rem, sign = '';
        var c_0 = "0".charCodeAt(0);
        var c_a = "a".charCodeAt(0);
        base = base.valueOf();

        if (aa.ob_size == 0) {
            if (addL) {
                text = "0L";
            } else {
                text = "0";
            }
        } else {
            if (aa.ob_size < 0) {
                sign = '-';
                size_a = -aa.ob_size;
            } else {
                size_a = aa.ob_size;
            }
            i = base;
            bits = 0;
            while (i > 1) {
                ++bits;
                i >>>= 1;
            }
            i = addL ? 6 : 5;
            j = size_a * PyLong_SHIFT + bits - 1;
            sz = Math.floor(i + j / bits);
            if (j / PyLong_SHIFT < size_a || sz < i) {
                throw pyjslib['OverflowError']("long is too large to format");
            }
            str = new Array();
            p = sz;
            if (addL) str[--p] = 'L';
            if ((base & (base - 1)) == 0) {
                var accum = 0, accumbits = 0, basebits = 1;
                i = base;
                while ((i >>>= 1) > 1) ++basebits;
                for (i = 0; i < size_a; ++i) {
                    accum |= aa.ob_digit[i] << accumbits;
                    accumbits += PyLong_SHIFT;
                    for (;;) {
                        var cdigit = accum & (base - 1);
                        str[--p] = $cdigit.charAt(cdigit);
                        accumbits -= basebits;
                        accum >>>= basebits;
                        if (i < size_a-1) {
                            if (accumbits < basebits) break;
                        } else if (accum <= 0) break;
                    }
                }
                text = str.join("");
            } else {
                // Not 0, and base not a power of 2.
                var scratch, pin, scratch_idx, pin_idx;
                var powbase = base, power = 1, size = size_a;
               
                for (;;) {
                    var newpow = powbase * base;
                    if (newpow >>> PyLong_SHIFT)  /* doesn't fit in a digit */
                        break;
                    powbase = newpow;
                    ++power;
                }
                scratch = aa.ob_digit.slice(0);
                pin = aa.ob_digit;
                scratch_idx = pin_idx = 0;
                do {
                        var ntostore = power;
                        rem = inplace_divrem1(scratch, pin, scratch_idx, pin_idx, size, powbase);
                        scratch_idx = rem[1];
                        rem = rem[0];
                        pin = scratch;
                        pin_idx = 0;
                        if (pin[size - 1] == 0) {
                            --size;
                        }
                        do {
                            var nextrem = Math.floor(rem / base);
                            str[--p] = $cdigit.charAt(rem - nextrem * base);
                            rem = nextrem;
                            --ntostore;
                        } while (ntostore && (size || rem));
                } while (size !=0);
                text = str.slice(p).join("");
            }
            text = text.lstrip('0');
            if (text == "" || text == "L") text = "0" + text;
        }
        if (noBase !== false) {
            switch (base) {
                case 10:
                    break;
                case 2:
                    text = '0b' + text;
                    break;
                case 8:
                    text = (newstyle ? '0o':(aa.ob_size ? '0': '')) + text;
                    break;
                case 16:
                    text = '0x' + text;
                    break;
                default:
                    text = base + '#' + text;
                    break;
            }
        }
        return sign + text;
    }

    function long_divrem(a, b, pdiv, prem) {
        var size_a = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var size_b = b.ob_size < 0 ? -b.ob_size : b.ob_size;
        var z = null;

        if (size_b == 0) {
            throw pyjslib['ZeroDivisionError']("long division or modulo by zero");
        }
        if (size_a < size_b ||
            (size_a == size_b &&
             a.ob_digit[size_a-1] < b.ob_digit[size_b-1])) {
                // |a| < |b|
                pdiv.ob_size = 0;
                prem.ob_digit = a.ob_digit.slice(0);
                prem.ob_size = a.ob_size;
                return 0;
        }
        if (size_b == 1) {
                rem = [0];
                prem.ob_digit = [0];
                prem.ob_size = 1;
                z = divrem1(a, b.ob_digit[0], prem.ob_digit);
                prem = long_normalize(prem);
        }
        else {
                z = x_divrem(a, b, prem);
        }
        if (z === null) {
            pdiv.ob_size = 0;
        } else {
            pdiv.ob_digit = z.ob_digit.slice(0);
            pdiv.ob_size = z.ob_size;
        }
        if ((a.ob_size < 0) != (b.ob_size < 0))
                pdiv.ob_size = -(pdiv.ob_size);
        if (a.ob_size < 0 && prem.ob_size != 0)
                prem.ob_size = -prem.ob_size;
        return 0;
    }

    function x_divrem(v1, w1, prem) {
        var size_w = w1.ob_size < 0 ? -w1.ob_size : w1.ob_size;
        var d = Math.floor(PyLong_BASE / (w1.ob_digit[size_w-1] + 1));
        var v = muladd1($x_divrem_v, v1, d, 0);
        var w = muladd1($x_divrem_w, w1, d, 0);
        var a, j, k;
        var size_v = v.ob_size < 0 ? -v.ob_size : v.ob_size;
        k = size_v - size_w;
        a = new $long(0);
        a.ob_size = k + 1;

        for (j = size_v; k >= 0; --j, --k) {
            var vj = (j >= size_v) ? 0 : v.ob_digit[j];
            var carry = 0;
            var q, i;

            if (vj == w.ob_digit[size_w-1])
                q = PyLong_MASK;
            else
                q = Math.floor(((vj << PyLong_SHIFT) + v.ob_digit[j-1]) /
                        w.ob_digit[size_w-1]);

            while (w.ob_digit[size_w-2]*q >
                    ((
                        (vj << PyLong_SHIFT)
                        + v.ob_digit[j-1]
                        - q*w.ob_digit[size_w-1]
                                                ) << PyLong_SHIFT)
                    + v.ob_digit[j-2])
                --q;

            for (i = 0; i < size_w && i+k < size_v; ++i) {
                var z = w.ob_digit[i] * q;
                var zz = z >>> PyLong_SHIFT;
                carry += v.ob_digit[i+k] - z
                        + (zz << PyLong_SHIFT);
                v.ob_digit[i+k] = carry & PyLong_MASK;
                // carry = Py_ARITHMETIC_RIGHT_SHIFT(BASE_TWODIGITS_TYPE, carry, PyLong_SHIFT);
                carry >>= PyLong_SHIFT;
                carry -= zz;
            }

            if (i+k < size_v) {
                carry += v.ob_digit[i+k];
                v.ob_digit[i+k] = 0;
            }

            if (carry == 0)
                a.ob_digit[k] = q;
            else {
                a.ob_digit[k] = q-1;
                carry = 0;
                for (i = 0; i < size_w && i+k < size_v; ++i) {
                    carry += v.ob_digit[i+k] + w.ob_digit[i];
                    v.ob_digit[i+k] = carry & PyLong_MASK;
                    // carry = Py_ARITHMETIC_RIGHT_SHIFT( BASE_TWODIGITS_TYPE, carry, PyLong_SHIFT);
                    carry >>= PyLong_SHIFT;
                }
            }
        } /* for j, k */

        i = divrem1(v, d, prem);
        prem.ob_digit = i.ob_digit.slice(0);
        prem.ob_size = i.ob_size;
        return long_normalize(a);
    }

    function x_add(a, b) {
        var size_a = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var size_b = b.ob_size < 0 ? -b.ob_size : b.ob_size;
        var z = new $long(0);
        var i;
        var carry = 0;

        if (size_a < size_b) {
            var temp = a;
            a = b;
            b = temp;
            temp = size_a;
            size_a = size_b;
            size_b = temp;
        }
        for (i = 0; i < size_b; ++i) {
                carry += a.ob_digit[i] + b.ob_digit[i];
                z.ob_digit[i] = carry & PyLong_MASK;
                carry >>>= PyLong_SHIFT;
        }
        for (; i < size_a; ++i) {
                carry += a.ob_digit[i];
                z.ob_digit[i] = carry & PyLong_MASK;
                carry >>>= PyLong_SHIFT;
        }
        z.ob_digit[i] = carry;
        z.ob_size = i+1;
        return long_normalize(z);
    }

    function x_sub(a, b) {
        var size_a = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var size_b = b.ob_size < 0 ? -b.ob_size : b.ob_size;
        var z = new $long(0);
        var i;
        var borrow = 0;
        var sign = 1;

        if (size_a < size_b) {
            var temp = a;
            a = b;
            b = temp;
            temp = size_a;
            size_a = size_b;
            size_b = temp;
            sign = -1;
        } else if (size_a == size_b) {
            i = size_a;
            while (--i >= 0 && a.ob_digit[i] == b.ob_digit[i])
                ;
            if (i < 0)
                return z;
            if (a.ob_digit[i] < b.ob_digit[i]) {
                var temp = a;
                a = b;
                b = temp;
                temp = size_a;
                size_a = size_b;
                size_b = temp;
                sign = -1;
            }
            size_a = size_b = i+1;
        }
        for (i = 0; i < size_b; ++i) {
                borrow = a.ob_digit[i] - b.ob_digit[i] - borrow;
                z.ob_digit[i] = borrow & PyLong_MASK;
                borrow >>>= PyLong_SHIFT;
                borrow &= 1;
        }
        for (; i < size_a; ++i) {
                borrow = a.ob_digit[i] - borrow;
                z.ob_digit[i] = borrow & PyLong_MASK;
                borrow >>>= PyLong_SHIFT;
                borrow &= 1;
        }
        z.ob_size = i;
        if (sign < 0)
            z.ob_size = -(z.ob_size);
        return long_normalize(z);
    }

    function x_mul(a, b) {
        var size_a = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        var size_b = b.ob_size < 0 ? -b.ob_size : b.ob_size;
        var z = new $long(0);
        var i, s;

        z.ob_size = size_a + size_b;
        for (i = 0; i < z.ob_size; i++) {
            z.ob_digit[i] = 0;
        }
        if (size_a == size_b && array_eq(a.ob_digit, b.ob_digit, size_a)) {
            // Efficient squaring per HAC, Algorithm 14.16:
            for (i = 0; i < size_a; ++i) {
                var carry;
                var f = a.ob_digit[i];
                var pz = (i << 1);
                var pa = i + 1;
                var paend = size_a;

                carry = z.ob_digit[pz] + f * f;
                z.ob_digit[pz++] = carry & PyLong_MASK;
                carry >>>= PyLong_SHIFT;

                f <<= 1;
                while (pa < paend) {
                    carry += z.ob_digit[pz] + a.ob_digit[pa++] * f;
                    z.ob_digit[pz++] = carry & PyLong_MASK;
                    carry >>>= PyLong_SHIFT;
                }
                if (carry) {
                    carry += z.ob_digit[pz];
                    z.ob_digit[pz++] = carry & PyLong_MASK;
                    carry >>>= PyLong_SHIFT;
                }
                if (carry) {
                    z.ob_digit[pz] += carry & PyLong_MASK;
                }
            }
        }
        else {  // a is not the same as b -- gradeschool long mult
            for (i = 0; i < size_a; ++i) {
                var carry = 0;
                var f = a.ob_digit[i];
                var pz = i;
                var pb = 0;
                var pbend = size_b;

                while (pb < pbend) {
                    carry += z.ob_digit[pz] + b.ob_digit[pb++] * f;
                    z.ob_digit[pz++] = carry & PyLong_MASK;
                    carry >>>= PyLong_SHIFT;
                }
                if (carry) {
                    z.ob_digit[pz] += carry & PyLong_MASK;
                }
            }
        }
        z.ob_size = z.ob_digit.length;
        return long_normalize(z);
    }

    function l_divmod(v, w, pdiv, pmod) {
        var div = $l_divmod_div, 
            mod = $l_divmod_mod; 

        if (long_divrem(v, w, div, mod) < 0)
                return -1;
        if (pdiv == null && pmod == null) return 0;

        if ((mod.ob_size < 0 && w.ob_size > 0) ||
            (mod.ob_size > 0 && w.ob_size < 0)) {
                mod = mod.__add__(w);
                div = div.__sub__($const_long_1);
        }
        if (pdiv !== null) {
            pdiv.ob_digit = div.ob_digit.slice(0);
            pdiv.ob_size = div.ob_size;
        }
        if (pmod !== null) {
            pmod.ob_digit = mod.ob_digit.slice(0);
            pmod.ob_size = mod.ob_size;
        }
        return 0;
    }




    var $long = pyjslib['long'] = function(value, radix) {
        var v, i;
        if (!radix || radix.valueOf() == 0) {
            if (typeof value == 'undefined') {
                throw pyjslib.TypeError("long() takes at least 1 argument");
            }
            switch (value.__number__) {
                case 0x01:
                    value = value > 0 ? Math.floor(value) : Math.ceil(value);
                    break;
                case 0x02:
                    break;
                case 0x04:
                    return value;
            }
            radix = null;
        }
        if (typeof this != 'object' || this.__number__ != 0x04) return new $long(value, radix);

        v = value;
        this.ob_size = 0;
        this.ob_digit = new Array();
        if (v.__number__) {
            if (radix) {
                throw pyjslib.TypeError("long() can't convert non-string with explicit base");
            }
            if (v.__number__ == 0x04) {
                var size = v.ob_size < 0 ? -v.ob_size:v.ob_size;
                for (var i = 0; i < size; i++) {
                    this.ob_digit[i] = v.ob_digit[i];
                }
                this.ob_size = v.ob_size;
                return this;
            }
            if (v.__number__ == 0x02) {
                var neg = false;
                var ndig = 0;
                v = v.valueOf();

                if (v < 0) {
                    v = -v;
                    neg = true;
                }
                // Count the number of Python digits.
                t = v;
                while (t) {
                    this.ob_digit[ndig] = t & PyLong_MASK;
                    t >>>= PyLong_SHIFT;
                    ++ndig;
                }
                this.ob_size = neg ? -ndig : ndig;
                return this;
            }
            if (v.__number__ == 0x01) {
                var ndig, frac, expo, bits;
                var neg = false;

                if (isNaN(v)) {
                    throw pyjslib['ValueError']('cannot convert float NaN to integer');
                }
                if (!isFinite(v)) {
                    throw pyjslib['OverflowError']('cannot convert float infinity to integer');
                }
                if (v == 0) {
                    this.ob_digit[0] = 0;
                    this.ob_size = 0;
                    return this;
                }
                if (v < 0) {
                    v = -v;
                    neg = true;
                }
                // frac = frexp(dval, &expo); // dval = frac*2**expo; 0.0 <= frac < 1.0
                if (v == 0) {
                    frac = 0;
                    expo = 0;
                } else {
                    expo = Math.log(v)/$log2;
                    expo = (expo < 0 ? Math.ceil(expo):Math.floor(expo)) + 1;
                    frac = v / Math.pow(2.0, expo);
                }
                if (expo <= 0) {
                    return this;
                }
                ndig = Math.floor((expo-1) / PyLong_SHIFT) + 1;
                // ldexp(a,b) == a * (2**b)
                frac = frac * Math.pow(2.0, ((expo-1) % PyLong_SHIFT) + 1);
                for (var i = ndig; --i >= 0;) {
                    bits = Math.floor(frac);
                    this.ob_digit[i] = bits;
                    frac -= bits;
                    frac = frac * Math.pow(2.0, PyLong_SHIFT);
                }
                this.ob_size = neg ? -ndig : ndig;
                return this;
            }
            throw pyjslib['ValueError']('cannot convert ' + pyjslib['repr'](value) + 'to integer');
        } else if (typeof v == 'string') {
            var nchars;
            var text = value.lstrip();
            var i = 0;
            var neg = false;

            switch (text.charAt(0)) {
                case '-':
                    neg = true;
                case '+':
                    text = text.slice(1).lstrip();
            }

            if (!radix) {
                if (text == '0' || text.charAt(0) != '0') {
                    radix = 10;
                } else {
                    switch (text.charAt(1)) {
                        case 'x':
                        case 'X':
                            radix = 16;
                            break;
                        case 'o':
                        case 'O':
                            radix = 8;
                            break;
                        case 'b':
                        case 'B':
                            radix = 2;
                            break;
                        default:
                            radix = 8;
                            break;
                    }
                }
            } else if (radix < 1 || radix > 36) {
                throw pyjslib['ValueError']("long() arg 2 must be >= 2 and <= 36");
            }
            if (text.charAt(0) == '0' && text.length > 1) {
                switch (text.charAt(1)) {
                    case 'x':
                    case 'X':
                        if (radix == 16) text = text.slice(2);
                        break;
                    case 'o':
                    case 'O':
                        if (radix == 8) text = text.slice(2);
                        break;
                    case 'b':
                    case 'B':
                        if (radix == 2) text = text.slice(2);
                        break;

                }
            }
            if ((radix & (radix - 1)) == 0) {
                // binary base: 2, 4, 8, ...
                var n, bits_per_char, accum, bits_in_accum, k, pdigit;
                var p = 0;

                n = radix;
                for (bits_per_char = -1; n; ++bits_per_char) {
                    n >>>= 1;
                }
                n = 0;
                while ($DigitValue[text.charCodeAt(p)] < radix) {
                    p++;
                }
                nchars = p;
                n = p * bits_per_char + PyLong_SHIFT-1; //14 = PyLong_SHIFT - 1
                if (n / bits_per_char < p) {
                    throw pyjslib['ValueError']("long string too large to convert");
                }
                this.ob_size = n = Math.floor(n/PyLong_SHIFT);
                for (var i = 0; i < n; i++) {
                    this.ob_digit[i] = 0;
                }
                // Read string from right, and fill in long from left
                accum = 0;
                bits_in_accum = 0;
                pdigit = 0;
                while (--p >= 0) {
                    k = $DigitValue[text.charCodeAt(p)];
                    accum |= k << bits_in_accum;
                    bits_in_accum += bits_per_char;
                    if (bits_in_accum >= PyLong_SHIFT) {
                        this.ob_digit[pdigit] = accum & PyLong_MASK;
                        pdigit++;
                        accum >>>= PyLong_SHIFT;
                        bits_in_accum -= PyLong_SHIFT;
                    }
                }
                if (bits_in_accum) {
                    this.ob_digit[pdigit++] = accum;
                }
                while (pdigit < n) {
                    this.ob_digit[pdigit++] = 0;
                }
                long_normalize(this);
            } else {
                // Non-binary bases (such as radix == 10)
                var c, i, convwidth, convmultmax, convmult, pz, pzstop, scan, size_z;

                if ($log_base_PyLong_BASE[radix] == 0.0) {
                    var i = 1;
                    convmax = radix;
                    $log_base_PyLong_BASE[radix] = Math.log(radix) / Math.log(PyLong_BASE);
                    for (;;) {
                        var next = convmax * radix;
                        if (next > PyLong_BASE) break;
                        convmax = next;
                        ++i;
                    }
                    $convmultmax_base[radix] = convmax;
                    $convwidth_base[radix] = i;
                }
                scan = 0;
                while ($DigitValue[text.charCodeAt(scan)] < radix)
                    ++scan;
                nchars = scan;
                size_z = scan * $log_base_PyLong_BASE[radix] + 1;
                for (var i = 0; i < size_z; i ++) {
                    this.ob_digit[i] = 0;
                }
                this.ob_size = 0;
                convwidth = $convwidth_base[radix];
                convmultmax = $convmultmax_base[radix];
                for (var str = 0; str < scan;) {
                    c = $DigitValue[text.charCodeAt(str++)];
                    for (i = 1; i < convwidth && str != scan; ++i, ++str) {
                        c = c * radix + $DigitValue[text.charCodeAt(str)];
                    }
                    convmult = convmultmax;
                    if (i != convwidth) {
                        convmult = radix;
                        for ( ; i > 1; --i) convmult *= radix;
                    }
                    pz = 0;
                    pzstop = this.ob_size;
                    for (; pz < pzstop; ++pz) {
                        c += this.ob_digit[pz] * convmult;
                        this.ob_digit[pz] = c & PyLong_MASK;
                        c >>>= PyLong_SHIFT;
                    }
                    if (c) {
                        if (this.ob_size < size_z) {
                            this.ob_digit[pz] = c;
                            this.ob_size++;
                        } else {
                            this.ob_digit[this.ob_size] = c;
                        }
                    }
                }
            }
            text = text.slice(nchars);
            if (neg) this.ob_size = -this.ob_size;
            if (text.charAt(0) == 'l' || text.charAt(0) == 'L') text = text.slice(1);
            text = text.lstrip();
            if (text.length === 0) {
                return this;
            }
            throw pyjslib.ValueError("invalid literal for long() with base " +
                                     radix + ": " + value);
        } else {
            throw pyjslib.TypeError("TypeError: long() argument must be a string or a number");
        }
        if (isNaN(v) || !isFinite(v)) {
            throw pyjslib.ValueError("invalid literal for long() with base " + radix + ": '" + v + "'");
        }
        return this;
    };
    $long.__init__ = function () {};
    $long.__number__ = 0x04;
    $long.__name__ = 'long';
    $long.prototype = $long;
    $long.__class__ = $long;
    $long.ob_size = 0;

    $long.toExponential = function (fractionDigits) {
        return (typeof fractionDigits == 'undefined' || fractionDigits === null) ? this.__v.toExponential() : this.__v.toExponential(fractionDigits);
    };

    $long.toFixed = function (digits) {
        return (typeof digits == 'undefined' || digits === null) ? this.__v.toFixed() : this.__v.toFixed(digits);
    };

    $long.toLocaleString = function () {
        return this.__v.toLocaleString();
    };

    $long.toPrecision = function (precision) {
        return (typeof precision == 'undefined' || precision === null) ? this.__v.toPrecision() : this.__v.toPrecision(precision);
    };

    $long.toString = function (radix) {
        return (typeof radix == 'undefined' || radix === null) ? Format(this, 10, false, false) : Format(this, radix, false, false, false);
    };

    $long.valueOf = function() {
        var x, v;
        x = AsScaledDouble(this);
        // ldexp(a,b) == a * (2**b)
        v = x[0] * Math.pow(2.0, x[1] * PyLong_SHIFT);
        if (!isFinite(v)) {
            throw pyjslib['OverflowError']('long int too large to convert to float');
        }
        return v;
    };

    $long.__str__ = function () {
        return Format(this, 10, false, false);
    };

    $long.__repr__ = function () {
        return Format(this, 10, true, false);
    };

    $long.__nonzero__ = function () {
        return this.ob_size != 0;
    };

    $long.__cmp__ = function (b) {
        var sign;
 
        if (this.ob_size != b.ob_size) {
            if (this.ob_size < b.ob_size) return -1;
            return 1;
        }
        var i = this.ob_size < 0 ? - this.ob_size : this.ob_size;
        while (--i >= 0 && this.ob_digit[i] == b.ob_digit[i])
            ;
        if (i < 0) return 0;
        if (this.ob_digit[i] < b.ob_digit[i]) {
            if (this.ob_size < 0) return 1;
            return -1;
        }
        if (this.ob_size < 0) return -1;
        return 1;
    };

    $long.__hash__ = function () {
        var s = this.__str__();
        var v = this.valueOf();
        if (v.toString() == s) {
            return v;
        }
        return s;
    };

    $long.__invert__ = function () {
        var x = this.__add__($const_long_1);
        x.ob_size = -x.ob_size;
        return x;
    };

    $long.__neg__ = function () {
        var x = new $long(0);
        x.ob_digit = this.ob_digit.slice(0);
        x.ob_size = -this.ob_size;
        return x;
    };

    $long.__abs__ = function () {
        if (this.ob_size >= 0) return this;
        var x = new $long(0);
        x.ob_digit = this.ob_digit.slice(0);
        x.ob_size = -x.ob_size;
        return x;
    };

    $long.__lshift = function (y) {
        var a, z, wordshift, remshift, oldsize, newsize, 
            accum, i, j;
        if (y < 0) {
            throw pyjslib['ValueError']('negative shift count');
        }
        if (y >= $max_float_int) {
            throw pyjslib['ValueError']('outrageous left shift count');
        }
        a = this;

        wordshift = Math.floor(y / PyLong_SHIFT);
        remshift  = y - wordshift * PyLong_SHIFT;

        oldsize = a.ob_size < 0 ? -a.ob_size : a.ob_size;
        newsize = oldsize + wordshift;
        if (remshift) ++newsize;
        z = new $long(0);
        z.ob_size = a.ob_size < 0 ? -newsize : newsize;
        for (i = 0; i < wordshift; i++) {
            z.ob_digit[i] = 0;
        }
        accum = 0;
        for (i = wordshift, j = 0; j < oldsize; i++, j++) {
            accum |= a.ob_digit[j] << remshift;
            z.ob_digit[i] = accum & PyLong_MASK;
            accum >>>= PyLong_SHIFT;
        }
        if (remshift) {
            z.ob_digit[newsize-1] = accum;
        }
        z = long_normalize(z);
        return z;
    };

    $long.__lshift__ = function (y) {
        switch (y.__number__) {
            case 0x01:
                if (y == Math.floor(y)) return this.__lshift(y);
                break;
            case 0x02:
                return this.__lshift(y.__v);
            case 0x04:
                y = y.valueOf();
                return this.__lshift(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rlshift__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__lshift(this.valueOf());
            case 0x04:
                return y.__lshift(this.valueOf());
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rshift = function (y) {
        var a, z, size, wordshift, newsize, loshift, hishift,
            lomask, himask, i, j;
        if (y.__number__ != 0x01) {
            y = y.valueOf();
        } else {
            if (y != Math.floor(y)) {
                throw pyjslib['TypeError']("unsupported operand type(s) for >>: 'long' and 'float'");
            }
        }
        if (y < 0) {
            throw pyjslib['ValueError']('negative shift count');
        }
        if (y >= $max_float_int) {
            throw pyjslib['ValueError']('shift count too big');
        }
        a = this;
        size = this.ob_size;
        if (this.ob_size < 0) {
            size = -size;
            a = this.__add__($const_long_1);
            a.ob_size = -a.ob_size;
        }

        wordshift = Math.floor(y / PyLong_SHIFT);
        newsize = size - wordshift;
        if (newsize <= 0) {
            z = $const_long_0;
        } else {
            loshift = y % PyLong_SHIFT;
            hishift = PyLong_SHIFT - loshift;
            lomask = (1 << hishift) - 1;
            himask = PyLong_MASK ^ lomask;
            z = new $long(0);
            z.ob_size = a.ob_size < 0 ? -newsize : newsize;
            for (i = 0, j = wordshift; i < newsize; i++, j++) {
                z.ob_digit[i] = (a.ob_digit[j] >>> loshift) & lomask;
                if (i+1 < newsize) {
                    z.ob_digit[i] |=
                      (a.ob_digit[j+1] << hishift) & himask;
                }
            }
            z = long_normalize(z);
        }

        if (this.ob_size < 0) {
            z = z.__add__($const_long_1);
            z.ob_size = -z.ob_size;
        }
        return z;
    };

    $long.__rshift__ = function (y) {
        switch (y.__number__) {
            case 0x01:
                if (y == Math.floor(y)) return this.__rshift(y);
                break;
            case 0x02:
                return this.__rshift(y.__v);
            case 0x04:
                y = y.valueOf();
                return this.__rshift(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rrshift__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__rshift(this.valueOf());
            case 0x04:
                return y.__rshift(this.valueOf());
        }
        return pyjslib['NotImplemented'];
    };

    $long.__and = function (b) {
        var a, maska, maskb, negz, size_a, size_b, size_z,
            i, z, diga, digb, v, op;

        a = this;

        if (a.ob_size < 0) {
            a = a.__invert__();
            maska = PyLong_MASK;
        } else {
            maska = 0;
        }
        if (b.ob_size < 0) {
            b = b.__invert__();
            maskb = PyLong_MASK;
        } else {
            maskb = 0;
        }
        negz = 0;


            op = '&';
            if (maska && maskb) {
                op = '|';
                maska ^= PyLong_MASK;
                maskb ^= PyLong_MASK;
                negz = -1;
            }


        size_a = a.ob_size;
        size_b = b.ob_size;
        size_z = op == '&'
                    ? (maska
                        ? size_b
                        : (maskb ? size_a : (size_a < size_b ? size_a : size_b)))
                    : (size_a > size_b ? size_a : size_b);
        z = new $long(0);
        z.ob_size = size_z;

        switch (op) {
            case '&':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga & digb;
                }
                break;
            case '|':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga | digb;
                }
                break;
            case '^':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga ^ digb;
                }
                break;
        }
        z = long_normalize(z);
        if (negz == 0) {
            return z;
        }
        return z.__invert__();
    };

    $long.__and__ = function (y) {
        switch (y.__number__) {
            case 0x01:
                if (y == Math.floor(y)) return this.__and(new $long(y));
                break;
            case 0x02:
                return this.__and(new $long(y.__v));
            case 0x04:
                return this.__and(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rand__ = $long.__and__;

    $long.__xor = function (b) {
        var a,maska, maskb, negz, size_a, size_b, size_z,
            i, z, diga, digb, v, op;

        a = this;

        if (a.ob_size < 0) {
            a = a.__invert__();
            maska = PyLong_MASK;
        } else {
            maska = 0;
        }
        if (b.ob_size < 0) {
            b = b.__invert__();
            maskb = PyLong_MASK;
        } else {
            maskb = 0;
        }
        negz = 0;


            op = '^';
            if (maska != maskb) {
                maska ^= PyLong_MASK;
                negz = -1;
            }


        size_a = a.ob_size;
        size_b = b.ob_size;
        size_z = op == '&'
                    ? (maska
                        ? size_b
                        : (maskb ? size_a : (size_a < size_b ? size_a : size_b)))
                    : (size_a > size_b ? size_a : size_b);
        z = new $long(0);
        z.ob_size = size_z;

        switch (op) {
            case '&':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga & digb;
                }
                break;
            case '|':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga | digb;
                }
                break;
            case '^':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga ^ digb;
                }
                break;
        }
        z = long_normalize(z);
        if (negz == 0) {
            return z;
        }
        return z.__invert__();
    };

    $long.__xor__ = function (y) {
        switch (y.__number__) {
            case 0x01:
                if (y == Math.floor(y)) return this.__xor(new $long(y));
                break;
            case 0x02:
                return this.__xor(new $long(y.__v));
            case 0x04:
                return this.__xor(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rxor__ = $long.__xor__;

    $long.__or = function (b) {
        var a, maska, maskb, negz, size_a, size_b, size_z,
            i, z, diga, digb, v, op;

        a = this;

        if (a.ob_size < 0) {
            a = a.__invert__();
            maska = PyLong_MASK;
        } else {
            maska = 0;
        }
        if (b.ob_size < 0) {
            b = b.__invert__();
            maskb = PyLong_MASK;
        } else {
            maskb = 0;
        }
        negz = 0;


            op = '|';
            if (maska || maskb) {
                op = '&';
                maska ^= PyLong_MASK;
                maskb ^= PyLong_MASK;
                negz = -1;
            }


        size_a = a.ob_size;
        size_b = b.ob_size;
        size_z = op == '&'
                    ? (maska
                        ? size_b
                        : (maskb ? size_a : (size_a < size_b ? size_a : size_b)))
                    : (size_a > size_b ? size_a : size_b);
        z = new $long(0);
        z.ob_size = size_z;

        switch (op) {
            case '&':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga & digb;
                }
                break;
            case '|':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga | digb;
                }
                break;
            case '^':
                for (i = 0; i < size_z; ++i) {
                    diga = (i < size_a ? a.ob_digit[i] : 0) ^ maska;
                    digb = (i < size_b ? b.ob_digit[i] : 0) ^ maskb;
                    z.ob_digit[i] = diga ^ digb;
                }
                break;
        }
        z = long_normalize(z);
        if (negz == 0) {
            return z;
        }
        return z.__invert__();
    };

    $long.__or__ = function (y) {
        switch (y.__number__) {
            case 0x01:
                if (y == Math.floor(y)) return this.__or(new $long(y));
                break;
            case 0x02:
                return this.__or(new $long(y.__v));
            case 0x04:
                return this.__or(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__ror__ = $long.__or__;

    $long.__oct__ = function () {
        return Format(this, 8, true, false);
    };

    $long.__hex__ = function () {
        return Format(this, 16, true, false);
    };

    $long.__add = function (b) {
        var a = this, z;
        if (a.ob_size < 0) {
            if (b.ob_size < 0) {
                z = x_add(a, b);
                z.ob_size = -(z.ob_size);
            }
            else {
                z = x_sub(b, a);
            }
        }
        else {
            z = b.ob_size < 0 ? x_sub(a, b) : x_add(a, b);
        }
        return z;
    };

    $long.__add__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__add(new $long(y.__v));
            case 0x04:
                return this.__add(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__radd__ = $long.__add__;

    $long.__sub = function (b) {
        var a = this, z;
        if (a.ob_size < 0) {
            z = b.ob_size < 0 ? x_sub(a, b) : x_add(a, b);
            z.ob_size = -(z.ob_size);
        }
        else {
            z = b.ob_size < 0 ?  x_add(a, b) : x_sub(a, b);
        }
        return z;
    };

    $long.__sub__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__sub(new $long(y.__v));
            case 0x04:
                return this.__sub(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rsub__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__sub(this);
            case 0x04:
                return y.__sub(this);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__mul = function (b) {
        //var z = k_mul(a, b);
        var z = x_mul(this, b);
        if ((this.ob_size ^ b.ob_size) < 0)
            z.ob_size = -(z.ob_size);
        return z;
    };

    $long.__mul__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__mul(new $long(y.__v));
            case 0x04:
                return this.__mul(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rmul__ = $long.__mul__;

    $long.__div = function (b) {
        var div = new $long(0);
        l_divmod(this, b, div, null);
        return div;
    };

    $long.__div__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__sub(new $long(y.__v));
            case 0x04:
                return this.__sub(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rdiv__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__div(this);
            case 0x04:
                return y.__div(this);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__mod = function (b) {
        var mod = new $long(0);
        l_divmod(this, b, null, mod);
        return mod;
    };

    $long.__mod__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__mod(new $long(y.__v));
            case 0x04:
                return this.__mod(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rmod__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__mod(this);
            case 0x04:
                return y.__mod(this);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__divmod = function (b) {
        var div = new $long(0);
        var mod = new $long(0);
        l_divmod(this, b, div, mod);
        return pyjslib['tuple']([div, mod]);
    };

    $long.__divmod__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__divmod(new $long(y.__v));
            case 0x04:
                return this.__divmod(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rdivmod__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__divmod(this);
            case 0x04:
                return y.__divmod(this);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__floordiv = function (b) {
        var div = new $long(0);
        l_divmod(this, b, div, null);
        return div;
    };

    $long.__floordiv__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return this.__floordiv(new $long(y.__v));
            case 0x04:
                return this.__floordiv(y);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__rfloordiv__ = function (y) {
        switch (y.__number__) {
            case 0x02:
                return (new $long(y.__v)).__floordiv(this);
            case 0x04:
                return y.__floordiv(this);
        }
        return pyjslib['NotImplemented'];
    };

    $long.__pow = function (w, x) {
        var v = this;
        var a, b, c, negativeOutput = 0, z, i, j, k, temp, bi;
        var table = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];

        a = this;
        b = w.__number__ == 0x04 ? w : new $long(w);
        if (x === null || typeof x == 'undefined') {
            c = null;
        } else {
            c = x.__number__ == 0x04 ? x : new $long(x);
        }

        if (b.ob_size < 0) {
            if (c !== null) {
                throw pyjslib['TypeError']("pow() 2nd argument cannot be negative when 3rd argument specified");
            }
            return Math.pow(v.valueOf(), w.valueOf());
        }

        if (c !== null) {
            if (c.ob_size == 0) {
                throw pyjslib['ValueError']("pow() 3rd argument cannot be 0");
            }
            if (c.ob_size < 0) {
                negativeOutput = 1;
                temp = $pow_temp_c;
                temp.ob_digit = c.ob_digit.slice(0);
                temp.ob_size = -c.ob_size;
                c = temp;
            }
            if (c.ob_size == 1 && c.ob_digit[0] == 1) {
                return $const_long_0;
            }
            if (a.ob_size < 0) {
                temp = $pow_temp_a;
                l_divmod(a, c, null, temp);
                a = temp;
            }
        }
        z = new $long(1);
        temp = $pow_temp_z;
        if (b.ob_size <= FIVEARY_CUTOFF) {
            for (i = b.ob_size - 1; i >= 0; --i) {
                bi = b.ob_digit[i];
                for (j = 1 << (PyLong_SHIFT-1); j != 0; j >>>= 1) {
                    z = z.__mul(z);
                    if (c !== null) {
                        l_divmod(z, c, null, temp);
                        z.ob_digit = temp.ob_digit.slice(0);
                        z.ob_size = temp.ob_size;
                    }
                    if (bi & j) {
                        z = z.__mul(a);
                        if (c !== null) {
                            l_divmod(z, c, null, temp);
                            z.ob_digit = temp.ob_digit.slice(0);
                            z.ob_size = temp.ob_size;
                        }
                    }
                }
            }
        } else {
            table[0] = z;
            for (i = 1; i < 32; ++i) {
                table[i] = table[i-1].__mul(a);
                if (c !== null) {
                    l_divmod(table[i], c, null, temp);
                    table[i].ob_digit = temp.ob_digit.slice(0);
                    table[i].ob_size = temp.ob_size;
                }
            }
            for (i = b.ob_size - 1; i >= 0; --i) {
                bi = b.ob_digit[i];
                for (j = PyLong_SHIFT - 5; j >= 0; j -= 5) {
                    var index = (bi >>> j) & 0x1f;
                    for (k = 0; k < 5; ++k) {
                        z = z.__mul(z);
                        if (c !== null) {
                            l_divmod(z, c, null, temp);
                            z.ob_digit = temp.ob_digit.slice(0);
                            z.ob_size = temp.ob_size;
                        }
                    }
                    if (index) {
                        z = z.__mul(table[index]);
                        if (c !== null) {
                            l_divmod(z, c, null, temp);
                            z.ob_digit = temp.ob_digit.slice(0);
                            z.ob_size = temp.ob_size;
                        }
                    }
                }
            }
        }

        if ((c !== null) && negativeOutput && 
            (z.ob_size != 0) && (c.ob_size != 0)) {
            z = z.__sub__(c);
        }
        return z;
    };

    $long.__pow__ = function (y, z) {
        switch (y.__number__) {
            case 0x02:
                if (typeof z == 'undefined')
                    return this.__pow(new $long(y.__v), null);
                switch (z.__number) {
                    case 0x02:
                        return this.__pow(new $long(y.__v), new $long(z));
                    case 0x04:
                        return this.__pow(new $long(y.__v), z);
                }
                break;
            case 0x04:
                if (typeof z == 'undefined')
                    return this.__pow(y, null);
                switch (z.__number) {
                    case 0x02:
                        return this.__pow(y, new $long(z));
                    case 0x04:
                        return this.__pow(y, z);
                }
                break;
        }
        return pyjslib['NotImplemented'];
    };


    var $const_long_0 = new $long(0),
        $const_long_1 = new $long(1);
    // Since javascript is single threaded:
    var $l_divmod_div = new $long(0),
        $l_divmod_mod = new $long(0),
        $x_divrem_v = new $long(0),
        $x_divrem_w = new $long(0),
        $pow_temp_a = new $long(0),
        $pow_temp_c = new $long(0),
        $pow_temp_z = new $long(0);
})();

""")


"""@CONSTANT_DECLARATION@"""

class NotImplementedType(object):
    def __repr__(self):
        return "<type 'NotImplementedType'>"
    def __str__(self):
        self.__repr__()
    def toString(self):
        self.__repr__()
NotImplemented = NotImplementedType()

JS("""
var $iter_array = function (l) {
    this.__array = l;
    this.i = -1;
};
$iter_array.prototype.next = function (noStop) {
    if (++this.i == this.__array.length) {
        if (noStop === true) {
            return;
        }
        throw pyjslib.StopIteration;
    }
    return this.__array[this.i];
};
$iter_array.prototype.__iter__ = function ( ) {
    return this;
};
var $reversed_iter_array = function (l) {
    this.___array = l;
    this.i = l.length;
};
$reversed_iter_array.prototype.next = function (noStop) {
    if (--this.i == -1) {
        if (noStop === true) {
            return;
        }
        throw pyjslib.StopIteration;
    }
    return this.___array[this.i];
};
$reversed_iter_array.prototype.__iter__ = function ( ) {
    return this;
};
//$reversed_iter_array.prototype.$genfunc = $reversed_iter_array.prototype.next;
var $enumerate_array = function (l) {
    this.array = l;
    this.i = -1;
    this.tuple = """)
tuple([0, ""])
JS("""
    this.tl = this.tuple.__array;
};
$enumerate_array.prototype.next = function (noStop, reuseTuple) {
    if (++this.i == this.array.length) {
        if (noStop === true) {
            return;
        }
        throw pyjslib.StopIteration;
    }
    this.tl[1] = this.array[this.i];
    if (this.tl[0].__number__ == 0x01) {
        this.tl[0] = this.i;
    } else {
        this.tl[0] = new pyjslib['int'](this.i);
    }
    return reuseTuple === true ? this.tuple : pyjslib.tuple(this.tl);
};
$enumerate_array.prototype.__iter__ = function ( ) {
    return this;
};
$enumerate_array.prototype.$genfunc = $enumerate_array.prototype.next;
""")
# NOTE: $genfunc is defined to enable faster loop code

class list:
    def __init__(self, data=JS("[]")):
        # Basically the same as extend, but to save expensive function calls...
        JS("""
        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
            self.__array = data.slice();
            return null;
        }
        if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                self.__array = data.__array.slice();
                return null;
            }
            var iter = data.__iter__();
            if (typeof iter.__array == 'object') {
                self.__array = iter.__array.slice();
                return null;
            }
            data = [];
            var item, i = 0;
            if (typeof iter.$genfunc == 'function') {
                while (typeof (item=iter.next(true)) != 'undefined') {
                    data[i++] = item;
                }
            } else {
                try {
                    while (true) {
                        data[i++] = iter.next();
                    }
                }
                catch (e) {
                    if (e.__name__ != 'StopIteration') throw e;
                }
            }
            self.__array = data;
            return null;
        }
        throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        """)

    def __hash__(self):
        raise TypeError("list objects are unhashable")

    def append(self, item):
        JS("""self.__array[self.__array.length] = item;""")

    # extend in place, just in case there's somewhere a shortcut to self.__array
    def extend(self, data):
        # Transform data into an array and append to self.__array
        JS("""
        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
        } else if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                data = data.__array;
            } else {
                var iter = data.__iter__();
                if (typeof iter.__array == 'object') {
                    data = iter.__array;
                }
                data = [];
                var item, i = 0;
                if (typeof iter.$genfunc == 'function') {
                    while (typeof (item=iter.next(true)) != 'undefined') {
                        data[i++] = item;
                    }
                } else {
                    try {
                        while (true) {
                            data[i++] = iter.next();
                        }
                    }
                    catch (e) {
                        if (e.__name__ != 'StopIteration') throw e;
                    }
                }
            }
        } else {
            throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        }
        var l = self.__array;
        var j = self.__array.length;
        var n = data.length, i = 0;
        while (i < n) {
            l[j++] = data[i++];
        }
        """)

    def remove(self, value):
        JS("""
        var index=self.index(value);
        if (index<0) {
            throw pyjslib.ValueError("list.remove(x): x not in list");
        }
        self.__array.splice(index, 1);
        return true;
        """)

    def index(self, value, start=0):
        JS("""
        start = start.valueOf();
        if (typeof value == 'number' || typeof value == 'string') {
            start = self.__array.indexOf(value, start);
            if (start >= 0)
                return start;
        } else {
            var len = self.__array.length >>> 0;

            start = (start < 0)
                    ? Math.ceil(start)
                    : Math.floor(start);
            if (start < 0)
                start += len;

            for (; start < len; start++) {
                if (start in self.__array &&
                    pyjslib.cmp(self.__array[start], value) == 0)
                    return start;
            }
        }
        """)
        raise ValueError("list.index(x): x not in list")

    def insert(self, index, value):
        JS("""    var a = self.__array; self.__array=a.slice(0, index).concat(value, a.slice(index));""")

    def pop(self, index = -1):
        JS("""
        index = index.valueOf();
        if (index<0) index += self.__array.length;
        if (index < 0 || index >= self.__array.length) {
            if (self.__array.length == 0) {
                throw pyjslib.IndexError("pop from empty list");
            }
            throw pyjslib.IndexError("pop index out of range");
        }
        var a = self.__array[index];
        self.__array.splice(index, 1);
        return a;
        """)

    def __cmp__(self, l):
        if not isinstance(l, list):
            return -1
        JS("""
        var n1 = self.__array.length,
            n2 = l.__array.length,
            a1 = self.__array,
            a2 = l.__array,
            n, c;
        n = (n1 < n2 ? n1 : n2);
        for (var i = 0; i < n; i++) {
            c = pyjslib.cmp(a1[i], a2[i]);
            if (c) return c;
        }
        if (n1 < n2) return -1;
        if (n1 > n2) return 1;
        return 0;""")

    def __getslice__(self, lower, upper):
        JS("""
        if (upper==null) return pyjslib.list(self.__array.slice(lower));
        return pyjslib.list(self.__array.slice(lower, upper));
        """)

    def __delslice__(self, lower, upper):
        JS("""
        var n = upper - lower;
        if (upper==null) {
            n =  self.__array.length;
        }
        if (!lower) lower = 0;
        if (n > 0) self.__array.splice(lower, n);
        """)
        return None

    def __setslice__(self, lower, upper, data):
        self.__delslice__(lower, upper)
        tail = self.__getslice__(lower, None)
        self.__delslice__(lower, None)
        self.extend(data)
        self.extend(tail)
        return None

    def __getitem__(self, index):
        JS("""
        index = index.valueOf();
        if (index < 0) index += self.__array.length;
        if (index < 0 || index >= self.__array.length) {
            throw pyjslib.IndexError("list index out of range");
        }
        return self.__array[index];
        """)

    def __setitem__(self, index, value):
        JS("""
        index = index.valueOf();
        if (index < 0) index += self.__array.length;
        if (index < 0 || index >= self.__array.length) {
            throw pyjslib.IndexError("list assignment index out of range");
        }
        self.__array[index]=value;
        """)

    def __delitem__(self, index):
        JS("""
        index = index.valueOf();
        if (index < 0) index += self.__array.length;
        if (index < 0 || index >= self.__array.length) {
            throw pyjslib.IndexError("list assignment index out of range");
        }
        self.__array.splice(index, 1);
        """)

    def __len__(self):
        return INT(JS("""self.__array.length"""))

    def __contains__(self, value):
        try:
            self.index(value)
        except ValueError:
            return False
        return True

    def __iter__(self):
        return JS("new $iter_array(self.__array)")

    def __reversed__(self):
        return JS("new $reversed_iter_array(self.__array)")

    def __enumerate__(self):
        return JS("new $enumerate_array(self.__array)")

    def reverse(self):
        JS("""    self.__array.reverse();""")

    def sort(self, cmp=None, key=None, reverse=False):
        if cmp is None:
            cmp = __cmp
        if key and reverse:
            def thisSort1(a,b):
                return -cmp(key(a), key(b))
            self.__array.sort(thisSort1)
        elif key:
            def thisSort2(a,b):
                return cmp(key(a), key(b))
            self.__array.sort(thisSort2)
        elif reverse:
            def thisSort3(a,b):
                return -cmp(a, b)
            self.__array.sort(thisSort3)
        else:
            self.__array.sort(cmp)

    def getArray(self):
        """
        Access the javascript Array that is used internally by this list
        """
        return self.__array

    #def __str__(self):
    #    return self.__repr__()
    #See monkey patch at the end of the list class definition

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        JS("""
        var s = "[";
        for (var i=0; i < self.__array.length; i++) {
            s += pyjslib.repr(self.__array[i]);
            if (i < self.__array.length - 1)
                s += ", ";
        }
        s += "]";
        return s;
        """)

    def __add__(self, y):
        if not isinstance(y, self):
            raise TypeError("can only concatenate list to list")
        return list(self.__array.concat(y.__array))

    def __mul__(self, n):
        if not JS("n !== null && n.__number__ && (n.__number__ != 0x01 || isFinite(n))"):
            raise TypeError("can't multiply sequence by non-int")
        a = []
        while n:
            n -= 1
            a.extend(self.__array)
        return a

    def __rmul__(self, n):
        return self.__mul__(n)
JS("pyjslib.list.__str__ = pyjslib.list.__repr__;")
JS("pyjslib.list.toString = pyjslib.list.__str__;")


class tuple:
    def __init__(self, data=JS("[]")):
        JS("""
        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
            self.__array = data.slice();
            return null;
        }
        if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                self.__array = data.__array.slice();
                return null;
            }
            var iter = data.__iter__();
            if (typeof iter.__array == 'object') {
                self.__array = iter.__array.slice();
                return null;
            }
            data = [];
            var item, i = 0;
            if (typeof iter.$genfunc == 'function') {
                while (typeof (item=iter.next(true)) != 'undefined') {
                    data[i++] = item;
                }
            } else {
                try {
                    while (true) {
                        data[i++] = iter.next();
                    }
                }
                catch (e) {
                    if (e.__name__ != 'StopIteration') throw e;
                }
            }
            self.__array = data;
            return null;
        }
        throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        """)

    def __hash__(self):
        return '$tuple$' + str(self.__array)

    def __cmp__(self, l):
        if not isinstance(l, tuple):
            return 1
        JS("""
        var n1 = self.__array.length,
            n2 = l.__array.length,
            a1 = self.__array,
            a2 = l.__array,
            n, c;
        n = (n1 < n2 ? n1 : n2);
        for (var i = 0; i < n; i++) {
            c = pyjslib.cmp(a1[i], a2[i]);
            if (c) return c;
        }
        if (n1 < n2) return -1;
        if (n1 > n2) return 1;
        return 0;""")

    def __getslice__(self, lower, upper):
        JS("""
        if (upper==null) return pyjslib.tuple(self.__array.slice(lower));
        return pyjslib.tuple(self.__array.slice(lower, upper));
        """)

    def __getitem__(self, index):
        JS("""
        index = index.valueOf();
        if (index < 0) index += self.__array.length;
        if (index < 0 || index >= self.__array.length) {
            throw pyjslib.IndexError("tuple index out of range");
        }
        return self.__array[index];
        """)

    def __len__(self):
        return INT(JS("""self.__array.length"""))

    def __contains__(self, value):
        return JS('self.__array.indexOf(value)>=0')

    def __iter__(self):
        return JS("new $iter_array(self.__array)")
        JS("""
        var i = 0;
        var l = self.__array;
        return {
            'next': function() {
                if (i >= l.length) {
                    throw pyjslib.StopIteration;
                }
                return l[i++];
            },
            '__iter__': function() {
                return this;
            }
        };
        """)

    def __enumerate__(self):
        return JS("new $enumerate_array(self.__array)")

    def getArray(self):
        """
        Access the javascript Array that is used internally by this list
        """
        return self.__array

    #def __str__(self):
    #    return self.__repr__()
    #See monkey patch at the end of the tuple class definition

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        JS("""
        var s = "(";
        for (var i=0; i < self.__array.length; i++) {
            s += pyjslib.repr(self.__array[i]);
            if (i < self.__array.length - 1)
                s += ", ";
        }
        if (self.__array.length == 1)
            s += ",";
        s += ")";
        return s;
        """)

    def __add__(self, y):
        if not isinstance(y, self):
            raise TypeError("can only concatenate tuple to tuple")
        return tuple(self.__array.concat(y.__array))

    def __mul__(self, n):
        if not JS("n !== null && n.__number__ && (n.__number__ != 0x01 || isFinite(n))"):
            raise TypeError("can't multiply sequence by non-int")
        a = []
        while n:
            n -= 1
            a.extend(self.__array)
        return a

    def __rmul__(self, n):
        return self.__mul__(n)
JS("pyjslib.tuple.__str__ = pyjslib.tuple.__repr__;")
JS("pyjslib.tuple.toString = pyjslib.tuple.__str__;")


class dict:
    def __init__(self, seq=JS("[]"), **kwargs):
        self.__object = JS("{}")
        # Transform data into an array with [key,value] and add set self.__object
        # Input data can be Array(key, val), iteratable (key,val) or Object/Function
        def init(data):
            JS("""
        var item, i, n, sKey;
        //self.__object = {};

        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
        } else if (typeof data.__object == 'object') {
            data = data.__object;
            for (sKey in data) {
                self.__object[sKey] = data[sKey].slice();
            }
            return null;
        } else if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                data = data.__array;
            } else {
                var iter = data.__iter__();
                if (typeof iter.__array == 'object') {
                    data = iter.__array;
                }
                data = [];
                var item, i = 0;
                if (typeof iter.$genfunc == 'function') {
                    while (typeof (item=iter.next(true)) != 'undefined') {
                        data[i++] = item;
                    }
                } else {
                    try {
                        while (true) {
                            data[i++] = iter.next();
                        }
                    }
                    catch (e) {
                        if (e.__name__ != 'StopIteration') throw e;
                    }
                }
            }
        } else if (typeof data == 'object' || typeof data == 'function') {
            for (var key in data) {
                self.__object['$'+key] = [key, data[key]];
            }
            return null;
        } else {
            throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        }
        // Assume uniform array content...
        if ((n = data.length) == 0) {
            return null;
        }
        i = 0;
        if (data[0].constructor === Array) {
            while (i < n) {
                item = data[i++];
                key = item[0]
                sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
                self.__object[sKey] = [key, item[1]];
            }
            return null;
        }
        if (typeof data[0].__array != 'undefined') {
            while (i < n) {
                item = data[i++].__array;
                key = item[0]
                sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
                self.__object[sKey] = [key, item[1]];
            }
            return null;
        }
        i = -1;
        var key;
        while (++i < n) {
            key = data[i].__getitem__(0);
            sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
            self.__object[sKey] = [key, data[i].__getitem__(1)];
        }
        return null;
        """)
        init(seq)
        if kwargs:
            init(kwargs)

    def __hash__(self):
        raise TypeError("dict objects are unhashable")

    def __setitem__(self, key, value):
        JS("""
        if (typeof value == 'undefined') {
            throw pyjslib['ValueError']("Value for key '" + key + "' is undefined");
        }
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        self.__object[sKey] = [key, value];
        """)

    def __getitem__(self, key):
        JS("""
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        var value=self.__object[sKey];
        if (typeof value == 'undefined'){
            throw pyjslib.KeyError(key);
        }
        return value[1];
        """)

    def __hash__(self):
        raise TypeError("dict objects are unhashable")

    def __nonzero__(self):
        JS("""
        for (var i in self.__object){
            return true;
        }
        return false;
        """)

    def __cmp__(self, other):
        if not isinstance(other, dict):
            raise TypeError("dict.__cmp__(x,y) requires y to be a 'dict'")
        JS("""
        var self_sKeys = new Array(),
            other_sKeys = new Array(),
            selfLen = 0,
            otherLen = 0,
            selfObj = self.__object;
            otherObj = other.__object;
        for (sKey in selfObj) {
           self_sKeys[selfLen++] = sKey;
        }
        for (sKey in otherObj) {
           other_sKeys[otherLen++] = sKey;
        }
        if (selfLen < otherLen) {
            return -1;
        }
        if (selfLen > otherLen) {
            return 1;
        }
        self_sKeys.sort();
        other_sKeys.sort();
        var c, sKey;
        for (var idx = 0; idx < selfLen; idx++) {
            c = pyjslib.cmp(selfObj[sKey = self_sKeys[idx]][0], otherObj[other_sKeys[idx]][0]);
            if (c != 0) {
                return c;
            }
            c = pyjslib.cmp(selfObj[sKey][1], otherObj[sKey][1]);
            if (c != 0) {
                return c;
            }
        }
        return 0;""")

    def __len__(self):
        size = 0
        JS("""
        for (var i in self.__object) size++;
        """)
        return INT(size);

    #def has_key(self, key):
    #    return self.__contains__(key)
    #See monkey patch at the end of the dict class definition

    def __delitem__(self, key):
        JS("""
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        delete self.__object[sKey];
        """)

    def __contains__(self, key):
        JS("""
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        return typeof self.__object[sKey] == 'undefined' ? false : true;
        """)

    def keys(self):
        JS("""
        var keys=pyjslib.list(),
            selfObj = self.__object,
            __array = keys.__array,
            i = 0;
        for (var sKey in self.__object) {
            __array[i++] = selfObj[sKey][0];
        }
        return keys;
        """)

    @staticmethod
    def fromkeys(iterable, v = None):
        d = {}
        for i in iterable:
            d[i] = v
        return d

    def values(self):
        JS("""
        var values=pyjslib.list();
        var i = 0;
        for (var key in self.__object) {
            values.__array[i++] = self.__object[key][1];
        }
        return values;
        """)

    def items(self):
        JS("""
        var items = pyjslib.list();
        var i = 0;
        for (var key in self.__object) {
          var kv = self.__object[key];
          items.__array[i++] = pyjslib.list(kv);
          }
          return items;
        """)

    def __iter__(self):
        JS("""
        var keys = new Array();
        var i = 0;
        for (var key in self.__object) {
            keys[i++] = self.__object[key][0];
        }
        return new $iter_array(keys);
""")

    def __enumerate__(self):
        JS("""
        var keys = new Array();
        var i = 0;
        for (var key in self.__object) {
            keys[i++] = self.__object[key][0];
        }
        return new $enumerate_array(keys);
""")

    #def iterkeys(self):
    #    return self.__iter__()
    #See monkey patch at the end of the dict class definition

    def itervalues(self):
        return self.values().__iter__();

    def iteritems(self):
        return self.items().__iter__();

    def setdefault(self, key, default_value):
        JS("""
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        return typeof self.__object[sKey] == 'undefined' ? (self.__object[sKey]=[key, default_value])[1] : self.__object[sKey][1];
""")

    def get(self, key, default_value=None):
        JS("""
        var empty = true;
        for (var sKey in self.__object) {
            empty = false;
            break;
        }
        if (empty) return default_value;
        var sKey = (key===null?null:(typeof key.$H != 'undefined'?key.$H:((typeof key=='string'||key.__number__)?'$'+key:pyjslib.__hash(key))));
        return typeof self.__object[sKey] == 'undefined' ? default_value : self.__object[sKey][1];
""")

    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            for k,v in args[0].iteritems():
                self[k] = v
        if kwargs:
            for k,v in kwargs.iteritems():
                self[k] = v

    def pop(self, k, *d):
        if len(d) > 1:
            raise TypeError("pop expected at most 2 arguments, got %s" %
                            (1 + len(d)))
        try:
            res = self[k]
            del self[k]
            return res
        except KeyError:
            if d:
                return d[0]
            else:
                raise

    def popitem(self):
        for k, v in self.iteritems():
            return (k, v)
        raise KeyError('popitem(): dictionary is empty')

    def getObject(self):
        """
        Return the javascript Object which this class uses to store
        dictionary keys and values
        """
        return self.__object

    def copy(self):
        return dict(self.items())

    def clear(self):
        self.__object = JS("{}")

    #def __str__(self):
    #    return self.__repr__()
    #See monkey patch at the end of the dict class definition

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        JS("""
        var keys = new Array();
        for (var key in self.__object)
            keys.push(key);

        var s = "{";
        for (var i=0; i<keys.length; i++) {
            var v = self.__object[keys[i]];
            s += pyjslib.repr(v[0]) + ": " + pyjslib.repr(v[1]);
            if (i < keys.length-1)
                s += ", ";
        }
        s += "}";
        return s;
        """)

    def toString(self):
        return self.__repr__()

JS("pyjslib.dict.has_key = pyjslib.dict.__contains__;")
JS("pyjslib.dict.iterkeys = pyjslib.dict.__iter__;")
JS("pyjslib.dict.__str__ = pyjslib.dict.__repr__;")

# __empty_dict is used in kwargs initialization
# There must me a temporary __init__ function used to prevent infinite 
# recursion
def __empty_dict():
    JS("""
    var dict__init__ = pyjslib.dict.__init__;
    var d;
    pyjslib.dict.__init__ = function() {
        this.__object = {};
    }
    d = pyjslib.dict();
    d.__init__ = pyjslib.dict.__init__ = dict__init__;
    return d;
""")


class set(object):
    def __init__(self, data=JS("[]")):
        # Transform data into an array with [key,value] and add set 
        # self.__object
        # Input data can be Array(key, val), iteratable (key,val) or 
        # Object/Function
        if isSet(data):
            JS("""
            self.__object = {};
            var selfObj = self.__object,
                dataObj = data.__object;
            for (var sVal in dataObj) {
                selfObj[sVal] = dataObj[sVal];
            }
            return null;""")
        JS("""
        var item, i, n;
        var selfObj = self.__object = {};

        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
        } else if (typeof data.__object == 'object') {
            data = data.__object;
            for (var sKey in data) {
                selfObj[sKey] = data[sKey][0];
            }
            return null;
        } else if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                data = data.__array;
            } else {
                var iter = data.__iter__();
                if (typeof iter.__array == 'object') {
                    data = iter.__array;
                }
                data = [];
                var item, i = 0;
                if (typeof iter.$genfunc == 'function') {
                    while (typeof (item=iter.next(true)) != 'undefined') {
                        data[i++] = item;
                    }
                } else {
                    try {
                        while (true) {
                            data[i++] = iter.next();
                        }
                    }
                    catch (e) {
                        if (e.__name__ != 'StopIteration') throw e;
                    }
                }
            }
        } else if (typeof data == 'object' || typeof data == 'function') {
            for (var key in data) {
                selfObj[pyjslib.hash(key)] = key;
            }
            return null;
        } else {
            throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        }
        // Assume uniform array content...
        if ((n = data.length) == 0) {
            return null;
        }
        i = 0;
        while (i < n) {
            item = data[i++];
            selfObj[pyjslib.hash(item)] = item;
        }
        return null;
        """)

    def __cmp__(self, other):
        # We (mis)use cmp here for the missing __gt__/__ge__/...
        # if self == other : return 0
        # if self is subset of other: return -1
        # if self is superset of other: return 1
        # else return 2
        if not isSet(other):
            return 2
            #other = frozenset(other)
        JS("""
        var selfLen = 0,
            otherLen = 0,
            selfObj = self.__object,
            otherObj = other.__object,
            selfMismatch = false,
            otherMismatch = false;
        for (var sVal in selfObj) {
            if (!selfMismatch && typeof otherObj[sVal] == 'undefined') {
                selfMismatch = true;
            }
            selfLen++;
        }
        for (var sVal in otherObj) {
            if (!otherMismatch && typeof selfObj[sVal] == 'undefined') {
                otherMismatch = true;
            }
            otherLen++;
        }
        if (selfMismatch && otherMismatch) return 2;
        if (selfMismatch) return 1;
        if (otherMismatch) return -1;
        return 0;
""")

    def __contains__(self, value):
        if isSet(value) == 1: # An instance of set
            # Use frozenset hash
            JS("""
            var hashes = new Array(), obj = self.__object, i = 0;
            for (var v in obj) {
                hashes[i++] = v;
            }
            hashes.sort()
            var h = hashes.join("|");
            return typeof self.__object[h] != 'undefined';
""")
        JS("""return typeof self.__object[pyjslib.hash(value)] != 'undefined';""")

    def __hash__(self):
        raise TypeError("set objects are unhashable")

    def __iter__(self):
        JS("""
        var items = new Array();
        var i = 0;
        for (var key in self.__object) {
            items[i++] = self.__object[key];
        }
        return new $iter_array(items);
        """)

    def __len__(self):
        size=0.0
        JS("""
        for (var i in self.__object) size++;
        """)
        return INT(size)

    #def __str__(self):
    #    return self.__repr__()
    #See monkey patch at the end of the set class definition

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        JS("""
        var values = new Array();
        var i = 0,
            obj = self.__object,
            s = self.__name__ + "([";
        for (var sVal in obj) {
            values[i++] = pyjslib.repr(obj[sVal]);
        }
        s += values.join(", ");
        s += "])";
        return s;
        """)

    def __and__(self, other):
        # Return the intersection of two sets as a new set
        if not isSet(other):
            return NotImplemented
        return self.intersection(other)

    def __or__(self, other):
        # Return the union of two sets as a new set.
        if not isSet(other):
            return NotImplemented
        return self.union(other)

    def __xor__(self, other):
        # Return the symmetric difference of two sets as a new set.
        if not isSet(other):
            return NotImplemented
        return self.symmetric_difference(other)

    def  __sub__(self, other):
        # Return the difference of two sets as a new Set.
        if not isSet(other):
            return NotImplemented
        return self.difference(other)

    def add(self, value):
        JS("""self.__object[pyjslib.hash(value)] = value;""")
        return None

    def clear(self):
        JS("""self.__object = {};""")
        return None

    def copy(self):
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object;
        for (var sVal in selfObj) {
            obj[sVal] = selfObj[sVal];
        }
""")
        return new_set

    def difference(self, other):
        # Return the difference of two sets as a new set.
        # (i.e. all elements that are in this set but not the other.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
""")
        return new_set

    def difference_update(self, other):
        # Remove all elements of another set from this set.
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] != 'undefined') {
                delete selfObj[sVal];
            }
        }
""")
        return None

    def discard(self, value):
        if isSet(value) == 1:
            value = frozenset(value)
        JS("""delete self.__object[pyjslib.hash(value)];""")
        return None

    def intersection(self, other):
        # Return the intersection of two sets as a new set.
        # (i.e. all elements that are in both sets.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] != 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
""")
        return new_set

    def intersection_update(self, other):
        # Update a set with the intersection of itself and another.
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                delete selfObj[sVal];
            }
        }
""")
        return None

    def isdisjoint(self, other):
        # Return True if two sets have a null intersection.
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] != 'undefined') {
                return false;
            }
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] != 'undefined') {
                return false;
            }
        }
""")
        return True

    def issubset(self, other):
        if not isSet(other):
            other = frozenset(other)
        return JS("self.__cmp__(other) < 0")

    def issuperset(self, other):
        if not isSet(other):
            other = frozenset(other)
        return JS("(self.__cmp__(other)|1) == 1")

    def pop(self):
        JS("""
        for (var sVal in self.__object) {
            var value = self.__object[sVal];
            delete self.__object[sVal];
            return value;
        }
        """)
        raise KeyError("pop from an empty set")

    def remove(self, value):
        if isSet(value) == 1:
            val = frozenset(value)
        else:
            val = value
        JS("""
        var h;
        if (typeof self.__object[(h = pyjslib.hash(val))] == 'undefined') {
            throw pyjslib['KeyError'](value);
        }
        delete self.__object[pyjslib.hash(val)];""")

    def symmetric_difference(self, other):
        # Return the symmetric difference of two sets as a new set.
        # (i.e. all elements that are in exactly one of the sets.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                obj[sVal] = otherObj[sVal];
            }
        }
""")
        return new_set

    def symmetric_difference_update(self, other):
        # Update a set with the symmetric difference of itself and another.
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var obj = new Object(),
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                obj[sVal] = otherObj[sVal];
            }
        }
        self.__object = obj;
""")
        return None

    def union(self, other):
        # Return the union of two sets as a new set.
        # (i.e. all elements that are in either set.)
        new_set = set()
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            obj[sVal] = selfObj[sVal];
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                obj[sVal] = otherObj[sVal];
            }
        }
""")
        return new_set

    def update(self, data):
        if not isSet(data):
            data = frozenset(data)
        JS("""
        var selfObj = self.__object,
            dataObj = data.__object;
        for (var sVal in dataObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                selfObj[sVal] = dataObj[sVal];
            }
        }
        """)
        return None

JS("pyjslib['set']['__str__'] = pyjslib['set']['__repr__'];")
JS("pyjslib['set']['toString'] = pyjslib['set']['__repr__'];")

class frozenset(object):
    def __init__(self, data=JS("[]")):
        # Transform data into an array with [key,value] and add set self.__object
        # Input data can be Array(key, val), iteratable (key,val) or Object/Function
        if JS("typeof self.__object != 'undefined'"):
            return None
        if isSet(data):
            JS("""
            self.__object = {};
            var selfObj = self.__object,
                dataObj = data.__object;
            for (var sVal in dataObj) {
                selfObj[sVal] = dataObj[sVal];
            }
            return null;""")
        JS("""
        var item, i, n;
        var selfObj = self.__object = {};

        if (data === null) {
            throw pyjslib['TypeError']("'NoneType' is not iterable");
        }
        if (data.constructor === Array) {
        } else if (typeof data.__object == 'object') {
            data = data.__object;
            for (var sKey in data) {
                selfObj[sKey] = data[sKey][0];
            }
            return null;
        } else if (typeof data.__iter__ == 'function') {
            if (typeof data.__array == 'object') {
                data = data.__array;
            } else {
                var iter = data.__iter__();
                if (typeof iter.__array == 'object') {
                    data = iter.__array;
                }
                data = [];
                var item, i = 0;
                if (typeof iter.$genfunc == 'function') {
                    while (typeof (item=iter.next(true)) != 'undefined') {
                        data[i++] = item;
                    }
                } else {
                    try {
                        while (true) {
                            data[i++] = iter.next();
                        }
                    }
                    catch (e) {
                        if (e.__name__ != 'StopIteration') throw e;
                    }
                }
            }
        } else if (typeof data == 'object' || typeof data == 'function') {
            for (var key in data) {
                selfObj[pyjslib.hash(key)] = key;
            }
            return null;
        } else {
            throw pyjslib['TypeError']("'" + pyjslib['repr'](data) + "' is not iterable");
        }
        // Assume uniform array content...
        if ((n = data.length) == 0) {
            return null;
        }
        i = 0;
        while (i < n) {
            item = data[i++];
            selfObj[pyjslib.hash(item)] = item;
        }
        return null;
        """)

    def __cmp__(self, other):
        # We (mis)use cmp here for the missing __gt__/__ge__/...
        # if self == other : return 0
        # if self is subset of other: return -1
        # if self is superset of other: return 1
        # else return 2
        if not isSet(other):
            return 2
            #other = frozenset(other)
        JS("""
        var selfLen = 0,
            otherLen = 0,
            selfObj = self.__object,
            otherObj = other.__object,
            selfMismatch = false,
            otherMismatch = false;
        for (var sVal in selfObj) {
            if (!selfMismatch && typeof otherObj[sVal] == 'undefined') {
                selfMismatch = true;
            }
            selfLen++;
        }
        for (var sVal in otherObj) {
            if (!otherMismatch && typeof selfObj[sVal] == 'undefined') {
                otherMismatch = true;
            }
            otherLen++;
        }
        if (selfMismatch && otherMismatch) return 2;
        if (selfMismatch) return 1;
        if (otherMismatch) return -1;
        return 0;
""")

    def __contains__(self, value):
        if isSet(value) == 1: # An instance of set
            # Use frozenset hash
            JS("""
            var hashes = new Array(), obj = self.__object, i = 0;
            for (var v in obj) {
                hashes[i++] = v;
            }
            hashes.sort()
            var h = hashes.join("|");
            return typeof self.__object[h] != 'undefined';
""")
        JS("""return typeof self.__object[pyjslib.hash(value)] != 'undefined';""")

    def __hash__(self):
        JS("""
        var hashes = new Array(), obj = self.__object, i = 0;
        for (var v in obj) {
            hashes[i++] = v;
        }
        hashes.sort()
        return (self.$H = hashes.join("|"));
""")

    def __iter__(self):
        JS("""
        var items = new Array();
        var i = 0;
        for (var key in self.__object) {
            items[i++] = self.__object[key];
        }
        return new $iter_array(items);
        """)

    def __len__(self):
        size=0.0
        JS("""
        for (var i in self.__object) size++;
        """)
        return INT(size)

    #def __str__(self):
    #    return self.__repr__()
    #See monkey patch at the end of the set class definition

    def __repr__(self):
        if callable(self):
            return "<type '%s'>" % self.__name__
        JS("""
        var values = new Array();
        var i = 0,
            obj = self.__object,
            s = self.__name__ + "([";
        for (var sVal in obj) {
            values[i++] = pyjslib.repr(obj[sVal]);
        }
        s += values.join(", ");
        s += "])";
        return s;
        """)

    def __and__(self, other):
        # Return the intersection of two sets as a new set
        if not isSet(other):
            return NotImplemented
        return self.intersection(other)

    def __or__(self, other):
        # Return the union of two sets as a new set.
        if not isSet(other):
            return NotImplemented
        return self.union(other)

    def __xor__(self, other):
        # Return the symmetric difference of two sets as a new set.
        if not isSet(other):
            return NotImplemented
        return self.symmetric_difference(other)

    def  __sub__(self, other):
        # Return the difference of two sets as a new Set.
        if not isSet(other):
            return NotImplemented
        return self.difference(other)

    def clear(self):
        JS("""self.__object = {};""")
        return None

    def copy(self):
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object;
        for (var sVal in selfObj) {
            obj[sVal] = selfObj[sVal];
        }
""")
        return new_set

    def difference(self, other):
        # Return the difference of two sets as a new set.
        # (i.e. all elements that are in this set but not the other.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
""")
        return new_set

    def intersection(self, other):
        # Return the intersection of two sets as a new set.
        # (i.e. all elements that are in both sets.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] != 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
""")
        return new_set

    def isdisjoint(self, other):
        # Return True if two sets have a null intersection.
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] != 'undefined') {
                return false;
            }
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] != 'undefined') {
                return false;
            }
        }
""")
        return True

    def issubset(self, other):
        if not isSet(other):
            other = frozenset(other)
        return JS("self.__cmp__(other) < 0")

    def issuperset(self, other):
        if not isSet(other):
            other = frozenset(other)
        return JS("(self.__cmp__(other)|1) == 1")

    def pop(self):
        JS("""
        for (var sVal in self.__object) {
            var value = self.__object[sVal];
            delete self.__object[sVal];
            return value;
        }
        """)
        raise KeyError("pop from an empty set")

    def symmetric_difference(self, other):
        # Return the symmetric difference of two sets as a new set.
        # (i.e. all elements that are in exactly one of the sets.)
        if not isSet(other):
            other = frozenset(other)
        new_set = set()
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            if (typeof otherObj[sVal] == 'undefined') {
                obj[sVal] = selfObj[sVal];
            }
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                obj[sVal] = otherObj[sVal];
            }
        }
""")
        return new_set

    def union(self, other):
        # Return the union of two sets as a new set.
        # (i.e. all elements that are in either set.)
        new_set = set()
        if not isSet(other):
            other = frozenset(other)
        JS("""
        var obj = new_set.__object,
            selfObj = self.__object,
            otherObj = other.__object;
        for (var sVal in selfObj) {
            obj[sVal] = selfObj[sVal];
        }
        for (var sVal in otherObj) {
            if (typeof selfObj[sVal] == 'undefined') {
                obj[sVal] = otherObj[sVal];
            }
        }
""")
        return new_set

JS("pyjslib['frozenset']['__str__'] = pyjslib['frozenset']['__repr__'];")
JS("pyjslib['frozenset']['toString'] = pyjslib['frozenset']['__repr__'];")


class property(object):
    # From: http://users.rcn.com/python/download/Descriptor.htm
    # Extended with setter(), deleter() and fget.__doc_ copy
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if not doc is None or not hasattr(fget, '__doc__') :
            self.__doc__ = doc
        else:
            self.__doc__ = fget.__doc__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj)

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self


def staticmethod(func):
    JS("""
    var fnwrap = function() {
        return func.apply(null,$pyjs_array_slice.call(arguments));
    };
    fnwrap.__name__ = func.__name__;
    fnwrap.__args__ = func.__args__;
    fnwrap.__bind_type__ = 0;
    return fnwrap;
    """)

def super(type_, object_or_type = None):
    # This is a partially implementation: only super(type, object)
    if not _issubtype(object_or_type, type_):
        i = _issubtype(object_or_type, type_)
        raise TypeError("super(type, obj): obj must be an instance or subtype of type")
    JS("""
    if (typeof type_.__mro__ == 'undefined') {
        type_ = type_.__class__;
    }
    var fn = $pyjs_type('super', type_.__mro__.slice(1), {});
    fn.__new__ = fn.__mro__[1].__new__;
    fn.__init__ = fn.__mro__[1].__init__;
    if (object_or_type.__is_instance__ === false) {
        return fn;
    }
    var obj = new Object();
    function wrapper(obj, name) {
        var fnwrap = function() {
            return obj[name].apply(object_or_type,$pyjs_array_slice.call(arguments));
        };
        fnwrap.__name__ = name;
        fnwrap.__args__ = obj[name].__args__;
        fnwrap.__bind_type__ = obj[name].__bind_type__;
        return fnwrap;
    }
    for (var m in fn) {
        if (typeof fn[m] == 'function') {
            obj[m] = wrapper(fn, m);
        }
    }
    obj.__is_instance__ = object_or_type.__is_instance__;
    return obj;
    """)

# taken from mochikit: range( [start,] stop[, step] )
def xrange(start, stop = None, step = 1):
    if stop is None:
        stop = start
        start = 0
    if not JS("start !== null && start.__number__ && (start.__number__ != 0x01 || isFinite(start))"):
        raise TypeError("xrange() integer start argument expected, got %s" % start.__class__.__name__)
    if not JS("stop !== null && stop.__number__ && (stop.__number__ != 0x01 || isFinite(stop))"):
        raise TypeError("xrange() integer end argument expected, got %s" % stop.__class__.__name__)
    if not JS("step !== null && step.__number__ && (step.__number__ != 0x01 || isFinite(step))"):
        raise TypeError("xrange() integer step argument expected, got %s" % step.__class__.__name__)
    rval = nval = start
    JS("""
    var nstep = (stop-start)/step;
    nstep = nstep < 0 ? Math.ceil(nstep) : Math.floor(nstep);
    if ((stop-start) % step) {
        nstep++;
    }
    stop = start + nstep * step;
    if (nstep <= 0) nval = stop;
    var x = {
        'next': function(noStop) {
            if (nval == stop) {
                if (noStop === true) {
                    return;
                }
                throw pyjslib.StopIteration;
            }
            rval = nval;
            nval += step;
""")
    return INT(rval);
    JS("""
        },
        '$genfunc': function() {
            return this.next(true);
        },
        '__iter__': function() {
            return this;
        },
        '__reversed__': function() {
            return pyjslib['xrange'](stop-step, start-step, -step);
        },
        'toString': function() {
            var s = "xrange(";
            if (start != 0) {
                s += start + ", ";
            }
            s += stop;
            if (step != 1) {
                s += ", " + step;
            }
            return s + ")";
        },
        '__repr__': function() {
            return "'" + this.toString() + "'";
        }
    };
    x['__str__'] = x.toString;
    return x;
    """)

def range(start, stop = None, step = 1):
    if stop is None:
        stop = start
        start = 0
    i = start
    if not JS("start !== null && start.__number__ && (start.__number__ != 0x01 || isFinite(start))"):
        raise TypeError("xrange() integer start argument expected, got %s" % start.__class__.__name__)
    if not JS("stop !== null && stop.__number__ && (stop.__number__ != 0x01 || isFinite(stop))"):
        raise TypeError("xrange() integer end argument expected, got %s" % stop.__class__.__name__)
    if not JS("step !== null && step.__number__ && (step.__number__ != 0x01 || isFinite(step))"):
        raise TypeError("xrange() integer step argument expected, got %s" % step.__class__.__name__)
    items = JS("new Array()")
    JS("""
    var nstep = (stop-start)/step;
    nstep = nstep < 0 ? Math.ceil(nstep) : Math.floor(nstep);
    if ((stop-start) % step) {
        nstep++;
    }
    stop = start + nstep * step;
    if (nstep <= 0) i = stop;
    for (; i != stop; i += step)
""")
    items.push(INT(i))
    return list(items)

def slice(object, lower, upper):
    JS("""
    if (object === null) {
        return null;
    }
    if (typeof object.__getslice__ == 'function') {
        return object.__getslice__(lower, upper);
    }
    if (object.slice == 'function')
        return object.slice(lower, upper);

    return null;
    """)

def __delslice(object, lower, upper):
    JS("""
    if (typeof object.__delslice__ == 'function') {
        return object.__delslice__(lower, upper);
    }
    if (object.__getslice__ == 'function' && object.__delitem__ == 'function') {
        if (upper == null) {
            upper = pyjslib.len(object);
        }
        for (var i = lower; i < upper; i++) {
            object.__delitem__(i);
        }
        return null;
    }
    throw pyjslib.TypeError('object does not support item deletion');
    return null;
    """)

def __setslice(object, lower, upper, value):
    JS("""
    if (typeof object.__setslice__ == 'function') {
        return object.__setslice__(lower, upper, value);
    }
    throw pyjslib.TypeError('object does not support __setslice__');
    return null;
    """)

def str(text):
    JS("""
    if (pyjslib.hasattr(text,"__str__")) {
        return text.__str__();
    }
    return String(text);
    """)

def ord(x):
    if(JS("typeof x == 'string'") and len(x) is 1):
        return INT(x.charCodeAt(0));
    else:
        JS("""throw pyjslib.TypeError("ord() expected string of length 1");""")
    return None

def chr(x):
    JS("""
        return String.fromCharCode(x);
    """)

def is_basetype(x):
    JS("""
       var t = typeof(x);
       return t == 'boolean' ||
       t == 'function' ||
       t == 'number' ||
       t == 'string' ||
       t == 'undefined';
    """)

def get_pyjs_classtype(x):
    JS("""
        if (x !== null && typeof x.__is_instance__ == 'boolean') {
            var src = x.__name__;
            return src;
        }
        return null;
    """)

def repr(x):
    """ Return the string representation of 'x'.
    """
    if hasattr(x, '__repr__'):
        if callable(x):
            return x.__repr__(x)
        return x.__repr__()
    JS("""
       if (x === null)
           return "null";

       if (x === undefined)
           return "undefined";

       var t = typeof(x);

        //alert("repr typeof " + t + " : " + x);

       if (t == "boolean")
           return x.toString();

       if (t == "function")
           return "<function " + x.toString() + ">";

       if (t == "number")
           return x.toString();

       if (t == "string") {
           if (x.indexOf("'") == -1)
               return "'" + x + "'";
           if (x.indexOf('"') == -1)
               return '"' + x + '"';
           var s = x.$$replace(new RegExp('"', "g"), '\\\\"');
           return '"' + s + '"';
       }

       if (t == "undefined")
           return "undefined";

       // If we get here, x is an object.  See if it's a Pyjamas class.

       if (!pyjslib.hasattr(x, "__init__"))
           return "<" + x.toString() + ">";

       // Handle the common Pyjamas data types.

       var constructor = "UNKNOWN";

       constructor = pyjslib.get_pyjs_classtype(x);

        //alert("repr constructor: " + constructor);

       // If we get here, the class isn't one we know -> return the class name.
       // Note that we replace underscores with dots so that the name will
       // (hopefully!) look like the original Python name.

       //var s = constructor.$$replace(new RegExp('_', "g"), '.');
       return "<" + constructor + " object>";
    """)

def len(object):
    v = 0
    JS("""
    if (typeof object == 'undefined') {
        throw pyjslib['UndefinedValueError']("obj");
    }
    if (object === null) return v;
    else if (typeof object.__array != 'undefined') v = object.__array.length;
    else if (typeof object.__len__ == 'function') v = object.__len__();
    else if (typeof object.length != 'undefined') v = object.length;
    else throw pyjslib.TypeError("object has no len()");
    if (v.__number__ & 0x06) return v;
    """)
    return INT(v)

def isinstance(object_, classinfo):
    JS("""
    if (typeof object_ == 'undefined') {
        return false;
    }
    if (object_ == null) {
        if (classinfo == null) {
            return true;
        }
        return false;
    }
    switch (classinfo.__name__) {
        case 'float':
            return typeof object_ == 'number' && object_.__number__ == 0x01 && isFinite(object_);
        case 'int':
        case 'float_int':
            return object_ !== null && object_.__number__ && (object_.__number__ != 0x01 || isFinite(object_));/* XXX TODO: check rounded? */
        case 'str':
            return typeof object_ == 'string';
        case 'bool':
            return typeof object_ == 'boolean';
        case 'long':
            return object_.__number__ == 0x04;
    }
    if (typeof object_ != 'object' && typeof object_ != 'function') {
        return false;
    }
""")
    if _isinstance(classinfo, tuple):
        if _isinstance(object_, tuple):
            return True
        for ci in classinfo:
            if isinstance(object_, ci):
                return True
        return False
    else:
        return _isinstance(object_, classinfo)

def _isinstance(object_, classinfo):
    JS("""
    if (   object_.__is_instance__ !== true 
        || classinfo.__is_instance__ === null) {
        return false;
    }
    var __mro__ = object_.__mro__;
    var n = __mro__.length;
    if (classinfo.__is_instance__ === false) {
        while (--n >= 0) {
            if (object_.__mro__[n] === classinfo.prototype) return true;
        }
        return false;
    }
    while (--n >= 0) {
        if (object_.__mro__[n] === classinfo.__class__) return true;
    }
    return false;
    """)

def issubclass(class_, classinfo):
    if JS(""" typeof class_ == 'undefined' || class_ === null || class_.__is_instance__ !== false """):
        raise TypeError("arg 1 must be a class")
        
    if isinstance(classinfo, tuple):
        for ci in classinfo:
            if issubclass(class_, ci):
                return True
        return False
    else:
        if JS(""" typeof classinfo == 'undefined' || classinfo.__is_instance__ !== false """):
            raise TypeError("arg 2 must be a class or tuple of classes")
        return _issubtype(class_, classinfo)
    
def _issubtype(object_, classinfo):
    JS("""
    if (   object_.__is_instance__ === null 
        || classinfo.__is_instance__ === null) {
        return false;
    }
    var __mro__ = object_.__mro__;
    var n = __mro__.length;
    if (classinfo.__is_instance__ === false) {
        while (--n >= 0) {
            if (object_.__mro__[n] === classinfo.prototype) return true;
        }
        return false;
    }
    while (--n >= 0) {
        if (object_.__mro__[n] === classinfo.__class__) return true;
    }
    return false;
    """)

def getattr(obj, name, default_value=None):
    JS("""
    if (obj === null || typeof obj == 'undefined' || typeof obj[name] == 'undefined') {
        if (arguments.length != 3 || typeof obj == 'undefined'){
            throw pyjslib.AttributeError("'" + pyjslib.repr(obj) + "' has no attribute '" + name + "'");
        }
        return default_value;
    }
    var method = obj[name];
    if (method === null) return method;

    if (typeof method.__get__ == 'function') {
        if (obj.__is_instance__) {
            return method.__get__(obj, obj.__class__);
        }
        return method.__get__(null, obj.__class__);
    }
    if (   typeof method != 'function'
        || obj.__is_instance__ !== true) {
        return obj[name];
    }

    var fnwrap = function() {
        return method.apply(obj,$pyjs_array_slice.call(arguments));
    };
    fnwrap.__name__ = name;
    fnwrap.__args__ = obj[name].__args__;
    fnwrap.__class__ = obj.__class__;
    fnwrap.__bind_type__ = obj[name].__bind_type__;
    return fnwrap;
    """)

def _del(obj):
    JS("""
    if (typeof obj.__delete__ == 'function') {
        obj.__delete__(obj);
    } else {
        delete obj;
    }
    """)

def delattr(obj, name):
    JS("""
    if (typeof obj == 'undefined') {
        throw pyjslib['UndefinedValueError']("obj");
    }
    if (   obj !== null
        && (typeof obj == 'object' || typeof obj == 'function')
        && (typeof(obj[name]) != "undefined")&&(typeof(obj[name]) != "function") ){
        if (typeof obj[name].__delete__ == 'function') {
            obj[name].__delete__(obj);
        } else {
            delete obj[name];
        }
        return;
    }
    if (obj === null) {
        throw pyjslib.AttributeError("'NoneType' object has no attribute '"+name+"'");
    }
    if (typeof obj != 'object' && typeof obj == 'function') {
       throw pyjslib.AttributeError("'"+typeof(obj)+"' object has no attribute '"+name+"'");
    }
    throw pyjslib.AttributeError(obj.__name__+" instance has no attribute '"+ name+"'");
    """)

def setattr(obj, name, value):
    JS("""
    if (typeof obj == 'undefined') {
        throw pyjslib['UndefinedValueError']("obj");
    }
    if (typeof name != 'string') {
        throw pyjslib['TypeError']("attribute name must be string");
    }
    if (   typeof obj[name] != 'undefined'
        && obj[name] !== null
        && typeof obj[name].__set__ == 'function') {
        obj[name].__set__(obj, value);
    } else {
        obj[name] = value;
    }
    """)

def hasattr(obj, name):
    JS("""
    if (typeof obj == 'undefined') {
        throw pyjslib['UndefinedValueError']("obj");
    }
    if (typeof name != 'string') {
        throw pyjslib['TypeError']("attribute name must be string");
    }
    if (obj === null || typeof obj[name] == 'undefined') return false;
    if (typeof obj != 'object' && typeof obj != 'function') return false;

    return true;
    """)

def dir(obj):
    JS("""
    if (typeof obj == 'undefined') {
        throw pyjslib['UndefinedValueError']("obj");
    }
    var properties=pyjslib.list();
    for (property in obj) properties.append(property);
    return properties;
    """)

def filter(obj, method, sequence=None):
    # object context is LOST when a method is passed, hence object must be passed separately
    # to emulate python behaviour, should generate this code inline rather than as a function call
    items = []
    if sequence is None:
        sequence = method
        method = obj

        for item in sequence:
            if method(item):
                items.append(item)
    else:
        for item in sequence:
            if method.call(obj, item):
                items.append(item)

    return items


def map(obj, method, sequence=None):
    items = []

    if sequence is None:
        sequence = method
        method = obj

        for item in sequence:
            items.append(method(item))
    else:
        for item in sequence:
            items.append(method.call(obj, item))

    return items


def reduce(func, iterable, initializer=JS("(function(){return;})()")):
    try:
        iterable = iter(iterable)
    except:
        raise TypeError, "reduce() arg 2 must support iteration"
    emtpy = True
    for value in iterable:
        emtpy = False
        if JS("typeof initializer == 'undefined'"):
            initializer = value
        else:
            initializer = func(initializer, value)
    if empty:
        if JS("typeof initializer == 'undefined'"):
            raise TypeError, "reduce() of empty sequence with no initial value"
        return initializer
    return initializer


def zip(*iterables):
    n = len(iterables)
    if n == 0:
        return []
    lst = []
    iterables = [iter(i) for i in iterables]
    try:
        while True:
            t = []
            i = 0
            while i < n:
                t.append(iterables[i].next())
                i += 1
            lst.append(tuple(t))
    except StopIteration:
        pass
    return lst


def sorted(iterable, cmp=None, key=None, reverse=False):
    lst = list(iterable)
    lst.sort(cmp, key, reverse)
    return lst


def reversed(iterable):
    if hasattr(iterable, '__reversed__'):
        return iterable.__reversed__()
    if hasattr(iterable, '__len__') and hasattr(iterable, '__getitem__'):
        if len(iterable) == 0:
            l = []
            return l.__iter__()
        try:
            v = iterable[0]
            return _reversed(iterable)
        except:
            pass
    raise TypeError("argument to reversed() must be a sequence")

def _reversed(iterable):
    i = len(iterable)
    while i > 0:
        i -= 1
        yield iterable[i]

def enumerate(sequence):
    JS("""
    if (typeof sequence.__enumerate__ == 'function') {
        return sequence.__enumerate__();
    }
""")
    return _enumerate(sequence)

def _enumerate(sequence):
    nextIndex = 0
    for item in sequence:
        yield (nextIndex, item)
        nextIndex += 1

def iter(iterable, sentinel=None):
    if sentinel is None:
        if isIteratable(iterable):
            return iterable.__iter__()
        if hasattr(iterable, '__getitem__'):
            return _iter_getitem(iterable)
        raise TypeError("object is not iterable")
    if isFunction(iterable):
        return _iter_callable(iterable, sentinel)
    raise TypeError("iter(v, w): v must be callable")

def _iter_getitem(object):
    i = 0
    try:
        while True:
            yield object[i]
            i += 1
    except IndexError:
        pass

def _iter_callable(callable, sentinel):
    while True:
        nextval = callable()
        if nextval == sentinel:
            break
        yield nextval

def min(*sequence):
    if len(sequence) == 1:
        sequence = sequence[0]
    minValue = None
    for item in sequence:
        if minValue is None:
            minValue = item
        elif cmp(item, minValue) == -1:
            minValue = item
    return minValue


def max(*sequence):
    if len(sequence) == 1:
        sequence = sequence[0]
    maxValue = None
    for item in sequence:
        if maxValue is None:
            maxValue = item
        elif cmp(item, maxValue) == 1:
            maxValue = item
    return maxValue

def sum(iterable, start=None):
    if start is None:
        start = 0
    for i in iterable:
        start += i
    return start


next_hash_id = 0

# hash(obj) == (obj === null? null : (typeof obj.$H != 'undefined' ? obj.$H : ((typeof obj == 'string' || obj.__number__) ? '$'+obj : pyjslib.__hash(obj))))
if JS("typeof 'a'[0] == 'undefined'"):
    # IE: cannot do "abc"[idx]
    # IE has problems with setting obj.$H on certain DOM objects
    #def __hash(obj):
    JS("""pyjslib.__hash = function(obj) {
        switch (obj.constructor) {
            case String:
            case Number:
            case Date:
                return '$'+obj;
        }
        if (typeof obj.__hash__ == 'function') return obj.__hash__();
        if (typeof obj.nodeType != 'number') {
            try {
            obj.$H = ++pyjslib.next_hash_id;
            } catch (e) {
                return obj;
            }
            return pyjslib.next_hash_id;
            return obj.$H = ++pyjslib.next_hash_id;
        }
        if (typeof obj.setAttribute == 'undefined') {
            return obj;
        }
        var $H;
        if ($H = obj.getAttribute('$H')) {
            return $H;
        }
        obj.setAttribute('$H', ++pyjslib.next_hash_id);
        return pyjslib.next_hash_id;
    }
        """)

    #def hash(obj):
    JS("""pyjslib.hash = function(obj) {
        if (obj === null) return null;

        if (typeof obj.$H != 'undefined') return obj.$H;
        if (typeof obj == 'string' || obj.__number__) return '$'+obj;
        switch (obj.constructor) {
            case String:
            case Number:
            case Date:
                return '$'+obj;
        }
        if (typeof obj.__hash__ == 'function') return obj.__hash__();
        if (typeof obj.nodeType != 'number') {
            try {
            obj.$H = ++pyjslib.next_hash_id;
            } catch (e) {
                return obj;
            }
            return pyjslib.next_hash_id;
            return obj.$H = ++pyjslib.next_hash_id;
        }
        if (typeof obj.setAttribute == 'undefined') {
            return obj;
        }
        var $H;
        if ($H = obj.getAttribute('$H')) {
            return $H;
        }
        obj.setAttribute('$H', ++pyjslib.next_hash_id);
        return pyjslib.next_hash_id;
    }
        """)
else:
    #def __hash(obj):
    JS("""pyjslib.__hash = function(obj) {
        switch (obj.constructor) {
            case String:
            case Number:
            case Date:
                return '$'+obj;
        }
        if (typeof obj.__hash__ == 'function') return obj.__hash__();
        obj.$H = ++pyjslib.next_hash_id;
        return obj.$H;
    }
        """)

    #def hash(obj):
    JS("""pyjslib.hash = function(obj) {
        if (obj === null) return null;

        if (typeof obj.$H != 'undefined') return obj.$H;
        if (typeof obj == 'string' || obj.__number__) return '$'+obj;
        switch (obj.constructor) {
            case String:
            case Number:
            case Date:
                return '$'+obj;
        }
        if (typeof obj.__hash__ == 'function') return obj.__hash__();
        obj.$H = ++pyjslib.next_hash_id;
        return obj.$H;
    }
        """)


# type functions from Douglas Crockford's Remedial Javascript: http://www.crockford.com/javascript/remedial.html
def isObject(a):
    JS("""
    return (a !== null && (typeof a == 'object')) || typeof a == 'function';
    """)

def isFunction(a):
    JS("""
    return typeof a == 'function';
    """)

callable = isFunction

def isString(a):
    JS("""
    return typeof a == 'string';
    """)

def isNull(a):
    JS("""
    return typeof a == 'object' && !a;
    """)

def isArray(a):
    JS("""
    return pyjslib.isObject(a) && a.constructor === Array;
    """)

def isUndefined(a):
    JS("""
    return typeof a == 'undefined';
    """)

def isIteratable(a):
    JS("""
    if (a === null) return false;
    return typeof a.__iter__ == 'function';
    """)

def isNumber(a):
    JS("""
    return a !== null && a.__number__ && (a.__number__ != 0x01 || isFinite(a));
    """)

def isInteger(a):
    JS("""
    switch (a.__number__) {
        case 0x01:
            if (a != Math.floor(a)) break;
        case 0x02:
        case 0x04:
            return true;
    }
    return false;
""")

def isSet(a):
    JS("""
    if (a === null) return false;
    if (typeof a.__object == 'undefined') return false;
    switch (a.__mro__[a.__mro__.length-2].__md5__) {
        case pyjslib['set'].__md5__:
            return 1;
        case pyjslib['frozenset'].__md5__:
            return 2;
    }
    return false;
""")
def toJSObjects(x):
    """
       Convert the pyjs pythonic list and dict objects into javascript Object and Array
       objects, recursively.
    """
    if isArray(x):
        JS("""
        var result = [];
        for(var k=0; k < x.length; k++) {
           var v = x[k];
           var tv = pyjslib.toJSObjects(v);
           result.push(tv);
        }
        return result;
        """)
    if isObject(x):
        if x.__number__:
            return x.valueOf()
        elif isinstance(x, dict):
            JS("""
            var o = x.getObject();
            var result = {};
            for (var i in o) {
               result[o[i][0].toString()] = pyjslib.toJSObjects(o[i][1]);
            }
            return result;
            """)
        elif isinstance(x, list):
            return toJSObjects(x.__array)
        elif hasattr(x, '__class__'):
            # we do not have a special implementation for custom
            # classes, just pass it on
            return x
    if isObject(x):
        JS("""
        var result = {};
        for(var k in x) {
            var v = x[k];
            var tv = pyjslib.toJSObjects(v);
            result[k] = tv;
            }
            return result;
         """)
    if isString(x):
        return str(x)
    return x

def sprintf(strng, args):
    # See http://docs.python.org/library/stdtypes.html
    JS(r"""
    var re_dict = /([^%]*)%[(]([^)]+)[)]([#0\x20\x2B-]*)(\d+)?(\.\d+)?[hlL]?(.)((.|\n)*)/;
    var re_list = /([^%]*)%([#0\x20\x2B-]*)(\*|(\d+))?(\.\d+)?[hlL]?(.)((.|\n)*)/;
    var re_exp = /(.*)([+-])(.*)/;

    var argidx = 0;
    var nargs = 0;
    var result = [];
    var remainder = strng;

    function formatarg(flags, minlen, precision, conversion, param) {
        var subst = '';
        var numeric = true;
        var left_padding = 1;
        var padchar = ' ';
        if (minlen === null || minlen == 0 || !minlen) {
            minlen=0;
        } else {
            minlen = parseInt(minlen);
        }
        if (!precision) {
            precision = null;
        } else {
            precision = parseInt(precision.substr(1));
        }
        if (flags.indexOf('-') >= 0) {
            left_padding = 0;
        }
        switch (conversion) {
            case '%':
                numeric = false;
                subst = '%';
                break;
            case 'c':
                numeric = false;
                subst = String.fromCharCode(parseInt(param));
                break;
            case 'd':
            case 'i':
            case 'u':
                subst = '' + parseInt(param);
                break;
            case 'e':
                if (precision === null) {
                    precision = 6;
                }
                subst = re_exp.exec(String(param.toExponential(precision)));
                if (subst[3].length == 1) {
                    subst = subst[1] + subst[2] + '0' + subst[3];
                } else {
                    subst = subst[1] + subst[2] + subst[3];
                }
                break;
            case 'E':
                if (precision === null) {
                    precision = 6;
                }
                subst = re_exp.exec(String(param.toExponential(precision)).toUpperCase());
                if (subst[3].length == 1) {
                    subst = subst[1] + subst[2] + '0' + subst[3];
                } else {
                    subst = subst[1] + subst[2] + subst[3];
                }
                break;
            case 'f':
                if (precision === null) {
                    precision = 6;
                }
                subst = String(parseFloat(param).toFixed(precision));
                break;
            case 'F':
                if (precision === null) {
                    precision = 6;
                }
                subst = String(parseFloat(param).toFixed(precision)).toUpperCase();
                break;
            case 'g':
                if (precision === null && flags.indexOf('#') >= 0) {
                    precision = 6;
                }
                if (param >= 1E6 || param < 1E-5) {
                    subst = String(precision == null ? param.toExponential() : param.toExponential().toPrecision(precision));
                } else {
                    subst = String(precision == null ? parseFloat(param) : parseFloat(param).toPrecision(precision));
                }
                break;
            case 'G':
                if (precision === null && flags.indexOf('#') >= 0) {
                    precision = 6;
                }
                if (param >= 1E6 || param < 1E-5) {
                    subst = String(precision == null ? param.toExponential() : param.toExponential().toPrecision(precision)).toUpperCase();
                } else {
                    subst = String(precision == null ? parseFloat(param) : parseFloat(param).toPrecision(precision)).toUpperCase().toUpperCase();
                }
                break;
            case 'r':
                numeric = false;
                subst = pyjslib['repr'](param);
                break;
            case 's':
                numeric = false;
                subst = pyjslib['str'](param);
                break;
            case 'o':
                param = pyjslib['int'](param);
                subst = param.toString(8);
                if (subst != '0' && flags.indexOf('#') >= 0) {
                    subst = '0' + subst;
                }
                break;
            case 'x':
                param = pyjslib['int'](param);
                subst = param.toString(16);
                if (flags.indexOf('#') >= 0) {
                    if (left_padding) {
                        subst = subst.rjust(minlen - 2, '0');
                    }
                    subst = '0x' + subst;
                }
                break;
            case 'X':
                param = pyjslib['int'](param);
                subst = param.toString(16).toUpperCase();
                if (flags.indexOf('#') >= 0) {
                    if (left_padding) {
                        subst = subst.rjust(minlen - 2, '0');
                    }
                    subst = '0x' + subst;
                }
                break;
            default:
                throw pyjslib['ValueError']("unsupported format character '" + conversion + "' ("+pyjslib['hex'](conversion.charCodeAt(0))+") at index " + (strng.length - remainder.length - 1));
        }
        if (minlen && subst.length < minlen) {
            if (numeric && left_padding && flags.indexOf('0') >= 0) {
                padchar = '0';
            }
            subst = left_padding ? subst.rjust(minlen, padchar) : subst.ljust(minlen, padchar);
        }
        return subst;
    }

    function sprintf_list(strng, args) {
        var a, left, flags, precision, conversion, minlen, param,
            __array = result;
        while (remainder) {
            a = re_list.exec(remainder);
            if (a === null) {
                __array[__array.length] = remainder;
                break;
            }
            left = a[1]; flags = a[2];
            minlen = a[3]; precision = a[5]; conversion = a[6];
            remainder = a[7];
            if (typeof minlen == 'undefined') minlen = null;
            if (typeof precision == 'undefined') precision = null;
            if (typeof conversion == 'undefined') conversion = null;
            __array[__array.length] = left;
            if (minlen == '*') {
                if (argidx == nargs) {
                    throw pyjslib['TypeError']("not enough arguments for format string");
                }
                minlen = args.__getitem__(argidx++);
                switch (minlen.__number__) {
                    case 0x02:
                    case 0x04:
                        break;
                    case 0x01:
                        if (minlen == Math.floor(minlen)) {
                            break;
                        }
                    default:
                        throw pyjslib['TypeError']('* wants int');
                }
            }
            if (conversion != '%') {
                if (argidx == nargs) {
                    throw pyjslib['TypeError']("not enough arguments for format string");
                }
                param = args.__getitem__(argidx++);
            }
            __array[__array.length] = formatarg(flags, minlen, precision, conversion, param);
        }
    }

    function sprintf_dict(strng, args) {
        var a = null,
            left = null,
            flags = null,
            precision = null,
            conversion = null,
            minlen = null,
            minlen_type = null,
            key = null,
            arg = args,
            param,
            __array = result;

        argidx++;
        while (remainder) {
            a = re_dict.exec(remainder);
            if (a === null) {
                __array[__array.length] = remainder;
                break;
            }
            left = a[1]; key = a[2]; flags = a[3];
            minlen = a[4]; precision = a[5]; conversion = a[6];
            remainder = a[7];
            if (typeof minlen == 'undefined') minlen = null;
            if (typeof precision == 'undefined') precision = null;
            if (typeof conversion == 'undefined') conversion = null;
            __array[__array.length] = left;
            param = arg.__getitem__(key);
            __array[__array.length] = formatarg(flags, minlen, precision, conversion, param);
        }
    }

    var constructor = args === null ? 'NoneType' : (args.__md5__ == pyjslib.tuple.__md5__ ? 'tuple': (args.__md5__ == pyjslib.dict.__md5__ ? 'dict': 'Other'));
    if (strng.indexOf("%(") >= 0) {
        if (re_dict.exec(strng) !== null) {
            if (constructor != "dict") {
                throw pyjslib['TypeError']("format requires a mapping");
            }
            sprintf_dict(strng, args);
            return result.join("");
        }
    }
    if (constructor != "tuple") {
        args = pyjslib['tuple']([args]);
    }
    nargs = args.__array.length;
    sprintf_list(strng, args);
    if (argidx != nargs) {
        throw pyjslib['TypeError']('not all arguments converted during string formatting');
    }
    return result.join("");
""")

def debugReport(msg):
    JS("""
    alert(msg);
    """)

JS("""
var $printFunc = null;
if (   typeof $wnd.console != 'undefined'
    && typeof $wnd.console.debug == 'function') {
    $printFunc = function(s) {
        $wnd.console.debug(s);
    }
} else if (   typeof $wnd.opera != 'undefined'
           && typeof $wnd.opera.postError == 'function') {
    $printFunc = function(s) {
        $wnd.opera.postError(s);
    }
}
""")

def printFunc(objs, newline):
    JS("""
    if ($printFunc === null) return null;
    var s = "";
    for(var i=0; i < objs.length; i++) {
        if(s != "") s += " ";
        s += objs[i];
    }
    $printFunc(s);
    """)

def type(clsname, bases=None, methods=None):
    if bases is None and methods is None:
        # return type of clsname
        raise NotImplementedError("type() with single argument is not supported (use isinstance())")
    # creates a class, derived from bases, with methods and variables
    JS(" var mths = {}; ")
    if methods:
        for k in methods.keys():
            mth = methods[k]
            JS(" mths[k] = mth; ")

    JS(" var bss = null; ")
    if bases:
        JS("bss = bases.__array;")
    JS(" return $pyjs_type(clsname, bss, mths); ")

def pow(x, y, z = None):
    p = None
    JS("p = Math.pow(x, y);")
    if z is None:
        return float(p)
    return float(p % z)

def hex(x):
    JS("""
    if (typeof x == 'number') {
        if (Math.floor(x) == x) {
            return '0x' + x.toString(16);
        }
    } else {
        switch (x.__number__) {
            case 0x02:
                return '0x' + x.__v.toString(16);
            case 0x04:
                return x.__hex__();
        }
    }
""")
    raise TypeError("hex() argument can't be converted to hex")

def oct(x):
    JS("""
    if (typeof x == 'number') {
        if (Math.floor(x) == x) {
            return x == 0 ? '0': '0' + x.toString(8);
        }
    } else {
        switch (x.__number__) {
            case 0x02:
                return x.__v == 0 ? '0': '0' + x.__v.toString(8);
            case 0x04:
                return x.__oct__();
        }
    }
""")
    raise TypeError("oct() argument can't be converted to oct")

def round(x, n = 0):
    n = pow(10, n)
    r = None
    JS("r = Math.round(n*x)/n;")
    return float(r)

def divmod(x, y):
    JS("""
    if (x !== null && y !== null) {
        switch ((x.__number__ << 8) | y.__number__) {
            case 0x0101:
            case 0x0104:
            case 0x0401:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                var f = Math.floor(x / y);
                return pyjslib['tuple']([f, x - f * y]);
            case 0x0102:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                var f = Math.floor(x / y.__v);
                return pyjslib['tuple']([f, x - f * y.__v]);
            case 0x0201:
                if (y == 0) throw pyjslib['ZeroDivisionError']('float divmod()');
                var f = Math.floor(x.__v / y);
                return pyjslib['tuple']([f, x.__v - f * y]);
            case 0x0202:
                if (y.__v == 0) throw pyjslib['ZeroDivisionError']('integer division or modulo by zero');
                var f = Math.floor(x.__v / y.__v);
                return pyjslib['tuple']([new pyjslib['int'](f), new pyjslib['int'](x.__v - f * y.__v)]);
            case 0x0204:
                return y.__rdivmod__(new pyjslib['long'](x.__v));
            case 0x0402:
                return x.__divmod__(new pyjslib['long'](y.__v));
            case 0x0404:
                return x.__divmod__(y);
        }
        if (!x.__number__) {
            if (   !y.__number__
                && x.__mro__.length > y.__mro__.length
                && pyjslib['isinstance'](x, y)
                && typeof x['__divmod__'] == 'function')
                return y.__divmod__(x);
            if (typeof x['__divmod__'] == 'function') return x.__divmod__(y);
        }
        if (!y.__number__ && typeof y['__rdivmod__'] == 'function') return y.__rdivmod__(x);
    }
""")
    raise TypeError("unsupported operand type(s) for divmod(): '%r', '%r'" % (x, y))

def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True

def any(iterable):
    for element in iterable:
        if element:
            return True
    return False

# For optimized for loops: fall back for userdef iterators
wrapped_next = JS("""function (iter) {
    try {
        var res = iter.next();
    } catch (e) {
        if (e === pyjslib['StopIteration']) {
            return;
        }
        throw e;
    }
    return res;
}""")

init()

__nondynamic_modules__ = {}

def __import__(name, globals={}, locals={}, fromlist=[], level=-1):
    module = ___import___(name, None)
    if not module is None and hasattr(module, '__was_initialized__'):
        return module
    raise ImportError("No module named " + name)

import sys # needed for debug option
import dynamic # needed for ___import___
