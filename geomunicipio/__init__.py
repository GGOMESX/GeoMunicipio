# -*- coding: utf-8 -*-
"""GeoMunicípio - localize municípios brasileiros no QGIS."""


def classFactory(iface):  # noqa: N802 (nome exigido pelo QGIS)
    from .plugin import GeoMunicipioPlugin
    return GeoMunicipioPlugin(iface)
