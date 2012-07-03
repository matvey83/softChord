# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'softchord_chord_dialog.ui'
#
# Created: Tue Jul 03 00:18:17 2012
#      by: PyQt4 UI code generator 4.7
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(470, 149)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.marker_ef = QtGui.QLineEdit(Dialog)
        self.marker_ef.setMinimumSize(QtCore.QSize(30, 0))
        self.marker_ef.setMaximumSize(QtCore.QSize(80, 16777215))
        self.marker_ef.setObjectName("marker_ef")
        self.horizontalLayout.addWidget(self.marker_ef)
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.note_menu = QtGui.QComboBox(Dialog)
        self.note_menu.setMinimumSize(QtCore.QSize(90, 0))
        self.note_menu.setObjectName("note_menu")
        self.horizontalLayout.addWidget(self.note_menu)
        self.chord_type_menu = QtGui.QComboBox(Dialog)
        self.chord_type_menu.setObjectName("chord_type_menu")
        self.horizontalLayout.addWidget(self.chord_type_menu)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.bass_menu = QtGui.QComboBox(Dialog)
        self.bass_menu.setMinimumSize(QtCore.QSize(90, 0))
        self.bass_menu.setObjectName("bass_menu")
        self.horizontalLayout.addWidget(self.bass_menu)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.in_parentheses_box = QtGui.QCheckBox(Dialog)
        self.in_parentheses_box.setObjectName("in_parentheses_box")
        self.verticalLayout.addWidget(self.in_parentheses_box)
        spacerItem1 = QtGui.QSpacerItem(20, 50, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.note_menu, self.chord_type_menu)
        Dialog.setTabOrder(self.chord_type_menu, self.bass_menu)
        Dialog.setTabOrder(self.bass_menu, self.in_parentheses_box)
        Dialog.setTabOrder(self.in_parentheses_box, self.marker_ef)
        Dialog.setTabOrder(self.marker_ef, self.buttonBox)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Chord Selector", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Chord for selected letter:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", ":", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "/", None, QtGui.QApplication.UnicodeUTF8))
        self.in_parentheses_box.setText(QtGui.QApplication.translate("Dialog", "In parentheses", None, QtGui.QApplication.UnicodeUTF8))

