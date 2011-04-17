__SchoolCalendarWidget.prototype.__class__ = "SchoolCalendarWidget";
function SchoolCalendarWidget() {
    return new __SchoolCalendarWidget();
}
function __SchoolCalendarWidget() {
}
__SchoolCalendarWidget.prototype.getDayIncluded = function(day) {
    return this.daysFilter.__getitem__(day);
};
