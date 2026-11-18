#!/usr/bin/env bash
# Gera GeoMunicipio-<versão>.zip pronto para enviar ao plugins.qgis.org
set -euo pipefail
cd "$(dirname "$0")"
VERSION=$(grep '^version=' GeoMunicipio/metadata.txt | cut -d= -f2)
OUT="GeoMunicipio-${VERSION}.zip"
rm -f "$OUT"
find GeoMunicipio -name '__pycache__' -type d -prune -exec rm -rf {} +
zip -r "$OUT" GeoMunicipio -x '*.pyc' '*/.git/*' '*/.DS_Store'
echo "Gerado: $OUT"
