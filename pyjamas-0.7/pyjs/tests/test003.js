__ui_UIObject.prototype.__class__ = "ui_UIObject";
function ui_UIObject() {
    return new __ui_UIObject();
}
function __ui_UIObject() {
}
pyjs_extend(__ui_Widget, __ui_UIObject);
__ui_Widget.prototype.__class__ = "ui_Widget";
function ui_Widget() {
    return new __ui_Widget();
}
function __ui_Widget() {
    __ui_UIObject.call(this);
}
__ui_Widget.prototype.setParent = function(parent) {
    this.parent = parent;
};
