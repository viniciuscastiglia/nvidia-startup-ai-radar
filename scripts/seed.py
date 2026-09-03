"""Carrega as fixtures de `data/seed/*.yaml` no Postgres. Idempotente.

POR QUE YAML VERSIONADO E NÃO INSERT NA MÃO
--------------------------------------------
Quem clona o repositório precisa conseguir reproduzir a base. Um `INSERT` colado no psql não é
reproduzível e não aparece no diff de forma legível; um YAML por startup aparece.

POR QUE IDEMPOTENTE
-------------------
`UPSERT` por `nome` (startups) e por `(startup_id, url_fonte)` (documentos). Dá para rodar
de novo depois de corrigir um texto sem duplicar nem limpar o banco.

O CAMPO `perfil_alvo` NÃO VAI PARA O BANCO
-------------------------------------------
Cada YAML declara qual caso aquela empresa existe para exercitar (AI-native, wrapper,
inelegível ao Inception, evidência fraca...). Esse rótulo é **anotação de curadoria**: ele
fica no arquivo e é usado pelos testes para medir o classificador, mas nunca é inserido nas
tabelas que os agentes leem. Se entrasse no banco, o Classifier poderia enxergar a resposta.
Na prática o seed vira, de graça, um conjunto rotulado de avaliação.

VERIFICAÇÃO DE URL
------------------
`--verificar-urls` faz uma requisição em cada `url_fonte` e falha se alguma não resolver.
Rastreabilidade é a única coisa que o sistema promete sobre toda conclusão que emite, e uma URL
quebrada a desfaz inteira — isso transforma "a URL tem que ser real" de promessa em teste.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import psycopg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DATABASE_URL  # noqa: E402

DIR_SEED = Path(__file__).resolve().parent.parent / "data" / "seed"

TIPOS_VALIDOS = {"site", "blog", "noticia", "vaga", "perfil_founder", "release"}

SQL_STARTUP = """
INSERT INTO startups (nome, site, setor, estagio, localizacao, descricao_curta,
                      ano_fundacao, tamanho_time, fonte_descoberta, coletado_em)
VALUES (%(nome)s, %(site)s, %(setor)s, %(estagio)s, %(localizacao)s, %(descricao_curta)s,
        %(ano_fundacao)s, %(tamanho_time)s, %(fonte_descoberta)s,
        COALESCE(%(coletado_em)s, CURRENT_DATE))
ON CONFLICT (nome) DO UPDATE SET
    site = EXCLUDED.site,
    setor = EXCLUDED.setor,
    estagio = EXCLUDED.estagio,
    localizacao = EXCLUDED.localizacao,
    descricao_curta = EXCLUDED.descricao_curta,
    ano_fundacao = EXCLUDED.ano_fundacao,
    tamanho_time = EXCLUDED.tamanho_time,
    fonte_descoberta = EXCLUDED.fonte_descoberta
RETURNING id
"""

SQL_DOCUMENTO = """
INSERT INTO documentos (startup_id, tipo, titulo, conteudo_texto, url_fonte,
                        data_publicacao, coletado_em)
VALUES (%(startup_id)s, %(tipo)s, %(titulo)s, %(conteudo_texto)s, %(url_fonte)s,
        %(data_publicacao)s, COALESCE(%(coletado_em)s, CURRENT_DATE))
ON CONFLICT (startup_id, url_fonte) DO UPDATE SET
    tipo = EXCLUDED.tipo,
    titulo = EXCLUDED.titulo,
    conteudo_texto = EXCLUDED.conteudo_texto,
    data_publicacao = EXCLUDED.data_publicacao
RETURNING id
"""


def carregar_fixtures() -> list[dict]:
    if not DIR_SEED.exists():
        return []
    fixtures = []
    for caminho in sorted(DIR_SEED.glob("*.yaml")):
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        dados["_arquivo"] = caminho.name
        fixtures.append(dados)
    return fixtures


def validar(fixtures: list[dict]) -> list[str]:
    """Validação estrutural antes de tocar no banco. Falhar cedo e por inteiro."""
    problemas: list[str] = []
    for f in fixtures:
        arq = f.get("_arquivo", "?")
        if not f.get("nome"):
            problemas.append(f"{arq}: falta `nome`")
        docs = f.get("documentos") or []
        if len(docs) < 3:
            problemas.append(
                f"{arq}: {len(docs)} documento(s) — o TAPI pede pelo menos 3 por empresa"
            )
        tipos = {d.get("tipo") for d in docs}
        if invalidos := tipos - TIPOS_VALIDOS:
            problemas.append(f"{arq}: tipo(s) inválido(s): {invalidos}")
        if len(tipos) < 2:
            problemas.append(
                f"{arq}: documentos de um tipo só ({tipos}) — a regra 2 do Evidence Validator "
                f"exige corroboração entre TIPOS diferentes para confiança alta"
            )
        for d in docs:
            if not (d.get("url_fonte") or "").startswith("http"):
                problemas.append(f"{arq}: documento sem url_fonte válida: {d.get('titulo')!r}")
            if len((d.get("conteudo_texto") or "").strip()) < 200:
                problemas.append(
                    f"{arq}: conteudo_texto curto demais em {d.get('titulo')!r} "
                    f"— texto raso não dá o que extrair"
                )
    return problemas


def verificar_urls(fixtures: list[dict]) -> list[str]:
    """Confere que toda url_fonte resolve de fato. É o requisito de rastreabilidade,
    executável."""
    falhas: list[str] = []
    cabecalhos = {"User-Agent": "Mozilla/5.0 (compatible; StartupAIRadar/0.1)"}
    with httpx.Client(follow_redirects=True, timeout=20.0, headers=cabecalhos) as cli:
        for f in fixtures:
            for d in f.get("documentos") or []:
                url = d.get("url_fonte", "")
                # UM `HEAD` QUE LEVANTA TAMBÉM É `HEAD` RECUSADO (03/09, D-090)
                # ---------------------------------------------------------------
                # A versão anterior já sabia que "alguns servidores recusam HEAD" e caía para
                # `GET` — mas só quando a recusa vinha como STATUS >= 400. Quando ela vem como
                # EXCEÇÃO, o `except` de fora engolia a tentativa inteira e o fallback nunca
                # rodava. Medido em 03/09 na `lauranetworks.com`, que é fixture da base desde
                # 22/08: `HEAD` entra em laço de redirect (`TooManyRedirects`) e `GET` responde
                # **200 com 63 mil caracteres**. A página está viva; o verificador é que dizia
                # que morreu — e ele é o teste que sustenta a única coisa que este sistema
                # promete sobre toda conclusão que emite.
                #
                # Falso NEGATIVO de rastreabilidade é pior que falso positivo: ele manda o
                # curador remover ou trocar uma fonte legítima. Por isso a falha só é relatada
                # quando os DOIS métodos falham, e o log diz qual dos dois respondeu.
                erro_head = None
                try:
                    r = cli.head(url)
                    if r.status_code >= 400:
                        erro_head = f"HTTP {r.status_code}"
                        r = cli.get(url)
                except Exception as exc:  # noqa: BLE001
                    erro_head = type(exc).__name__
                    try:
                        r = cli.get(url)
                    except Exception as exc2:  # noqa: BLE001
                        print(f"    [FALHA] HEAD {erro_head} · GET {type(exc2).__name__}  {url}")
                        falhas.append(
                            f"{f['nome']}: HEAD {erro_head} e GET {type(exc2).__name__} em {url}")
                        continue
                marca = "ok " if r.status_code < 400 else "FALHA"
                via = f" (HEAD {erro_head}, resolvida por GET)" if erro_head else ""
                print(f"    [{marca}] {r.status_code}  {url}{via}")
                if r.status_code >= 400:
                    falhas.append(f"{f['nome']}: HTTP {r.status_code} em {url}")
    return falhas


def semear(fixtures: list[dict]) -> tuple[int, int]:
    n_startups = n_docs = 0
    with psycopg.connect(DATABASE_URL) as conexao:
        with conexao.cursor() as cur:
            for f in fixtures:
                cur.execute(
                    SQL_STARTUP,
                    {
                        "nome": f["nome"],
                        "site": f.get("site"),
                        "setor": f.get("setor"),
                        "estagio": f.get("estagio"),
                        "localizacao": f.get("localizacao"),
                        "descricao_curta": f.get("descricao_curta"),
                        "ano_fundacao": f.get("ano_fundacao"),
                        "tamanho_time": f.get("tamanho_time"),
                        "fonte_descoberta": f.get("fonte_descoberta"),
                        "coletado_em": f.get("coletado_em"),
                    },
                )
                startup_id = cur.fetchone()[0]
                n_startups += 1
                for d in f.get("documentos") or []:
                    cur.execute(
                        SQL_DOCUMENTO,
                        {
                            "startup_id": startup_id,
                            "tipo": d["tipo"],
                            "titulo": d["titulo"],
                            "conteudo_texto": d["conteudo_texto"].strip(),
                            "url_fonte": d["url_fonte"],
                            "data_publicacao": d.get("data_publicacao"),
                            "coletado_em": d.get("coletado_em") or f.get("coletado_em"),
                        },
                    )
                    n_docs += 1
                print(f"  {f['nome']:32} id={startup_id:<4} {len(f.get('documentos') or [])} documentos")
        conexao.commit()
    return n_startups, n_docs


def main() -> int:
    ap = argparse.ArgumentParser(description="Carrega data/seed/*.yaml no Postgres.")
    ap.add_argument("--verificar-urls", action="store_true",
                    help="requisita cada url_fonte e falha se alguma não resolver")
    ap.add_argument("--so-validar", action="store_true",
                    help="valida as fixtures sem escrever no banco")
    args = ap.parse_args()

    fixtures = carregar_fixtures()
    if not fixtures:
        print(f"nenhuma fixture em {DIR_SEED}")
        return 1
    print(f"{len(fixtures)} fixture(s) em {DIR_SEED.name}/\n")

    if problemas := validar(fixtures):
        print("VALIDAÇÃO FALHOU:")
        for p in problemas:
            print(f"  - {p}")
        return 1
    print("validação estrutural: ok")

    if args.verificar_urls:
        print("\nverificando url_fonte:")
        if falhas := verificar_urls(fixtures):
            print("\nURLS QUE NÃO RESOLVEM:")
            for f in falhas:
                print(f"  - {f}")
            return 1
        print("  todas as URLs resolvem")

    if args.so_validar:
        return 0

    print("\nsemeando:")
    n_s, n_d = semear(fixtures)
    print(f"\n{n_s} startups · {n_d} documentos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
