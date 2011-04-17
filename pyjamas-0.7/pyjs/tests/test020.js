pyjs_extend(__DayCheckBox, __ui_CheckBox);
__DayCheckBox.prototype.__class__ = "DayCheckBox";
function DayCheckBox(caption, day) {
    return new __DayCheckBox(caption, day);
}
function __DayCheckBox(caption, day) {
    __ui_CheckBox.call(this, caption);
    this.day = day;
}
