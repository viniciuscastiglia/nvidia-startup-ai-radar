# Log de decisões de arquitetura

Registro append-only. **Uma entrada por decisão, escrita no momento em que ela é tomada.**

Este arquivo tem três usos, e é por isso que ele é o hábito de maior alavancagem do projeto:

- **Eliminatório nº 4** do barema — *"o candidato precisa explicar as decisões de arquitetura do
  próprio projeto"*
- **Vídeo** (peso 20) — é o roteiro pronto
- **Repositório e documentação** (peso 10) — vira a seção de arquitetura do README

## Formato

```
## D-NNN — Título curto
**Data:** DD/MM/AAAA
**Decisão:** o que foi escolhido.
**Alternativas descartadas:** o que mais estava na mesa.
**Motivo:** por que esta e não as outras. Qual o trade-off aceito.
**Reversível?** fácil / caro / irreversível — e o que dispararia a revisão.
```

O campo **Alternativas descartadas** é o mais importante: é literalmente a pergunta que o
avaliador vai fazer.

---

## D-001 — Python 3.12 em vez do 3.14 do sistema
**Data:** 22/08/2026
**Decisão:** ambiente conda dedicado com Python 3.12.
**Alternativas descartadas:** usar o `python3` do sistema (Anaconda, 3.14.6).
**Motivo:** 3.14 é recente demais para o ecossistema. Bibliotecas com dependências compiladas
(drivers de Postgres, tokenizers, clientes de vector DB) frequentemente ainda não publicaram
wheel para 3.14, o que força build a partir do fonte e custa horas de depuração que não têm nada
a ver com o projeto. 3.12 é a versão com melhor cobertura de wheels no ecossistema de IA hoje.
**Reversível?** Fácil — é só recriar o ambiente.

---

## D-002 — Provedor de LLM, embedding e rerank atrás de variáveis de ambiente
**Data:** 22/08/2026
**Decisão:** `src/config.py` expõe `LLM`, `EMBEDDING` e `RERANK` lidos do `.env`. Nenhum agente
conhece o nome "NVIDIA" — todos recebem `base_url` + `modelo`.
**Alternativas descartadas:** instanciar o cliente da NVIDIA direto em cada agente.
**Motivo:** o risco nº 1 do `plano.md` é os créditos grátis do build.nvidia.com não sustentarem
8 agentes rodando dezenas de vezes por dia. A abstração custa ~100 linhas hoje; descobrir no dia
04/09 que os créditos acabaram e ter que mexer em 8 agentes custa o projeto. Trade-off aceito:
uma camada de indireção que, se a NVIDIA funcionar bem, nunca será exercida.
**Reversível?** Fácil, mas a assimetria importa: adicionar depois é caro, remover é trivial.

---

## D-003 — `langchain-openai` como cliente, não `langchain-nvidia-ai-endpoints`
**Data:** 22/08/2026
**Decisão:** falar com a NVIDIA pelo cliente OpenAI, trocando só o `base_url`.
**Alternativas descartadas:** `langchain-nvidia-ai-endpoints`, o SDK oficial da integração.
**Motivo:** os endpoints NIM são OpenAI-compatible por design (`contexto/03` §1) — é literalmente
o argumento de venda do produto. Usar o cliente genérico (a) tira uma dependência, (b) faz o
código de D-002 funcionar com qualquer provedor sem `if`, e (c) demonstra no vídeo a própria tese
do NIM: "migrar não exige mudar código". Trade-off: perde-se açúcar sintático específico da NVIDIA.
**Reversível?** Fácil — é trocar a classe do cliente em um lugar só.

---

## D-004 — conda para o ambiente de desenvolvimento + `requirements.txt` pinado
**Data:** 22/08/2026 · fecha a pendência **P-07**
**Decisão:** ambiente conda `case-nvidia` (Python 3.12.13) para desenvolver, `requirements.txt`
com versões exatas (`pip freeze`) para reprodução.
**Alternativas descartadas:** `uv` (mais rápido, lockfile melhor) · Poetry (gestão de projeto
mais completa).
**Motivo:** `uv` não está instalado na máquina e ambos exigem que quem for avaliar instale um
gerenciador a mais antes de rodar o projeto. `requirements.txt` roda em qualquer Python. O critério
aqui não é elegância de tooling — é atrito de reprodução para o avaliador, que conta no critério 7.
Trade-off aceito: `requirements.txt` não é lockfile de verdade (não trava dependências transitivas
por hash).
**Reversível?** Fácil.

---

## D-005 — Smoke test como script versionado com asserções semânticas
**Data:** 22/08/2026
**Decisão:** `scripts/smoke_nvidia.py`, em HTTP cru, que além de checar HTTP 200 verifica: se a
dimensão Matryoshka pedida é a devolvida, se o embedding separa relevante de irrelevante **em
português**, se funciona **crosslingual** (consulta PT × passagem EN) e se o reranker coloca a
passagem certa no topo. Grava latências em `docs/smoke-nvidia.md`.
**Alternativas descartadas:** `curl` descartável no terminal · passar por `langchain-openai`.
**Motivo:** três razões. (1) Um teste que só checa 200 não prova nada útil — a pergunta real é se
o modelo funciona em português e entre idiomas, porque a base NVIDIA é em inglês e os documentos
das startups em português; se o crosslingual falhasse, a arquitetura do RAG mudaria. (2) HTTP cru
torna a falha inequívoca: é do endpoint, não da biblioteca. (3) Vira evidência reproduzível para
o avaliador e a fonte dos números de latência do vídeo.
**Reversível?** Irrelevante — é ferramenta de apoio, não arquitetura.

---

## D-006 — Fan-in do grafo por `defer=True`, retry e isolamento de erro por nó
**Data:** 22/08/2026
**Decisão:** usar quatro recursos do LangGraph 1.2 que uma chain de prompts não tem: `defer=True`
no nó de Briefing (só executa quando o run está terminando, ou seja, depois de todas as análises
paralelas), `retry_policy` por nó, `error_handler` por nó, e `cache_policy` em desenvolvimento.
**Alternativas descartadas:** arestas condicionais manuais contando quantas análises voltaram ·
try/except dentro de cada nó · nenhum cache.
**Motivo:** o TAPI justifica LangGraph por "estado, transições condicionais, checkpoints, retry e
intervenção humana". Se o projeto usa LangGraph só como executor linear, a escolha vira decorativa
e o critério 1 fica em nível 2. Cada recurso aqui resolve um problema concreto e diferente:
`defer` resolve o fan-in sem contador manual; `retry_policy` cobre falha transitória de LLM;
`error_handler` impede que uma startup com dado ruim derrube as outras quatro; `cache_policy`
evita queimar crédito re-rodando o mesmo nó em desenvolvimento — que amarra direto com o risco
nº 1 do `plano.md`.
**Reversível?** Fácil, um parâmetro por nó. Verificado na API do langgraph 1.2.11 instalado.

---

## D-007 — Topologia: subgrafo de análise + fan-out por `Send`
**Data:** 22/08/2026 · fecha a pendência **P-05**
**Decisão:** o grafo pai tem 4 nós (`query_planner` → `retriever` → `analisar_startup` →
`briefing`). O Retriever emite um `Send` por startup para um nó-wrapper que invoca um **subgrafo
compilado** com as 5 etapas de análise (extractor, classifier, evidence validator, nvidia_rag,
recommendation). O fan-in acontece no reducer `operator.add` de `EstadoRadar.analises`, e o
Briefing usa `defer=True` para só executar quando todas as branches terminaram.
**Alternativas descartadas:**
(a) **Lote** — cada nó itera sobre todas as startups internamente. Descartada porque o prompt
cresce com N e a qualidade da extração cai; uma startup com dado ruim derruba as outras; e o
retry só existe no nível do nó. Pior: uma chain simples de prompts faria exatamente isso, o que
tornaria a escolha do LangGraph decorativa — nível 2 no critério 1.
(b) **Fan-out direto para o Extractor**, sem subgrafo. Mesmo ganho de paralelismo e retry, mas
o grafo vira 8 nós mais um leque de N branches: o diagrama fica poluído no README e no vídeo, e
testar uma etapa isolada dá mais trabalho.
**Motivo:** (c) é a única opção em que a escolha do LangGraph é *necessária* em vez de estética.
Além disso o subgrafo roda sozinho no pytest — dá para testar a análise de uma startup sem tocar
no grafo pai — e o diagrama do pai cabe num slide de 4 caixas, o que importa porque o vídeo tem
teto de 7 minutos. Trade-off aceito: uma camada de abstração a mais e **dois** diagramas para
explicar em vez de um.
**Reversível?** Média. Voltar para (b) é remover o wrapper e religar arestas; voltar para (a)
exigiria remover os reducers e reescrever os 5 nós de análise.

---

## D-008 — TypedDict para o estado do grafo, Pydantic para o que trafega dentro
**Data:** 22/08/2026
**Decisão:** `EstadoRadar` e `EstadoAnalise` são `TypedDict` com `Annotated[..., operator.add]`
nos campos que acumulam. Todos os payloads (`Afirmacao`, `PerfilStartup`, `Diagnostico`,
`Recomendacao`, `AnaliseStartup`) são modelos Pydantic.
**Alternativas descartadas:** estado inteiro como modelo Pydantic · estado inteiro como dict solto.
**Motivo:** os dois lados da fronteira têm exigências opostas. O estado precisa aceitar
atualização **parcial** — um nó devolve `{"perfil": x}` e o LangGraph funde; com Pydantic como
estado, todo nó teria que reconstruir o objeto inteiro. Já os payloads atravessam a fronteira do
LLM, onde validar é o ponto: `Literal` fechado faz o classificador devolver exatamente
`AI-native | AI-enabled | non-AI` ou levantar erro de validação que o `retry_policy` trata —
em vez de "meio AI-native" passando adiante. Dict solto perderia as duas coisas.
**Reversível?** Fácil no sentido mecânico, caro na prática: mudaria a assinatura dos 8 nós.

---

## D-009 — Evidência é o átomo do estado, não um campo adicionado no fim
**Data:** 22/08/2026
**Decisão:** `Afirmacao` — a unidade que todo agente produz — não existe sem `list[Evidencia]`,
e `Evidencia` guarda o **trecho exato**, não só o `documento_id`. `PerfilStartup`,
`Diagnostico`, `Elegibilidade` e `Recomendacao` são compostos de `Afirmacao`.
**Alternativas descartadas:** um campo `fontes: list[int]` no fim de cada saída · uma tabela
de auditoria separada, preenchida em paralelo ao raciocínio.
**Motivo:** o TAPI exige rastreabilidade **duas vezes** (§5.2 e §5.5). Um campo opcional no fim
de cada modelo é exatamente o que não sobrevive a cinco saltos até o Briefing — em algum nó
alguém devolve a conclusão sem a fonte e ninguém percebe. Fazendo do tipo, deixar de citar vira
erro de validação. Guardar o trecho e não só o id permite o briefing citar literalmente e o
avaliador conferir sem abrir o banco. Trade-off: os modelos ficam mais verbosos e os prompts
terão que pedir o trecho junto da conclusão.
**Reversível?** Irreversível na prática — é a espinha do estado.

---

## D-010 — Evidence Validator anota e rebaixa; quem barra é o Recommendation
**Data:** 22/08/2026
**Decisão:** o Validator preenche `confianca` e `validada` em cada `Afirmacao` e **nunca deleta**.
O bloqueio acontece uma camada adiante: o Recommendation não emite prioridade alta apoiada só em
afirmação de `confianca=baixa`. `Elegibilidade` segue a mesma disciplina, separando
`motivos_exclusao` (a base **prova** que é consultoria) de `requisitos_nao_verificados`
(a base **não prova** que tem developer).
**Alternativas descartadas:** o Validator descartar afirmações sem fonte suficiente.
**Motivo:** pela regra 4 de `contexto/02` §6, ausência de sinal ≠ sinal negativo. Deletar
destrói informação que o humano precisa — "não conseguimos confirmar que têm time técnico" é
justamente o que o gerente do Inception quer saber antes de ligar. E separar as duas camadas dá
uma responsabilidade a cada agente em vez de concentrar julgamento num só.
**Reversível?** Fácil.

---

## D-011 — As oito dores do TAPI viram enum fechada
**Data:** 22/08/2026
**Decisão:** `Dor` é um `Literal` com os oito valores que o TAPI lista (custo, latência,
escalabilidade, governança, privacidade, avaliação, observabilidade, dependência de fornecedor).
O Extractor só pode emitir uma dessas; a tabela "dor → tecnologia" de `contexto/03` §4 casa por
essa chave.
**Alternativas descartadas:** dor como texto livre gerado pelo LLM.
**Motivo:** é o que separa um motor de recomendação de um LLM improvisando associação. Com enum
fechada, a recomendação é uma junção auditável entre o que foi observado na startup e a tabela de
tecnologias — dá para explicar no vídeo por que uma tecnologia apareceu. Com texto livre, a única
resposta possível é "o modelo achou que combinava".
**Nota factual:** o TAPI lista **oito** dores (linhas 55-57 do original); nosso destilado em
`contexto/01` e `contexto/03` dizia "sete". Corrigido nos dois arquivos.
**Reversível?** Fácil — acrescentar valor à enum é aditivo.

---

## D-012 — Adotar a stack NVIDIA inteira, com os modelos que existem hoje
**Data:** 22/08/2026 · fecha a pendência **P-01**
**Decisão:** LLM dos agentes, embedding e reranking todos no build.nvidia.com.
Chat: `meta/llama-3.1-8b-instruct`. Embedding: `nvidia/llama-nemotron-embed-1b-v2`.
Reranking: `nvidia/llama-nemotron-rerank-1b-v2`.
**Alternativas descartadas:** NVIDIA só para embedding e reranking, com outro provedor para os
LLMs dos agentes (era o fallback previsto no `sessao-01.md` caso os créditos não sustentassem).
**Motivo:** as três capacidades responderam (755 / 593 / 520 ms) e ~30 chamadas de teste não
esbarraram em limite. Adotar tudo dá o argumento mais forte do vídeo — *"o sistema roda na
própria stack que ele recomenda"* — e é o candidato principal a Diferencial (peso 5) que também
empurra o critério 2 (peso 20). O fallback continua existindo em D-002: é uma linha do `.env`.
**Ressalva honesta:** ~30 chamadas não é teste de limite de crédito. A validação real vem quando
o pipeline de 8 agentes rodar dezenas de vezes por dia. Por isso `cache_policy` (D-006) e
`MAX_STARTUPS` continuam sendo os botões de contenção.
**Reversível?** Fácil, por env var.

---

## D-013 — Os modelos que o TAPI cita estão mortos; achei os atuais medindo
**Data:** 22/08/2026
**Decisão:** trocar `llama-3.2-nv-embedqa-1b-v2` e `llama-3.2-nv-rerankqa-1b-v2` — que a
documentação de junho e o `contexto/03` original citavam — por `llama-nemotron-embed-1b-v2` e
`llama-nemotron-rerank-1b-v2`. `contexto/03` §3 e `contexto/05` §1 corrigidos.
**Alternativas descartadas:** assumir que era problema de credencial e pedir key nova · assumir
que o `contexto/` estava certo e insistir no nome documentado.
**Motivo:** o embedding devolveu **HTTP 410 Gone**, não 401 nem 404. A distinção resolveu o
diagnóstico sozinha: 401 seria credencial, 404 seria nome errado, 410 é recurso **retirado** — e
o chat com a mesma key já tinha passado, o que eliminava credencial. O corpo da resposta
confirmou: *"This endpoint has reached its end of life on 2026-05-18T00:00:00Z"*. Achei os
substitutos listando `GET /v1/models` e cruzando com um tutorial de 07/08/2026.
**Por que isso é o achado mais valioso do dia:** é evidência direta de que a stack foi verificada
em vez de copiada da documentação. Vale citar no vídeo — o TAPI foi escrito em junho, os
endpoints morreram em maio, e um projeto que só copiasse os nomes do enunciado **não executaria**.
**Reversível?** N/A — é constatação de fato, não escolha.

---

## D-014 — Embedding com `dimensions=1024` via Matryoshka
**Data:** 22/08/2026 · fecha a pendência **P-02**
**Decisão:** `llama-nemotron-embed-1b-v2` pedindo explicitamente 1024 dimensões.
**Alternativas descartadas:**
- **`nemotron-3-embed-1b`** — separou melhor no teste (0.5241 vs 0.1137), mas **rejeita
  `dimensions` com HTTP 400**: fica preso em 2048.
- **`nv-embedqa-e5-v5`** — 1024 nativas e o mais rápido (494 ms), mas o **crosslingual falha**:
  0.3107 contra 0.3096 de irrelevante é ruído numérico, não separação semântica.
- **Aceitar as 2048 nativas** e indexar com `halfvec(2048)`.
**Motivo:** duas restrições se cruzam e só um modelo satisfaz as duas.
(1) Verifiquei no psql que **pgvector recusa índice HNSW acima de 2000 dimensões** no tipo
`vector` (`ERROR: column cannot have more than 2000 dimensions for hnsw index`); `halfvec(2048)`
aceita, mas ao custo de meia precisão.
(2) A base NVIDIA é em inglês e os documentos das startups em português, então **recuperação
crosslingual não é luxo, é o caminho principal** do RAG.
O `llama-nemotron-embed-1b-v2` é o único que trunca para 1024 (cabendo no HNSW nativo) **e**
tem crosslingual real (0.4280 contra 0.0049 de irrelevante — separação de ~70x).
**A decidir depois, com medida:** 1024 vs 768 vs 384. O harness de avaliação da M2 compara
recall@k entre as dimensões — aí a escolha vira medição em vez de argumento.
**Reversível?** Média: mudar a dimensão exige re-embedar o corpus e recriar a coluna.

---

## D-015 — Reranker text-only, não o multimodal
**Data:** 22/08/2026 · fecha a pendência **P-03**
**Decisão:** `nvidia/llama-nemotron-rerank-1b-v2`.
**Alternativas descartadas:**
- **`llama-nemotron-rerank-vl-1b-v2`** — é o que o tutorial recente da NVIDIA usa, mas separou
  muito menos no mesmo teste: margem de **3.24** contra **12.94** do text-only, com latência
  praticamente igual (535 vs 520 ms).
- **Cohere Rerank** — é o que o TAPI sugere, mas é pago e quebraria a narrativa de rodar tudo
  na stack NVIDIA.
- **Cross-encoder local** (BGE, Jina) — sem custo de API, mas exige baixar e rodar o modelo, e
  perde o argumento do Diferencial.
**Motivo:** o corpus do RAG é texto puro (documentação NVIDIA). O ganho do modelo VL é entender
imagem, o que não se aplica aqui — e ele paga esse ganho em precisão no texto. Escolher o VL
porque "é o mais novo" seria decidir por recência em vez de por adequação.
**Reversível?** Fácil — duas linhas do `.env` (modelo e URL, que embute o modelo no path).

---

## D-016 — pgvector para o denso, BM25 em processo para o léxico
**Data:** 22/08/2026 · fecha a pendência **P-04**
**Decisão:** vetores densos no Postgres com pgvector; busca lexical do RAG NVIDIA com Okapi BM25
em processo (`bm25s`). A busca lexical sobre os **documentos das startups** é caso diferente e
usa `tsvector` do próprio Postgres.
**Alternativas descartadas:**
- **Qdrant** — é o recomendado pelo TAPI, tem sparse vectors nativos e fusão RRF pronta.
- **`ts_rank_cd` do Postgres como o "BM25"** da busca híbrida.
**Motivo:** três razões, em ordem de peso.
(1) `ts_rank_cd` **não é BM25** — é cobertura de termos, sem saturação de frequência nem
normalização por comprimento de documento. Chamar aquilo de BM25 no vídeo seria impreciso e o
avaliador pode perguntar. `bm25s` dá Okapi de verdade, com `k1` e `b` ajustáveis — e ajustável
significa que o harness de avaliação (passo 9 do pipeline, o que mais separa nível 2 de nível 4)
tem o que medir.
(2) O corpus do RAG é pequeno e **estático**: 16 tecnologias, ~20-40 documentos-fonte, algumas
centenas de chunks. Reconstruir o índice na ingestão custa segundos.
(3) O pgvector 0.8.1 **já estava instalado** no Postgres.app 18.3 da máquina, e o Docker não
está rodando — Qdrant custaria uma peça de infra e um passo a mais para quem for avaliar.
**Onde a decisão se reverteria:** se o corpus crescesse uma ordem de grandeza ou passasse a ser
atualizado com frequência, manter índice BM25 em memória vira problema e o Qdrant ganha. É
barato reverter porque tudo fica atrás de uma função `buscar_hibrido(query, k)`.
**Nota sobre os dois problemas de recuperação:** documentos de startup ficam no `tsvector` do
Postgres porque a busca lexical ali anda junto de filtro estruturado (setor, estágio, porte) e o
corpus cresce — SQL é a ferramenta certa. São problemas diferentes, ferramentas diferentes.
**Reversível?** Média.

---

## D-017 — Postgres.app para desenvolver, docker-compose para quem avaliar
**Data:** 22/08/2026 · fecha a pendência **P-08**
**Decisão:** os dois. `DATABASE_URL` aponta para o Postgres.app local em desenvolvimento;
o repositório versiona um `docker-compose.yml` com `pgvector/pgvector:pg17` para reprodução.
**Alternativas descartadas:** só Postgres.app (o avaliador não tem) · só Docker (o daemon não
está rodando nesta máquina, e subir Docker Desktop para cada sessão é atrito diário).
**Motivo:** os dois públicos têm restrições opostas. Quem desenvolve quer o banco já de pé; quem
avalia quer um comando só, sem instalar Postgres. Custa ~20 linhas de YAML e o schema é o mesmo
arquivo nos dois caminhos. Atrito de reprodução conta no critério 7.
**Reversível?** Fácil.

---

## D-018 — Stubs que produzem evidência REAL, não texto inventado
**Data:** 22/08/2026
**Decisão:** os nós-stub da sessão 01 casam o vocabulário de sinal de `contexto/02` §5 contra as
frases reais dos documentos e devolvem o **trecho literal** como `Evidencia`. Nenhum stub inventa
texto. E dois nós não são stub nenhum: o **Retriever** (SQL sobre `tsvector`) e o **Evidence
Validator** (as 5 regras de `contexto/02` §6 são lógica pura).
**Alternativas descartadas:** stubs que devolvem objetos hard-coded só para o grafo compilar.
**Motivo:** o que precisava ser provado hoje não era que a extração é boa — era que a
**rastreabilidade sobrevive aos cinco saltos** até o Briefing. Um stub com texto inventado
compilaria igual e não provaria nada; o teste `test_toda_recomendacao_tem_evidencia` passaria
sobre dados falsos. Com evidência real, o teste tem valor desde o dia 1.
**Reversível?** N/A — os stubs são substituídos por LLM na M4, mantendo a assinatura.

---

## D-019 — Diagramas do grafo como Mermaid em texto, não PNG
**Data:** 22/08/2026
**Decisão:** `docs/grafo-pai.mmd` e `docs/subgrafo-analise.mmd` via `draw_mermaid()`.
**Alternativas descartadas:** `draw_mermaid_png()`, que é o que a documentação do LangGraph
sugere de imediato.
**Motivo:** `draw_mermaid_png()` chama a API externa `mermaid.ink` — vira dependência de rede
para gerar um artefato de build, e quebra offline. O GitHub renderiza Mermaid nativamente, então
o `.mmd` aparece como diagrama no README sem imagem intermediária, e continua legível e
versionável em diff. Bônus: o diagrama gerado mostra `defer = True` no nó de Briefing, o que
torna a decisão de topologia (D-007) visível no próprio desenho.
**Reversível?** Fácil.

---

## D-020 — Limitações conhecidas dos stubs, registradas em vez de escondidas
**Data:** 22/08/2026
**Decisão:** registrar o que a heurística da sessão 01 erra, com a causa, em vez de ajustar
palavra-chave até a saída parecer boa.
**O que está errado hoje, e por quê:**
1. **Falso positivo de inelegibilidade na Axenya.** O filtro do Inception a marcou como
   consultoria porque o site dela diz *"Integramos consultoria, dados e operação clínica em uma
   única plataforma"*. Ela não é uma consultoria — ela **absorve** a função de consultoria num
   produto, que é justamente o wedge da Sequoia (`contexto/02` §1). Casamento de substring não
   distingue "somos uma consultoria" de "substituímos a consultoria".
2. **Todas as empresas acusam quase todas as 8 dores.** Os gatilhos ("custo", "escala",
   "monitoramento") são termos comuns em qualquer texto de negócio.
3. **Doutor-AI saiu AI-enabled apesar de linguagem de autopilot pura** ("força de trabalho
   digital", "funcionários robôs"): a palavra "plataforma" acionou o contador de copilot.
4. **Confiança baixa em tudo**, porque muitos documentos não têm `data_publicacao` — o que é
   comportamento **correto** da regra 3, não bug.
**Motivo de registrar em vez de corrigir:** os três primeiros são exatamente o argumento de por
que este trabalho precisa de LLM com evidência e validação, e não de regex. Um sistema de
palavra-chave produz erro **confiante** — a Axenya foi reprovada com uma justificativa que soa
plausível e cita a fonte certa. É o melhor material de "antes e depois" possível para o vídeo, e
some se eu ajustar a lista de termos até a saída ficar bonita.
**Encaminhamento:** itens 1-3 são resolvidos na M4, quando os nós passam a usar LLM com saída
estruturada. O item 4 fica como está.

---

## Decisões pendentes

Levantadas em `contexto/05-achados-e-decisoes.md` §4, a serem fechadas na sessão 01:

| # | Decisão | Encaminhamento sugerido |
|---|---|---|
| ~~P-01~~ | ~~Provedor de LLM dos agentes~~ | **resolvida em D-012** — NVIDIA, três capacidades verificadas |
| ~~P-02~~ | ~~Modelo de embedding e dimensão~~ | **resolvida em D-014** — `llama-nemotron-embed-1b-v2` com `dimensions=1024` |
| ~~P-03~~ | ~~Reranker~~ | **resolvida em D-015** — `llama-nemotron-rerank-1b-v2` (text-only vence o VL por margem 12.94 vs 3.24) |
| ~~P-04~~ | ~~Banco vetorial~~ | **resolvida em D-016** — pgvector para o denso, `bm25s` em processo para o léxico |
| ~~P-05~~ | ~~Topologia do grafo~~ | **resolvida em D-007** — subgrafo de análise + fan-out por `Send` |
| P-06 | Framework de frontend | vale 5 pontos; alvo é funcional e limpo |
| ~~P-07~~ | ~~Gerenciamento de dependências~~ | **resolvida em D-004** — conda + requirements.txt pinado |
| ~~P-08~~ | ~~Como o Postgres sobe para quem for avaliar~~ | **resolvida em D-017** — os dois |
