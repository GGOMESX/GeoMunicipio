# -*- coding: utf-8 -*-
"""Classe principal do plugin GeoMunicípio."""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .core import GeoMunicipioService
from .dock import GeoMunicipioDock
from .locator import GeoMunicipioLocatorFilter

PLUGIN_DIR = os.path.dirname(__file__)
MENU = "&GeoMunicípio"


class GeoMunicipioPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.service = None
        self.dock = None
        self.action = None
        self.locator_filter = None

    def initGui(self):  # noqa: N802
        self.service = GeoMunicipioService(self.iface)

        self.dock = GeoMunicipioDock(self.service, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()

        icon = QIcon(os.path.join(PLUGIN_DIR, "icon.svg"))
        self.action = QAction(icon, "GeoMunicípio", self.iface.mainWindow())
        self.action.setToolTip("Localizar município (GeoMunicípio)")
        self.action.setCheckable(True)
        self.action.toggled.connect(self._toggle_dock)
        self.dock.visibilityChanged.connect(self.action.setChecked)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(MENU, self.action)

        self.locator_filter = GeoMunicipioLocatorFilter(self.service)
        self.iface.registerLocatorFilter(self.locator_filter)

        self.service.load()

    def _toggle_dock(self, checked):
        self.dock.setVisible(checked)
        if checked:
            self.dock.raise_()
            self.dock.focus_search()

    def unload(self):
        if self.locator_filter is not None:
            self.iface.deregisterLocatorFilter(self.locator_filter)
            self.locator_filter = None
        if self.service is not None:
            self.service.cancel()
        if self.action is not None:
            self.iface.removePluginWebMenu(MENU, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        self.service = None
