"""Module containing the class ProfileBox"""

#from qgis.PyQt import QtWidgets
from qgis.PyQt.QtGui import QBrush, QColor, QPen
from qgis.core import Qgis, QgsMessageLog

class ProfileBox:
    """ProfileBox represents one layer of a petrographic drilling profile.
    This class contains all relevant data for drawing"""

    def __init__(self, layer):
        """Initialize the box"""
        self.layer = layer
        self.group = self.layer
        self.y = 0.0
        self.width = 0.0
        self.height = 0.0
        self.info = ''
        self.color = ''
        self.texture = ''
        self.isFirst = layer == 1
        self.isLast = False

    def paint(self, scene, xpos):
        """Paint box onto scene"""
        pen, brush = self._getPenAndBrush()
        # convert dimensions from cm to mm
        x = xpos * 10
        y = self.y * -10 # direction of y-axis is top down, point (0,0) is in the upper left
        w = self.width * 10
        h = self.height * 10
        scene.addRect(x, y, w, h, pen, brush)

    def _getPenAndBrush(self):
        """Get the pen and brush"""
        col = QColor(self.color)
        pen = QPen()
        brush = QBrush(col)
        return pen, brush