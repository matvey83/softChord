pyjs_extend(__Bar, __foo_Foo);
__Bar.prototype.__class__ = "Bar";
function Bar() {
    return new __Bar();
}
function __Bar() {
    __foo_Foo.call(this);
}
