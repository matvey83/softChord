function i(x) {
    return x;
}


function __Foo() {
}
function Foo() {
    var instance = new __Foo();
    if(instance.__init__) instance.__init__.apply(instance, arguments);
    return instance;
}


function __Foo_initialize() {
    if(__Foo.__was_initialized__) return;
    __Foo.__was_initialized__ = true;
    pyjs_extend(__Foo, __pyjslib_Object);
    __Foo.prototype.__class__.__new__ = Foo;
}
function test_builtins() {
    var x = new pyjslib_List([]);
    var y = pyjslib_isFunction(x);
    var z = pyjslib_map(i, x);
    pyjslib_filter(callable, z);
    pyjslib_dir(x);
    if (pyjslib_hasattr(x, 'foo')) {
    var foo = pyjslib_getattr(x, 'foo');
    }
    var f = Foo();
    pyjslib_setattr(f, 'bar', 42);
    if (pyjslib_hasattr(f, 'bar')) {
    var bar = pyjslib_getattr(f, 'bar');
    }
}


    test_builtins();
__Foo_initialize();
