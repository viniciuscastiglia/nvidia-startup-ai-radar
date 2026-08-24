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

**Correção de 23/08 — esta entrada estava adiantada em relação ao código.** Ela foi escrita
como decisão de projeto, mas ficou lida como descrição do que existe. Na sessão 01 só dois dos
quatro recursos chegaram ao código: `defer=True` e `retry_policy`. O isolamento de erro era um
`try/except` manual no wrapper — que entrega a garantia prometida ("uma startup não derruba as
outras") mas por mecanismo diferente do declarado, e com uma perda que eu não tinha visto:
descarta o trabalho parcial. `error_handler` de verdade entrou em **D-024**. `cache_policy`
continua **não implementado** — e de propósito: os nós de hoje são heurística em memória, não
há o que cachear. Ele entra junto com o primeiro nó que chama LLM (M4), que é quando cachear
passa a economizar crédito de verdade. Até lá, esta entrada declara intenção, não estado.

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

## D-021 — Campo estruturado sem fonte literal vira `null`, não valor plausível
**Data:** 22/08/2026
**Decisão:** nos YAMLs do seed, só ficam preenchidos os campos que aparecem **literalmente** nos
documentos coletados. Auditoria de 22/08 zerou 6 dos 12 campos estruturados das 3 empresas.
**Alternativas descartadas:** manter os valores obtidos por inferência ou por resumo automático
de página, marcando-os com um flag de confiança.
**Motivo:** a auditoria começou por uma pergunta do Vinícius sobre risco de alucinação, e achou
um caso concreto: `Laura.tamanho_time = 80` veio de *"pretendia expandir de 65 para 80 até o
final de 2021"* — que é **plano**, não fato, e de 2021. `Axenya.ano_fundacao = 2020` não aparece
em documento nenhum da base. Isso é grave porque `ano_fundacao` alimenta o filtro de
elegibilidade do Inception, que testa "menos de 10 anos".
O ponto decisivo é assimétrico: **`null` dispara comportamento correto, valor errado não dispara
nada.** Com `null`, o Briefing reporta *"ano de fundação não consta na base — verificar"*, que é
uma pendência acionável para quem vai abordar a empresa. Com um ano plausível e errado, o
sistema afirma elegibilidade com confiança e ninguém revisa.
É a mesma disciplina da regra 4 do Evidence Validator (`contexto/02` §6) aplicada aos campos
estruturados: ausência de informação é um estado legítimo, e mentir sobre ela é pior que admiti-la.
**Consequência de método, que vale mais que a correção:** `scripts/coletar.py` (texto bruto por
`curl` + parser) é fonte confiável; resumo automático de página **não é** e não deve preencher
campo do banco. Vale para a M3, quando a base for de 30 a 50 empresas — é lá que o atalho tentaria voltar.
**Reversível?** Fácil — é só reabrir cada URL e conferir.

---

## D-022 — `thread_id` novo por execução; retomar é opt-in
**Data:** 23/08/2026
**Decisão:** o CLI gera `cli-<uuid4>` a cada execução e imprime o id; `--thread <id>` retoma um
run existente.
**Alternativas descartadas:** manter `thread_id: "cli"` fixo · zerar os canais acumuladores no
início de cada run · trocar o reducer de `analises` por sobrescrita.
**Motivo:** era um bug, não uma preferência. Com o id fixo, a segunda execução do mesmo comando
devolvia a mesma startup **duas vezes** no briefing — medido: `run 1 -> 1 análise`,
`run 2 -> 2 análises, ['Acme', 'Acme']`. A causa não é o reducer: `thread_id` é a identidade da
**conversa**, não do processo. Invocar de novo no mesmo thread não recomeça — o checkpointer
restaura os canais e o run continua, então o `operator.add` de `analises` soma em cima do
anterior. Isso é o comportamento **correto** de retomada; o erro foi usar retomada como default.
As outras duas alternativas "consertariam" o sintoma quebrando a semântica: zerar canais no
início impede retomar de verdade (que é justamente o que o `PostgresSaver` vai habilitar na M2),
e tirar o reducer quebraria o fan-in.
**Onde isso aparecia:** rodar o comando duas vezes gravando o vídeo.
**Reversível?** Fácil.

---

## D-023 — Fan-out vazio roteia para o Briefing, não para o silêncio
**Data:** 23/08/2026
**Decisão:** `distribuir()` devolve `"briefing"` quando o Retriever não casa nenhuma startup, e
o `path_map` da aresta condicional passa a listar `["analisar_startup", "briefing"]`. O Briefing
ganhou um caso zero que reporta o motivo e sugere como alargar a busca.
**Alternativas descartadas:** o Retriever levantar exceção quando não acha nada · o CLI checar
`startups == []` antes de imprimir · deixar como estava, tratando "sem resultado" como erro.
**Motivo:** com `[]`, nenhuma tarefa é agendada; e como o `briefing` só era alcançável pela
aresta vinda de `analisar_startup`, ele **nunca executava**. `defer=True` não cobre isso —
ele ATRASA uma tarefa já agendada, não agenda uma que não foi. O run terminava sem a chave
`briefing`, o erro ficava preso em `erros`, e o CLI imprimia `(sem briefing)`.
O ponto de produto: "não encontrei nada, e aqui está por quê" **é uma resposta do sistema**.
Levantar exceção transformaria um resultado legítimo em falha; checar no CLI colocaria regra de
apresentação fora do grafo, e a interface web da M5 teria que repetir a mesma checagem.
**É a mesma disciplina de D-010 e D-021:** ausência de resultado é um estado que merece ser
reportado, não um buraco.
**Reversível?** Fácil.

---

## D-024 — `error_handler` por nó em vez de `try/except` em volta do subgrafo
**Data:** 23/08/2026
**Decisão:** cada um dos 6 nós do subgrafo recebe `error_handler=registrar_falha`, que registra
`nó: Tipo: mensagem` em `erros` e devolve `Command(goto=END)`. O `try/except` do wrapper
permanece, rebaixado a terceiro nível.
**Alternativas descartadas:** manter só o `try/except` do wrapper · `try/except` dentro de cada
nó · deixar o handler seguir o fluxo normal em vez de saltar para o END.
**Motivo:** o `try/except` em volta de `SUBGRAFO.invoke()` entrega a garantia que D-006 prometeu
— uma startup ruim não derruba as outras — mas **descarta tudo que já tinha sido computado**:
o invoke levanta, `final` nunca é atribuído, e a startup volta com `perfil=None` e
`diagnostico=None`. Com `error_handler`, as escritas dos super-steps anteriores já estão nos
canais; o handler só acrescenta o erro. Medido num grafo de teste: falha no classifier devolve
`{'perfil': 'perfil-2', 'erros': ['classifier: ValueError: dado ruim']}` em vez de `{}`.
Isso muda o que o gerente do Inception recebe: "extraímos o perfil, a classificação falhou" é
acionável; "esta empresa falhou" não é.
`goto=END` e não seguir o fluxo porque sem diagnóstico as etapas seguintes produziriam
recomendação sem base — e recomendação sem base é exatamente o que D-009 existe para impedir.
**Os três níveis, cada um pegando uma coisa diferente:** `retry_policy` cobre falha transitória
(timeout, 5xx); `error_handler` cobre falha persistente da etapa; o `try/except` cobre falha da
própria máquina do subgrafo. O terceiro quase nunca dispara agora — e continua lá por isso.
**Nota sobre retry e erro de validação:** retry **não** resolve `ValidationError` do Pydantic.
A chamada é determinística: repetir o mesmo prompt tende a dar o mesmo erro. O que resolve é
reprompt com a mensagem de validação de volta ao modelo — fica para a M4, quando os nós virarem
LLM de verdade.
**Reversível?** Fácil — é um parâmetro por nó.

---

# Sessão 02 — RAG NVIDIA (M2), passos 1-5 do pipeline

## D-025 — Chunking estrutural por seção, com banda de tamanho e breadcrumb prefixado
**Data:** 23/08/2026
**Decisão:** a unidade de chunk é a **seção do documento** (`h1/h2/h3` no HTML, `#` ATX e setext
no markdown), passada por duas normalizações — **fundir** seções irmãs abaixo de um piso e
**dividir** seções acima de um teto — e indexada com o **breadcrumb prefixado**:
`NVIDIA NIM > Boost Throughput With NIM\n\n<texto>`. Guarda-se `texto` (limpo, é o que vira
`CitacaoRAG.trecho`) separado de `texto_indexado` (com breadcrumb, é o que é embedado).
O primeiro elemento do breadcrumb é **sempre o nome da tecnologia**, vindo do metadado de
curadoria — nunca do heading.

**Alternativas descartadas:**
- **Janela fixa 800 chars / 15% overlap.** Não some: vira o braço de controle medido (ver D-027).
- **Semântico por similaridade de embeddings** (embedar frase a frase e cortar onde a cosseno cai).
- **Um chunk por tecnologia** — 18 chunks, sem chunking real.
- **Proposições atômicas extraídas por LLM.**

**Motivo:** medi o corpus antes de decidir, buscando as 18 URLs de `contexto/03` §5 com
`scripts/coletar.py`. Três números mandaram na escolha:

1. **As páginas têm formas opostas.** NIM: 51 seções em 9.909 chars = **~194 chars por seção**.
   NeMo: 102 em 22.160 = ~217. README do TensorRT-LLM: 8 seções em 27.060 = **~3.383**.
   Um chunk por heading daria fragmento inútil num extremo e bloco grande demais no outro —
   por isso **as duas normalizações são caminho principal**, cada uma em um tipo de documento,
   e não tratamento de caso de canto.
2. **Os headings não nomeiam o produto.** Os `h3` do NIM incluem `Benefits`, `Models`,
   `Features`, `Technology`. Uma janela fixa corta a bullet `- Quantização: FP8, FP4, INT4-AWQ`
   e a separa para sempre de "TensorRT-LLM": o denso ainda recupera por "quantização", mas o
   **BM25 por "TensorRT-LLM" não recupera**, e o LLM que ler o chunk não tem como atribuir.
   Isso é perda de **atribuição**, não só de contexto — e atribuição é o 7º campo obrigatório
   do TAPI. Prefixar o breadcrumb resolve para os dois motores ao mesmo tempo.
3. **O semântico por embeddings custaria ~1.500 chamadas de embedding só para decidir
   fronteiras** — o risco nº 1 do `plano.md` é crédito. E é uma técnica desenhada para prosa
   corrida: este corpus é bullet e tabela, onde a similaridade entre frases consecutivas é
   ruído, não sinal de fronteira. O termo "chunking semântico" do TAPI **não obriga** a essa
   técnica; respeitar a estrutura que o autor do documento escreveu é semântico no sentido que
   importa.

As proposições por LLM foram descartadas por **risco, não por custo**: o LLM reescreveria o
corpus, e "rastreabilidade é requisito duro" aparece duas vezes no TAPI. Alucinação na ingestão
envenena a base de evidências inteira.

**O que ainda não está decidido:** os valores do piso e do teto. O Bloco 0 mediu que o embedder
aceita **entre 6.144 e 8.192 tokens** — ou seja, **o teto não é restrição técnica**, é escolha de
precisão de recuperação. Sai da distribuição real de chunks no Bloco 4 e é medido na sessão 04.
**Reversível?** Fácil por construção — é exatamente o que D-027 existe para garantir.

---

## D-026 — Chunker escrito à mão, sem `langchain-text-splitters`
**Data:** 23/08/2026
**Decisão:** ~80 linhas próprias em `src/rag/chunking.py`.
**Alternativas descartadas:** `RecursiveCharacterTextSplitter` / `MarkdownHeaderTextSplitter`
do `langchain-text-splitters`.
**Motivo:** é decisão de **defensabilidade**, não de "não inventado aqui". O eliminatório nº 4 é
*"código integralmente gerado sem compreensão"* — e a diferença entre "escolhi fundir irmãs sob
o pai comum porque medi 194 chars por seção nas páginas de produto" e "o splitter fez isso" é
exatamente o que a banca vai cobrar. Some a isso que `langchain-text-splitters` **não está
instalado** hoje: a alternativa custaria uma dependência nova para entregar menos controle.
A regra de fundir-com-breadcrumb-do-pai-comum não existe pronta em nenhum dos dois splitters.
**Reversível?** Fácil — mesma assinatura, é trocar a implementação.

---

## D-027 — `estrategia` como coluna, não como constante: a alternativa descartada vira controle
**Data:** 23/08/2026
**Decisão:** `chunks_nvidia` tem coluna `estrategia` e `UNIQUE (estrategia, documento_url,
ordinal)`. As duas estratégias coexistem na mesma tabela; a busca filtra por `estrategia`.
`chunk_fixo()` (~15 linhas, mesma assinatura de `chunk_estrutural()`) é gravado como `fixo-800`.
**Alternativas descartadas:** uma estratégia por vez, escolhida por constante no código —
re-ingerindo o corpus quando quisesse comparar.
**Motivo:** sem isso, D-025 é uma afirmação. Com isso, é um número. É a diferença entre dizer ao
avaliador *"escolhi chunking estrutural"* e mostrar *"estrutural dá recall@10 = X, janela fixa dá
Y, no mesmo gabarito"* — que é literalmente a descrição do nível 4 do barema, "decisões técnicas
conscientes". O custo é uma coluna e ~15 linhas; o corpus é pequeno o bastante para caber duas
vezes sem que ninguém note.
**Efeito colateral aceito:** o índice HNSW cobre as duas estratégias, então filtrar por
`estrategia` é pós-filtro. Irrelevante a algumas centenas de linhas; viraria problema num corpus
uma ordem de grandeza maior.
**Reversível?** Fácil — `DELETE WHERE estrategia = '...'`.

---

## D-028 — Fonte por tecnologia: markdown bruto no GitHub, HTML nas páginas de produto
**Data:** 23/08/2026
**Decisão:** o manifesto `data/nvidia/fontes.yaml` declara o `formato` de cada fonte. GitHub é
lido em `raw.githubusercontent.com/.../README.md`; páginas de produto em HTML via `extrair()`.
A ingestão tem **piso de qualidade** — mínimo de caracteres e de headings — que **falha alto**,
com o nome da tecnologia na mensagem.
**Alternativas descartadas:** HTML uniforme para tudo · deixar a ingestão aceitar o que vier.
**Motivo:** medido, não deduzido. O texto extraído de `github.com/NVIDIA/TensorRT-LLM` começa com
*"Uh oh! There was an error while loading… Go to file… Last commit message"* — é o chrome do
GitHub, que renderiza o README por JS. O `raw.githubusercontent.com` devolve **27.060 chars de
markdown limpo**, com a estrutura de headings intacta. Mesma fonte, qualidade incomparável.
O piso existe porque a mesma varredura achou **4 URLs das 18 sem conteúdo utilizável**: API
Catalog (28 chars, é SPA), cuDF (558), cuML (1.911, zero headings), Triton docs (2.753, 2
headings). Sem o piso, essas quatro entrariam na base como chunks vazios e o RAG responderia
"não sei" sobre cuDF sem ninguém entender por quê. Falhar alto transforma isso em tarefa de
curadoria, que é onde o problema pertence.
**Reversível?** Fácil — é uma linha no manifesto por fonte.

---

## D-029 — Guardar `embedding_bruto vector(2048)` sem índice ao lado do `vector(1024)` indexado
**Data:** 23/08/2026 · **verificado por medição no mesmo dia**
**Decisão:** duas colunas. `embedding vector(1024)` com índice HNSW é a que a busca usa;
`embedding_bruto vector(2048)` fica **sem índice**, só para o harness derivar 384/768/1024 por
truncagem local.
**Alternativas descartadas:** só `vector(1024)`, re-embedando o corpus quando a sessão 04 quisesse
comparar dimensões.
**Motivo, agora com número:** D-014 registrou que trocar de dimensão exige re-embedar o corpus, e
tratou isso como custo aceito. **Testei se dá para evitar** (`scripts/verificar_embedder.py`):
embedei o mesmo texto pedindo 2048 e pedindo 1024/768/384, truncei o de 2048 localmente e
renormalizei. `cos(api, truncagem_local)` = **0.99999996 · 0.99999996 · 0.99999995**. A promessa
Matryoshka se confirma nas três dimensões — o sweep da sessão 04 passa a custar **zero chamada de
API**, é fatiar a coluna.
Dois achados de brinde, do mesmo teste:
- **os vetores voltam já normalizados** (norma L2 = 1.000063), então cosseno e produto interno
  são equivalentes aqui. Isso deixa de ser dúvida e vira frase no README;
- **o embedder aceita entre 6.144 e 8.192 tokens** de entrada (aprox. `tiktoken`). Muito acima de
  qualquer chunk desejável — o limite do modelo **não** é o que fixa o teto de D-025.
**Custo:** ~8 KB por chunk, alguns MB no corpus inteiro. Verifiquei em psql que `vector(2048)`
armazena normalmente e que só o **índice** HNSW recusa acima de 2000 dimensões.
**Reversível?** Fácil — `DROP COLUMN` quando a sessão 04 terminar o sweep.

> **Nota de atualização em D-014** (o log é append-only, D-014 não é reescrita): a
> reversibilidade que ela registrou como "média — mudar a dimensão exige re-embedar o corpus"
> passa a ser **fácil**, pela equivalência medida acima. A escolha de 1024 continua valendo pelo
> motivo original: é o que cabe no HNSW nativo do pgvector.

---

## D-030 — Gabarito ancorado no documento-fonte, não no chunk
**Data:** 23/08/2026
**Decisão:** cada pergunta de `data/avaliacao/gabarito.yaml` aponta para a **URL do documento** que
a responde. `recall@k` = "algum dos k primeiros chunks veio do documento certo". A `frase_ancora`
é opcional e habilita uma variante estrita: "e o chunk contém a frase".
**Alternativas descartadas:** ancorar em `id` de chunk · ancorar só na frase exata.
**Motivo:** ancorar no chunk amarraria a métrica a uma estratégia de chunking — e a comparação
entre estratégias é justamente o que D-027 existe para permitir. Um gabarito preso a ids de chunk
teria que ser reescrito a cada mudança de banda, o que na prática significa nunca mudar a banda.
Ancorar na URL faz a régua sobreviver a qualquer re-chunking.
**Por que o gabarito é escrito agora e não na sessão 04:** é preciso ler as 18 páginas para
curar as fontes de qualquer jeito. Escrever a pergunta durante essa leitura é quase de graça;
na sessão 04 custaria reler tudo.
**Reversível?** Fácil — é dado versionado, não código.

---

## D-031 — Busca densa e `recall@k` entram na sessão 02, não na 03/04
**Data:** 23/08/2026
**Decisão:** a sessão 02 entrega também `buscar_denso(query, k, estrategia)` (~20 linhas de SQL) e
`scripts/avaliar_rag.py` com `recall@k`. Sai da sessão com a tabela estrutural-vs-fixo preenchida.
BM25, fusão e reranking continuam intocados na sessão 03.
**Alternativas descartadas:** manter o corte de `sessao-02.md` (02 termina com a tabela populada) ·
fundir 02 e 03 numa sessão só.
**Motivo:** duas razões, uma de coerência e uma de método.
(1) `sessao-02.md` define o critério de pronto da **03** como *"cada incremento foi medido contra o
gabarito"*, mas agenda o harness que calcula recall@k para a **04**. Como estava, o critério da 03
dependia de um artefato que ainda não existia.
(2) A 02 decide chunking e dimensão. Sem instrumento, ela decide por argumento e descobre por
medição depois — que é exatamente o que o próprio arquivo diz querer evitar quando moveu o
gabarito para cá. Mover o *dado* (gabarito) sem mover a *função que o consome* fazia metade do
movimento.
**Por que não fundir 02 e 03:** a medição do corpus é argumento contra. 4 das 18 URLs precisam de
re-curadoria e o GitHub precisa de outro caminho de fetch — a coleta vai consumir mais que o
previsto, exatamente como `sessao-02.md` antecipou. Fundir faria da busca híbrida a parte cortada
às pressas, e ela é metade do critério 2.
**Reversível?** N/A — é decisão de sequenciamento.

---

## D-032 — D-025 confirmada por medição, e `recall@3` é a métrica que discrimina
**Data:** 23/08/2026 · **é o resultado, não a intenção**
**Decisão:** manter `estrutural-v1` como estratégia de produção. A comparação com o braço de
controle, no gabarito de 20 perguntas, recuperação densa pura, 1024 dimensões:

| k | estrutural frouxo | fixo-800 frouxo | estrutural estrito | fixo-800 estrito |
|---|---|---|---|---|
| 1 | 89% | 84% | 68% | 58% |
| **3** | **100%** | **84%** | **79%** | **68%** |
| 5 | 100% | 100% | 84% | 74% |

**O que os números dizem, incluindo o que eles não dizem:**

1. **`recall@5` satura e não serve para decidir.** 100% nos dois braços. Com 16 documentos e
   k=5, a pergunta é fácil demais. Reportar só o k=5 esconderia a diferença inteira — é o tipo
   de métrica que parece boa e não informa nada.
2. **k=3 é o ponto de discriminação: 100% contra 84%**, 16 pontos de diferença.
3. **O estrito separa mais que o frouxo em todo k** (79% vs 68% em k=3). Faz sentido: o frouxo
   só pergunta se o documento certo apareceu, e a página do TensorRT-LLM tem 27 mil caracteres
   — recuperar qualquer pedaço dela não prova que o pedaço responde.
4. **A q19 fez exatamente o que foi desenhada para fazer.** Ela pergunta por um trecho que está
   na página do NIM mas cujo texto destaca "TensorRT-LLM" e nunca repete "NIM". Em k=1 os
   **dois** braços erram — o breadcrumb não põe o chunk em primeiro. Em k=3 o estrutural
   acerta e o fixo continua errando. É a validação medida do argumento central de D-025, e
   também o limite dele: o breadcrumb leva o chunk certo para a zona onde o reranker pode
   promovê-lo, não para o topo sozinho.
5. **A q14 (cuDF vs cuML) erra em k=1 nos dois braços**, recuperando cuML. Os dois READMEs têm
   estrutura e vocabulário quase idênticos. É honestamente um caso para o léxico: `cudf.pandas`
   é literal e o BM25 deveria resolver — fica como previsão registrada para a sessão 03.

**Alternativa descartada, agora com número:** `fixo-800` perde em todas as seis células.
**Reversível?** A tabela é reprodutível com `python scripts/avaliar_rag.py`. Se a sessão 04
mudar a banda ou a dimensão, esta tabela é refeita — e é para isso que ela existe.

> **Nota de atualização em 24/08** (o log é append-only, o texto acima não é reescrito): a
> **previsão do item 5 sobre a q14 acerta o resultado e erra o mecanismo.** Ela diz *"a âncora
> `cudf.pandas` é literal e o BM25 deveria resolver"* — mas **`cudf.pandas` não está na
> consulta**, que é *"dá para acelerar um pipeline de pandas em GPU sem reescrever o código?"*.
> O BM25 casa termos da CONSULTA contra o documento; a âncora ser literal é irrelevante se ela
> não for consultada. O que de fato resolve é a frequência de `pandas`: 15 ocorrências em 2
> chunks do cuDF, 3 em 1 do RAPIDS, **zero no cuML** — que é quem ganhava em k=1. O braço
> lexical isolado de fato põe o cuDF em 1º (D-037).
>
> E há um segundo erro embutido, maior: a q14 **não é falha de recuperação**. O chunk que o
> reranker escolhe (RAPIDS/CUDA-X) diz literalmente *"zero-code-change APIs that accelerate
> popular PyData tools like pandas and scikit-learn"*, e responde a pergunta como ela está
> escrita melhor que qualquer chunk do cuDF. **A pergunta é que está subespecificada.** Ver
> D-038, incluindo a decisão de não reescrevê-la depois de ver o resultado.

---

## D-033 — Abstenção não sai de limiar sobre o score denso
**Data:** 23/08/2026 · **achado que muda a sessão 03**
**Decisão:** o sistema **não** vai decidir "não sei" comparando `score_denso` com um limiar.
A decisão de abstenção passa a ser requisito do reranker (sessão 03) e, se ele não bastar, da
geração.
**Alternativas descartadas:** limiar sobre a similaridade densa — que era o caminho óbvio e
o que eu teria implementado sem medir.
**Motivo — medido, e o resultado é o contrário do esperado:** a pergunta q20 do gabarito não
tem resposta na base (pede o preço da licença do AI Enterprise, que a página não publica).
Ela recuperou:

```
0.4813  NVIDIA AI Enterprise  "Try it for free... Download and prototype... before deploying"
0.4607  NVIDIA AI Enterprise  "Getting Started With NVIDIA AI Enterprise on AWS Marketplace"
0.4553  NVIDIA AI Enterprise  "Activate Your License / The Reliable and Secure Path for AI..."
```

Os três são **topicamente perfeitos** — AI Enterprise, licenciamento, como começar — e nenhum
contém um preço. E o score de 0.4813 é **mais alto que o pior acerto verdadeiro** (0.2934 no
estrutural, 0.3302 no fixo). A margem é **negativa nos dois braços**: −0.1879 e −0.1200. As
distribuições se sobrepõem, então **não existe limiar** que abstenha na q20 sem descartar
respostas corretas.

**A razão é conceitual, não um defeito do modelo:** similaridade de embedding mede
**pertinência de tópico**, não **existência de resposta**. Uma pergunta bem formulada sobre um
assunto que a base cobre casa bem com a base — exatamente por ser bem formulada.

**Consequência prática para a sessão 03:** o cross-encoder do reranker pontua o par
(consulta, passagem) julgando se aquela passagem **responde** aquela pergunta, o que é uma
pergunta diferente da que o bi-encoder responde. É a hipótese a testar, com este mesmo gabarito
e esta mesma margem como medida do antes.
**Reversível?** N/A — é um achado. O que é reversível é o mecanismo que se escolher no lugar.

---

## D-034 — A janela do reranker é 8192 conjuntos, e `TETO_TOKENS = 450` fica por outro motivo
**Data:** 24/08/2026 · **Bloco 0 da sessão 03, bloqueante** · é o resultado, não a intenção
**Decisão:** manter `TETO_TOKENS = 450` e **reescrever a justificativa dele**. O comentário antigo
em `src/rag/chunking.py` dizia *"450 cabe com folga na janela típica de um cross-encoder (512)"* —
essa janela **não existe** neste modelo.

**O que foi medido:** `llama-nemotron-rerank-1b-v2` aceita **8.192 tokens somando query e
passagem**. Dois métodos, resultados coerentes:

1. **A API entrega o número de graça se o payload omitir `truncate`.** Com `truncate` ela corta em
   silêncio; sem ele, recusa: `HTTP 422 — Input length 19886 exceeds maximum allowed token size
   8192`. Isso não estava em documentação nenhuma que consultei.
2. **A janela é conjunta, confirmado por bissecção.** Query de 6 tokens aceita passagem de
   ~8.212; query de 78 tokens aceita ~8.137. O que prova a conjunção não é o corte andar — é
   **a soma ser invariante**: 8.218 e 8.215, com queries que diferem em 72 tokens. E a contagem
   da própria API no limite (8.223-8.226) bate com 8.192 mais tokens especiais.
   Consequência prática: o orçamento real de um chunk é `8.192 − a maior consulta plausível`.
   Com as perguntas do gabarito em 24-45 tokens, isso é irrelevante aqui — mas deixa de ser se
   o Recommendation Agent passar a mandar o perfil inteiro da startup como consulta.

O diferencial ao estilo do `verificar_embedder.py` — `logit(A)` idêntico a `logit(A + marcador)`
significa que os dois foram cortados no mesmo ponto — também rodou e não achou corte até 4.096,
consistente com os 8.192.

**O achado que de fato importa, e que não era o objetivo do bloco — a diluição.** A mesma
frase-resposta afogada em enchimento crescente, mesma query:

| passagem | só enchimento | com a frase-resposta (2 execuções) |
|---|---|---|
| 25 tok (a frase sozinha) | — | **−0,36** |
| 63 | −25,03 | −7,96 · −7,96 |
| 199 | −25,03 | −9,10 · −4,55 |
| 449 | −25,03 | −10,24 · −6,83 |
| 599 | −22,75/−25,03 | −5,69 · −4,55 |
| 799 | −22,75 | −9,10 · −9,10 |
| 1199 | −20,48/−22,75 | −10,24 · −11,38 |
| 1999 | −20,48/−22,75 | −12,52 · −10,24 |

**Uma ressalva antes da leitura, porque ela muda o que se pode afirmar:** rodei duas vezes e os
logits **não reproduzem dígito a dígito** — 449 tokens deu −10,24 numa execução e −6,83 na outra.
A forma se manteve; os valores não. Então isto **não é uma curva**, é uma faixa. Qualquer
afirmação sobre diferença de 2-3 logits entre dois tamanhos seria ruído vendido como sinal.

O que sobrevive à variância, e é o suficiente para decidir: **caber na janela não é o mesmo que
pontuar bem nela.** De 63 a ~600 tokens os valores ficam entre −4,5 e −10 sem tendência; de ~800
em diante ficam entre −9 e −12,5 nas duas execuções. O reranker **não impõe** o teto do chunk —
ele **cobra** por chunk grande, e a cobrança começa a aparecer em algum ponto entre 600 e 800. Somado ao Bloco 0 da sessão 02 — o embedder
aceita 6.144 a 8.192 — os **dois motores** confirmam que o teto de D-025 é escolha de precisão de
recuperação, e nenhum dos dois o restringe. O sweep de `TETO` da sessão 04 ganha uma faixa de busca
fechada em vez de aberta.

**Consequência operacional registrada aqui porque ela vai morder depois:** os logits voltam
**quantizados** — `−25,0312`, `−22,7500`, `−10,2422` se repetem exatamente entre chamadas
independentes, o que é assinatura de bf16. Somando isso à variância entre execuções acima,
**nenhuma lógica do sistema pode depender de margem abaixo de ~2 logits**: abaixo disso não há
diferença, há o passo da grade mais o ruído do serving. Isso vale especialmente para qualquer
limiar de abstenção que se queira construir sobre o logit.

**Alternativa descartada:** manter o comentário como estava e seguir. Descartada porque o
eliminatório nº 4 é sobre defender decisões: um número certo (450) sustentado por um fato falso
(janela de 512) é pior que um número errado, porque a banca pergunta pelo raciocínio e não pelo
valor.
**Risco que o bloco existia para matar, e que não existia:** se a janela fosse menor que 450, todo
chunk acima dela teria o final truncado no rerank. Não é o caso — nenhum chunk do corpus chega
perto (máximo medido: 446 tokens contra 8.192 disponíveis).
**Reversível?** N/A — é medição.

## D-041 — `Passagem` interna, `CitacaoRAG` de contrato: dois tipos, não um
**Data:** 24/08/2026
**Decisão:** o pipeline de recuperação (`src/rag/`) trabalha com `Passagem` — um dataclass com
`chunk_id`, `texto`, `texto_indexado`, `caminho_secao`, `documento_url`. A conversão para
`CitacaoRAG` acontece **só na borda**, em `para_citacao()`.
**Alternativas descartadas:** acrescentar `chunk_id` e `texto_indexado` ao próprio `CitacaoRAG`
(seria um campo a mais e nenhum arquivo novo) · casar os rankings pelo texto do trecho.
**Motivo:** a fusão precisa reconhecer que o item no ranking denso e o item no ranking lexical são
o **mesmo chunk**. Casar por texto é frágil (qualquer normalização quebra) e caro (comparação de
strings longas em O(n·m)); o id vem do banco de graça.

O que decidiu contra colocar os campos em `CitacaoRAG` foi **onde ela mora**: em `src/state.py`,
dentro do estado do grafo, e ela vai para `Recomendacao.citacoes_rag`. `chunk_id` e
`texto_indexado` são detalhes de implementação da recuperação — o breadcrumb prefixado existe para
o embedder e para o reranker lerem (D-025, D-038), não para o agente. Mantendo a fronteira,
trocar a fusão ou o reranker **não propaga para o estado do grafo**, que é a peça mais cara de
mexer depois (o risco "estado mal modelado, exigindo refatorar os 8 nós" está no `plano.md`).
**Custo aceito:** uma conversão explícita e ~25 linhas. Em troca, `src/state.py` não muda nesta
sessão por causa de recuperação.
**Reversível?** Fácil — é tipo interno, nada fora de `src/rag/` o conhece.

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
