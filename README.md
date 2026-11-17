# GeoMunicípio

Plugin do QGIS para **localizar qualquer município brasileiro** pelo nome (com ou sem acento) ou pelo código IBGE, dando zoom no **limite oficial do IBGE**.

## Funcionalidades
- Busca instantânea entre os 5.570 municípios, sem precisar de acento: `sao joao`, `embu guacu`.
- Filtro por UF, ou digite `nome UF` / `nome - UF` (ex.: `sao jose sc`).
- Busca pelo código IBGE de 7 dígitos (ex.: `3550308`).
- Zoom e destaque do limite municipal (malha IBGE, SIRGAS 2000 / EPSG:4674).
- Opcional: guarda os limites numa camada temporária "Municípios (GeoMunicípio)", com código, nome e UF.
- Integração com a barra **Localizador** (Ctrl+K) usando o prefixo `mun`: `mun curitiba`.
- Sem dependências externas. A lista fica no seu computador e é atualizada a cada 30 dias.

## Fonte dos dados
APIs públicas do IBGE:
- Localidades: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`
- Malhas: `https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{código}`

## Instalação
- **Pelo QGIS** (depois de publicado): *Complementos → Gerenciar e instalar complementos*, busque "GeoMunicípio".
- **Pelo ZIP:** baixe o arquivo em [Releases](https://github.com/GGOMESX/GeoMunicipio/releases) e use *Complementos → Gerenciar e instalar complementos → Instalar a partir do ZIP*.

## Estrutura do repositório
```
geomunicipio/        código do plugin (a pasta que vai dentro do ZIP)
tests/               testes da busca (rodam sem QGIS)
package.sh           gera geomunicipio-<versão>.zip
.github/workflows/   CI: testes a cada push e release automática a cada tag v*
```

## Lançar uma nova versão
1. Atualize `version=` e o `changelog` em `geomunicipio/metadata.txt`.
2. Crie e envie a tag com a mesma versão (o CI gera o ZIP e cria a release no GitHub):
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. Envie o ZIP da release em https://plugins.qgis.org/plugins/add/ (na primeira vez) ou em *Add version* na página do plugin.

## Desenvolvimento
Testes: `python -m unittest discover tests`

Copie (ou crie um link simbólico de) a pasta `geomunicipio` para a pasta de plugins do seu perfil do QGIS:
- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

Depois reinicie o QGIS e ative o plugin em *Complementos → Gerenciar e instalar complementos*. O plugin **Plugin Reloader** ajuda a recarregar o código sem reiniciar o QGIS.

## Licença
GPL-2.0 ou posterior (veja `LICENSE`).
