"""Testes da busca (não precisam do QGIS): python -m unittest discover tests"""
import importlib.util
import json
import os
import tempfile
import unittest

_PATH = os.path.join(os.path.dirname(__file__), "..", "GeoMunicipio", "ibge.py")
_spec = importlib.util.spec_from_file_location("ibge", _PATH)
ibge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ibge)

SAMPLE = [
    {"municipio-id": 3550308, "municipio-nome": "São Paulo", "UF-sigla": "SP"},
    {"municipio-id": 4216602, "municipio-nome": "São José", "UF-sigla": "SC"},
    {"municipio-id": 3549904, "municipio-nome": "São José dos Campos", "UF-sigla": "SP"},
    {"municipio-id": 1505536, "municipio-nome": "Pau D'Arco", "UF-sigla": "PA"},
    {"municipio-id": 3515004, "municipio-nome": "Embu-Guaçu", "UF-sigla": "SP"},
    {"municipio-id": 2408102, "municipio-nome": "Natal", "UF-sigla": "RN"},
]


def names(result):
    return ["{}/{}".format(m["nome"], m["uf"]) for m in result]


class SearchTest(unittest.TestCase):

    def setUp(self):
        self.idx = ibge.MunicipioIndex(ibge.parse_municipios(json.dumps(SAMPLE)))

    def test_sem_acento_e_ordem(self):
        self.assertEqual(names(self.idx.search("sao jose")),
                         ["São José/SC", "São José dos Campos/SP"])

    def test_uf_no_texto(self):
        self.assertEqual(names(self.idx.search("sao jose sc")), ["São José/SC"])
        self.assertEqual(names(self.idx.search("São José - SP")), ["São José dos Campos/SP"])

    def test_pontuacao(self):
        self.assertEqual(names(self.idx.search("pau d arco")), ["Pau D'Arco/PA"])
        self.assertEqual(names(self.idx.search("embu guacu")), ["Embu-Guaçu/SP"])

    def test_codigo(self):
        self.assertEqual(names(self.idx.search("3550308")), ["São Paulo/SP"])
        self.assertEqual(self.idx.get(2408102)["nome"], "Natal")

    def test_filtro_uf(self):
        self.assertEqual(names(self.idx.search("sao", "SC")), ["São José/SC"])
        self.assertEqual(self.idx.search(""), [])

    def test_formato_aninhado(self):
        data = json.dumps([{"id": 5101837, "nome": "Boa Esperança do Norte",
                            "microrregiao": None,
                            "regiao-imediata": {"regiao-intermediaria": {"UF": {"sigla": "MT"}}}}])
        self.assertEqual(ibge.parse_municipios(data)[0]["uf"], "MT")

    def test_cache(self):
        path = os.path.join(tempfile.mkdtemp(), "sub", "cache.json")
        ibge.save_cache(path, self.idx.items)
        items, age = ibge.load_cache(path)
        self.assertEqual(len(items), len(SAMPLE))
        self.assertLess(age, 60)
        self.assertEqual(ibge.load_cache(path + ".nao-existe"), (None, None))


if __name__ == "__main__":
    unittest.main()
