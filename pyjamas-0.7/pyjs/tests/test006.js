__ui_UIObject.prototype.__class__ = "ui_UIObject";
function ui_UIObject() {
    return new __ui_UIObject();
}
function __ui_UIObject() {
}
__ui_UIObject.prototype.getElement = function() {
    return this.element;
};
__ui_UIObject.prototype.setElement = function(element) {
    this.element = element;
};
__ui_UIObject.prototype.setStyleName = function(style) {
    DOM_setAttribute(this.element, "className", style);
};
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
pyjs_extend(__ui_FocusWidget, __ui_Widget);
__ui_FocusWidget.prototype.__class__ = "ui_FocusWidget";
function ui_FocusWidget(element) {
    return new __ui_FocusWidget(element);
}
function __ui_FocusWidget(element) {
    this.setElement(element);
}
pyjs_extend(__ui_ButtonBase, __ui_FocusWidget);
__ui_ButtonBase.prototype.__class__ = "ui_ButtonBase";
function ui_ButtonBase(element) {
    return new __ui_ButtonBase(element);
}
function __ui_ButtonBase(element) {
    __ui_FocusWidget.call(this, element);
}
__ui_ButtonBase.prototype.setHTML = function(html) {
    DOM_setInnerHTML(this.getElement(), html);
};
pyjs_extend(__ui_Button, __ui_ButtonBase);
__ui_Button.prototype.__class__ = "ui_Button";
function ui_Button(html) {
    return new __ui_Button(html);
}
function __ui_Button(html) {
    if (typeof html == 'undefined') html=null;
    __ui_ButtonBase.call(this, DOM_createButton());
    this.setStyleName("gwt-Button");
    if (html) {
    this.setHTML(html);
    }
}
