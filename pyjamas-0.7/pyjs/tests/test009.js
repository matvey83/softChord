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
pyjs_extend(__ui_Panel, __ui_Widget);
__ui_Panel.prototype.__class__ = "ui_Panel";
function ui_Panel() {
    return new __ui_Panel();
}
function __ui_Panel() {
    __ui_Widget.call(this);
}
pyjs_extend(__ui_ComplexPanel, __ui_Panel);
__ui_ComplexPanel.prototype.__class__ = "ui_ComplexPanel";
function ui_ComplexPanel() {
    return new __ui_ComplexPanel();
}
function __ui_ComplexPanel() {
    this.children = new pyjslib_List([]);
}
__ui_ComplexPanel.prototype.add = function(widget) {
    this.children.append(widget);
    widget.setParent(this);
    return true;
};
pyjs_extend(__ui_AbsolutePanel, __ui_ComplexPanel);
__ui_AbsolutePanel.prototype.__class__ = "ui_AbsolutePanel";
function ui_AbsolutePanel() {
    return new __ui_AbsolutePanel();
}
function __ui_AbsolutePanel() {
    __ui_ComplexPanel.call(this);
    this.setElement(DOM_createDiv());
    DOM_setStyleAttribute(this.getElement(), "overflow", "hidden");
}
__ui_AbsolutePanel.prototype.add = function(widget) {
    __ui_ComplexPanel.prototype.add.call(this, widget);
    DOM_appendChild(this.getElement(), widget.getElement());
    return true;
};
pyjs_extend(__ui_RootPanel, __ui_AbsolutePanel);
__ui_RootPanel.prototype.__class__ = "ui_RootPanel";
function ui_RootPanel() {
    return new __ui_RootPanel();
}
function __ui_RootPanel() {
    __ui_AbsolutePanel.call(this);
    var element = this.getBodyElement();
    this.setElement(element);
}
__ui_RootPanel.prototype.getBodyElement = function() {
    return $doc.body;
};
