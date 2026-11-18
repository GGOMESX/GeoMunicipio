# -*- coding: utf-8 -*-
"""Painel (dock) de busca do GeoMunicípio."""

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qgis.gui import QgsFilterLineEdit

from . import ibge
from .core import set_setting, setting

CODE_ROLE = Qt.ItemDataRole.UserRole


class GeoMunicipioDock(QDockWidget):

    def __init__(self, service, parent=None):
        super().__init__("GeoMunicípio", parent)
        self.setObjectName("GeoMunicipioDock")
        self.service = service

        body = QWidget(self)
        layout = QVBoxLayout(body)

        row = QHBoxLayout()
        self.search = QgsFilterLineEdit(body)
        self.search.setShowSearchIcon(True)
        self.search.setPlaceholderText(self.tr("Nome ou código IBGE (ex.: sao jose sc)"))
        row.addWidget(self.search, 1)
        self.uf = QComboBox(body)
        self.uf.addItem(self.tr("Todas UF"), "")
        for uf in ibge.UFS:
            self.uf.addItem(uf, uf)
        row.addWidget(self.uf)
        layout.addLayout(row)

        self.results = QListWidget(body)
        self.results.setAlternatingRowColors(True)
        layout.addWidget(self.results, 1)

        self.add_layer = QCheckBox(self.tr("Adicionar limite à camada de resultados"), body)
        layout.addWidget(self.add_layer)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Detalhe do limite:"), body))
        self.quality = QComboBox(body)
        for value, text in (("minima", self.tr("Mínimo (rápido)")),
                            ("intermediaria", self.tr("Intermediário")),
                            ("maxima", self.tr("Máximo (detalhado)"))):
            self.quality.addItem(text, value)
        row.addWidget(self.quality, 1)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.locate_btn = QPushButton(self.tr("Localizar"), body)
        self.locate_btn.setDefault(True)
        row.addWidget(self.locate_btn, 1)
        self.refresh_btn = QPushButton(self.tr("Atualizar lista"), body)
        self.refresh_btn.setToolTip(self.tr("Baixar novamente a lista de municípios do IBGE"))
        row.addWidget(self.refresh_btn)
        layout.addLayout(row)

        self.status = QLabel(body)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.setWidget(body)

        # Restaura preferências
        self.add_layer.setChecked(setting("add_to_layer", True, bool))
        self.uf.setCurrentIndex(max(0, self.uf.findData(setting("uf", ""))))
        self.quality.setCurrentIndex(max(0, self.quality.findData(setting("quality", "intermediaria"))))

        # Debounce para não filtrar a cada tecla em máquinas lentas
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self.update_results)

        self.search.textChanged.connect(lambda _: self._timer.start())
        self.search.returnPressed.connect(self.locate_current)
        self.uf.currentIndexChanged.connect(self._on_uf)
        self.quality.currentIndexChanged.connect(
            lambda _: set_setting("quality", self.quality.currentData()))
        self.add_layer.toggled.connect(lambda v: set_setting("add_to_layer", v))
        self.results.itemActivated.connect(lambda item: self.locate_item(item))
        self.locate_btn.clicked.connect(self.locate_current)
        self.refresh_btn.clicked.connect(service.refresh_list)

        service.listChanged.connect(self.update_results)
        service.status.connect(self.status.setText)
        service.busy.connect(self._on_busy)

    def _on_uf(self, _):
        set_setting("uf", self.uf.currentData())
        self.update_results()

    def _on_busy(self, busy):
        self.locate_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)

    def update_results(self):
        self.results.clear()
        hits = self.service.index.search(self.search.text(), self.uf.currentData())
        for mun in hits:
            item = QListWidgetItem("{}  —  {}".format(mun["nome"], mun["uf"]))
            item.setData(CODE_ROLE, mun["codigo"])
            item.setToolTip(self.tr("Código IBGE: {}").format(mun["codigo"]))
            self.results.addItem(item)
        if hits:
            self.results.setCurrentRow(0)

    def locate_item(self, item):
        if item is not None:
            self.service.locate(item.data(CODE_ROLE), self.add_layer.isChecked())

    def locate_current(self):
        item = self.results.currentItem()
        if item is None and self.results.count():
            item = self.results.item(0)
        self.locate_item(item)

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()
