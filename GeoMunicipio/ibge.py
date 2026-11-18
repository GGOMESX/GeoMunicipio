# -*- coding: utf-8 -*-
"""Acesso às APIs públicas do IBGE e índice de busca de municípios.

Este módulo não depende de Qt para a parte de busca (MunicipioIndex),
o que permite testá-la fora do QGIS.
"""

import json
import os
import re
import time
import unicodedata

LIST_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    "?view=nivelado"
)
MESH_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}"
    "?formato=application/vnd.geo%2Bjson&qualidade={quality}"
)
MESH_CRS = "EPSG:4674"  # SIRGAS 2000, sistema usado pelas malhas do IBGE
QUALITIES = ("minima", "intermediaria", "maxima")
CACHE_MAX_AGE = 30 * 24 * 3600  # 30 dias

UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
)


def normalize(text):
    """Minúsculas, sem acentos, pontuação vira espaço: "Pau D'Arco" -> "pau d arco"."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def _dig(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def parse_municipios(data):
    """Converte a resposta da API de localidades em lista de dicts
    {"codigo", "nome", "uf"}. Aceita o formato "nivelado" e o aninhado."""
    items = json.loads(data)
    out = []
    for it in items:
        if "municipio-id" in it:
            code, name, uf = it["municipio-id"], it["municipio-nome"], it.get("UF-sigla")
        else:
            code, name = it.get("id"), it.get("nome")
            # Alguns municípios novos vêm com "microrregiao" nulo; por isso
            # tentamos também a hierarquia de regiões imediatas.
            uf = (_dig(it, "microrregiao", "mesorregiao", "UF", "sigla")
                  or _dig(it, "regiao-imediata", "regiao-intermediaria", "UF", "sigla"))
        if code and name:
            out.append({"codigo": str(code), "nome": name, "uf": uf or ""})
    out.sort(key=lambda m: (normalize(m["nome"]), m["uf"]))
    return out


class MunicipioIndex:
    """Índice em memória (~5.570 itens) com busca sem acento."""

    def __init__(self, items=None):
        self.set_items(items or [])

    def set_items(self, items):
        items = list(items)
        # Atribuição única: o filtro do Localizador lê o índice em outra thread.
        self._data = (
            items,
            [normalize(m["nome"]) for m in items],
            {m["codigo"]: m for m in items},
        )

    @property
    def items(self):
        return self._data[0]

    def __len__(self):
        return len(self._data[0])

    def get(self, code):
        return self._data[2].get(str(code))

    def search(self, query, uf=None, limit=200):
        """Retorna municípios ordenados por relevância:
        nome exato > começa com > alguma palavra começa com > contém.

        Aceita "nome UF", "nome - UF" ou "nome/UF" para restringir pelo estado.
        """
        items, norms, _ = self._data
        query = (query or "").strip()
        uf = (uf or "").upper() or None

        # Busca por código IBGE (7 dígitos ou prefixo numérico)
        if query.isdigit():
            hits = [m for m in items
                    if m["codigo"].startswith(query) and (not uf or m["uf"] == uf)]
            return hits[:limit]

        q = normalize(query)
        if not uf:
            match = re.match(r"^(.+?)[\s\-/,]+([a-z]{2})$", q)
            if match and match.group(2).upper() in UFS:
                hits = self._match(items, norms, match.group(1), match.group(2).upper())
                if hits:
                    return hits[:limit]

        if not q:
            return [m for m in items if m["uf"] == uf][:limit] if uf else []
        return self._match(items, norms, q, uf)[:limit]

    @staticmethod
    def _match(items, norms, q, uf):
        buckets = ([], [], [], [])
        for m, name in zip(items, norms):
            if uf and m["uf"] != uf:
                continue
            if name == q:
                buckets[0].append(m)
            elif name.startswith(q):
                buckets[1].append(m)
            elif (" " + q) in (" " + name):
                buckets[2].append(m)
            elif q in name:
                buckets[3].append(m)
        return buckets[0] + buckets[1] + buckets[2] + buckets[3]


# ---------------------------------------------------------------- cache local

def load_cache(path):
    """Retorna (itens, idade_em_segundos) ou (None, None)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data["items"], time.time() - float(data["updated"])
    except (OSError, ValueError, KeyError, TypeError):
        return None, None


def save_cache(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"updated": time.time(), "items": items}, fh, ensure_ascii=False)
    os.replace(tmp, path)
