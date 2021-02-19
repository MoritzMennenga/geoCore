# -*- coding: utf-8 -*-
"""
    geoCore - a QGIS plugin for drawing drilling profiles
    Copyright (C) 2019 - 2021  Gerrit Bette, T-Systems on site services GmbH

    This file is part of geoCore.

    geoCore is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    geoCore is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with geoCore.  If not, see <https://www.gnu.org/licenses/>.

/*************************************************************
 Scaffolding generated by Plugin Builder:
         http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-12-23
        git sha              : $Format:%H$
 *************************************************************/
"""
import os
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QActionGroup, QMenu
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QPainter, QImage, QColor
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.PyQt.QtCore import QRectF, QEvent
from qgis.core import Qgis, QgsMessageLog

from .profileBuilder import ProfileBuilder
from .profilePainter import ProfilePainter
from .scale_dialog import ScaleDialog

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
        self._setupGeoDirectionActions()
        self._xFac = None
        self._yFac = None

    def _setupScene(self):
        """Set up a new scene"""
        self.scene = QtWidgets.QGraphicsScene()
        self.view = self.findChild(QtWidgets.QGraphicsView, "graphicsView")
        self.view.setScene(self.scene)
        self.view.viewport().installEventFilter(self)

    def _setupGeoDirectionActions(self):
        """Set up actions for geo-directions"""
        self._nsAction = QAction("North \u2794 South", self)
        self._nsAction.triggered.connect(self.drawProfilesNorthSouth)
        self._nsAction.setEnabled(True)
        self._nsAction.setCheckable(True)

        self._snAction = QAction("South \u2794 North", self)
        self._snAction.triggered.connect(self.drawProfilesSouthNorth)
        self._snAction.setEnabled(True)
        self._snAction.setCheckable(True)

        self._weAction = QAction("West \u2794 East", self)
        self._weAction.triggered.connect(self.drawProfilesWestEast)
        self._weAction.setEnabled(True)
        self._weAction.setCheckable(True)

        self._ewAction = QAction("East \u2794 West", self)
        self._ewAction.triggered.connect(self.drawProfilesEastWest)
        self._ewAction.setEnabled(True)
        self._ewAction.setCheckable(True)

    def _getActions(self):
        """Get actions that are displayed in the context menu"""
        actions = []

        scaleAction = QAction("Scale...", self)
        scaleAction.triggered.connect(self._scale)
        scaleAction.setEnabled(True)
        actions.append(scaleAction)

        exportAction = QAction("Export as...", self)
        exportAction.triggered.connect(self._exportToFile)
        exportAction.setEnabled(True)
        actions.append(exportAction)

        sep = QAction("", self)
        sep.setSeparator(True)
        actions.append(sep)

        group = QActionGroup(self)

        group.addAction(self._nsAction)
        actions.append(self._nsAction)

        group.addAction(self._snAction)
        actions.append(self._snAction)

        group.addAction(self._weAction)
        actions.append(self._weAction)

        group.addAction(self._ewAction)
        actions.append(self._ewAction)

        sepAbout = QAction("", self)
        sepAbout.setSeparator(True)
        actions.append(sepAbout)

        manualAction = QAction("Manual...", self)
        manualAction.triggered.connect(self._openManual)
        manualAction.setEnabled(True)
        actions.append(manualAction)

        aboutAction = QAction("About...", self)
        aboutAction.triggered.connect(self._aboutPlugin)
        aboutAction.setEnabled(True)
        actions.append(aboutAction)

        return actions

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
        self.drawProfilesNorthSouth()

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

    def eventFilter(self, obj, e):
        """Filter wheel event"""
        if e.type() == QEvent.Wheel:
            return True

        return super().eventFilter(obj, e)

    def _scale(self):
        """Provide scaling factor"""
        dlg = ScaleDialog(self._xFac, self._yFac, self)
        dlg.show()
        result = dlg.exec_() # Run the dialog event loop
        if result:
            self._xFac = dlg.xFac()
            self._yFac = dlg.yFac()
            if self._nsAction.isChecked():
                self.drawProfilesNorthSouth()
            elif self._snAction.isChecked():
                self.drawProfilesSouthNorth()
            elif self._weAction.isChecked():
                self.drawProfilesWestEast()
            elif self._ewAction.isChecked():
                self.drawProfilesEastWest()

    def _exportToFile(self):
        """Export drawing to file"""
        name = self._getFilename()
        if (name is None) or (len(name) == 0):
            return

        self._exportWithPainter(name)

    def _svgPaintDevice(self, name, sourceRect, targetRect):
        """Get QSvgGenerator as paint device"""
        generator = QSvgGenerator()
        generator.setDescription("This SVG was generated with the geoCore "
            "plugin of QGIS, written by T-Systems on site services GmbH")
        generator.setTitle("geoCore")
        generator.setSize(sourceRect.size().toSize())
        generator.setViewBox(targetRect)
        generator.setFileName(name)
        return generator

    def _imgPaintDevice(self, sourceRect):
        """Get QImage as paint device"""
        img = QImage(sourceRect.width(), sourceRect.height(),
            QImage.Format_ARGB32)
        img.fill(QColor("transparent"))
        return img

    def _getSourceAndTargetRect(self):
        """Returns the source and target rect for export"""
        self.scene.clearSelection()
        margin = 5
        sourceRect = self.scene.itemsBoundingRect()
        sourceRect.adjust(-margin, -margin, margin, margin)
        targetRect = QRectF(0, 0, sourceRect.width(), sourceRect.height())
        return sourceRect, targetRect

    def _exportWithPainter(self, name):
        """Export as image file"""
        try:
            sourceRect, targetRect = self._getSourceAndTargetRect()

            pd = None
            if Path(name).suffix.upper() == ".SVG":
                pd = self._svgPaintDevice(name, sourceRect, targetRect)
            else:
                pd = self._imgPaintDevice(sourceRect)

            painter = QPainter()
            painter.begin(pd)
            painter.setRenderHint(QPainter.Antialiasing)
            self.scene.render(painter, targetRect, sourceRect)
            painter.end()
            if hasattr(pd, 'save') and callable(pd.save):
                pd.save(name)
            QgsMessageLog.logMessage("exported to {}".format(name),
                level=Qgis.Info)
        except IOError:
            self.showMessage("Error", "Failed to export to {}".format(name),
                Qgis.Critical)

    def _getFilename(self):
        """Get file name via file dialog"""
        home = str(Path.home())
        name = QFileDialog.getSaveFileName(self, "Export to file", home,
            "Vector graphics (*.svg);;Images (*.png *.jpg)")

        if (name is None) or (len(name[0]) == 0):
            return None

        filename = name[0]
        suffix = Path(filename).suffix
        if len(suffix) == 0:
            if "svg" in name[1]:
                filename = filename + ".svg"
            else:
                filename = filename + ".png"

        return filename

    def drawProfilesNorthSouth(self):
        """Draw profiles in direction from north to south"""
        self._nsAction.setChecked(True)
        crit = lambda f: -f.attribute('ycoord') # north -> south
        self._drawProfiles(crit)

    def drawProfilesSouthNorth(self):
        """Draw profiles in direction from south to north"""
        self._snAction.setChecked(True)
        crit = lambda f: f.attribute('ycoord') # south -> north
        self._drawProfiles(crit)

    def drawProfilesWestEast(self):
        """Draw profiles in direction from west to east"""
        self._weAction.setChecked(True)
        crit = lambda f: f.attribute('xcoord') # west -> east
        self._drawProfiles(crit)

    def drawProfilesEastWest(self):
        """Draw profiles in direction from east to west"""
        self._ewAction.setChecked(True)
        crit = lambda f: -f.attribute('xcoord') # east -> west
        self._drawProfiles(crit)

    def _drawProfiles(self, sortCrit):
        """Draw the selected drilling profiles"""
        self.scene.clear()
        features = self._getSortedDrillingPositions(sortCrit)
        builder = ProfileBuilder(self.iface.activeLayer().name(),
            self.showMessage)
        pac = builder.getProfilesAndConnectors(features)
        painter = ProfilePainter(self.scene, self.view.width(), self.view.height())
        painter.applyScale(self._xFac, self._yFac)
        painter.paint(pac, len(pac) == 1)
        self.view.resetTransform()
        self.view.setSceneRect(self.scene.itemsBoundingRect())

    def _getSortedDrillingPositions(self, crit):
        """Sort profiles using given criterium"""
        features = self.iface.activeLayer().selectedFeatures()
        return sorted(features, key=crit)

    def _aboutPlugin(self):
        """Show the about dialog"""
        QMessageBox.about(self, "About",
            """<h1>geoCore</h1>
            <p>
            Copyright (C) 2019-2021  Gerrit Bette, T-Systems on site services GmbH<br>
            This program comes with ABSOLUTELY NO WARRANTY.
            This is free software, and you are welcome to redistribute it
            under certain conditions; see
            <a href="https://www.gnu.org/licenses/gpl-3.0-standalone.html">
            https://www.gnu.org/licenses</a> for details.
            </p>
            <p>
            Citation: G. Bette & M. Mennenga 2021:  t-systems-on-site-services-gmbh/geoCore v0.8 (Version v0.8).
            Zenodo. <a href=" http://doi.org/10.5281/zenodo.4548887"> http://doi.org/10.5281/zenodo.4548887</a>
            </p>
            <p>
            <a href="https://github.com/t-systems-on-site-services-gmbh/geoCore/blob/master/geoCore/help/usage.md">
            Manual</a>
            </p>
            """)

    def _openManual(self):
        """Open the user manual"""
        script_dir = os.path.dirname(__file__)
        rel_path = "help/usage.html"
        abs_file_path = os.path.join(script_dir, rel_path)
        os.system("start " + abs_file_path)

    def showMessage(self, title, message, level):
        """Display a message in the main window's messageBar"""
        self.iface.messageBar().pushMessage(title, message, level)
