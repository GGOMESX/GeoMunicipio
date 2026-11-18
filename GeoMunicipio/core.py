# -*- coding: utf-8 -*-
"""Serviço central: baixa a lista/malhas do IBGE e localiza municípios no mapa."""

import os

from qgis.PyQt.QtCore import QObject, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFields,
    QgsGeometry,
    QgsJsonUtils,
    QgsNetworkAccessManager,
    QgsProject,
    QgsSettings,
    QgsVectorLayer,
)

from . import ibge

SETTINGS_PREFIX = "geomunicipio/"
LAYER_PROPERTY = "geomunicipio/results_layer"


def setting(key, default=None, type_=str):
    return QgsSettings().value(SETTINGS_PREFIX + key, default, type=type_)


def set_setting(key, value):
    QgsSettings().setValue(SETTINGS_PREFIX + key, value)


class GeoMunicipioService(QObject):
    """Compartilhado entre o painel e o filtro da barra Localizador."""

    listChanged = pyqtSignal()
    status = pyqtSignal(str)
    busy = pyqtSignal(bool)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.index = ibge.MunicipioIndex()
        self.cache_path = os.path.join(
            QgsApplication.qgisSettingsDirPath(), "geomunicipio", "municipios.json")
        self._replies = set()
        self._list_reply = None

    # ------------------------------------------------------------- rede

    def _get(self, url, callback):
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json")
        reply = QgsNetworkAccessManager.instance().get(request)
        self._replies.add(reply)

        def done():
            self._replies.discard(reply)
            error = None
            if reply.error() != QNetworkReply.NetworkError.NoError:
                error = reply.errorString()
            data = bytes(reply.readAll())
            reply.deleteLater()
            callback(data, error)

        reply.finished.connect(done)
        return reply

    # ---------------------------------------------------- lista de municípios

    def load(self):
        """Carrega o cache local; baixa do IBGE se não houver ou estiver velho."""
        items, age = ibge.load_cache(self.cache_path)
        if items:
            self.index.set_items(items)
            self.listChanged.emit()
            self.status.emit(self.tr("{} municípios carregados.").format(len(items)))
        if not items or age > ibge.CACHE_MAX_AGE:
            self.refresh_list()

    def refresh_list(self):
        if self._list_reply is not None:
            return
        self.busy.emit(True)
        self.status.emit(self.tr("Baixando lista de municípios do IBGE…"))
        self._list_reply = self._get(ibge.LIST_URL, self._on_list)

    def _on_list(self, data, error):
        self._list_reply = None
        self.busy.emit(False)
        if error:
            msg = self.tr("Não foi possível baixar a lista do IBGE: {}").format(error)
            self.status.emit(msg)
            if not len(self.index):
                self.iface.messageBar().pushMessage("GeoMunicípio", msg, Qgis.MessageLevel.Warning, 8)
            return
        try:
            items = ibge.parse_municipios(data)
        except (ValueError, TypeError, KeyError) as exc:
            self.status.emit(self.tr("Resposta inesperada do IBGE: {}").format(exc))
            return
        if not items:
            self.status.emit(self.tr("O IBGE retornou uma lista vazia."))
            return
        self.index.set_items(items)
        try:
            ibge.save_cache(self.cache_path, items)
        except OSError:
            pass  # sem cache, mas segue funcionando
        self.listChanged.emit()
        self.status.emit(self.tr("{} municípios carregados.").format(len(items)))

    # ------------------------------------------------------------ localizar

    def locate(self, code, add_to_layer=None):
        mun = self.index.get(code)
        if mun is None:
            self.status.emit(self.tr("Código IBGE desconhecido: {}").format(code))
            return
        if add_to_layer is None:
            add_to_layer = setting("add_to_layer", True, bool)
        quality = setting("quality", "intermediaria")
        if quality not in ibge.QUALITIES:
            quality = "intermediaria"

        label = "{} ({})".format(mun["nome"], mun["uf"])
        self.busy.emit(True)
        self.status.emit(self.tr("Buscando limite de {}…").format(label))
        url = ibge.MESH_URL.format(code=mun["codigo"], quality=quality)
        self._get(url, lambda data, err: self._on_mesh(mun, add_to_layer, data, err))

    def _on_mesh(self, mun, add_to_layer, data, error):
        self.busy.emit(False)
        label = "{} ({})".format(mun["nome"], mun["uf"])
        if error:
            msg = self.tr("Falha ao obter o limite de {}: {}").format(label, error)
            self.status.emit(msg)
            self.iface.messageBar().pushMessage("GeoMunicípio", msg, Qgis.MessageLevel.Warning, 8)
            return

        features = QgsJsonUtils.stringToFeatureList(data.decode("utf-8"), QgsFields())
        geoms = [f.geometry() for f in features if f.hasGeometry()]
        if not geoms:
            self.status.emit(self.tr("O IBGE não retornou geometria para {}.").format(label))
            return
        geom = geoms[0] if len(geoms) == 1 else QgsGeometry.unaryUnion(geoms)
        geom.convertToMultiType()

        src_crs = QgsCoordinateReferenceSystem(ibge.MESH_CRS)
        self._zoom_and_flash(geom, src_crs)
        if add_to_layer:
            self._add_to_layer(mun, geom)
        self.status.emit(self.tr("{} — código IBGE {}").format(label, mun["codigo"]))

    def _zoom_and_flash(self, geom, src_crs):
        canvas = self.iface.mapCanvas()
        dst_crs = canvas.mapSettings().destinationCrs()
        xform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        rect = xform.transformBoundingBox(geom.boundingBox())
        rect.scale(1.15)
        canvas.setExtent(rect)
        canvas.refresh()
        canvas.flashGeometries([geom], src_crs)

    # ------------------------------------------------------ camada de resultados

    def _results_layer(self):
        project = QgsProject.instance()
        for layer in project.mapLayers().values():
            if layer.customProperty(LAYER_PROPERTY):
                return layer
        uri = ("MultiPolygon?crs={}&field=codigo_ibge:string(7)"
               "&field=nome:string(100)&field=uf:string(2)").format(ibge.MESH_CRS)
        layer = QgsVectorLayer(uri, self.tr("Municípios (GeoMunicípio)"), "memory")
        layer.setCustomProperty(LAYER_PROPERTY, True)
        symbol = layer.renderer().symbol()
        symbol.setColor(QColor(21, 101, 192, 40))
        if symbol.symbolLayerCount():
            symbol.symbolLayer(0).setStrokeColor(QColor(13, 60, 122))
            symbol.symbolLayer(0).setStrokeWidth(0.6)
        project.addMapLayer(layer)
        return layer

    def _add_to_layer(self, mun, geom):
        layer = self._results_layer()
        # Evita duplicar o mesmo município
        for feat in layer.getFeatures():
            if feat["codigo_ibge"] == mun["codigo"]:
                return
        feat = QgsFeature(layer.fields())
        feat.setGeometry(geom)
        feat.setAttributes([mun["codigo"], mun["nome"], mun["uf"]])
        layer.dataProvider().addFeatures([feat])
        layer.updateExtents()
        layer.triggerRepaint()

    def cancel(self):
        for reply in list(self._replies):
            reply.abort()
