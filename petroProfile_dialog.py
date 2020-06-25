# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PetroProfileDialog
                                 A QGIS plugin
 Constructs a graphical representation of drilling profiles
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-12-23
        git sha              : $Format:%H$
        copyright            : (C) 2019 by T-Systems on site service GmbH
        email                : gerrit.bette@t-systems.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QMenu, QFileDialog
from qgis.PyQt.QtGui import QPainter, QImage, QColor
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.PyQt.QtCore import QRectF, QEvent
from qgis.core import Qgis, QgsMessageLog

from .profileBuilder import ProfileBuilder
from .profilePainter import ProfilePainter

# This loads your .ui file so that PyQt can populate your plugin
# with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'petroProfile_dialog_base.ui'))


class PetroProfileDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog to show the petrographic drilling profiles"""

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(PetroProfileDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self._setupScene()

    def _setupScene(self):
        """Setup a new scene"""
        self.scene = QtWidgets.QGraphicsScene()
        self.view = self.findChild(QtWidgets.QGraphicsView, "graphicsView")
        self.view.setScene(self.scene)
        self.view.installEventFilter(self)

    def _getActions(self):
        """Get actions that are displayed in the context menu"""
        exportAction = QAction("Export as...", self)
        exportAction.triggered.connect(self._exportToFile)
        exportAction.setEnabled(True)
        return [exportAction]

    def contextMenuEvent(self, e):
        """Show context menu"""
        m = QMenu()
        for a in self._getActions():
            m.addAction(a)
        m.exec(e.globalPos())
        e.setAccepted(True)

    def showEvent(self, e):
        """Override showEvent"""
        super().showEvent(e)
        self.drawProfiles()

    def wheelEvent(self, e):
        """Zoom in/out"""
        delta = e.angleDelta()
        if delta.isNull():
            return        
        s =  1.0
        if delta.y() > 0:
            s = 1.15
        else:
            s = 0.85 
        self.view.scale(s, s)

    def mousePressEvent(self, e):
        QgsMessageLog.logMessage("button pressed {}".format(e.button()), level=Qgis.Info)

    def eventFilter(self, obj, e):
        QgsMessageLog.logMessage("filter {}".format(e.type()), level=Qgis.Info)
        if e.type() == QEvent.Wheel:
            return True
        else:
            return super().eventFilter(obj, e)

    def _exportToFile(self):
        """Export drawing to file"""
        name = self._getFilename()
        if (name is None) or (len(name) == 0):
            return
        
        suffix = Path(name).suffix
        if len(suffix) == 0:
            return
        if suffix.upper() == ".svg":
            self._exportAsSvg(name)
        else:
            self._exportAsImg(name)

    def _exportAsSvg(self, name):
        #generator = QSvgGenerator()
        #generator.setFileName("C:\\temp\\t.svg")
        #generator.setDescription("This SVG was generated with the petroProfile plugin of QGis, written by T-Systems on site services GmbH")
        #generator.setTitle("petroProfile")        
        #generator.setViewBox(self.scene.sceneRect())
        pass

    def _exportAsImg(self, name):
        """Export as image file"""
        try:
            self.scene.clearSelection()
            size = self.scene.sceneRect().size().toSize()
            margin = 5

            img = QImage(size.width() + margin, size.height() + margin, QImage.Format_ARGB32)
            img.fill(QColor("transparent"))

            painter = QPainter()
            painter.begin(img)
            painter.setRenderHint(QPainter.Antialiasing)
            self.scene.render(painter, QRectF(img.rect()))
            painter.end()
            img.save(name)
            QgsMessageLog.logMessage("exported to {}".format(name), level=Qgis.Info)
        except:
            self.showMessage("Error", "Failed to export to {}".format(name), Qgis.Critical)

    def _getFilename(self):
        """Get file name via file dialog"""
        home = str(Path.home())
        name = QFileDialog.getSaveFileName(self, "Export to file", home, "Images (*.png *.jpg);;Vector graphics (*.svg)")
        QgsMessageLog.logMessage("name {}".format(name), level=Qgis.Info)
        return name[0]

    def drawProfiles(self):
        """Draw the selected drilling profiles"""
        self.scene.clear()
        features = self.iface.activeLayer().selectedFeatures()
        builder = ProfileBuilder(self.showMessage)
        pac = builder.getProfilesAndConnectors(features)
        painter = ProfilePainter(self.scene)
        painter.paint(pac, len(pac) == 1)
        self.scene.setSceneRect(self.scene.itemsBoundingRect())        

    def showMessage(self, title, message, level):
        """Display a message in the main window's messageBar"""
        self.iface.messageBar().pushMessage(title, message, level)
