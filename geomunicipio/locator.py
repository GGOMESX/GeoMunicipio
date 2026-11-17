# -*- coding: utf-8 -*-
"""Integração com a barra Localizador do QGIS (Ctrl+K), prefixo "mun"."""

from qgis.core import QgsLocatorFilter, QgsLocatorResult


class GeoMunicipioLocatorFilter(QgsLocatorFilter):

    def __init__(self, service):
        super().__init__()
        self.service = service

    def clone(self):
        return GeoMunicipioLocatorFilter(self.service)

    def name(self):
        return "geomunicipio"

    def displayName(self):  # noqa: N802
        return self.tr("Municípios do Brasil (GeoMunicípio)")

    def prefix(self):
        return "mun"

    def priority(self):
        return QgsLocatorFilter.Priority.Medium

    def fetchResults(self, string, context, feedback):  # noqa: N802
        # Roda em thread separada: só lê o índice em memória, sem tocar na GUI.
        if len(string.strip()) < 2:
            return
        for mun in self.service.index.search(string, limit=30):
            if feedback.isCanceled():
                return
            result = QgsLocatorResult()
            result.filter = self
            result.displayString = "{} ({})".format(mun["nome"], mun["uf"])
            result.description = "IBGE {}".format(mun["codigo"])
            self.resultFetched.emit(result)

    def triggerResult(self, result):  # noqa: N802
        code = result.description.split()[-1]
        self.service.locate(code)
