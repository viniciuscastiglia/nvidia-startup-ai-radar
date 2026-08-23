-- Schema da base de startups — NVIDIA Startup AI Radar
--
-- Segue o schema mínimo sugerido pelo TAPI (contexto/01), com três acréscimos deliberados,
-- cada um justificado abaixo. Idempotente: pode rodar de novo sem quebrar.

CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector 0.8.1, já presente no Postgres.app 18
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- similaridade por trigrama (busca por nome aproximado)
CREATE EXTENSION IF NOT EXISTS unaccent;   -- ver a função imutável abaixo

-- ─────────────────────────────────────────────────────────────────────────────
-- unaccent imutável
--
-- POR QUE ISTO EXISTE: uma coluna GENERATED do Postgres só aceita funções IMMUTABLE, e
-- `unaccent(text)` na forma de um argumento NÃO é imutável — depende de qual dicionário
-- estiver ativo na sessão. A forma de DOIS argumentos, com o dicionário nomeado
-- explicitamente, é determinística; envolvê-la assim é o padrão aceito para poder usar
-- unaccent em índice e em coluna gerada.
--
-- POR QUE PRECISAMOS: o stemmer 'portuguese' do Postgres NÃO remove acento. Sem isto,
-- "inteligência" e "inteligencia" viram lexemas diferentes e a busca lexical erra em
-- português — que é o idioma de toda a base de startups.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION imutavel_unaccent(text)
RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT public.unaccent('public.unaccent', $1) $$;


CREATE TABLE IF NOT EXISTS startups (
    id              SERIAL PRIMARY KEY,
    nome            TEXT NOT NULL UNIQUE,   -- UNIQUE: é a chave do upsert do seed
    site            TEXT,
    setor           TEXT,
    estagio         TEXT,
    localizacao     TEXT,
    descricao_curta TEXT,
    ano_fundacao    INTEGER,
    tamanho_time    INTEGER,

    -- ACRÉSCIMO 1: proveniência. contexto/04 §3 item 5 pede registrar de onde e quando o
    -- dado veio — vira a seção de metodologia do README e conta no critério 7.
    fonte_descoberta TEXT,
    coletado_em      DATE NOT NULL DEFAULT CURRENT_DATE,

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE TABLE IF NOT EXISTS documentos (
    id              SERIAL PRIMARY KEY,
    startup_id      INTEGER NOT NULL REFERENCES startups(id) ON DELETE CASCADE,

    -- ACRÉSCIMO 2: CHECK espelhando o Literal TipoDocumento de src/state.py.
    -- Mantém banco e código sincronizados: um tipo novo falha na inserção em vez de
    -- vazar silenciosamente até o Extractor.
    tipo            TEXT NOT NULL CHECK (tipo IN
                        ('site','blog','noticia','vaga','perfil_founder','release')),

    titulo          TEXT NOT NULL,

    -- NÃO ESTRUTURADO DE PROPÓSITO. É sobre este campo que o Extractor, o Classifier e o
    -- Evidence Validator trabalham. Estruturar demais aqui mata o trabalho dos agentes
    -- (contexto/01, regra grifada nº 1).
    conteudo_texto  TEXT NOT NULL,

    url_fonte       TEXT NOT NULL,
    data_publicacao DATE,                   -- regra 3 do Evidence Validator: documento antigo vale menos
    coletado_em     DATE NOT NULL DEFAULT CURRENT_DATE,

    -- ACRÉSCIMO 3: busca lexical em português para o Retriever.
    --
    -- POR QUE tsvector AQUI E BM25 EM PROCESSO NO RAG DA NVIDIA (ver D-013):
    -- são dois problemas de recuperação diferentes. Aqui a busca lexical anda junto de
    -- filtro estruturado (setor, estágio, porte) e o corpus cresce — SQL é a ferramenta
    -- certa. Lá o corpus é pequeno, estático e o que se quer é Okapi BM25 de verdade,
    -- com k1/b ajustáveis para o harness de avaliação medir.
    busca           tsvector GENERATED ALWAYS AS (
                        to_tsvector('portuguese',
                            imutavel_unaccent(coalesce(titulo, '') || ' ' || coalesce(conteudo_texto, '')))
                    ) STORED,

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Chave do upsert idempotente do seed
    UNIQUE (startup_id, url_fonte)
);


CREATE INDEX IF NOT EXISTS idx_documentos_busca      ON documentos USING GIN (busca);
CREATE INDEX IF NOT EXISTS idx_documentos_startup    ON documentos (startup_id);
CREATE INDEX IF NOT EXISTS idx_documentos_tipo       ON documentos (tipo);
CREATE INDEX IF NOT EXISTS idx_startups_setor        ON startups (setor);
CREATE INDEX IF NOT EXISTS idx_startups_nome_trgm    ON startups USING GIN (nome gin_trgm_ops);


-- ─────────────────────────────────────────────────────────────────────────────
-- BASE DE CONHECIMENTO NVIDIA — passos 3-5 do pipeline RAG (Entregável 2)
--
-- Corpus pequeno, estático e curado à mão: 16 tecnologias, 16 documentos, ~163k chars.
-- O manifesto de fontes é `data/nvidia/fontes.yaml`; a ingestão é `scripts/ingerir_nvidia.py`.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks_nvidia (
    id                SERIAL PRIMARY KEY,

    -- CURADORIA, NÃO INFERÊNCIA: vem do manifesto, não de heurística sobre o texto. É a chave
    -- de CitacaoRAG.tecnologia, do motor de recomendação e do recall@k do gabarito.
    tecnologia        TEXT NOT NULL,

    -- A URL que um humano abre — 7º campo obrigatório do TAPI. Difere da URL de onde o texto
    -- foi buscado nos casos de GitHub, onde o raw dá texto limpo e o repositório dá leitura
    -- (ver D-028). Aqui fica SEMPRE a de leitura.
    documento_url     TEXT NOT NULL,
    titulo_documento  TEXT NOT NULL,

    -- Breadcrumb: "NVIDIA NIM > Boost Throughput With NIM". O primeiro elemento é sempre o
    -- nome da tecnologia, porque os headings do corpus não nomeiam produto — os h3 do NIM
    -- incluem 'Benefits', 'Models', 'Features' (medido em 23/08). Ver D-025.
    caminho_secao     TEXT NOT NULL,

    -- DOIS TEXTOS, DE PROPÓSITO:
    --   texto          = limpo, sem breadcrumb. É o que vira CitacaoRAG.trecho e o que um
    --                    humano lê no briefing.
    --   texto_indexado = breadcrumb + \n\n + texto. É o que é EMBEDADO e o que o BM25 vai
    --                    indexar na sessão 03. Guardar os dois é o que permite a citação ser
    --                    legível sem que a recuperação perca a atribuição.
    texto             TEXT NOT NULL,
    texto_indexado    TEXT NOT NULL,

    ordinal           INTEGER NOT NULL,
    n_tokens          INTEGER NOT NULL,

    -- A ALTERNATIVA DESCARTADA VIRA BRAÇO DE CONTROLE (D-027). 'estrutural-v1' e 'fixo-800'
    -- coexistem na mesma tabela; o harness compara recall@k entre as duas sem re-ingerir nada.
    estrategia        TEXT NOT NULL DEFAULT 'estrutural-v1',

    -- A busca usa esta. 1024 porque é o que cabe no HNSW nativo do pgvector (D-014).
    embedding         vector(1024),

    -- SEM ÍNDICE, de propósito. Só o harness da sessão 04 lê, para derivar 384/768/1024 por
    -- truncagem local — medido em 23/08: cos(api, truncagem_local) = 0.99999996 (D-029).
    -- Verificado em psql que vector(2048) armazena; é só o índice HNSW que recusa >2000.
    embedding_bruto   vector(2048),

    coletado_em       DATE NOT NULL DEFAULT CURRENT_DATE,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Chave do upsert idempotente da ingestão, e o que deixa as duas estratégias conviverem
    UNIQUE (estrategia, documento_url, ordinal)
);

-- COSSENO e não produto interno: medido em 23/08 que os vetores do llama-nemotron-embed-1b-v2
-- voltam normalizados (norma L2 = 1.000063), então as duas métricas são equivalentes aqui.
-- Cosseno é a que o smoke test já usou para medir a separação crosslingual de D-014.
--
-- HONESTIDADE SOBRE ESTE ÍNDICE: a ~200 chunks ele não muda latência de forma mensurável —
-- um scan sequencial é instantâneo nesse tamanho. Ele existe porque o desenho tem que estar
-- certo uma ordem de grandeza acima. Vendê-lo como ganho de performance aqui seria a mesma
-- imprecisão que D-016 recusou ao não chamar ts_rank_cd de BM25.
CREATE INDEX IF NOT EXISTS idx_chunks_nvidia_hnsw
    ON chunks_nvidia USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_nvidia_estrategia ON chunks_nvidia (estrategia);
CREATE INDEX IF NOT EXISTS idx_chunks_nvidia_tecnologia ON chunks_nvidia (tecnologia);
