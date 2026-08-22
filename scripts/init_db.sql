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
