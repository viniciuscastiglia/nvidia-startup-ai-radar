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

**Atualização — 25/08/2026 (D-046). Aconteceu de novo, e a lição que faltava é esta.** Os dois
substitutos escolhidos AQUI — `llama-nemotron-embed-1b-v2` e `llama-nemotron-rerank-1b-v2` —
morreram com o mesmo HTTP 410 em **25/08/2026 09:00Z**, três dias depois de adotados.

Esta decisão tirou a conclusão de que *o TAPI está desatualizado* e marcou o episódio como
material de vídeo. Havia uma segunda conclusão disponível, mais cara e mais útil: **o catálogo de
preview do build.nvidia.com aposenta modelos em cadência de MESES, e o projeto inteiro está
montado nele.** Um EOL é anedota; dois é a taxa de falha do fornecedor. A tabela de riscos do
`plano.md` só ganhou essa linha em 25/08.

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

**Atualização — 25/08/2026 (D-046).** O `llama-nemotron-embed-1b-v2` morreu (HTTP 410). Adotado
`nvidia/llama-nemotron-embed-vl-1b-v2`, que aceita `dimensions` 1024 e 2048 — schema, HNSW e
D-029 ficam intactos.

**Dois números desta decisão foram re-testados três dias depois, em outro processo, e
reproduziram:** o `nemotron-3-embed-1b` deu **0,5241 vs 0,1137**, os mesmos dígitos registrados
aqui, e continua recusando `dimensions=1024` com HTTP 400 exatamente como escrito. A alternativa
descartada segue descartada — mas por pouco: na sonda de 25/08 ela separa **melhor** que o VL
(margem crosslingual +0,4323 vs +0,3801), e só não foi adotada porque 1,14x não paga o custo de
preencher a coluna indexada por truncagem local não verificável naquele modelo.

**A frase "a decidir depois, com medida: 1024 vs 768 vs 384" continua não resolvida** — e agora
tem um custo a mais, porque qualquer sweep de dimensão precisa rodar na stack nova.

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
  > **CORREÇÃO DE 27/08 (D-065): "é pago" está ERRADO, e era verificável em 22/08.** A Cohere
  > oferece **trial key gratuita** cobrindo Command, Embed e Rerank — 1.000 chamadas/mês, Rerank a
  > 10 req/min, vedada a uso comercial (o que não é o caso de um processo seletivo). O motivo real
  > que sobra é o segundo, e ele é **narrativo**, igual ao que descartou o cross-encoder local
  > logo abaixo. Ou seja: as DUAS alternativas ao fornecedor único foram descartadas por narrativa,
  > uma delas com um fato falso em cima. Foi isso que deixou o projeto sem contingência em 25/08 e
  > sem reranker nenhum em 27/08.
- **Cross-encoder local** (BGE, Jina) — sem custo de API, mas exige baixar e rodar o modelo, e
  perde o argumento do Diferencial.
**Motivo:** o corpus do RAG é texto puro (documentação NVIDIA). O ganho do modelo VL é entender
imagem, o que não se aplica aqui — e ele paga esse ganho em precisão no texto. Escolher o VL
porque "é o mais novo" seria decidir por recência em vez de por adequação.
**Reversível?** Fácil — duas linhas do `.env` (modelo e URL, que embute o modelo no path).

**Atualização — 25/08/2026 (D-046). Esta decisão é a que envelheceu pior, e vale dizer por quê.**
O `llama-nemotron-rerank-1b-v2` morreu com HTTP 410, e o VL descartado aqui morreu junto. Sobrou
**um** reranker no catálogo, o `nvidia/rerank-qa-mistral-4b` — não houve escolha a fazer.

Duas correções ao que está escrito acima:

1. **"Duas linhas do `.env`" subestimou.** A URL nova é genérica (`.../nvidia/reranking`) e NÃO
   embute o modelo no path, então a forma da URL também mudou; e trocar o reranker obriga a
   re-medir janela, escala de logit e a régua inteira, porque um 4B não pontua como um 1B.
2. **O cross-encoder local foi descartado aqui com o motivo *"perde o argumento do Diferencial"*
   — um motivo narrativo, não de engenharia.** É a única linha deste log onde uma história venceu
   uma propriedade técnica, e é exatamente por causa dela que em 25/08 não havia caminho de
   contingência: o projeto ficou parado até um substituto ser achado, sondado e o corpus
   re-embedado. O Diferencial não é usar a stack NVIDIA; é ter medido a propriedade do fornecedor
   que ninguém mediu. Um fallback local documentado **fortalece** esse argumento.
   Fica como Bloco 0 da próxima sessão.

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

**Atualização — 24/08/2026, sessão de revisão.** Três correções, todas medidas
(`scripts/auditoria/auditoria_diluicao.py` e `auditoria_lote.py`):

1. **"Os logits não reproduzem dígito a dígito" não se confirmou.** Quatro execuções novas dos
   nove tamanhos deram 36 de 36 logits IDÊNTICOS. A hipótese de que a variação vinha da
   composição do lote foi testada e DERRUBADA: 18 chamadas em 6 composições (1, 2, 10 e 30
   passagens, ordens trocadas) devolveram sempre −6,8281. A variação registrada aqui é rara e
   intermitente, não sistemática. A regra operacional — nada depende de margem abaixo de ~2
   logits — continua valendo; o mecanismo descrito acima não descreve o que se observa.
2. **O teste de diluição tem um problema de VALIDADE que a ressalva de variância não cobre.** O
   enchimento fala de cuDF enquanto a query pergunta de NIM: o que ele mede é "o chunk ficou mais
   off-topic", não "o chunk ficou maior". Um chunk real de 800 tokens é 800 tokens sobre o mesmo
   produto.
3. **Refeito com texto REAL** (chunks vizinhos concatenados do documento do NIM, que é o que um
   TETO maior produziria): 176→−2,56 · 380→−2,56 · 564→−6,83 · 712→−9,10 · e depois PLATÔ entre
   −6,26 e −9,10 até 2.181. Duas execuções idênticas. A cobrança começa entre 380 e 564, não
   entre 600 e 800, e SATURA. Isso reforça TETO_TOKENS=450 e fecha a faixa de busca do sweep em
   ~120–560, não ~800. Limite: um documento, uma consulta.

---

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

## D-036 — BM25 variante `lucene`, e a tokenização que dobra acento
**Data:** 24/08/2026 · três decisões medidas dentro de uma
**Decisão:** `bm25s` com `method="lucene"`, `k1=1.2`, `b=0.75`, sobre `texto_indexado`, com
tokenizador próprio que **dobra acento**, **preserva o ponto entre alfanuméricos** e **não usa
stemmer**.

### 1. Variante: `lucene`, não o Okapi original (`robertson`)

**Alternativa descartada:** `method="robertson"` — o BM25 do artigo original, que é o que "Okapi de
verdade" sugere e o que eu teria escolhido por fidelidade histórica.

**Motivo, medido neste corpus:** a palavra **"nvidia" ocorre em 163 dos 177 chunks (92%)**. O IDF
de Robertson, `ln((N−df+0.5)/(df+0.5))`, dá **−2,4227** para ela. Negativo. Num corpus que é
inteiramente documentação da NVIDIA, e com consultas que quase sempre dizem "NVIDIA", o Okapi
original **puniria o chunk por conter a marca**. O IDF do Lucene, `ln(1 + (N−df+0.5)/(df+0.5))`,
é sempre positivo — 0,0850 no mesmo caso.

| termo | df | df/N | idf robertson | idf lucene |
|---|---|---|---|---|
| `and` | 173 | 98% | **−3,6521** | 0,0256 |
| `nvidia` | 163 | 92% | **−2,4227** | 0,0850 |
| `ai` | 123 | 69% | **−0,8180** | 0,3655 |
| `colang` | 5 | 3% | 3,4456 | 3,4770 |

IDF negativo é um problema conhecido do BM25 original e some em corpus grande e heterogêneo, onde
nenhum termo de conteúdo chega a 90% de df. **Corpus pequeno e temático é exatamente onde ele
morde** — e o nosso tem 177 chunks sobre um assunto só.

### 2. `k1 = 1.2` e `b = 0.75`, explícitos

D-016 justifica `bm25s` por `k1` e `b` serem ajustáveis. Deixá-los no default da biblioteca
entregaria o argumento sem entregar a coisa. Os valores são os clássicos do Okapi, e o motivo de
cada um é concreto aqui:
- **`k1` (saturação de tf)** decide a q14: "pandas" ocorre 15 vezes em 2 chunks do cuDF contra 3
  vezes em 1 do RAPIDS, e é a repetição que separa os dois.
- **`b` (normalização por comprimento)** pesa menos que o normal neste sistema, porque o chunker
  estrutural **já normaliza comprimento** numa banda de 120 a 450 tokens (D-025). A variação que
  `b` existe para corrigir foi em boa parte corrigida antes, no passo 3.

O sweep de `k1 × b` custa **zero chamada de API** (o BM25 é local) e fica para a sessão 04, junto
do sweep de dimensão e de teto.

### 3. Tokenização — a dobra de acento não é higiene, é requisito

**Sem `NFD` + remoção de diacrítico, a regex parte a palavra no acento:** `genômica` → `gen` +
`mica`, `inferência` → `infer` + `ncia`, `português` → `portugu` + `s`. **Metade do vocabulário
das consultas viraria lixo.** Isso não é hipótese: na primeira medição do sinal lexical do
gabarito, a q12 apareceu classificada como ATRAPALHA por causa do termo espúrio `gen`.

**O ponto sobrevive entre alfanuméricos e morre no fim da frase** (`[a-z0-9]+(?:\.[a-z0-9]+)*`):
`cudf.pandas` é identificador e é a âncora da q14; `containers.` é pontuação.
*Efeito colateral aceito:* uma ocorrência de `cudf.pandas` não conta como ocorrência de `pandas`.
A alternativa — emitir o token inteiro **e** as partes — inflaria tf e comprimento do documento,
mexendo em `k1` e `b` por via indireta.

**Sem stemmer.** `PyStemmer` seria dependência nova, e stemming de inglês não ajuda consulta em
português. O valor do léxico aqui é nome literal de produto, que stemmer nenhum melhora.

### 4. Score zero é ausência, não evidência fraca

`buscar_lexical_bruto` **descarta resultados com score 0**. Um chunk com score zero não contém
nenhum termo da consulta — é ausência de evidência lexical. Deixá-lo entrar poluiria o pool da
fusão com ruído ranqueado. **É o que faz a q18 devolver lista vazia** (a consulta é inteiramente
em português: `monitorar`, `metricas`, `servidor`, `inferencia`, `producao`, e nenhum desses
termos existe no corpus em inglês). O braço lexical dizer "não tenho nada" é resposta correta.

### O braço lexical sozinho, medido

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| denso (linha de base, D-032) | 89% | 100% | 100% | 68% | 79% | 84% |
| **lexical** | **58%** | **63%** | **74%** | 42% | 47% | 63% |

**Ele é pior que o denso em tudo — e isso era o esperado.** O que importa é *onde* ele erra:
q05, q09, q12, q16, q18. Antes de escrever uma linha eu medi o sinal lexical de cada pergunta
(soma de idf dos termos da consulta que casam no corpus) e marquei 6 como MUDO ou ATRAPALHA.
**5 dessas 6 são exatamente as 5 falhas.** A complementaridade com o denso é medida, e é ela que
justifica **fundir** os dois em vez de trocar um pelo outro.

**Dívida conhecida, deixada de propósito:** `&nbsp;` vaza para o `caminho_secao` de 7 chunks (bug
de limpeza da sessão 02). Nenhuma consulta contém o termo, então o efeito em recuperação é nulo;
o efeito é cosmético no breadcrumb. Consertar exige re-ingerir → re-embedar → **invalidar a linha
de base de D-032 no meio da sessão**. Vai junto do re-ingest que a sessão 04 já fará pelo sweep de
teto.
**Reversível?** Fácil — `METODO`, `K1`, `B` e o tokenizador são constantes de um módulo só.

**Atualização — 24/08/2026, sessão de revisão.** A tabela de IDF acima foi calculada num script
solto com tokenizador inline, não com `src.rag.lexical.tokenizar`. Recalculada com o tokenizador
real (`scripts/auditoria/idf_lucene_vs_robertson.py`):

1. **A linha `and` não existe.** `and` está na STOPWORDS e nunca vira token: não tem df, não tem
   IDF e não participa de ranking. As outras três linhas reproduzem exatas sobre `texto_indexado`.
2. **O ARGUMENTO CENTRAL ESTÁ ERRADO PARA A BIBLIOTECA EM USO.** `bm25s/scoring.py:178` trava o
   IDF de Robertson em zero (`if inner < 1: inner = 1`), e `allow_negative` não é passado de lugar
   nenhum. Medido no índice real: com `robertson`, `nvidia` e `ai` pontuam exatamente +0,0000. O
   Okapi original NEUTRALIZA o termo, não o pune. A fórmula citada acima é a do artigo, não a do
   `bm25s`.
3. **O recall é idêntico nas duas variantes:** 58/63/74 e 42/47/63, os seis números. A escolha não
   tem consequência medida neste corpus — um termo com df de 92% é quase um deslocamento
   constante em qualquer das duas fórmulas.

A decisão (`lucene`) FICA, e o argumento passa a ser este: só 2 de 3.063 termos do vocabulário
teriam IDF negativo pela fórmula do papel, mas são `nvidia` e `ai`, e 14 das 24 consultas contêm
um dos dois — sob `robertson` esses tokens ficariam inertes; sob `lucene` contribuem pouco e
positivo. É um argumento mais estreito que o escrito, e sem efeito na régua.

---

## D-037 — Fusão por RRF, soma ponderada como controle — e o léxico não paga o que custa
**Data:** 24/08/2026 · **o resultado contraria a expectativa da pauta**
**Decisão:** `fundir_rrf` é o motor de produção, com `K`, `peso_denso` e `peso_lexical`
explícitos; `fundir_soma` existe implementada e medida como **braço de controle** (padrão de
D-027). Default de produção: **RRF, `K=10`, denso 1.0, lexical 0.3**.
**Alternativas descartadas:** só soma ponderada · só RRF · não implementar o braço lexical.

### Por que RRF e não soma ponderada — o argumento é medido, não citado

RRF é o default do Elastic, Qdrant, Weaviate e OpenSearch, e vem de Cormack, Clarke & Buettcher
(2009). Isso resolve a pergunta na banca em uma frase, mas não é a razão. A razão é **D-033**: a
magnitude do score denso **não é calibrada** — a q20, que não tem resposta na base, recupera com
0,4813, mais alto que o pior acerto verdadeiro (0,2934). Uma fusão que consome magnitude consome
um sinal que já medimos ser não confiável. RRF só olha posição.

A soma ponderada foi implementada e medida assim mesmo, e a normalização é **parâmetro** porque
ela é a decisão escondida dentro da decisão: `minmax` faz o 1º colocado valer 1,0 *por
construção*, então na q20 os 0,4813 viram 1,0 igual a um acerto perfeito — ela **fabrica**
confiança exatamente onde o sistema precisa abster-se.

### `K` é parâmetro e não a constante 60 da literatura — e a medição confirma

Com `K=60` e listas de 20, as contribuições vão de 1/61 a 1/80: **31% de amplitude**, e o RRF
degenera em "aparece nas duas listas?". A varredura confirma: `K=60` é **uniformemente pior** que
`K=10` em toda a grade de pesos. Corpus pequeno e pool curto é onde esse defeito morde.

### A varredura completa, que custou zero chamada de API

As listas densa e lexical são recuperadas uma vez por consulta e reaproveitadas; RRF e soma são
funções puras delas. Grade inteira em 13 segundos, sem gastar crédito — mesmo truque de D-029.

| fusão | K/norm | peso lex | r@1 | r@3 | q05 |
|---|---|---|---|---|---|
| — (denso puro) | — | — | **89%** | **100%** | #1 |
| rrf | 10 | 0.3 | 84% | 100% | #1 |
| rrf | 10 | 1.0 | 63% | 89% | #2 |
| rrf | 60 | 0.3 | 68% | 89% | #2 |
| soma | minmax | 0.3 | **89%** | **100%** | #1 |
| soma | soma | 1.0 | 68% | 79% | #2 |

**Nenhuma configuração bate a linha de base.** A melhor apenas empata.

### O achado que importa: o léxico não paga o que custa NESTE gabarito

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| denso | 89% | 100% | 100% | 68% | 79% | 84% |
| lexical | 58% | 63% | 74% | 42% | 47% | 63% |
| híbrido | 84% | 100% | 100% | **74%** | 79% | 84% |
| **rerank sobre denso** | **95%** | 100% | 100% | 79% | 84% | 95% |
| **rerank sobre híbrido** | **95%** | 100% | 100% | 79% | 84% | 95% |

**As duas últimas linhas são idênticas.** Depois do reranker, o braço lexical contribui **zero**.
E no tamanho do pool (k=20) o denso sozinho já dá r@20 = 100% e e@20 = 95% — o léxico também não
acrescenta candidato novo que importe.

Um detalhe que sobrevive: **antes** do rerank a híbrida é melhor no critério estrito (e@1 74% vs
68%) e pior no frouxo (84% vs 89%). Faz sentido — o BM25 casa a âncora literal, que mora no chunk
da resposta, então ele acha o *chunk* certo mais vezes e o *documento* certo menos. O reranker
chega ao mesmo chunk sozinho.

### Por que a fusão não propaga as duas vitórias do léxico — dois mecanismos diferentes

O denso acerta 17 de 19 em 1º lugar; suas únicas falhas são q14 e q19. **O léxico acerta
exatamente essas duas em 1º.** Complementaridade perfeita, e mesmo assim a fusão não a colhe:

- **q19 — ranks espelhados, e o RRF só obedece à ordem dos PESOS.** O chunk 38 (NIM, certo) é
  denso #2 e lexical #1; o chunk 181 (TensorRT-LLM, errado) é denso #1 e lexical #2. Como as
  posições são simétricas e o RRF só soma posições, **o resultado não depende de evidência
  nenhuma — depende só de qual peso é maior**: com `denso > lexical` vence o 181 (errado), com os
  pesos iguais empatam exatamente, com `lexical > denso` vence o 38 (certo).
  **Não existe ajuste intermediário que decida o caso pelo mérito.** E o lado que consertaria a
  q19 é precisamente o que quebra a garantia crosslingual da q05, onde o braço lexical é mudo.
  É um trade-off sem solução interior, e é o custo estrutural de descartar magnitude.
  *(Este parágrafo está mais preciso do que eu o escrevi da primeira vez: eu havia registrado
  "empatam sempre, nenhum peso quebra". O teste `test_rrf_em_ranks_espelhados_so_obedece_a_ordem_dos_PESOS`
  derrubou a afirmação — o empate só ocorre em `w_denso == w_lexical`.)*
- **q14 — crédito dividido entre chunks.** O léxico põe o chunk 226 do cuDF em 1º; o denso põe o
  227. Documento certo forte nos dois braços, espalhado por chunks diferentes, nenhum acumula. E o
  chunk 209 (RAPIDS) é denso #2 **e** lexical #3, ganha crédito duplo e sobe na frente.

### A decisão: manter, com o número escrito em vez de escondido

A regra da sessão manda remover incremento que não move a métrica. Mantive, por três razões que
não são "dá pena jogar fora":

1. **O passo 6 do TAPI é literalmente "busca híbrida: vetorial + lexical".** Entregar 8 dos 9
   passos com a justificativa "medi e não ajudou" é pior que entregar 9 com o número honesto ao
   lado — e o número honesto é uma resposta de nível 4, não uma desculpa.
2. **O gabarito sub-representa o tipo de consulta em que o léxico ganha.** Ele tem 20 perguntas em
   português conceitual; o sistema real vai consultar com a **stack literal** extraída da startup
   ("usa LangChain, Pinecone, GPT-4"), que é exatamente onde o BM25 venceu aqui (q02 `colang`,
   q03 `cuxfilter`, q19 `vllm`+`sglang`). Isto é hipótese declarada, **não** medida — e o jeito de
   medi-la é ampliar o gabarito com consultas desse tipo, não argumentar.
3. **Custa uma chamada de API a mais igual a zero:** o BM25 roda em processo e a união dos dois
   braços cabe num lote só do reranker.

**O que eu NÃO fiz, e é decisão:** não subi o peso lexical até a métrica melhorar, nem troquei de
gabarito. As duas coisas seriam ajustar a régua ao resultado.
**Reversível?** Fácil — `peso_lexical=0.0` reduz a híbrida ao denso puro exatamente.

**Atualização — 24/08/2026, sessão de revisão.**

1. **A tabela de ablação acima vale em K=10 / peso_lexical=0,3, e isso não estava escrito.** Os
   defaults do `avaliar_rag.py` eram K=20 / 0,5, e nessa configuração a híbrida dá 68/89/100 ·
   53/68/84 — que é a tabela publicada no `sessao-04.md`. Os dois números estão certos; o erro é
   três documentos apresentarem tabelas diferentes como se fossem a mesma régua. O corolário
   "antes do rerank a híbrida é melhor no estrito, e@1 74% vs 68%" só vale em K=10/0,3: no default
   antigo do CLI a híbrida era PIOR (53% vs 68%). **Resolvido em D-044**, que faz o harness
   importar os defaults de produção em vez de redeclarar os seus.
2. **"`K=60` é uniformemente pior que `K=10`" é falso num ponto:** em peso 1,0 os dois dão 63%.
   Pior ou igual, estritamente pior em 3 dos 4 pesos.
3. **A identidade `rerank_denso ≡ rerank_hibrido` foi reconfirmada e é mais forte que o escrito:**
   vale também sobre a UNIÃO INTEIRA, com os mesmos logits, mesma falha única (q14). Corolário
   incômodo: não truncar a união custa 37,5% mais chamadas de rerank e compra zero nesta régua.

**Atualização 2 — 25/08/2026, sessão 05, depois da troca de stack (D-046).** A identidade
**QUEBROU**, e o braço lexical tem, pela primeira vez, um argumento medido.

Na stack nova (`llama-nemotron-embed-vl-1b-v2` + `rerank-qa-mistral-4b`):

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| rerank sobre denso | 95% | 100% | 100% | 84% | 95% | 95% |
| **rerank sobre híbrida** | 95% | 100% | 100% | 84% | 95% | **100%** |

**Onde nasce a vantagem, isolado pelo braço de controle:** com `--truncar-pool` os dois voltam a
95% em e@5. Ou seja, ela vem do **pool maior** — dos candidatos que só o braço lexical traz, além
do top-20 da fusão — e **não** da reordenação da fusão. É exatamente a separação que D-044
preservou o controle para poder fazer.

**Qual pergunta, e por quê** (`scripts/auditoria/quem_o_lexico_compra.py`, 22 chamadas): a
**q17** — *"Minha startup não tem processo nenhum para medir a qualidade do agente que entrega.
O que a NVIDIA oferece?"*, âncora `Evaluator`.

| | pool | posição da âncora |
|---|---|---|
| `rerank_denso` | 20 | **AUSENTE** — o chunk nem é candidato |
| `rerank_hibrido` | 35 | **4º** — dentro do top-5 |

Das 19 perguntas com resposta, a q17 é **a única** cuja âncora está na cauda da união e fora do
pool denso. O braço denso não recupera aquele chunk de jeito nenhum; o BM25 é a razão inteira de
ele existir como candidato.

**E o mecanismo é o que D-037 §2 previu e não conseguiu medir.** A hipótese registrada era *"o
gabarito sub-representa o tipo de consulta em que o léxico ganha — nome literal de produto"*. A
q17 é pergunta conversacional em português cuja âncora é **uma palavra em inglês, `Evaluator`,
nome de produto**. O léxico casa a string; o denso, não. Isto não valida a hipótese inteira — ela
falava da consulta com stack literal que o Extractor produz, e isso continua não medido (ver
D-043) —, mas é a primeira evidência do mecanismo dentro da régua.

**A honestidade sobre o tamanho, porque ela decide o quanto isto vale:** é **uma pergunta em 19**.
e@5 de 100% contra 95% é uma unidade. O argumento de D-039 contra n=1 se aplica aqui contra mim:
com um caso não há distribuição, há um ponto. E a vantagem aparece **só em e@5** — não em e@1,
não em e@3, não em nenhum r@k. O léxico compra um chunk que aterrissa em 4º, não em 1º.

**O que isso faz com a proposta que a sessão 04 deixou em aberto** — tirar o léxico do default de
produção e transformá-lo em flag: **está retirada.** Ela se apoiava em "o léxico compra zero
depois do reranker", que era verdade na stack antiga e deixou de ser. O custo continua sendo os
37,5% de chamadas de rerank a mais; agora há um número do outro lado da conta.
**O que continua NÃO medido:** se a vantagem sobrevive a outra pergunta. O jeito de saber é
ampliar o gabarito com consultas de nome literal — o mesmo teste que D-037 §2 já apontava e que
ninguém fez.

---

## D-038 — O reranker lê `texto_indexado`, com o breadcrumb
**Data:** 24/08/2026
**Decisão:** o cross-encoder recebe `texto_indexado` (breadcrumb prefixado), não `texto`.
**Alternativa descartada:** `texto` puro — o mesmo campo que vira `CitacaoRAG.trecho`, o que
teria a vantagem de "o reranker lê exatamente o que é citado", uma coisa a menos para explicar.
**Motivo:** reranquear o texto puro **descartaria no passo 7 a correção feita no passo 3**. O
chunk que responde a q19 cita "TensorRT-LLM" com destaque e nunca repete "NIM"; é o breadcrumb
`NVIDIA NIM > ...` que diz ao cross-encoder de que produto aquilo fala — e atribuição é o 7º
campo obrigatório do output do TAPI.

Medido nas duas variantes, k=10, critério estrito (logit do chunk que contém a `frase_ancora`):
empatam em recall@1 (18/19), e o breadcrumb **sobe o logit da âncora em 9 das 17** perguntas —
q03 +3,70→+7,39 · q13 +3,98→+9,10 · q05 −4,55→−1,71 · q10, q11, q15, q16 também.
**Efeito colateral medido e aceito:** o breadcrumb também sobe o score da q20, que não tem
resposta (−6,83 → −2,84), piorando a margem de abstenção. Irrelevante, porque **nenhuma das duas
variantes separa** (ver D-035).

### O que o reranking entregou, medido contra a linha de base

| | recall@1 | estrito@1 | estrito@5 |
|---|---|---|---|
| denso puro (D-032) | 89% | 68% | 84% |
| **+ rerank** | **95%** | **79%** | **95%** |

**A q19 subiu de 2º para 1º** — que era exatamente o pedido da pauta e a validação de que o
breadcrumb de D-025 leva o chunk certo até onde o reranker consegue promovê-lo.

**A única falha restante em recall@1 é a q14 — e inspecionando, o recuperador está certo e o
gabarito está subespecificado.** A pergunta é *"dá para acelerar um pipeline de pandas em GPU sem
reescrever o código?"*, e o chunk que o reranker escolhe (RAPIDS/CUDA-X) diz literalmente
*"zero-code-change APIs that accelerate popular PyData tools like pandas and scikit-learn"*. Os
chunks do cuDF que estão no pool falam de Polars, requisitos de sistema e instalação por conda. A
âncora `cudf.pandas` existe (chunks 223 e 226), está no pool, e é reranqueada abaixo — **com
razão**, porque a pergunta como escrita não pede "qual biblioteca específica".

**Não corrigi a pergunta depois de ver o resultado.** Reescrevê-la agora seria ajustar a régua ao
resultado, e o número que interessa a um avaliador é justamente este: 95% com a falha restante
explicada, em vez de 100% com a régua movida. Fica registrado como limitação conhecida do
gabarito, não como falha do recuperador.
**Reversível?** Fácil — é qual campo entra no payload.

**Atualização — 25/08/2026 (D-046), na stack nova.** Os números desta decisão foram medidos com
o embedder e o reranker que morreram em 25/08 e **não são reproduzíveis**. A tabela nova:

| | recall@1 | estrito@1 | estrito@3 | estrito@5 |
|---|---|---|---|---|
| denso puro (stack antiga) | 89% | 68% | 79% | 84% |
| + rerank (stack antiga) | 95% | 79% | 84% | 95% |
| **denso puro (stack nova)** | **95%** | **79%** | 79% | 84% |
| **+ rerank (stack nova)** | **95%** | **84%** | **95%** | **95–100%** |

**O que mudou de qualitativo:** o embedder novo sozinho já entrega os 95% de recall@1 que antes
exigiam o reranker. O ganho do passo 7 **migrou do frouxo para o estrito** — não move mais r@1,
e move e@3 de 79% para 95%. O argumento de D-038 fica mais limpo, não mais fraco: o reranker
existe para achar o CHUNK que responde, não o documento, e agora é isso que os números mostram.

**A decisão em si (ler `texto_indexado`) não foi re-testada contra `texto` puro na stack nova** —
seria mais uma ablação, e o mecanismo que a justifica (o breadcrumb diz de que produto o chunk
fala) não depende do modelo. Fica declarado como não re-medido.
**A falha da q14 em recall@1 não existe mais** nesta stack; a análise de gabarito subespecificado
acima continua registrada como o que se sabia então.

---

## D-039 — O gabarito ganha 4 perguntas sem resposta, de regimes diferentes, com prova executável
**Data:** 24/08/2026
**Decisão:** o gabarito passa de 20 para **24 perguntas — 19 com resposta e 5 sem**. Cada
`sem_resposta` carrega `regime`, `justificativa_ausencia` (prosa, obrigatória) e `termos_ausentes`
(opcional, verificado por `--validar`).
**Alternativa descartada:** manter a q20 sozinha e registrar a ressalva de n=1 na decisão.

**Motivo:** a conclusão mais consequente da sessão — *"nenhum limiar separa abstenção"* — é uma
afirmação sobre **sobreposição de duas distribuições**, e com n=1 de um lado não há distribuição,
há um ponto. Pior: a q20 foi escrita para ser o caso difícil ("plausível o bastante para o denso
recuperar com score razoável"), então ela podia estar **exagerando** a sobreposição e condenando
um mecanismo que funcionaria. Sem amostra, não havia como saber. E é uma frase que vai para o
README e para o vídeo, sob o eliminatório nº 4.

**Dois regimes, de propósito, porque cinco variações de preço mediriam só o pior caso:**

| regime | o que é | perguntas |
|---|---|---|
| `topicamente_perfeita` | a base fala do assunto com autoridade e só não tem o fato pedido | q20 preço · q21 Brasil · q23 comparação · q24 contagem |
| `topicamente_ausente` | o assunto não está na base | q22 litografia computacional |

A `topicamente_ausente` existe para provar que **a fronteira entre os dois é observável**. Um
sistema que abstém só nela não aprendeu a abster-se — aprendeu a reconhecer assunto estranho, que
é outra coisa e muito mais fácil.

**`termos_ausentes` é a prova executável, o espelho de `frase_ancora`.** Se qualquer termo
declarado ocorrer no corpus, a pergunta não é `sem_resposta` e `--validar` falha. Verificado com
**fronteira de palavra e não substring** — e essa distinção nasceu de um erro real: `ILIKE '%SLA%'`
reportava `SLA` como presente porque casa dentro de "tran**sla**tion", e por pouco não deixei uma
pergunta errada entrar no gabarito.

**A prosa é obrigatória e o termo não, e isso é decisão.** Há ausências que nenhuma string prova:
a da q20 é a de um **número**, e não existe termo cuja falta demonstre que um preço não está
publicado. Onde o termo serve, ele é prova; onde não serve, a curadoria escreve o argumento e
assina embaixo. Fingir que toda ausência é verificável por `grep` seria a mentira confortável.

**A pergunta que mais importa é a q21** — *"a NVIDIA tem algum programa específico para startups no
Brasil?"*. É a pergunta que o **usuário real deste sistema** faria: o gerente de Startups & VCs da
NVIDIA Brasil, que é para quem o briefing é escrito. Se o sistema inventar um benefício regional,
inventa para a única pessoa que saberia na hora que é falso.
**Reversível?** Fácil — é dado versionado, não código.

---

## D-035 — A hipótese de D-033 está REFUTADA: o reranker também não abstém
**Data:** 24/08/2026 · **é o resultado, e ele contraria o que a sessão apostava**
**Decisão:** o sistema **não** decide "não sei" por limiar sobre score algum — nem sobre a cosseno
densa (já descartado em D-033), nem sobre o logit do cross-encoder. A abstenção sobe para o
**passo 8, a geração** (D-040).

**A hipótese que D-033 registrou para esta sessão:** *"o cross-encoder pontua o par (consulta,
passagem) julgando se aquela passagem **responde** aquela pergunta, o que é uma pergunta diferente
da que o bi-encoder responde."* Era o caminho óbvio e eu apostava nele.

### O que a medição diz, com o gabarito ampliado para 5 perguntas sem resposta

| motor | pior acerto | pior sem-resposta | margem |
|---|---|---|---|
| denso, n=1 (D-033) | 0,2934 | 0,4813 (q20) | −0,1879 |
| **denso, n=5** | 0,2934 | **0,5744 (q24)** | **−0,2810** |
| **rerank, n=5** | −9,1016 | **+8,5312 (q23)** | **−17,6328** |

**Ampliar a amostra piorou a margem em 4x — o n=1 estava SUBESTIMANDO o problema, não
exagerando.** É o contrário do que eu temia ao propor a ampliação, e é a razão de ela ter valido a
pena: com uma pergunta só, eu teria registrado um número quatro vezes mais gentil que a realidade.

**A q23 é a demonstração.** Ela pergunta *"o TensorRT-LLM é mais rápido que o vLLM? Em quantos por
cento?"* e recebe logit **+8,53**, um dos mais altos do gabarito inteiro — mais alto que o de
quase todas as perguntas que TÊM resposta. O cross-encoder está certo no que ele mede: o chunk 38
do NIM cita "TensorRT-LLM, vLLM ou SGLang" na mesma frase, e é a passagem mais relevante do corpus
para aquela pergunta. Ela só não contém a comparação.

### A razão é conceitual, e agora está confirmada em duas camadas

**Relevância não é responsibilidade.** O bi-encoder mede pertinência de tópico; o cross-encoder
mede relevância do par, que é mais fino e ainda é relevância. Distinguir "fala do assunto" de
"contém o fato pedido" exige **ler a passagem procurando a coisa específica** — e o único
componente do pipeline que lê é o gerador.

D-033 chegou a essa conclusão por argumento e a marcou como hipótese. Agora ela tem dois números.

**Um limiar global também é impedido por um segundo motivo, medido em D-034:** os logits são
quantizados em bf16 e variam entre execuções — a mesma passagem pontuou −10,24 e −6,83 em
chamadas diferentes. Mesmo que existisse uma margem positiva, ela precisaria ser maior que ~2
logits para ser sinal e não ruído do serving.

**O que sobra, e vai para o passo 8:** a decisão de abstenção passa a ser um **campo estruturado
produzido pela geração** (`RespostaRAG.abstencao`), com o LLM lendo as passagens e declarando se o
fato pedido está lá — não interpretando prosa depois. Mesmo princípio de D-021: campo sem fonte
literal vira `null`, não valor plausível.
**Alternativa que fica registrada como não testada:** um critério **relativo** dentro da consulta
(gap entre 1º e 2º, ou o topo contra a própria distribuição daquela consulta) em vez de limiar
global. Não testei porque, com 5 perguntas sem resposta, calibrar um segundo hiperparâmetro seria
sobreajuste declarado. Fica para quando o gabarito crescer.
**Reversível?** N/A — é um achado. O que é reversível é o mecanismo escolhido no lugar.

**Atualização — 25/08/2026 (D-046), na stack nova.** O achado se mantém e os números mudaram:

| motor | pior acerto | pior sem-resposta | margem |
|---|---|---|---|
| denso, n=5 (stack antiga) | 0,2934 | 0,5744 (q24) | −0,2810 |
| **denso, n=5 (stack nova)** | 0,2640 | 0,4891 (q23) | **−0,2251** |
| rerank, n=5 (stack antiga) | −9,1016 | +8,5312 (q23) | −17,6328 |
| **rerank, n=5 (stack nova)** | −7,1641 | +3,8398 (q23) | **−11,0039** |

A margem continua **negativa nas quatro linhas** — as distribuições se sobrepõem em qualquer dos
dois motores, em qualquer das duas stacks. A conclusão "nenhum limiar separa" sobreviveu à troca
dos dois modelos, o que é a evidência mais forte que ela tem: **não era artefato de um modelo.**

A regra desta sessão dizia que, se a margem virasse positiva, NÃO se reabriria a hipótese de
limiar — derivar um sobre 5 negativos seria o sobreajuste que esta própria decisão declinou.
Não foi preciso: ela não virou.

---

## D-042 — A consulta do NVIDIA RAG Agent sai da dor observada + da stack declarada
**Data:** 24/08/2026 · fecha a dívida nº 1 da sessão 02
**Decisão:** `src/agents/nvidia_rag.py` perde a `BASE_PROVISORIA` de 8 dores e passa a chamar
`pipeline.buscar_com_rerank()` **uma vez por dor observada**, com a consulta montada como
`"{texto da dor} (stack atual: {stack declarada})"`. Dedupe por `url_fonte`, 3 trechos por dor.
**Alternativas descartadas:** manter o dicionário dor → tecnologia · consultar uma vez só,
concatenando todas as dores numa consulta.

**Motivo — o dicionário não é simples demais, é DESLIGADO.** `contexto/03` §4 diz que a dor é a
chave de junção com a tabela de tecnologias, e o stub implementava isso ao pé da letra. O problema
não é o tamanho da tabela: é que com ela as 16 páginas ingeridas, chunkadas, embedadas e indexadas
**não mudariam uma vírgula da recomendação**. O critério 2 do barema vale 20 pontos e viraria
decoração.

**Por que uma consulta POR DOR e não uma consulta só:** dores diferentes recuperam tecnologias
diferentes — é o comportamento que a regra 5 de `contexto/03` §4 descreve (o estágio muda a
recomendação). Concatenar produziria uma consulta média que não é a de ninguém, e o reranker
receberia um pool sem foco. O custo é linear no número de dores, e o teto de 8 dores da rubrica
o limita naturalmente.

**Por que a stack declarada entra na consulta — e é aqui que D-037 se paga.** A medição do braço
lexical mostrou que ele é **mudo em consulta conceitual em português** e **forte em nome literal
de produto** (`colang`, `vllm`, `pytorch`, `scikit`). O gabarito é quase todo do primeiro tipo, e
por isso o BM25 não moveu a métrica lá. Mas a `stack_declarada` que o Extractor produz ("usa
LangChain, Pinecone, GPT-4") é **a única fonte de nome literal deste sistema** — é exatamente o
tipo de consulta em que o léxico ganha.

Isso continua sendo **hipótese declarada, não medida**: para medi-la seria preciso um gabarito de
consultas no formato que o Extractor produz, e ele não existe. Fica registrado como o teste que
justificaria ou condenaria D-037 de vez.

**Por que este nó NÃO gera texto**, mesmo com `pipeline.responder()` pronto: quem o consome é o
Recommendation Agent, que precisa dos **trechos com scores** para cruzar com o perfil, não de um
parágrafo já redigido. Redigir aqui e reinterpretar lá perderia a evidência no meio do caminho.
A geração com citação é para quando um **humano** faz a pergunta — ela entra pela interface.

**Efeito colateral que apareceu na hora e foi corrigido:** o stub do Recommendation Agent derivava
`justificativa_negocio` de uma tabela com 5 tecnologias. Com tecnologias reais chegando da base, o
campo vinha vazio — e ele é um dos **7 campos obrigatórios do TAPI**. O teste
`test_recomendacao_tem_os_sete_campos_do_tapi` pegou na primeira execução. O fallback agora deriva
das dores observadas: formulaico e visivelmente de stub, mas nunca vazio. Campo obrigatório vazio
é nível 0 no critério, não "quase lá".
**Reversível?** Fácil — é o corpo de um nó.

---

## D-040 — O passo 8 entra na M2: geração com citação e abstenção estruturada
**Data:** 24/08/2026 · fecha os 9 passos do pipeline do TAPI dentro da M2
**Decisão:** `src/rag/geracao.py` implementa o passo 8 — o LLM lê os top-k reranqueados e devolve
`RespostaRAG` com `texto`, `abstencao: bool`, `motivo_abstencao` e `indices_citados`. Todo acesso
a LLM passa por `src/llm.py`, sempre com `with_structured_output(..., method="json_schema")`.
**Alternativas descartadas:** deixar o Bloco 4 só com citação estruturada e adiar a geração para a
M4 · `method="function_calling"` · `method="json_mode"` · abstenção como prosa a interpretar.

### Por que o passo 8 entrou aqui e não na M4

Depois de D-035 a abstenção ficou **sem outro lugar para morar**: nenhum limiar sobre score
funciona, e o único componente que lê a passagem é o gerador. Adiar o passo 8 adiaria junto a
única afirmação de qualidade que este RAG tem para fazer. E a regra da sessão — *todo incremento é
medido* — deixou de ser obstáculo no momento em que D-039 ampliou o gabarito: **acurácia de
abstenção sobre 24 perguntas é contagem pura**, sem LLM-as-judge e sem rubrica de fidelidade.

### `json_schema` e não `function_calling` — medido na armadilha

Mesmo modelo, mesmo prompt, `temperature=0`, na q23 (*"o TensorRT-LLM é mais rápido que o vLLM?
Em quantos por cento?"*, cuja resposta não existe na base):

| método | resultado |
|---|---|
| `function_calling` | `abstencao=False` · **"o TensorRT-LLM é mais rápido que o vLLM em 30%"** |
| `json_mode` | não faz parse — o modelo devolve JSON com outro shape |
| **`json_schema`** | **`abstencao=True`** · "a passagem não fornece informação sobre..." |

A diferença entre alucinar um número e abster-se, decidida pelo método de saída estruturada. A
leitura provável é que `function_calling` adiciona pressão para PREENCHER os campos da ferramenta.
Seja qual for a causa, o comportamento é medido e é ele que manda.

### O resultado, em TRÊS execuções — porque uma teria mentido

| execução | acurácia | erros | fonte certa | fonte errada | sem citação |
|---|---|---|---|---|---|
| 1 (sem a instrução de idioma) | 23/24 | q05 | 16 | 1 | 1 |
| 2 | **24/24** | — | 13 | 1 | 5 |
| 3 | 22/24 | q09, q17 | 13 | 1 | 3 |

**A métrica é 22–24 de 24, não 100%.** Rodei três vezes justamente porque a primeira deu 23 e a
segunda 24; parar na segunda teria produzido um número bonito e falso. A fonte da variação é o
serving: `temperature=0` não torna o endpoint determinístico.

**A assimetria é o resultado que importa.** Em três execuções foram **15 oportunidades de alucinar**
(3 × 5 perguntas sem resposta) e **zero alucinações**. Todos os erros das três execuções são
**abstenções falsas** — o sistema erra sempre para o lado de não responder. Num briefing escrito
para o gerente de Startups & VCs da NVIDIA Brasil, uma recomendação a menos custa uma
oportunidade; um número inventado custa a credibilidade do sistema inteiro.

### Uma das três "falhas" não é falha, e o diagnóstico importa

Cruzei as abstenções falsas com "a âncora está entre os 5 trechos que o gerador leu":

- **q17 — a âncora NÃO está no top-5, nem no top-10.** A recuperação entrega o documento certo e
  não o chunk que responde. **O gerador abster-se ali é comportamento correto**, e é a minha
  métrica que conta errado: ela pergunta "a base tem a resposta?" quando deveria perguntar "a
  recuperação entregou a resposta?". Com isso, o **teto real desta métrica é 23/24** enquanto a
  recuperação não melhorar — e melhorar isso é banda de chunk, que é sessão 04.
- **q05 e q09 — a âncora estava lá e o modelo não viu.** Falha genuína de geração.

### A instrução de idioma, e por que ela não é ajustar a régua ao resultado

A q05 falhou na primeira execução: o gerador leu *"high transcription accuracy for Arabic,
English, ..., **Portuguese**, Russian, and Spanish"* e respondeu *"não há menção explícita à língua
portuguesa nos trechos"*. Acrescentei ao prompt que **os trechos estão em inglês e a pergunta vem
em português, e que traduzir para comparar faz parte do trabalho**.

Isso é declarar um fato de arquitetura do sistema (D-014: corpus EN, consulta PT), não plantar uma
resposta. A versão inaceitável seria *"se perguntarem sobre português, diga que o Riva suporta"*.
E a mudança foi **verificada contra regressão**: as 5 abstenções continuaram corretas nas duas
execuções seguintes, incluindo a armadilha da q23.

### A citação é o ponto fraco, e fica registrado como tal

`indices_citados` erra com frequência não desprezível: a **q07 aponta a fonte errada nas três
execuções** (é sistemático, não ruído), e entre 1 e 5 respostas por execução não apontam nada.
A resposta continua acompanhada de todas as passagens lidas em `RespostaRAG.citacoes` — então
nada sai sem fonte anexada —, mas *qual* trecho sustenta *qual* afirmação ainda não é confiável.
**A abstenção está resolvida; o "de onde veio" não.** Como rastreabilidade é requisito duro do
TAPI, citado duas vezes, isso é trabalho explícito da M4: modelo maior só neste nó, ou verificação
por código de que a afirmação ocorre no trecho citado.
**O que NÃO foi medido:** fidelidade da prosa ao contexto. Exigiria LLM-as-judge ou anotação
humana, e as duas trazem uma régua que também precisaria ser validada. Fica declarado como não
medido em vez de alegado.

### Detalhes de desenho

- **Citação por ÍNDICE, não por URL escrita na prosa.** Índice fora da faixa é erro detectável por
  código; URL no meio de um parágrafo não é. Rastreabilidade precisa ser verificável.
- **Abstenção é campo booleano**, não frase que alguém depois classificaria com regex — mesmo
  princípio de D-021.
- **Zero passagens não chama o LLM.** Não há o que ler; pedir ao modelo que decida sobre o vazio é
  exatamente onde ele inventaria.
**Reversível?** Fácil — é um módulo e um prompt.

**Atualização — 24/08/2026, sessão de revisão.** A afirmação "a âncora da q17 NÃO está no top-5,
nem no top-10" não reproduz sob o pipeline final (`scripts/auditoria/auditoria_q17.py`):

- pela `pipeline.responder()`, a âncora (chunk 81) está na união e o reranker a põe em **6º**;
- pelo `--geracao`, ela **não está no pool** — o harness trunca a fusão em 20 e o chunk 81 entra
  só pelo braço lexical, além dessa posição.

O teto de 23/24 sobrevive por acidente aritmético (6 > 5 = k do gerador), mas o diagnóstico está
trocado: não é "a recuperação entrega o documento certo e não o chunk que responde", é **entrega
em 6º e o gerador lê 5**. `k=6` resolveria a q17 hoje, sem tocar em chunking — o que remove a
justificativa de atacar este caso com um modelo de 70b antes de testar o parâmetro.

**Atualização 2 — 24/08/2026, sessão 04, Bloco 0.** A ressalva acima dizia que o `--geracao` não
tinha sido re-rodado. Foi, depois de duas mudanças desta sessão: D-044 (o harness parou de
truncar o pool) e o schema estreito de saída registrado em D-045.

**Duas execuções, 24/24 nas duas** — 19/19 respondidas e 5/5 abstidas, e a q17 respondendo com a
fonte certa. **Isto NÃO é "subiu de 23 para 24".** D-040 já registra este passo como
não-determinístico, com 22, 23 e 24 de 24 observados no mesmo código; duas execuções são dois
pontos, não uma distribuição, e o mesmo argumento que D-039 usa contra o n=1 se aplica aqui
contra o n=2. O que se pode afirmar: o teto aritmético de 23/24 descrito acima **deixou de
existir**, porque a âncora da q17 passou a estar dentro do que o gerador lê.

**Continua não medida** a escolha `json_schema` vs `function_calling` — a tabela que a decide é
uma pergunta com uma execução por método, contra um passo que a própria decisão declara
não-determinístico. É o risco mais carregado que a revisão levantou (§5) e ele segue aberto,
agora dentro de `METODO_ESTRUTURADO` em `src/llm.py`, o portão único dos oito agentes da M4.

**Atualização 3 — 25/08/2026, sessão 05, na stack pós-EOL (D-046). A afirmação central desta
decisão levou um golpe direto, e ele fica escrito aqui e não numa nota de rodapé.**

Três execuções na stack nova, com a recuperação MELHOR que antes (r@1 95%, e@1 84%, e@3 95%):

| execução | acurácia | respondeu | absteve | erros |
|---|---|---|---|---|
| 1 | **22/24** | 17/19 | 5/5 | q05, q11 |
| 2 | **21/24** | 16/19 | 5/5 | q05, q07, q11 |
| 3 | **20/24** | 16/19 | **4/5** | q05, q07, q11, **q23** |

**Faixa: 20–22 de 24.** Na stack antiga era 22–24, e a Atualização 2 registrou 24/24 duas vezes.
**A métrica caiu, e não se mexe em nada para recuperá-la** — a regra desta sessão foi fixada
antes de medir, e ajustar prompt, `k` ou pesos depois de ver o resultado é exatamente o que D-037
e D-038 recusaram fazer.

**O que mais importa não é a queda de 2 pontos — é O QUE quebrou.** Esta decisão afirma:

> Em três execuções foram **15 oportunidades de alucinar** e **zero alucinações**. Todos os erros
> das três execuções são abstenções falsas — o sistema erra sempre para o lado de não responder.

Na execução 3, a **q23** — a pergunta-armadilha, a mesma que esta decisão usa como prova de que
`json_schema` é o método certo — recebeu:

```
q23  topicamente_perfeita  abster  responder  ERRO  [3] FONTE ERRADA (!)
     "O TensorRT-LLM é mais rápido que o vLLM em 60%"
```

**Um número inventado, com citação de fonte errada, sob `json_schema`.** É o mesmo formato de
alucinação que a tabela desta decisão atribui ao `function_calling` (*"...em 30%"*) e que serviu
para descartá-lo. **A assimetria "erra sempre para o lado de não responder" está refutada:** 15
oportunidades, 1 alucinação.

**Honestidade sobre o que isso prova e o que não prova.** 1 em 15 contra 0 em 15 não distingue
"a stack nova alucina mais" de "sempre alucinou nessa taxa e as três execuções antigas não
pegaram". O que está estabelecido é o mais forte dos dois: **`json_schema` não impede a alucinação
da q23** — basta um contraexemplo para derrubar uma afirmação de impossibilidade, e ele apareceu.
A defesa de D-040 precisa mudar de *"o método impede"* para *"o método reduz a frequência"* — e
isso exige o n que a revisão §5 pediu, medido a seguir em D-047.

**Três abstenções falsas viraram sistemáticas**, o que é diferente do ruído que esta decisão
descreve: **q05 falha nas 3**, **q11 nas 3**, **q07 em 2 de 3**. A q05 é o caso crosslingual que
a instrução de idioma existia para resolver — a instrução está no prompt e ela falha assim mesmo,
agora com a âncora bem posicionada pela recuperação nova. Isso desloca o diagnóstico do
recuperador para o gerador, e é dívida declarada da M4, não coisa para consertar aqui com o
resultado à vista.

---

## D-043 — A consulta do RAG sai do RÓTULO da dor + das EVIDÊNCIAS, não do `texto` da dor

**Data:** 24/08/2026 · **Sessão 04, Bloco 0** · corrige D-042 sem revogá-la

**O que a medição achou.** D-042 trocou o `BASE_PROVISORIA` (um `dict` de 8 dores para 8
tecnologias) por uma consulta ao RAG real, montada de `DorObservada.texto` mais a
`stack_declarada`. As duas metades estavam quebradas, e o code review da revisão mediu as duas:

1. `DorObservada.texto` **não é a linguagem da startup** — `extractor.py:91` o preenche com um
   template fixo, `f"Sinal de dor em {dor} encontrado nos documentos"`. Existem OITO consultas
   possíveis no sistema inteiro.
2. `perfil.stack_declarada` **não é preenchida por nenhum produtor**. `grep` no `src/` devolve a
   declaração do campo e esta única leitura. O ramo `if not stack` é o único que executa.

**Medido em 24/08 sobre três startups reais da base** (Axenya, Doutor-AI, Laura Networks):

| | antes (D-042) | depois (D-043) |
|---|---|---|
| as 3 tecnologias que chegam ao Recommendation | **idênticas nas três startups** — `Inception, Morpheus, CUDA Toolkit` | uma lista diferente por startup |
| braço lexical nas consultas do grafo | **0 resultados** nas 8 consultas possíveis | vota em 6 das 7 dores (4 a 20 resultados) |

Ou seja: D-042 tinha reintroduzido o `BASE_PROVISORIA` como constante disfarçada, agora pagando
embedding e rerank por dor por startup. A startup não entrava na conta.

**Decisão:** a consulta passa a ser `rótulo da dor + trechos de `dor.evidencias` + stack`.

- **o rótulo** (`custo`, `latencia`) é a âncora tópica — era o único sinal dentro do template;
- **os trechos** são a frase LITERAL do documento da startup, que `Evidencia.trecho` guarda desde
  D-018. É o que faz duas startups com a mesma dor recuperarem coisas diferentes;
- **a stack** continua no código e continua inalcançável, agora dito em voz alta no docstring.

**O que isso faz pela hipótese de D-037** ("o léxico paga na consulta com stack literal"): ela
continua **não medida numa régua**, mas deixou de ser inverificável. O gatilho
`dependencia_fornecedor` casa em `"gpt-4"`, `"api da openai"`, `"chatgpt"` — os trechos trazem
nome literal. Antes o braço lexical não votava; agora vota. Depois da revisão da sessão 03, que
derrubou o argumento de IDF de D-036 e mostrou o léxico irrelevante depois do reranker, este é o
**único argumento vivo** para manter o BM25 — e ele agora pode ser medido em vez de alegado.

**Alternativa descartada:** fazer o Extractor preencher `stack_declarada`. É a correção "certa"
e ela vem na M4 — mas é reescrever o Extractor, e as evidências já entregam nome literal hoje
sem tocar naquele agente. Trocar uma constante por outra teria custado uma sessão.

**Segunda decisão, no mesmo nó — a lista sai INTERCALADA por dor, não concatenada.** O
Recommendation corta em `TETO_RECOMENDACOES = 3`. Concatenada dor a dor, esse corte é POR DOR:
as três recomendações saem todas da primeira dor e as outras somem em silêncio. Intercalando com
`zip_longest`, o corte pega o 1º colocado das três primeiras dores, que é o que a regra 4 de
`contexto/03` §4 ("não empilhar tecnologia") quer dizer. Sem isso, o efeito da tabela acima ficava
escondido: as três startups recebiam as mesmas três tecnologias mesmo com a consulta corrigida.

**Terceira, pequena:** `CitacaoRAG` ganha `dor_origem`. É carimbado por `nvidia_rag`, não pelo
pipeline — `src/rag/` continua sem conhecer o conceito de dor, que é o que mantém D-041 de pé.
Serve à `justificativa_negocio` (ver D-045) e é a informação que faltava para a dívida do filtro
de dores do `recommendation.py`, hoje anotada e não paga.

---

## D-044 — O harness de avaliação mede a configuração que a produção roda

**Data:** 24/08/2026 · **Sessão 04, Bloco 0** · era a decisão que a revisão deixou em aberto

**O problema, em uma frase:** `scripts/avaliar_rag.py` declarava os PRÓPRIOS defaults de fusão e
truncava o pool antes do rerank, e `src/rag/pipeline.py` fazia diferente nos dois pontos.

Custo já pago por essa divergência, e não é hipotético:

1. O comando que o `CLAUDE.md` documenta como a ablação (`python scripts/avaliar_rag.py`) **não
   reproduzia a tabela que o `CLAUDE.md` publica.** Os defaults do CLI eram K=20 / peso 0,5 e
   davam 68/89/100 · 53/68/84; a tabela publicada é a de K=10 / 0,3. Quem fosse reproduzir o
   repositório encontrava outros números — num projeto cujo argumento inteiro é "está medido".
2. O `--geracao` truncava a fusão em 20 e a produção não trunca. Resultado: a q17 foi medida num
   pipeline **em que a passagem-âncora não existia**, e D-040 registrou o diagnóstico errado
   ("a recuperação entrega o documento certo e não o chunk que responde") quando o real era
   "entrega em 6º e o gerador lê 5".

**Decisão:** `POOL_PADRAO`, `K_RRF_PADRAO`, `PESO_DENSO_PADRAO` e `PESO_LEXICAL_PADRAO` são
**importados de `src.rag.pipeline`**, não redeclarados; e o pool **não é truncado** antes do
rerank, como em `pipeline.buscar_com_rerank`.

**A alternativa era defensável e por isso isto é decisão, não correção.** Manter o harness
truncando DE PROPÓSITO o preservava como braço de controle da pergunta "vale a pena mandar a
união inteira ao reranker?" — que é hoje a única evidência de que não truncar custa 37,5% mais
chamadas de rerank e compra zero. Os dois lados:

| | harness = produção | harness truncando de propósito |
|---|---|---|
| o número publicado reproduz? | sim | não, e já enganou uma vez (q17) |
| o braço de controle sobrevive? | só se virar opção explícita | sim, de graça |
| custo por execução | ~37,5% mais chamadas de rerank | menor |
| risco | a comparação "truncar vs não" tem que ser pedida | **medir um sistema que ninguém roda** |

O que decidiu foi o risco da última linha: um controle que é o default silencioso não é controle,
é divergência. **`--truncar-pool` restaura a truncagem e se pede pelo nome.** Verificado em 24/08:
com a flag, `rerank_denso` e `rerank_hibrido` dão 95/100/100 · 79/84/95 — **os seis números
idênticos** aos de sem a flag. O controle continua medível e continua dizendo a mesma coisa.

**Verificação do resultado:** `python scripts/avaliar_rag.py` sem argumento nenhum agora imprime
denso 89/100/100 · 68/79/84, híbrida 84/100/100 · 74/79/84, rerank 95/100/100 · 79/84/95 e as
margens −0,2810 e −17,6328 — que é, linha por linha, a tabela do `CLAUDE.md`.

**Efeito colateral bom:** os imports tardios de `fusao`, `lexical`, `rerank` e `geracao` saíram.
Eles existiam para "`--motor denso` rodar antes de a fusão existir", uma razão de ordem de
sessão que expirou — e depois que o `pipeline` entra no topo do arquivo eles não isolavam mais
nada. Um comentário que descreve uma proteção que não protege é pior que nenhum comentário.

---

## D-045 — O modelo recebe um schema estreito; `RespostaRAG` é montado em código

**Data:** 24/08/2026 · **Sessão 04, Bloco 0** · achado do code review

**O que estava acontecendo.** `geracao.gerar()` chamava `estruturado(RespostaRAG, ...)`, mandando
ao modelo o schema inteiro do contrato — incluindo `citacoes: list[CitacaoRAG]` com todo o
`$defs.CitacaoRAG`, um campo que a linha seguinte do código **descarta** para montar a lista a
partir das citações que já estavam em mãos.

E arrastava junto uma coisa que a sessão 03 não tinha percebido: **o docstring de uma classe
Pydantic vira o `description` do JSON Schema, ou seja, vira PROMPT.** O de `RespostaRAG` é prosa
de decisão — cita "margem −0,2810", "Mesmo princípio de D-021", "D-033 e D-035". Isso é
documentação para quem lê o repositório, e é ruído quando endereçado ao modelo.

**Medido:** 2.690 chars de schema por chamada, contra 524 do tipo estreito — **80% menor**, sem
`$defs`, com o mesmo `required` (`['texto']`, então não há mudança de obrigatoriedade de campo).

**Decisão:** `SaidaGerador`, local a `src/rag/geracao.py`, com os quatro campos que o MODELO
decide (`texto`, `abstencao`, `motivo_abstencao`, `indices_citados`) e docstring curto escrito
PARA O MODELO. `RespostaRAG` continua sendo o contrato e continua montado em código.

**Alternativa descartada:** manter `RespostaRAG` na chamada e só encurtar o docstring. Resolvia
metade — deixava de pé um campo cujo valor é descartado, que o modelo pode gastar tokens
preenchendo e que, com uma passagem longa, é um caminho para estourar `max_tokens` e devolver
JSON truncado.

**A regra que fica:** todo schema que vai para `with_structured_output` é interface com o modelo,
não com o repositório. Docstring de schema é prompt. Vale para os oito agentes da M4.

**Re-medido depois da mudança** (junto com D-044, que também mexe no que chega ao gerador): duas
execuções do `--geracao`, **24/24 nas duas**. Ver a Atualização 2 de D-040 para por que isso NÃO
é "subiu de 23 para 24".

---

# Sessão 05 — o segundo EOL, e o chão medido de novo

## D-046 — A stack de recuperação morreu pela SEGUNDA vez; o embedder é o VL, e o empate é o motivo

**Data:** 25/08/2026 · **Sessão 05, Bloco 0-1** · é o resultado, não a intenção

**O fato.** Em **25/08/2026 às 09:00Z** a NVIDIA aposentou os dois motores do RAG deste projeto:

```
POST /v1/embeddings  (nvidia/llama-nemotron-embed-1b-v2)   -> 410
  "The model ... has reached its end of life on 2026-08-25T09:00:00Z"
POST .../llama-nemotron-rerank-1b-v2/reranking             -> 410
  "This endpoint has reached its end of life on 2026-08-25T09:00:00Z"
POST /v1/chat/completions (meta/llama-3.1-8b-instruct)     -> 200
```

O LLM sobreviveu; a recuperação inteira, não. Medido na hora: `pytest -q` caiu para **39 passed,
1 failed** (o e2e que `ea720f1` criou justamente para pegar RAG quebrado), e dos seis comandos de
avaliação que o `CLAUDE.md` documenta **só `--validar` continua rodando** — porque ele não toca a
API. Nenhum número publicado saía de comando nenhum: nem 89/95/100, nem −0,2810, nem −17,6328,
nem 24/24.

**A leitura que D-013 não fez, e que é o achado desta decisão.** D-013 registrou este mesmo 410
em 18/05/2026 e concluiu que *o TAPI está desatualizado*, marcando o episódio como material de
vídeo. Havia uma segunda conclusão disponível e ela não foi tirada: **o catálogo de preview do
build.nvidia.com aposenta modelos em cadência de meses, e este projeto inteiro está montado nele.**
A tabela de riscos do `plano.md` não tinha essa linha — a mais próxima era "créditos
insuficientes", mitigada por *"provedor configurável por env var"*. Essa mitigação protege a
camada que não precisava de proteção: o LLM é intercambiável por env var, mas trocar o **embedder**
invalida os 381 vetores de `chunks_nvidia`, porque o espaço vetorial é outro. A configurabilidade
de `src/config.py` nunca cobriu este caso.

Com o vídeo em 07/09 e o eliminatório nº 3 sendo *"projeto que não executa **e** cujo vídeo não
demonstra funcionamento real"*, um terceiro EOL na semana da gravação custa o case. A linha entra
no `plano.md` nesta sessão.

### O que restou vivo, sondado em 25/08

| papel | modelo | situação |
|---|---|---|
| embedding | `nvidia/llama-nemotron-embed-vl-1b-v2` | aceita `dimensions` **1024 e 2048**, nos dois `input_type` |
| embedding | `nvidia/nemotron-3-embed-1b` | **só 2048**; recusa 1024 com HTTP 400 |
| rerank | `nvidia/rerank-qa-mistral-4b` | **o único vivo**; mesmo shape (`rankings`/`logit`) |

O `/v1/models` não lista mais nenhum rerank, e os quatro paths de reranking que testei deram 404.
O endpoint sobrevivente só apareceu porque um 404 devolveu a lista de modelos aceitos no corpo:
`['nvidia/rerank-qa-mistral-4b', 'nv-rerank-qa-mistral-4b:1']`. **No reranker não houve escolha** —
há um modelo, e ele é 4B contra o 1B que morreu.

### A decisão do embedder, e por que ela é um empate resolvido por regra

**Decisão:** `nvidia/llama-nemotron-embed-vl-1b-v2` com `dimensions=1024`.
**Alternativa descartada:** `nvidia/nemotron-3-embed-1b` a 2048 nativas.

A regra de desempate foi **escrita antes de medir** (`scripts/auditoria/sonda_embedder_pos_eol.py`,
docstring): adotar o `nemotron-3` só se (a) a margem crosslingual dele batesse a do VL por
**≥1,5x** e (b) a truncagem local 2048→1024 preservasse a separação — porque ele recusa
`dimensions=1024` e a coluna indexada é `vector(1024)`.

Medido, com os mesmos textos de `smoke_nvidia.teste_embedding` para ser comparável a D-014:

| | PT rel. vs irrel. | margem PT | crosslingual EN | margem cross | q19 real PT→EN |
|---|---|---|---|---|---|
| **VL @1024** | 0,3459 vs 0,0059 | **+0,3400** | 0,3860 | **+0,3801** | 0,5157 |
| nemotron-3 @2048 | 0,5241 vs 0,1137 | +0,4105 | 0,5460 | +0,4323 | 0,5923 |
| nemotron-3 truncado @1024 | 0,5305 vs 0,0851 | +0,4454 | 0,5900 | +0,5049 | 0,6137 |

- **(a) falhou:** 0,4323 / 0,3801 = **1,14x**, contra o 1,5x exigido.
- **(b) passou:** truncar o `nemotron-3` para 1024 não só preserva como **melhora** a margem
  (+0,4323 → +0,5049). Registro isso porque é contra-intuitivo e porque é a metade da regra que o
  candidato descartado venceu.

**Então o `nemotron-3` é melhor nesta sonda, e mesmo assim não foi escolhido — isso é o ponto,
não um detalhe.** Ele ganha em margem absoluta nos dois regimes. O que a regra diz é que ganhar
por 1,14x não paga o custo arquitetural: adotá-lo significa preencher `vector(1024)` por truncagem
local, e a coluna indexada passaria a conter um vetor cuja equivalência com o pedido à API **não
é verificável neste modelo**, porque ele recusa o parâmetro. Trocar uma propriedade medida (D-029)
por uma suposição, para ganhar 14%, é o negócio que a regra existia para recusar.

**Dois números que reproduziram de sessões anteriores, e valem como controle:**
1. O `nemotron-3` deu **0,5241 vs 0,1137** — os mesmos dois dígitos que **D-014 registrou em
   22/08**, em outro processo e três dias depois. O ponto de comparação não derivou.
2. A propriedade Matryoshka do VL: `cos(api_1024, trunc_local_1024) = **0,99999996**` — o mesmo
   valor que D-029 mediu no modelo morto. **D-029 sobrevive intacta** e a coluna
   `embedding_bruto vector(2048)` continua fazendo o que foi construída para fazer.

**Consequência de schema: nenhuma.** `vector(1024)` + HNSW e `vector(2048)` sem índice ficam como
estão. Foi o desempate.

**O que fica registrado como NÃO medido:** esta sonda tem 4 passagens e 2 consultas. Ela mede
separação semântica, não `recall@k` — o número que decide de verdade sai da ablação sobre as 24
perguntas, adiante nesta mesma sessão. Se o recall cair com o VL, o `nemotron-3` volta à mesa com
o custo de schema explícito.
**Reversível?** Média — trocar de embedder exige re-embedar os 381 chunks (25 chamadas), o que é
barato; o que não é barato é a régua, que precisa ser re-medida junto.

### O reranker: sem escolha, e a janela precisou ser re-medida

`nvidia/rerank-qa-mistral-4b`, em `https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking`.
**Não houve alternativa a descartar** — é o único que responde.

D-034 mediu **8.192 tokens conjuntos** no 1B que morreu, e esse número é o que sustenta
`TETO_TOKENS = 450`. Deixá-lo apoiado num fato sobre um modelo extinto recriaria exatamente o bug
que D-034 foi escrita para matar: *"um número certo (450) sustentado por um fato falso (janela de
512) é pior que um número errado"*. Re-medido em
`scripts/auditoria/janela_rerank_qa_mistral_4b.py`:

| | 1B (D-034, morto) | **4B (25/08)** |
|---|---|---|
| a API recusa sem `truncate`? | sim, HTTP 422 | **sim, HTTP 400** (mensagem do Triton) |
| maior passagem, query de 6 tok | ~8.212 | **~6.952** |
| maior passagem, query de 78 tok | ~8.137 | **~6.880** |
| **soma passagem + query** | 8.218 / 8.215 (Δ 3) | **6.958 / 6.958 (Δ 0)** |
| repetibilidade do logit | "variam" (refutado na revisão) | **3/3 idênticos, espalhamento 0,000000** |

**A janela é conjunta, e a demonstração aqui é mais forte que a de D-034.** Duas queries que
diferem em 72 tokens produzem somas que diferem em **zero**. D-034 argumentava a conjunção com
uma diferença de 3 tokens entre 8.218 e 8.215 e chamava isso de invariante; aqui é identidade
exata. O bracket foi por sondagem exponencial (256 → 65.536) em vez de bissecar numa faixa
chutada — o `verificar_reranker.py` bisseca em [7000, 8600], herdado do 1B, e teria devolvido
"faixa inválida" sem explicar por quê.

*Ressalva de unidade, a mesma que `verificar_embedder.py` carrega:* a contagem é do `tiktoken`,
que é o tokenizador da OpenAI e não o deste modelo. O número serve como ordem de grandeza — e
para a decisão em jogo a margem é tão grande que a imprecisão não morde.

**Consequência para `TETO_TOKENS = 450`: nenhuma, e agora por um fato vivo.** O maior chunk do
corpus tem 446 tokens contra ~6.958 disponíveis. A janela encolheu 15% e continua sendo **15x** o
teto. Como em D-034, o reranker não impõe o teto do chunk — o teto continua sendo escolha de
precisão de recuperação (D-025).

**O que NÃO foi re-medido, e fica declarado:** a **curva de diluição**. A versão corrigida dela
(revisão da sessão 03, §2.3 — chunks vizinhos reais, platô entre −6,26 e −9,10) é sobre o 1B, e
a faixa de sweep que ela fechou em ~120–560 não se transfere. Como esta sessão não faz sweep de
banda de chunk, nada depende disso hoje; fica como dívida explícita para quando o sweep entrar.

**A regra operacional de D-034 muda de status, não de valor.** *"Nenhuma lógica pode depender de
margem abaixo de ~2 logits"* nasceu de variação entre execuções que a revisão da sessão 03 depois
refutou (36/36 idênticos). No 4B, 3 chamadas independentes deram `11.937500` exato — e `11,9375`
é `11 + 15/16`, assinatura de quantização, a mesma leitura que D-034 fez. **A quantização é real;
a variação entre execuções não se observa.** A regra fica valendo por causa da grade quantizada,
não por causa de ruído de serving.

---

## D-047 — `json_schema` fica, com n=5: a decisão estava certa e o argumento estava errado

**Data:** 25/08/2026 · **Sessão 05, Bloco 6** · fecha a §5 da revisão da sessão 03

**O que estava aberto.** D-040 escolheu `method="json_schema"` com uma tabela de três linhas —
**uma pergunta, uma execução por método** — contra um passo que a mesma decisão declara
não-determinístico. A revisão chamou isso de *"o risco mais carregado"* porque a escolha virou
`METODO_ESTRUTURADO` em `src/llm.py`, o portão único dos oito agentes da M4. Em 25/08 deixou de
ser teórico: o `json_schema` alucinou na q23 numa das três execuções do `--geracao` (D-040,
Atualização 3).

**Medido** (`scripts/auditoria/metodo_estruturado_n5.py`): a q23 recuperada **uma vez**, os mesmos
top-5 alimentando as 15 gerações, `temperature=0`, `max_retries=0` — para que uma execução seja
exatamente uma chamada e um método que falha e é re-tentado não pareça mais confiável do que é.

| método | absteve | respondeu (= alucinou) | erro | acurácia |
|---|---|---|---|---|
| **`json_schema`** | **4** | 1 | 0 | **4/5** |
| `function_calling` | 0 | 3 | 2 (timeout) | **0/5** |
| `json_mode` | 0 | 0 | 5 (parse) | **0/5** |

**Decisão: `json_schema` fica.** A margem é grande e agora tem amostra: 4/5 contra 0/5 e 0/5.
**Alternativas descartadas:** `function_calling` e `json_mode`, as mesmas de D-040, agora com n=5
em vez de n=1.

**O que muda é o ARGUMENTO, e é por isso que isto é decisão nova e não uma nota.** D-040 afirma
que o método *impede* a alucinação. Não impede: 1 em 5. A defesa correta na banca passa a ser
**"reduz de 3/3 para 1/5 na pergunta desenhada para induzi-la"** — que é uma afirmação sobre
frequência, e é a que os números sustentam. Bastou um contraexemplo para derrubar a afirmação de
impossibilidade, e ele apareceu na primeira vez que se olhou com n>1.

**Três achados que só aparecem com n=5:**

1. **O `function_calling` não erra "escolhendo responder" — ele degenera.** Duas das três
   respostas têm `texto` igual ao **eco da própria pergunta** (*"O TensorRT-LLM é mais rápido que
   o vLLM? Em quantos por cento?"*) e uma devolveu *"O que é TensorRT-LLM?"*. Isso é mais coerente
   com a leitura de D-040 — *"adiciona pressão para PREENCHER os campos da ferramenta"* — do que
   com "o modelo decidiu responder". O campo é preenchido com o que estiver à mão.
2. **O `json_mode` acerta o julgamento e falha no encanamento.** As cinco falhas de parse trazem
   `{"abstencao": true, "motivo_abstenc...` no corpo — **o modelo estava abstendo corretamente**,
   e o que quebra é o shape. D-040 registrou "devolve JSON com outro shape" com n=1; com n=5 dá
   para separar melhor: o `json_mode` não é pior a julgar, é inutilizável a serializar.
3. **A alucinação da q23 hoje é pior que a de 24/08, e o motivo é a recuperação nova.** Os top-5
   desta stack são **cinco chunks de TensorRT-LLM e nenhum menciona vLLM** — o chunk 38 do NIM,
   que citava "TensorRT-LLM, vLLM ou SGLang" na mesma frase e era o topo com +8,53 (D-035), não
   está mais lá. Uma das abstenções corretas diz exatamente isso: *"Não há menção ao vLLM em
   nenhum dos trechos fornecidos"*. Ou seja, o "60%" foi inventado **sem nem a âncora parcial**
   que existia antes. Menos gancho no contexto não produziu menos alucinação.

**O que continua não medido:** os outros dois regimes de `sem_resposta` e as 19 perguntas com
resposta, sob `function_calling` e `json_mode`. Esta medição é sobre **a q23** — a mesma limitação
que D-040 tinha, só que agora com n=5 no eixo que importava. Ampliar para as 24 × 3 métodos ×
5 execuções custaria ~360 chamadas e mediria sobretudo o que já se sabe.
**Reversível?** Fácil — é uma constante em `src/llm.py`.

**Consequência para a M4, que é o motivo de isto ter sido feito agora:** os oito agentes vão
passar por `METODO_ESTRUTURADO`, e o número que eles herdam é **4/5, não 5/5**. Nenhum agente pode
tratar a saída estruturada como garantida; a checagem de sanidade por código continua obrigatória.
Vale especialmente para o Evidence Validator, cujo trabalho é justamente não deixar passar
afirmação sem lastro.

---

## D-048 — `"token"` sai da lista de cripto, e a exclusão passa a casar por fronteira de palavra

**Data:** 25/08/2026 · **Sessão 06, passo 0** · paga o achado nº 1 do code review de 25/08

**O defeito, e ele produzia saída errada em produção.** `EXCLUSOES["cripto"]` continha `"token"`
e `elegibilidade()` casava com `if termo in texto` — substring. `SINAIS_TECNICOS` do Extractor
inclui `"tokens por segundo"`, então uma frase sobre custo de inferência virava evidência técnica
e disparava *"exclusão por 'cripto'"*. **Qualquer startup que falasse em "custo por token" era
reportada NÃO ELEGÍVEL ao NVIDIA Inception, pelo motivo errado** — no filtro que o projeto declara
como Diferencial.

**O gatilho já estava dentro do repositório e ninguém via:** `tests/test_grafo.py:102` monta um
documento com *"reduzindo latência e custo por token em produção"*. Aquela startup de teste era
reprovada em toda execução do `pytest` desde a sessão 01, e nenhuma asserção olhava para
`elegibilidade` — o filtro do Diferencial não tinha um único teste.

**Decisão, em duas partes independentes:**

1. **`"token"` sai.** O termo é ambíguo entre dois domínios — cripto e inferência de LLM — e o
   contexto que os separa não cabe numa lista de termos. Entram no lugar `"tokenização de
   ativos"`, `"security token"`, `"utility token"`, `"token não fungível"` e `"nft"`, que só
   existem em contexto cripto. **Medido:** o caso de teste de tokenização em blockchain continua
   excluído — por `blockchain`, não por `token`. Remover não abriu buraco.
2. **O casamento exige fronteira de palavra** (`re.search(rf"\b{re.escape(termo)}\b")`). É a
   correção estrutural: a mesma mecânica casaria `"ipo"` dentro de "equipo"/"princípio". É
   também a mesma correção que D-039 já exigiu no gabarito do RAG, onde `ILIKE '%SLA%'` casava
   dentro de "tran(**sla**)tion" e quase deixou entrar uma pergunta errada.

**Alternativa descartada — só a fronteira de palavra, mantendo `"token"`:** não resolve. `\btoken\b`
casa `"custo por token"` igualzinho. A fronteira conserta a *classe* do defeito; o termo ambíguo
precisava sair de qualquer jeito, e confundir as duas coisas teria deixado o bug de pé com a
aparência de consertado.

**Alternativa descartada — janela de coocorrência** ("`token` só exclui perto de outro termo de
cripto"): mais poderosa e mais cara de defender, e desnecessária depois que se mediu que
`blockchain` já pega o caso. Regra que não muda nenhum resultado medido é complexidade sem preço.

**Escrito em red-green.** `tests/test_elegibilidade.py` — o teste do falso positivo falhou antes
da correção, e vem **em par** com `test_tokenizacao_em_blockchain_continua_excluindo`, que existe
para impedir que a correção seja "apagar a regra de cripto". Um teste sozinho aqui é satisfeito
pela pior correção possível.

**Nota de risco, não paga:** a mesma classe de defeito vive em `SINAIS_TECNICOS` do Extractor —
`"rag"` casa dentro de "fragmento", `"eval"` dentro de "evaluation", `"lora"` dentro de "flora".
Não foi corrigida aqui porque o Extractor será reescrito no bloco 2 desta sessão, e a régua do
bloco 1 é que vai dizer se isso custa precisão de verdade ou se é preocupação teórica.

---

## D-049 — `Elegibilidade.evidencias` deixa de nascer vazia: a exclusão aponta para o trecho

**Data:** 25/08/2026 · **Sessão 06, passo 0** · paga o achado nº 2 do code review de 25/08

**O defeito.** `Elegibilidade.evidencias` nascia `[]` e nunca era preenchida, enquanto
`motivos_exclusao` afirmava *"o termo X aparece nos documentos"* e o Briefing imprimia tudo sob o
rodapé *"Toda conclusão acima aponta para o documento que a sustenta"*. **Era a única conclusão do
sistema sem `list[Evidencia]`** — contra a convenção que `src/state.py` chama de decisão nº 1
("evidência é o átomo, não um campo opcional") — e sem teste.

**A causa era de desenho, não distração:** a função concatenava os trechos de todas as afirmações
numa string só antes de procurar os termos. Depois do `in`, a informação de *qual* trecho
continha o termo já tinha sido destruída. Um campo `evidencias` era impossível de preencher sem
mudar o laço.

**Decisão:** o laço percorre **evidência a evidência**, e o primeiro par (termo, evidência) que
casa produz o motivo **e** anexa a `Evidencia` que o sustenta. Custo: um `next()` sobre um
gerador. O teste novo é a invariante executável — `motivos_exclusao` não vazio ⇒ `evidencias` não
vazia, e o `trecho` anexado é aquele onde o termo ocorre.

**Alternativa descartada — anexar todas as evidências do perfil:** faria o teste passar e seria
falso. "Evidência que sustenta esta exclusão" e "tudo que a base tem sobre a empresa" são coisas
diferentes; a segunda dá aparência de lastro sem apontar nada, que é exatamente o defeito que
D-021 nomeou (campo sem fonte literal vira valor explícito, não valor plausível).

**Correção de comportamento que veio junto, e ela é visível no briefing:** a pendência *"ano de
fundação não consta na base"* estava num `else` do teste de idade, o que fazia a startup COM ano
de fundação recente não receber pendência nenhuma sobre isso — correto — mas também acoplava duas
regras num ramo só. Agora a exclusão por idade e a pendência por ausência de idade são dois testes
independentes sobre o mesmo campo, que é a disciplina que o docstring do módulo já declarava:
*"a base não prova"* é diferente de *"a base prova que não"*.

---

## D-050 — A régua dos agentes: 8 fixtures, e uma só entra se flipar uma decisão que nenhuma outra flipa

**Data:** 25/08/2026 · **Sessão 06, Bloco 1**

**O problema.** A base tinha 3 startups e as 3 eram `perfil_alvo: AI-native`. Um classificador que
devolvesse `"AI-native"` incondicionalmente passava em **3 de 3**. Não existia número capaz de
distinguir um Extractor com LLM do casador de substring da sessão 01. O critério 2 chegou a nível
4 porque teve régua desde o primeiro dia; os critérios 1 e 3 — **40 pontos** — não tinham nenhuma.

**Critério de seleção, e ele é o argumento:** *uma fixture só entra se flipar pelo menos uma
decisão que nenhuma fixture existente flipa.* Fixture que não flipa nada é custo de curadoria com
zero valor de medição. Sob essa regra, 3 + **5 novas = 8**:

| fixture | o que ela flipa, e que nada flipava |
|---|---|
| **RD Station** | `AI-enabled`. Cada produto carimbado "Com Inteligência Artificial", recurso chamado "Copiloto de IA", preço por plano. Copilot puro — sem ela o eixo 1 não tinha contraste |
| **SunnyHUB** | `non-AI`. Cleantech que instala painel solar; zero termo técnico nos três documentos. A regra "non-AI está fora do funil" só era testada em unidade sobre `derivar_quadrante` |
| **Freedom AI** | **Mirage PMF.** "Vendo mão de obra digital", 900% de receita, o fundador chama a empresa de "agência" — e alega "LLM própria" sem uma linha que sustente |
| **Deal** | `elegivel: false` por `consultoria`. `contexto/03` §2 pede este caso por escrito, e ele é o Diferencial declarado |
| **Maritaca AI** | `maturidade_stack: alta` → quadrante **`ja-otimizada`**, que existia só no papel. Quantização QAT, MoE, prefill/decode separados, MFU em B200, GPU-hora |

**Ficaram FORA de propósito, e o corte é decisão:**
- **Exclusão por idade** — `ano_fundacao` é campo estruturado e determinístico. Coletar 3 páginas
  reais para exercitar um `if` aritmético não compra medição. Virou teste unitário.
- **Regras 2 e 4 do Evidence Validator** — já têm teste unitário, e pior: uma fixture "documento de
  um tipo só" **violaria a validação do próprio `seed.py`** (`len(tipos) < 2` é erro). Criar
  fixture que quebra o validador para exercitar o validador é dívida, não cobertura.

**Regra de curadoria, porque estas fixtures rotulam empresas reais.** Toda `url_fonte` é real e
resolve — `seed.py --verificar-urls` confirmou as 24. O rótulo é afirmação sobre **o que a base
pública prova**, não sobre a empresa: para non-AI e consultoria, a coleta buscou empresas que *se
descrevem* assim (classificar uma consultoria como consultoria é ler o documento); para a Freedom,
o esperado é ambíguo justamente porque a base não decide.

---

## D-051 — O gabarito mora na fixture, e "não decide" é resultado com coluna própria

**Data:** 25/08/2026 · **Sessão 06, Bloco 1**

**Onde mora:** bloco `gabarito:` em `data/seed/*.yaml`, ao lado do `perfil_alvo` que já existia.
**Alternativa descartada:** arquivo separado `data/avaliacao/gabarito-agentes.yaml`, espelhando o
gabarito do RAG. Perdeu por dois motivos: o `seed.py` já documenta e já garante que este material
não vai para o banco (se fosse, o Classifier enxergaria a resposta), e uma empresa nova passaria a
exigir edição em dois arquivos, com risco de dessincronia por nome.

**Cada campo aceita três formas, e a terceira é a que faltava:**

    classe: AI-native                valor  -> DECIDE      · entra em acertos/decididos
    classe: [AI-native, AI-enabled]  lista  -> AMBÍGUO     · bater um não é acerto limpo
    maturidade_stack: null           null   -> NÃO MEDIDO  · sai do denominador

A saída publica sempre `acertos / decididos (+A ambíguos, +N não medidos)`. Duas fixtures usam as
formas novas por razão substantiva: a **Laura** tem `maturidade_stack: null` (o site diz
"computação cognitiva" e nada mais — ausência de sinal não é prova de stack imatura, pela regra 4)
e `confianca: [baixa, media]`; a **Freedom** tem `classe: [AI-native, AI-enabled]`.

**O que se conta:**

| métrica | critério |
|---|---|
| classe · maturidade · confiança | igualdade exata com o gabarito |
| elegibilidade | bool exato **E** o RÓTULO do motivo. Recusar pelo motivo errado é erro nomeado, não acerto — é o defeito que D-048 pagou |
| **dor — precisão** | **manchete.** O modo de falha do stub é emitir demais, não de menos |
| dor — recall | secundário: um extrator que emite as 8 dores faz 100% por construção |
| dor — proibida | falha **nomeada**, com startup e dor. "Errou 0,3" não é acionável |
| **discriminação** | conjuntos DISTINTOS de dores / 8 |
| evidência literal | todo `trecho` ocorre **verbatim** no documento citado. Zero API |

**`dores_ambiguas` sai dos dois lados** — emitir uma não conta a favor nem contra. **Quadrante não
é contado:** é `derivar_quadrante(classe, maturidade)`, função pura já testada; contá-lo inflaria
o número contando os dois eixos duas vezes.

**A linha de base trivial é obrigatória na tabela** (`--baseline`): sempre `AI-native`, stack
`baixa`, todas as 8 dores, sempre elegível. É o `denso puro` deste critério, e nenhum número de
agente vai para o `CLAUDE.md` sem ela ao lado.

**`--validar` já se pagou antes de medir qualquer coisa:** apontou que o gabarito da Freedom não
dava veredito para `latencia`. A regra "toda dor precisa de veredito explícito, inclusive
'ambígua'" existe para que omissão não vire silenciosamente um zero.

---

## D-052 — O que a régua mediu no primeiro dia: três achados, e um deles corrige o `CLAUDE.md`

**Data:** 25/08/2026 · **Sessão 06, Bloco 1** · zero chamada de API

| | linha de base TRIVIAL | stub atual |
|---|---|---|
| classe | **4/7** | **3/7** |
| maturidade_stack | 6/7 | 6/7 |
| confiança | 3/8 | 0/6 (+2 ambíguos) |
| elegível | 6/7 | 5/7 |
| motivo_exclusão | 0/1 | **1/1** |
| **dor — precisão** | 32% | **49%** |
| dor — recall | 100% | 100% |
| **discriminação** | 1/8 | **8/8** |
| dor proibida emitida | 28 | 10 |

**Achado 1 — o stub é PIOR que o classificador trivial no rótulo do TAPI: 3/7 contra 4/7.** É o
número que justifica a sessão inteira. Ele não era observável com 3 fixtures todas AI-native, e é
exatamente a situação que a régua existia para tornar visível.

**Achado 2 — a discriminação REFUTA metade do diagnóstico da dívida nº 6.** O `CLAUDE.md` e a
sessão 04 afirmam que o Extractor *"produz o mesmo conjunto de dores para toda startup"*. Sobre
8 fixtures diversas, ele produz **8 conjuntos distintos de 8**. A afirmação era verdadeira sobre a
base que existia — 3 startups, todas de saúde — e generalizava um artefato da amostra. O
diagnóstico que **sobrevive** é o outro lado: a precisão é de 49%, e são as dores ERRADAS que
poluem a consulta, não a falta de variação. É a segunda vez no projeto que ampliar a amostra
derruba uma conclusão tirada com n pequeno; a primeira foi D-039.

**Achado 3 — o filtro do Inception exclui por MENÇÃO, não por identidade, e derruba o prospect
prioritário.** Com as evidências que D-049 passou a anexar, o motivo é legível:

- **Axenya** (prioridade máxima da curadoria) é recusada por *"Integramos **consultoria**, dados e
  operação clínica"* — ela **usa** consultoria, não **é** uma consultoria;
- **Freedom AI** é recusada porque um **parceiro** (Grant Thornton) é *"auditoria, **consultoria** e
  tributos"* — a palavra não se refere à startup;
- **Deal** é recusada corretamente: *"A Deal **é a consultoria** de IA"*.

**Fronteira de palavra NÃO resolve este caso** — e é isso que o separa de D-048. Lá o termo era
ambíguo entre domínios; aqui o termo é o certo e o **sujeito** é outro. Separar "a empresa é X" de
"a empresa menciona X" é julgamento semântico.

**Decisão: não consertar agora com heurística nova, e o motivo não é preguiça.** Um padrão de
identidade (`"é uma consultoria"` casa, `"integramos consultoria"` não) resolveria os três casos
medidos e introduziria um risco pior — **falso negativo silencioso**: se a frase que afirma a
identidade não estiver entre as evidências recortadas, a Deal deixa de ser excluída e o
Diferencial para de funcionar sem ninguém notar. Falso positivo aparece no briefing; falso
negativo não aparece em lugar nenhum. O julgamento de sujeito é precisamente o que o Extractor com
LLM entra para fazer, e agora existe régua para dizer se ele o fez: `motivo_exclusao` é 1/1 hoje e
`elegivel` é 5/7, e os dois números têm que subir juntos.

**Achado 4, menor e da mesma família de D-048 — substring no Extractor.** `'rag'` casa dentro de
"co(rag)em" na Freedom, e `'sla'` (que está em `SINAIS_AUTOPILOT` para pegar SLA) casa dentro de
"legi(sla)ção" na Maritaca. O segundo é literalmente o erro que D-039 achou no gabarito do RAG
(`ILIKE '%SLA%'` em "tran(sla)tion"). Está anotado nas fixtures.

---

## D-053 — Extractor: heurística gera CANDIDATO, LLM julga — e o teto do casador é 100%

**Data:** 25/08/2026 · **Sessão 06, Bloco 2** · portão escrito ANTES de medir

**Três desenhos avaliados:**

**A — uma chamada por startup, schema largo (`PerfilStartup` inteiro). DESCARTADA.** Viola D-045
(*"tipo estreito por chamada — docstring de schema é prompt"*): seis campos heterogêneos num
schema só diluem a instrução. O motivo real, porém, é a citação: pedir ao modelo que devolva o
`trecho` **junto com** a conclusão convida paráfrase, e todo o projeto repousa em
`Evidencia.trecho` ser literal. Três documentos inteiros num modelo de 8b também é o regime em que
D-034 mediu o julgamento cair por diluição.

**B — fan-out interno, uma chamada por dimensão, schema estreito.** Cumpre D-045; custa 4 × 8 = 32
chamadas por medição. **Fica como plano B, promovível por medida.**

**C — candidato por heurística, julgamento por LLM. ESCOLHIDA.** `SINAIS_*` e `GATILHOS_DOR`
continuam existindo, rebaixados de *decisor* a *gerador de candidatos*: produzem frases literais,
como já produzem. O LLM recebe **só as frases candidatas** — nunca as páginas — e decide se a
frase sustenta a dor. Quatro razões, em ordem de peso:

1. **É impossível o LLM inventar citação.** `Evidencia.trecho` continua vindo do recorte por
   `str`. Mesma disciplina de `indices_citados` em D-040 — o modelo devolve referência, não fonte.
2. **Contexto pequeno por chamada**, que é o regime em que um 8b funciona.
3. **Ataca a métrica que está quebrada.** A régua mediu precisão de 49% e recall de 100%: o
   problema é emitir demais. C aumenta precisão sem mexer no recall.
4. **Degrada com graça** — com a API fora do ar, volta ao comportamento de hoje em vez de parar.

**O custo honesto de C foi MEDIDO, e ele não existe.** A objeção legítima é que o recall fica
preso ao vocabulário de `contexto/02` §5: dor com palavra fora da lista nunca vira candidata e o
LLM nunca a vê. `avaliar_agentes.py --validar` mede esse teto sem gastar uma chamada — quantas
`dores_esperadas` do gabarito têm ao menos um candidato hoje. Resultado: **12/12 = 100%**. Não há
recall a comprar ampliando gatilhos, e a decisão de pôr o LLM como juiz e não como buscador está
medida em vez de argumentada.

**Alternativas descartadas, com o motivo pronto para banca:**

| pergunta | resposta |
|---|---|
| *"Por que não fine-tuning?"* | 8 fixtures rotuladas é few-shot, não treino. E o TAPI pede sistema multi-agente, não modelo treinado |
| *"Por que não NER/spaCy para a stack?"* | O que falta não é entidade, é julgamento sobre a entidade: *"usamos GPT-4"* e *"self-hospedamos um modelo em GPU"* têm as mesmas entidades e significados opostos |
| *"Por que não um 70b?"* | Mesmo portão de D-039: medir com o 8b na régua primeiro. Um 70b de preview carrega a mesma classe de risco de EOL que já matou a stack duas vezes |
| *"Por que não o LLM lendo os 3 documentos inteiros?"* | Contexto num 8b, mais paráfrase de citação. D-034 já mediu julgamento caindo com passagem longa |

---

## D-054 — A dívida nº 6 ataca o Extractor primeiro, e a ordem sai do CUSTO DA RÉGUA

**Data:** 25/08/2026 · **Sessão 06, Bloco 3**

A dívida nº 6 da sessão 04 deixou duas linhas de ataque *"a decidir com medição"*: **Extractor
real** ou **filtro de recomendabilidade no chunk**. Ordem: **Extractor primeiro**, por três
motivos, e o primeiro é o que vale na banca.

1. **A ordem é decidida pelo custo da RÉGUA, não pela força da hipótese.** O filtro de chunk
   exigiria um gabarito de *recomendação* — para 8 startups × N dores, qual das 16 tecnologias é a
   certa —, que não existe e é curadoria de especialista. O Extractor tem régua barata: quem lê o
   documento anota `dores_esperadas` e `dores_proibidas` em minutos, e foi o que esta sessão fez.
   Extractor primeiro porque é o único dos dois que dá para medir esta semana.
2. **O argumento causal é assimétrico.** O filtro de chunk age DEPOIS da consulta: consulta
   genérica com filtro remove os chunks de navegação e devolve outros chunks genéricos — melhora a
   aparência sem tocar a causa. O contrário vale: consulta específica melhora tudo que vem depois,
   **inclusive** a taxa de chunk de navegação no topo, porque *"Resources / Developer Forums"*
   vence consulta vaga, não consulta com stack literal.
3. O recuperador faz r@1 de 95% quando a consulta é boa (D-046). O suspeito não é ele.

---

## D-055 — O critério de empate do Extractor, fixado ANTES da medição

**Data:** 25/08/2026 · **Sessão 06, Bloco 3** · escrito antes de rodar

Mesmo procedimento que fez D-046 dar certo: a regra do desempate do embedder foi fixada antes da
sonda, e por isso o empate virou argumento em vez de racionalização. **Empate** = o Extractor com
LLM, contra a linha de base medida em D-052:

- não bate a **precisão de dor** (49%) por margem ≥ **0,15**, **e**
- não leva a **discriminação** a ≥ **6 conjuntos distintos de 8** (o stub já faz 8/8, então este
  braço está satisfeito por construção — o que significa que **a decisão fica inteira na
  precisão**, e isso é consequência do achado 2 de D-052, não uma facilidade concedida).

**Se empatar:** o Extractor com LLM **não entra em produção**. O stub fica, a régua fica, e o
esforço migra para o filtro de recomendabilidade, que passa a ser a hipótese sobrevivente. A frase
de defesa é a mesma que D-046 escreveu sobre o `nemotron-3-embed`: *"medi que o LLM não bate o
casador de substring nesta base, com este modelo; o gargalo é outro"*.

**Se piorar:** reverter e registrar qual métrica caiu. O `git` guarda o código; a régua diz qual.

---

## D-056 — O Extractor com LLM foi medido, EMPATOU pela regra de D-055, e não entra em produção

**Data:** 25/08/2026 · **Sessão 06, Bloco 2** · ~104 chamadas em duas medições

**O resultado, na régua de D-051 (já com as correções de D-057), sobre as 8 fixtures.**

**O juiz é reportado em FAIXA, com três execuções, e isso não é excesso de zelo** — é a regra que
a sessão 03 aprendeu e a 04 escreveu: *"a geração varia entre execuções; número de geração se
reporta em três execuções ou não se reporta"*. A primeira redação desta decisão publicou 58% como
se fosse **o** número, com n=1, no mesmo projeto que criou D-039 para resolver exatamente isso do
outro lado. As colunas determinísticas não variam e são reportadas como valor.

| | trivial | casador (produção) | **juiz com LLM (n=3)** |
|---|---|---|---|
| classe | 4/7 | 3/7 | **2–3 / 7** |
| maturidade_stack | 6/7 | 6/7 | 6/7 |
| confiança | 3/8 | 0/6 | 0/6 |
| elegível | 6/7 | 5/7 | **5–6 / 7** |
| motivo_exclusão | 6/7 | 5/7 | **5–6 / 7** |
| **dor — precisão** | 32% | **49%** | **50–62%** |
| dor — recall | 100% | 100% | 79–96% |
| discriminação | 1/8 | 8/8 | 8/8 |
| dor proibida emitida | 28 | 10 | 6–9 |

**A regra de D-055, escrita antes de medir, exigia margem de precisão ≥ 0,15 sobre os 49% do
casador — ou seja, 64%. A faixa do juiz é 50–62%: NEM O MELHOR CASO DAS TRÊS EXECUÇÕES ALCANÇA.**
D-055 também já havia registrado que a discriminação estaria satisfeita por construção (o casador
já faz 8/8), *"o que significa que a decisão fica inteira na precisão"*. Fica — e com n=3 a
conclusão é mais forte do que era com n=1, não mais fraca.

**Decisão: `USAR_JUIZ_LLM = False`.** O juiz existe, está medido, é ligável por `--juiz` no
harness, e **não roda por default**. A justificativa não é que ele seja ruim — ele reduz emissões
proibidas de 10 para 6–9 e sobe a precisão —, é que a margem foi fixada para exigir ganho que pagasse o custo: **52 chamadas
de API por execução, seis minutos de parede, e uma dependência a mais de um catálogo que aposentou
modelo duas vezes em três meses**. Nove pontos de precisão não compram isso.

É a mesma frase que D-046 escreveu sobre o `nemotron-3-embed`, que separava melhor e perdeu:
o empate está registrado como o motivo, não escondido.

**O que a medição comprou mesmo empatando, e é bastante:**

1. **A opção C está validada como desenho** — o teto de recall do casador é 100% (D-053), a
   evidência continua literal em 100% dos trechos, e o juiz reduz emissões proibidas e conserta o
   falso positivo de elegibilidade da Freedom AI em 2 das 3 execuções. O que falta não é a
   arquitetura; é margem estável, e a instabilidade entre execuções é ela mesma um argumento
   contra pôr o juiz no caminho crítico de uma demonstração ao vivo.
2. **O gargalo mudou de lugar e agora tem nome.** Depois do juiz, `confianca` continua 0/6 e
   `classe` continua 3/7 — ou seja, **o problema não está mais no Extractor**. `classe` é aritmética
   de pontos no Classifier e `confianca` é o `min()` do Evidence Validator, e nenhum dos dois é
   afetado por melhorar a evidência de entrada. A próxima sessão sabe onde mexer porque esta mediu.

**O ACHADO TÉCNICO DA MEDIÇÃO, e ele vale mais que o número: enumerar modos de falha no prompt
ensinou o modelo a recitá-los.**

A primeira versão da instrução listava os três erros da busca por palavra-chave e fechava com
*"na dúvida, reprove"*. Resultado: precisão **22%**, recall **20%**, e **cinco das oito** startups
classificadas como `non-AI` porque o juiz reprovava toda evidência. Duas amostras diagnosticaram:

- **Maritaca AI** — o modelo escreveu que a frase *"pode ser interpretado como uma preocupação com
  a otimização de inferência e self-hosting"* e concluiu, na mesma resposta, que *"não há nenhuma
  frase que sustente"*. O raciocínio contradiz a conclusão.
- **Doutor-AI** — sobre a frase *"Com mais de 700 multiagentes e tecnologia própria…"*, o motivo
  devolvido foi, palavra por palavra, a **regra nº 2 do próprio prompt**: *"A frase fala do cliente
  da empresa, de um parceiro, de um concorrente ou do mercado"*. Ele não aplicou a regra — copiou.

**Um ajuste, declarado como único e aceito qualquer que fosse o resultado:** critério POSITIVO
primeiro ("aprove quando a frase afirma isso sobre a própria empresa, mesmo parcialmente"), o
viés `"na dúvida, reprove"` removido, e a exigência de que o motivo CITE a frase julgada — que é o
que ataca diretamente a recitação. Precisão foi de 22% para 58%, recall de 20% para 89%.

**A lição é generalizável e vai para o vídeo:** num modelo de 8b, uma lista de erros a evitar
funciona como um menu de desculpas prontas. O prompt precisa dizer o que APROVAR; o que reprovar
vem depois e curto. Vale para os outros sete agentes, e é o oposto do que a intuição sugere.

**Alternativa não exercida, e o motivo:** ajustar o prompt uma terceira, quarta e quinta vez até
passar de 64%. Isso não é medir, é ajustar ao gabarito — e destruiria a régua que a sessão acabou
de construir. Um ajuste, com o diagnóstico escrito antes, é correção; três é sobreajuste com
outro nome.

**Nota de comportamento alterada junto, e ela é do casador:** o desempate copilot/autopilot passou
de `len(ev_auto) >= len(ev_copi)` para `>`. Com `>=`, empate 1×1 resolvia para AUTOPILOT — e foi
por isso que a RD Station, que é copilot puro ("Copiloto de IA", preço por plano), era lida como
quem vende o trabalho executado. Empate não é evidência de autopilot; é ausência de evidência.

---

## D-057 — O code review derrubou três afirmações desta sessão, e uma delas era a régua medindo errado

**Data:** 25/08/2026 · **Sessão 06, code review `high`** · 8 achados, 6 pagos

**Achado 1 — a fronteira de palavra de D-048 estava ancorada dos DOIS lados, e isso desligou o
plural.** `\bconsultoria\b` **não casa** "consultorias"; nem `\brevenda\b` em "revendas", nem
`\bcriptomoeda\b` em "criptomoedas". Plural é a forma comum em texto institucional, então uma
empresa que se descrevesse como *"consultorias de IA"* passava pelo filtro do Inception. **D-048
trocou um falso positivo visível por um falso negativo silencioso**, que é a troca ruim — e o
comentário que a decisão escreveu afirmava o contrário ("`revenda` casava dentro de `revendas`
(aceitável)"), implicando um comportamento que a própria mudança tinha removido.

**Correção:** âncora **só no início** — `rf"\b{re.escape(termo)}"`. Mantém o alvo real (`"ipo"` não
casa "equ(ipo)") e devolve o plural. Dois testes novos, um para cada lado. Ressalva registrada:
a comparação é sensível a acento — `"ipo concluído"` não casa "ipo concluido".

**Achado 3 — a justificativa do desempate copilot/autopilot citava uma medição que não existe.**
D-056 e o comentário do código afirmavam que a RD Station *"empatava 1×1"* e por isso era lida
como autopilot. **Ela é 3×1** e sai autopilot com os dois operadores. O erro de origem: eu li a
lista de TERMOS distintos que casaram (`AUTOPILOT ['resultado']`, `COPILOT ['ferramenta']`) como se
fosse a contagem de EVIDÊNCIAS.

**Medido depois, com os dois operadores sobre as 8 fixtures: `>=` e `>` dão o MESMO placar** —
classe 3/7, precisão 49%. A mudança fica, mas por argumento **conceitual** e declarado como tal:
empate não é evidência de autopilot, é ausência de evidência, e o default de um empate não deveria
ser o rótulo mais favorável. Ela não compra métrica, e dizer que compra seria inventar um ganho no
arquivo que existe para defender decisões diante de uma banca.

**Achado 6 — a régua estava medindo `motivo_exclusao` errado, e o número publicado era enganoso.**
`motivo_exclusao: null` era tratado como "não medido" mesmo quando o gabarito já dizia
`elegivel: true` — ou seja, quando o motivo esperado é **nenhum**. Consequência: Axenya e Freedom
AI, recusadas pelo rótulo errado (achado 3 de D-052), apareciam numa coluna limpa de **1/1**, e era
esse 1/1 que o `CLAUDE.md` publicava.

Com a correção, `null` + `elegivel: true` passa a exigir que nenhum motivo seja emitido:

| | trivial | casador (produção) |
|---|---|---|
| motivo_exclusão | **6/7** | **5/7** |

**E isso muda a leitura da sessão.** O achado 1 de D-052 dizia que o stub perde do classificador
trivial no rótulo do TAPI. Com a régua corrigida, ele perde em **quatro dos cinco campos**:
classe 3/7 × 4/7, confiança 0/6 × 3/8, elegível 5/7 × 6/7, motivo 5/7 × 6/7. Empata em
maturidade (6/7) e só ganha em dor — precisão 49% × 32%, discriminação 8/8 × 1/8.

A leitura honesta: **o valor do casador está inteiro na extração de dores; a camada de
classificação em cima dele é pior que constante.** É uma afirmação mais forte e mais útil que a
anterior, e ela só apareceu porque a régua foi auditada.

**Achado 5 — D-049 guardava a evidência da exclusão e o briefing não a imprimia.** `_secao`
imprimia `x exclusão por 'consultoria': o termo aparece nos documentos` sem URL e sem trecho, sob o
rodapé *"Toda conclusão acima aponta para o documento que a sustenta"* — exatamente o defeito que
D-049 foi escrita para fechar, sobrevivendo na única saída que o sistema produz. Corrigido e
testado: `test_briefing_imprime_a_evidencia_da_exclusao`.

**Achado 7 — precisão indefinida estava sendo contada como zero.** Uma fixture que emite só dores
ambíguas tem `contaveis` vazio; com `dores_esperadas` não vazias, o cálculo devolvia `0.0` e isso
entrava na média que é a métrica de manchete. "Não previu" não é "previu tudo errado", e o recall
já pune esse caso. Agora é pulado, simétrico com o recall — que já pulava fixtures sem esperadas.
Nenhuma fixture atinge o caso hoje; o braço `--juiz`, que reduz emissões, atinge.

**Achado 8 — `--validar` prometia "ZERO API" e não cumpria com `--juiz`.** As duas verificações
chamam `extractor.node` nas 8 fixtures. Pior que o custo: com o juiz ligado, o número medido deixa
de ser o **teto do casador** e vira o recall do juiz, que é outra grandeza com o mesmo nome. A
combinação agora é recusada com aviso, em vez de produzir um número errado em silêncio.

**Achados 2 e 4 NÃO pagos, e continuam registrados:** a exclusão por menção (D-052, achado 3) e o
`min()` do Evidence Validator sobre TODAS as afirmações. O review acrescentou ao segundo o
diagnóstico que faltava e que vira pauta: `alta` é **estruturalmente inalcançável**, porque
`perfil.afirmacoes` inclui toda `DorObservada` e `_casar` emite uma frase por documento — a maioria
tem um tipo só e devolve `baixa`. Consequência perversa: **um extrator que acha MAIS dores reais
BAIXA a confiança do diagnóstico**. O mínimo deveria ser sobre as afirmações que sustentam a
classificação — as que já estão em `diagnostico.evidencias` —, não sobre sinais de dor não
relacionados. É isso que o 0/6 da régua está medindo, e não a qualidade do classificador.

---

## D-058 — O critério de sucesso do Classifier e do Evidence Validator, fixado ANTES do código

**Data:** 27/08/2026 · **Sessão 07, Bloco 0** · escrito antes de a primeira linha ser alterada

D-055 é a única razão pela qual a conclusão sobre o juiz do Extractor é defensável hoje: a margem
existia antes do número. Sem ela, 58% teria virado "melhorou" e o juiz teria entrado. Esta decisão
aplica a mesma disciplina aos dois campos que a régua nomeou como gargalo, e ela precisa existir
por escrito porque **o alvo aqui não é "melhorou"** — nos dois campos o sistema atual **perde do
classificador trivial**, então "melhorou" pode significar continuar perdendo.

**A linha de base, medida em 27/08 antes de planejar** (`--baseline` e o default, zero API):

| campo | trivial | casador (produção) |
|---|---|---|
| classe | 4/7 (+1 ambíguo) | **3/7** (+1 ambíguo) |
| confianca | 3/8 | **0/6** (+2 ambíguos) |

E o `--falhas` dá o diagnóstico que a tabela esconde:

- **Os 4 erros de `classe` apontam todos para o mesmo lado** — Axenya, Doutor-AI, Laura Networks e
  Maritaca são `AI-native` no gabarito e saem `AI-enabled`. Nenhum erro no sentido contrário. As
  três que o casador acerta são Deal, RD Station e SunnyHUB.
- **Os 6 erros de `confianca` são todos `baixa`.** O campo é constante, não impreciso.

### Os alvos

| campo | trivial | hoje | alvo |
|---|---|---|---|
| `classe` | 4/7 | 3/7 | **≥ 5/7** *e* nenhuma perda entre Deal, RD Station e SunnyHUB |
| `confianca` | 3/8 (37,5%) | 0/6 | **≥ 4 acertos absolutos** *e* taxa sobre decididos ≥ 50% |

**Por que duas condições em cada um, e não uma taxa:**

- Em `classe`, porque os 4 erros são unidirecionais. Uma regra mais frouxa compra `AI-native`
  barato e o preço aparece na SunnyHUB — emitir `AI-native` para uma empresa de painel solar é,
  nas palavras da própria fixture, *"o falso positivo mais caro que este projeto pode cometer numa
  demonstração"*. Subir de 3 para 5 perdendo a SunnyHUB seria uma vitória na tabela e uma derrota
  na demo.
- Em `confianca`, porque **a taxa é gamificável pelo denominador**: duas fixtures têm conjunto
  ambíguo (`[baixa, media]`), e responder dentro deles tira a fixture do denominador sem acertar
  nada. É exatamente o que o casador faz hoje para chegar a 0/**6** enquanto o trivial é medido
  sobre **8**. Exigir 4 acertos em valor absoluto fecha essa porta: o trivial tem 3.

### As guardas — não são alvo, são veto

`maturidade_stack ≥ 6/7` · `dor — precisão ≥ 49%` · `dor — recall = 100%` · `discriminação 8/8` ·
`elegivel ≥ 5/7` · `motivo_exclusao ≥ 5/7` · `pytest -q` verde.

**Se qualquer guarda cair, a mudança sai — mesmo que o campo-alvo tenha passado.** É a lição de
D-048, que trocou um falso positivo visível por um falso negativo silencioso e só foi pega pelo
code review.

### O que fazer se empatar

1. **Os dois campos são julgados INDEPENDENTEMENTE.** São dois agentes e dois defeitos distintos.
   `confianca` pode entrar sem `classe` e vice-versa. Julgar em bloco deixaria um campo carregar o
   outro, que é "ajustar até passar" com outra roupa.
2. **Empate ou derrota: a mudança não entra em produção.** Vira achado medido aqui, com o número, e
   o código volta ao que era — o mesmo destino de `USAR_JUIZ_LLM` em D-056.
3. **Um ajuste só, declarado como único antes de rodar.** Se a primeira redação da regra não
   alcançar o alvo, não há segunda tentativa calibrada contra o gabarito. É literalmente o erro que
   D-056 nomeou: *"ajustar até passar de 64% não seria medir, seria ajustar ao gabarito"*.
4. **O gabarito não muda para o sistema passar.** Um valor só pode ser alterado com argumento
   escrito a partir de `contexto/02`, **nunca a partir do resultado medido**, e a alteração é
   commitada *antes* da medição do novo desenho. Candidato já visível e registrado agora, antes de
   qualquer placar: `SunnyHUB.confianca: media` é o único valor do gabarito das 8 fixtures sem
   justificativa escrita na `nota`. Auditar é legítimo; auditar depois de ver o placar não é.

### A linha de controle, e por que ela existe

A tabela da sessão 06 tem a linha trivial porque sem ela 49% de precisão pareceria bom em vez de
"17 pontos acima de emitir tudo". O Bloco 1 tem a dele: **a mesma aritmética de hoje com o limiar
em 3** (`pontos >= 3`) — a correção de um caractere.

Ela é medida **antes** de a aritmética ser substituída e vai para a tabela junto. Se a rubrica em
degraus não bater o limiar-3, a rubrica não paga a complexidade que introduz. É o mesmo papel de
`--truncar-pool` em D-037, que separou "ganho do pool" de "ganho da fusão".

**Medida em 27/08, antes de qualquer mudança de desenho: `classe` 4/7.** Nada mais se move —
maturidade 6/7, confiança 0/6, dor 49%, discriminação 8/8, todos idênticos. Ou seja: **um caractere
já empata com o classificador trivial** e recupera a Axenya. Isso não afrouxa o alvo, aperta: a
barra de ≥ 5/7 fixada acima é exatamente o que separa "a rubrica pagou" de "a rubrica fez o que um
`>= 3` faz de graça". Se a rubrica em degraus parar em 4/7, ela não entra — pela regra 2, e porque
seria complexidade sem contrapartida medida.

### A ordem de medição tem três passos, e o motivo é atribuição

O desenho escolhido para `confianca` lê `diagnostico.evidencias`, e quem preenche esse campo é o
Classifier. Mexer no Classifier move `confianca` junto — e uma medição em que as duas mudanças
entram ao mesmo tempo não consegue dizer de quem é o delta.

| passo | o que muda | o que fica atribuído |
|---|---|---|
| 0 | nada | a linha de base |
| 0b | `pontos >= 3` | a linha de controle |
| 1 | **só** o Evidence Validator | o delta de `confianca`, isolado |
| 2 | **e então** o Classifier | o delta de `classe` + o efeito de 2ª ordem em `confianca` |

O efeito de segunda ordem é **reportado, nunca escondido**: se o passo 2 mexer em `confianca`, as
duas colunas vão para a tabela.

---

## D-059 — A confiança do diagnóstico sai da evidência DO DIAGNÓSTICO — e mesmo assim perde do trivial

**Data:** 27/08/2026 · **Sessão 07, Bloco 1a** · alvo fixado em D-058 · **REPROVADA, fica atrás de flag**

**O defeito, que D-057 já tinha nomeado:** `diagnostico.confianca` era `min()` sobre
`perfil.afirmacoes`, e essa property inclui TODAS as `dores_observadas`. Com 7 dores na Axenya e 6
na Maritaca, sempre existe um elo fraco: `alta` era **estruturalmente inalcançável** e o campo saía
`baixa` para as oito fixtures. Não era impreciso, era **constante**. E a consequência ia na direção
errada: um Extractor que achasse MAIS dores reais BAIXAVA a confiança do diagnóstico — a métrica de
um agente se movendo contra a melhoria de outro.

**A correção:** aplicar `avaliar()` — a função que já existe, com as mesmas 5 regras de
`contexto/02` §6 — sobre uma `Afirmacao` sintética montada com `diagnostico.evidencias`, que são os
trechos que o Classifier anexou porque sustentam o rótulo.

O argumento é da rubrica e não do gabarito: a **regra 2** fala de corroboração entre TIPOS de
documento *da conclusão*; a **regra 5** fala do *output* carregar a confiança. As duas falam da
evidência da conclusão, nunca de sinais de dor não relacionados. O `min()` sobre o perfil inteiro
era uma terceira coisa, herdada do stub da sessão 01, que ninguém decidiu.

**O resultado, contra o alvo de D-058 (>= 4 acertos absolutos e taxa >= 50%):**

| | trivial | produção | **com a correção** |
|---|---|---|---|
| confianca | **3/8 (37,5%)** | 0/6 | **2/6 (33%)** |

**O defeito estrutural sumiu** — `alta` volta a ser alcançável, Axenya e RD Station passam a
acertar, e o campo deixa de ser constante. **E mesmo assim perde de responder "alta" para todo
mundo.** Pela regra 2 de D-058, não entra em produção: fica em
`CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO = False`, ligável por `--confianca-diagnostico`, medida e
com o número no comentário. É o destino de `USAR_JUIZ_LLM` em D-056, e D-058 citou esse precedente
por nome antes de a medição existir.

**O achado vale mais que o número: o gargalo mudou de lugar, e não é mais o validator.**

| fixture | evidência anexada ao diagnóstico | confiança | gabarito |
|---|---|---|---|
| Doutor-AI | **1 trecho**, de um `release` **sem data** | baixa | alta |
| SunnyHUB | **nenhum** — nenhum sinal disparou | baixa | media |
| Deal | 1 trecho, `site`, sem data | baixa | media |
| Maritaca | 3 trechos, `blog` + `site`, nenhum recente | media | alta |

O validator está relatando **fielmente** a espessura da evidência que o Classifier produziu. Quatro
dos seis erros são casos em que o diagnóstico se apoia em um documento só, ou em nenhum. Melhorar a
confiança daqui para frente não é mexer no validator — é fazer o Classifier anexar evidência mais
larga, e isso é trabalho do Extractor, que recorta **uma frase por documento**.

**Alternativas descartadas, e os motivos:**

- **`min()` sobre um subconjunto nomeado** (só os sinais dos dois eixos, sem dores). Continua sendo
  `min()` sobre um conjunto de tamanho variável, então preserva a monotonicidade perversa em escala
  menor; e duplicaria "o que sustenta o diagnóstico" em dois lugares quando o Classifier já
  materializa isso em `diagnostico.evidencias`. Duas fontes da mesma verdade divergem.
- **Média ponderada das confianças.** Inventa uma escala numérica que a rubrica não tem, esconde o
  caso "uma afirmação forte e cinco fracas" e deixa de ser explicável em uma frase — `avaliar()`
  devolve um motivo citável, uma média não devolve nada.
- **Tirar `dores_observadas` da property `afirmacoes`.** Parece a correção óbvia e quebraria o
  sistema **em silêncio**: `afirmacoes` é o que o validator varre para ANOTAR cada dor, e
  `recommendation.py` filtra por `d.validada`. Sem a anotação, o filtro da regra 3 do Recommendation
  para de funcionar sem derrubar nenhum teste. A property tem dois consumidores com necessidades
  diferentes; a correção é separar os consumidores, não mutilar a property.

**Fica em produção, porque não é métrica:** `Diagnostico.motivo_confianca` e a linha que o briefing
imprime. A regra 5 é *"o output carrega a confiança, não só o rótulo"*, e imprimir
`(confiança baixa)` sem dizer qual regra a produziu deixava o rodapé — *"toda conclusão acima aponta
para o documento que a sustenta"* — mentindo na linha mais lida do relatório. Com a flag desligada o
campo fica `None` e nada é impresso, que é o comportamento honesto: `min()` não produz motivo.

---

## D-060 — A rubrica em degraus empata com um caractere, e o teto que faltava explica por quê

**Data:** 27/08/2026 · **Sessão 07, Bloco 1b** · alvo fixado em D-058 · **REPROVADA, fica atrás de flag**

**O defeito:** o eixo 1 era `pontos = 2·autopilot + 2·dado_proprietário + 1·técnica`, com `>= 4`
para `AI-native`. Os pesos 2/2/1 não vinham da rubrica — `contexto/02` §4 lista os sinais como um
conjunto, sem hierarquia —, e o limiar exigia na prática autopilot **E** dado proprietário, porque
profundidade técnica sozinha valia 1. Por isso a Maritaca (quantização QAT, MoE, prefill/decode,
MFU em B200) saía `AI-enabled`. E os 4 erros da régua apontavam **todos para o mesmo lado**:
Axenya, Doutor-AI, Laura Networks e Maritaca são `AI-native` no gabarito e saíam `AI-enabled`.

**O que foi implementado e medido — três degraus declarados, sem aritmética:**

```
1. nenhum sinal de IA no caminho crítico                    -> non-AI
2. a empresa OPERA a própria IA — basta UM dos dois:
   a. profundidade técnica própria (>= 3 marcadores
      distintos de PROFUNDOS, nos DOCUMENTOS INTEIROS)
   b. autopilot + dado proprietário                         -> AI-native
3. resto                                                    -> AI-enabled
```

`2b` é exatamente o que a aritmética já deixava passar (2+2=4), então a mudança é aditiva do lado
`AI-native` e o raio de regressão fica limitado às três fixtures que o casador acertava. O `>= 3` de
`2a` não é parâmetro novo: é o número que o eixo 2 já declara para `maturidade alta`. Zero grau de
liberdade introduzido, e portanto nada para calibrar contra o gabarito.

**O resultado, contra o alvo de D-058 (>= 5/7, sem perder Deal, RD Station e SunnyHUB):**

| | trivial | **controle: `pontos >= 3`** | produção | **rubrica em degraus** |
|---|---|---|---|---|
| classe | 4/7 | **4/7** | 3/7 | **4/7** |

Recupera a Maritaca, não perde nenhuma das três. E **empata com o classificador trivial E com a
linha de controle** — que é a mesma aritmética com um caractere trocado. Não compra nada que `>= 3`
não compre de graça. Pela regra 2 de D-058, não entra: `RUBRICA_EM_DEGRAUS = False`, ligável por
`--rubrica`.

### O erro desta sessão não foi a rubrica, foi a barra ter sido fixada sem o teto

O harness tinha `teto_do_casador` para dores desde D-053 — *"nenhum julgamento por LLM pode superá-lo,
então ele é o teto"* — e **nenhum teto equivalente para `classe`**. D-058 escreveu `>= 5/7` sem ele.

O teto, calculado depois e agora medido pelo `--validar`:

```
teto do degrau 2a da rubrica: 1/4 das AI-native decididas
    - Axenya: 0 marcador(es) de profundidade — fora do alcance do degrau 2a, depende do 2b
    - Doutor-AI: 0 marcador(es)
    - Laura Networks: 0 marcador(es)
```

**Sete das oito fixtures têm profundidade ZERO** — só a Maritaca tem vocabulário de infraestrutura
nos documentos. O degrau `2a` **nunca poderia mover mais de uma fixture**, e as outras três
`AI-native` dependem do `2b`, que é idêntico à aritmética antiga. Logo o máximo alcançável era
3/7 + 1 = **4/7 — exatamente o placar do trivial.** O alvo de 5/7 era **inalcançável por
construção, e isso era calculável antes de medir**.

Isso não invalida a medição: a rubrica de fato empata, e a decisão de não promovê-la está certa. O
que fica registrado é o defeito de método — **D-055 ensinou a fixar a margem antes de medir, e esta
sessão aprendeu que fixar a margem sem calcular o teto é fixar um número, não um critério.**
`teto_do_degrau_2a` entrou no harness para que a próxima barra seja fixada sabendo o que é
alcançável.

**E o teto diz para onde ir:** o gargalo de `classe` não está na regra de decisão, está no
**vocabulário** — três das quatro fixtures `AI-native` não têm um único marcador de infraestrutura.
Ou os documentos coletados não contêm o sinal (e o trabalho é de curadoria, na M3), ou a lista
`PROFUNDOS` não cobre como uma healthtech descreve a própria stack (e o trabalho é de rubrica). As
duas hipóteses são testáveis com a base ampliada, e nenhuma se resolve mexendo no limiar.

**Duas coisas ficam em produção, porque nenhuma delas é métrica:**

1. **`profundidade_tecnica()` e `MARCADORES_PARA_PROFUNDIDADE`**, usados pelos dois eixos. O número
   passou a existir uma vez só: mexer nele para consertar a classe mexeria na maturidade no mesmo
   movimento, o que torna a calibração contra o gabarito visível em vez de silenciosa.
2. **`extractor._frases` virou `extractor.frases`**, pública. O Classifier precisa do MESMO recorte
   para que a evidência do eixo 1 seja literal pela mesma regra — duas regexes criariam duas
   definições de "trecho literal", e `--validar` só consegue verificar enquanto houver uma.

**`maturidade_stack` não foi tocada e ficou em 6/7 em todos os braços**, que era a guarda: se ela
tivesse se mexido, o contador do eixo 1 teria vazado para o eixo 2. As outras guardas de D-058
também seguraram em todos os braços — dor 49%, recall 100%, discriminação 8/8, elegível 5/7.

### Alternativa descartada: LLM neste nó

O motivo é medido, não estético. D-056 mostrou o `llama-3.1-8b` **recitando a rubrica** quando ela é
enumerada no prompt — 22% de precisão, com a regra nº 2 do próprio prompt devolvida como
justificativa. A rubrica de classe tem mais categorias e mais modos de falha que o julgamento de
dor, então é o pior caso conhecido para este modelo. E a variação entre execuções (50–62% em três
runs) é veneno numa demo ao vivo: o vídeo vale 20 pontos e é eliminatório.

### Nota de método: uma medição desta sessão foi contaminada por bytecode obsoleto

A primeira leitura do passo 1 deu `classe` 4/7 quando **só o Evidence Validator** tinha mudado — e
ele roda DEPOIS do Classifier, então era estruturalmente impossível. Causa: a medição da linha de
controle trocou `>= 4` por `>= 3`, que **preserva o tamanho do arquivo**, e o `git checkout` devolveu
um mtime que o `.pyc` já tinha registrado — o Python serviu o bytecode do limiar-3 com o fonte
dizendo 4. Só foi pego porque o número se mexeu onde não podia.

**Toda medição desta sessão passou a ser precedida de limpeza do `__pycache__`.** Vale para qualquer
harness que rode a partir do fonte: uma edição que preserva o tamanho do arquivo pode ser invisível
para o Python, e a régua mede a versão anterior sem avisar.

---

## D-061 — A régua de exclusão entra, a correção NÃO — e a régua achou um falso negativo já em produção

**Data:** 27/08/2026 · **Sessão 07, Bloco 2** · `data/avaliacao/exclusoes.yaml` + `--exclusoes`

D-052, achado 3, adiou a correção do filtro do Inception por **assimetria de risco**: um padrão de
identidade introduz falso negativo silencioso, e falso positivo aparece no briefing enquanto falso
negativo não aparece em lugar nenhum. A decisão estava certa e era **argumentada, não medida** — a
base tinha UMA fixture (Deal) exercitando o lado positivo, o que é anedota.

**O entregável desta sessão é a régua, não a correção.** 14 casos em pares mínimos: mesmo termo,
sujeito diferente. 6 vêm de documento real das fixtures, 8 são sintéticos e estão **declarados como
tais** — cobrir `revenda`, que nenhuma fixture exercita, exige frase escrita para o teste, e passar
sintético por real seria a desonestidade que D-021 barrou no seed.

**Os dois números nunca são somados.** Um filtro que exclui tudo tem zero falso negativo; um que não
exclui nada tem zero falso positivo. Uma acurácia única premiaria os dois e esconderia a assimetria
que motivou o arquivo. É a mesma razão pela qual a linha trivial existe em `avaliar_agentes.py`.

### O que a régua achou na PRIMEIRA execução, e ninguém sabia

```
excluídas corretamente         6/7   <- falso NEGATIVO: o risco silencioso
passaram corretamente          3/7   <- falso positivo: aparece no briefing
  x FALSO NEGATIVO · revenda    passou: 'Somos revendedores autorizados de licenças de software...'
```

**`"Somos revendedores autorizados"` passa pelo filtro do Inception.** `"revenda"` não é prefixo de
`"revendedores"` — o 7º caractere é `a` contra `e` —, então nunca casou, com âncora ou sem.

E o comentário de `briefing.py` afirmava o contrário: *"`revenda` continua casando em `revenda(s)` /
`revende(dor)`"*. O plural casa; a família `revende-` **nunca** casou. É a mesma classe do achado 1
de D-057 — o comentário descrevendo comportamento que o código não tem — e **sobreviveu à auditoria
que D-057 fez de D-048**, porque não havia régua que exercitasse `revenda`. É a terceira vez neste
projeto que ampliar o instrumento derruba uma afirmação escrita (D-039, D-052, agora esta).

### A correção de corpus foi medida e NÃO entra, apesar de fazer 7/7

O desenho recomendado no plano era trocar o CORPUS, não o padrão: o defeito não é o termo, é onde
ele é procurado — `elegibilidade()` varre TODAS as evidências do perfil, inclusive trechos sobre
parceiros e clientes.

| corpus | fixtures (`elegivel`) | régua: excluídas | régua: passaram |
|---|---|---|---|
| produção — todas as afirmações | 5/7 | 6/7 | 3/7 |
| A — `proposta_valor` + `descricao_curta` | 6/7 | 6/7 | 3/7 |
| **B — só `descricao_curta`** | **7/7** | **6/7** | **3/7** |

O corpus A **não conserta a Axenya**: *"Integramos consultoria, dados e operação clínica"* está nos
primeiros 400 caracteres do site, que é exatamente o que `proposta_valor` recorta.

O corpus B conserta as duas e faz 7/7 nas fixtures. **E mesmo assim não entra**, por um motivo que a
segunda coluna torna visível: ele deixa a regra de casamento em **6/7 · 3/7, idêntica à produção**.
Ele não resolve discriminação de sujeito — **ele evita as frases onde o problema acontece.** O 7/7
é comprado lendo um campo de UMA LINHA, curado à mão, em vez dos documentos:

- `descricao_curta` é `str | None` em `StartupRef` — opcional por tipo. Empresa sem o campo nunca
  seria excluída, por nada.
- Ele **não é texto coletado**, é redação de curadoria. E a M3 vai somar 22 empresas cuja
  `descricao_curta` eu mesmo escrevo: a correção do Diferencial passaria a ser propriedade da minha
  curadoria, não do sistema, e a régua estaria medindo a curadoria.

**É exatamente a troca que D-057 puniu**: falso positivo visível trocado por falso negativo
silencioso. Que 7/7 nas fixtures não baste é o ponto — foi para isso que a segunda régua existe.

**Nota sobre o critério, e é um defeito de método:** o critério fixado no plano dizia *"zero falso
negativo NOVO"* e, entre parênteses, *"nenhum caso do lado `exclui` pode passar"*. As duas leituras
divergem, porque foi escrito sem saber que **já existia** um falso negativo em produção. Resolvido
pela leitura conservadora, que é a que a assimetria de D-052 exige. A lição é a mesma de D-060: um
critério fixado antes de conhecer o estado da linha de base pode ser ambíguo justamente onde importa.

### O que fica medido para a próxima sessão decidir

Trocar `"revenda"` pelo prefixo `"revend"` leva o falso negativo de **6/7 para 7/7** e o falso
positivo de **3/7 para 2/7** — conserta o vazamento silencioso e cria um falso positivo visível em
*"Nossos clientes revendem os relatórios"*. Pela lógica de D-057, essa é a direção **boa** da troca.
Não entrou hoje porque é mudança de comportamento fora do critério fixado, e mudança de
comportamento não medida contra o critério é o que esta sessão inteira existe para não fazer.

**Descartada:** adicionar startups reais inelegíveis como fixtures. Custa ~12 min por empresa e uma
empresa real traz muitas variáveis ao mesmo tempo — não isola o filtro. Fica como complemento
gratuito da M3: 3-4 das 22 novas empresas escolhidas de propósito para serem inelegíveis.

---

## D-062 — A M3 fecha em 30 empresas, em duas camadas, e a coleta é sessão própria

**Data:** 27/08/2026 · **Sessão 07, Bloco 3** · M3 vence em 02/09

**A decisão é 30** — o piso do TAPI e do `plano.md`. Hoje são 8.

**O argumento, e ele começa admitindo o que joga contra:** o barema **não tem linha para tamanho de
base**. Os critérios 1, 2 e 3 medem os agentes, o RAG e o motor de recomendação; nenhum deles
pontua por número de empresas. Pela lógica de "a sessão marginal rende onde há pontos", 22 empresas
a mais compram zero.

O que decide contra esse raciocínio é que **`30 a 50` está escrito no requisito**, e o barema pontua
"nível 2 = cumpre o mínimo". Ficar visivelmente abaixo de um número escrito no TAPI é perda de ponto
**não recuperável** em dois critérios (1 e 7), e não é recuperável por qualidade: nenhuma explicação
no README transforma 8 em "cumpriu a M3". Já as ~2h que separam 20 de 30 **cabem no calendário** —
custo medido na sessão 06: ~12 min por empresa com 3 documentos, logo 22 empresas ≈ 4,4h.

**A estrutura é em duas camadas, e é ela que faz a hora pagar duas vezes:**

- **8 com bloco `gabarito:`** — as atuais. São a régua dos critérios 1 e 3, e **só elas movem
  número**. Nenhuma empresa nova recebe gabarito: gabarito é curadoria cara e o valor marginal da
  nona fixture rotulada é menor que o da primeira.
- **22 como dado**, sem `gabarito:`. Dão volume ao Retriever, cobrem a diversidade que a M3 exige
  (AI-native / AI-enabled / non-AI) e cumprem o requisito.
- **3-4 das 22 escolhidas adversarialmente** — uma consultoria de IA real, uma revenda, uma non-AI.
  Viram caso real da régua de D-061, que hoje cobre `revenda` só com frase sintética. É a única
  parte da coleta que compra ponto de critério, e ela sai de graça.

**A coleta acontece em sessão PRÓPRIA, depois desta.** A régua de exclusão de D-061 usa pares
mínimos e não depende de coleta, então nada nesta sessão fica bloqueado. Somar 3-4h de curadoria a
uma sessão que já tem dois blocos de agente mais o code review faria dela ~8h — e é exatamente
assim que as sessões 05 e 06 estouraram o orçamento.

**Timebox de 3h, com piso declarado em 20.** Se estourar, para onde estiver e o número entra no
README com o argumento. É a regra 5 do `plano.md` aplicada como está escrita: *"corte o número de
empresas, não o rigor"*.

**Alternativas descartadas:** **25** (o número que o próprio `plano.md` ilustra) e **20** — as duas
economizam 1 a 2h e as duas exigem justificar no README por que o requisito não foi cumprido. O
argumento que as venceu é que o texto de justificativa carrega mais risco que as 2h que ele
economiza, num critério (7) que vale 10 pontos e é lido por quem também leu o TAPI.

---

## D-063 — `dores_enderecadas` deixa de ser tautológico: duas perguntas, duas listas

**Data:** 27/08/2026 · **Sessão 07** · paga a dívida deixada visível em D-020

`recommendation.node` filtrava dores com `any(c.tecnologia == citacao.tecnologia for c in citacoes)`.
Como `citacao` **pertence** a `citacoes`, a condição é sempre verdadeira. Efeito: `dores_enderecadas`
listava **todas** as dores validadas em toda recomendação — as 7 da Axenya apareciam idênticas sob
cada tecnologia recomendada, impressas no briefing, sugerindo que cada tecnologia endereça tudo.

**Por que a correção de uma linha não servia**, e isso já estava escrito no módulo desde 24/08:
`evidencias` derivava da MESMA lista `dores`. Trocar a condição por `d.dor == citacao.dor_origem`
estreitaria as duas juntas, e recomendação cuja dor de origem não passou pelo Evidence Validator
cairia no `if not evidencias: continue` e **sumiria** — mudando quantas recomendações o sistema
emite, que é comportamento medido por `test_toda_recomendacao_tem_evidencia`.

**O que entrou é a separação que o próprio comentário apontava como a reescrita:**

```python
validadas   = [d for d in perfil.dores_observadas if d.validada]
evidencias  = [e for d in validadas for e in d.evidencias][:3]      # lastro: continua largo
dores       = [d for d in validadas if d.dor == citacao.dor_origem]  # declaração: só a dor de origem
```

"De quais dores tiro EVIDÊNCIA" e "quais dores DECLARO endereçadas" são perguntas diferentes e
agora são listas diferentes. O lastro continua vindo de todas as dores validadas — nenhuma
recomendação some, o teste continua valendo — e a declaração passa a ser só a dor que puxou aquela
citação, que é o que `CitacaoRAG.dor_origem` sabe desde D-043.

**Detalhe que teria virado bug de apresentação:** `proxima_acao` interpola essa lista numa frase que
termina em `": {dores}."`. Com `dor_origem = None` — o caminho da interface, onde quem pergunta é um
humano e não uma dor — a lista fica vazia e a frase terminaria em `": ."` no briefing. A ação ganhou
um fecho alternativo para esse caso.

---

## D-064 — TERCEIRO EOL, em 27/08: o LLM e o reranker morreram. Decisão EM ABERTO

**Data:** 27/08/2026 · **Sessão 07** · descoberto pelo `pytest`, confirmado pelo smoke e por sondagem
direta · **13 dias da entrega, 11 do vídeo**

O risco nº 1 da tabela do `plano.md` disparou pela **terceira vez em três meses** — e desta vez
**dois dias** depois da anterior:

| data | o que morreu |
|---|---|
| 18/05/2026 | `llama-3.2-nv-embedqa-1b-v2` e `llama-3.2-nv-rerankqa-1b-v2` (D-013) |
| 25/08/2026 | `llama-nemotron-embed-1b-v2` e `llama-nemotron-rerank-1b-v2` (D-046) |
| **27/08/2026** | **`meta/llama-3.1-8b-instruct` e `nvidia/rerank-qa-mistral-4b`** |

**O que foi medido, não suposto:**

| capacidade | modelo | resultado |
|---|---|---|
| chat completion | `meta/llama-3.1-8b-instruct` (D-012) | **HTTP 410 Gone** |
| embedding | `nvidia/llama-nemotron-embed-vl-1b-v2` (D-046) | **PASSOU** — 1024 dims, PT 0,3456 vs 0,0069 |
| reranking | `nvidia/rerank-qa-mistral-4b` (D-046) | **HTTP 404** |

O 410 é **do modelo, não do endpoint**: `GET /v1/models` responde **200 com 84 modelos**, e nenhum
casa `llama-3.1-8b`. Seis combinações de path × modelo de reranking foram sondadas — todas 404,
menos `llama-3_2-nemoretriever-500m-rerank-v2`, que devolve **410 Gone**, a semântica de
aposentadoria.

**A notícia boa, e ela é grande:** o **embedder sobreviveu**. Era o único cuja morte invalidaria os
**381 vetores** de `chunks_nvidia` e exigiria `reembedar.py` mais re-medir a régua inteira. O corpus
está intacto.

### O tamanho honesto do estrago, critério a critério

- **Critério 2 (RAG, 20 pts, hoje em nível 4):** o motor de produção é `rerank sobre híbrida`. Sem
  reranker ele não roda. **A linha de base sobrevive**: o denso puro faz **95% de r@1 e 100% de
  r@3** sozinho (D-046) — o que o reranking comprava era o critério estrito, **e@3 de 79% → 95%**.
  O sistema continua respondendo; perde a camada que o levava ao teto.
- **Critério 1 e 3 (agentes, 40 pts):** **quase intactos.** Os 8 agentes são determinísticos e
  `USAR_JUIZ_LLM = False` desde D-056. `pytest` deu **48 passed, 1 failed**, e a única falha é
  `nvidia_rag` recebendo 404 no rerank. Nada do trabalho desta sessão depende de LLM.
- **Passo 8 (geração com abstenção):** `src/rag/geracao.py` é o único arquivo que chama LLM. Sem
  modelo, a abstenção não roda.
- **O que perde valor de prova:** toda medição de geração — abstenção **20–22/24** (D-040),
  `json_schema` **4/5 × 0/5 × 0/5** (D-047), o juiz do Extractor **50–62%** (D-056). Foram
  produzidas por um modelo que não existe mais. **Trocar o LLM não as conserta: invalida.**

### As opções, com o custo de cada uma. A decisão é do Vinícius

**Para o LLM** — o catálogo vivo oferece substitutos diretos:
`nvidia/mistral-nemo-minitron-8b-8k-instruct` (8b, o mais próximo do que morreu),
`nv-mistralai/mistral-nemo-12b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`.
Trocar é **uma env var** (`LLM_MODEL`) — o `src/llm.py` isola. O custo não é o código, é a
**re-medição**: as três medições acima precisam ser refeitas com n=3 para continuarem citáveis, ou
declaradas como históricas com a data e o modelo, do jeito que D-046 fez com as sessões 02/03.

**Para o reranking** — não há substituto visível no catálogo, e é aqui que mora o risco real:
1. **Rodar sem reranker** (`peso_lexical` e fusão continuam; o passo 7 vira no-op). O RAG entrega
   95% r@1. Custo: o critério 2 perde a decisão técnica que o levava a nível 4, e o TAPI cita
   reranking explicitamente.
2. **Cross-encoder local** (`sentence-transformers`, ex. `BAAI/bge-reranker-v2-m3`). Mantém o passo
   7 real e demonstrável no vídeo. Custo: sai da stack NVIDIA, que é o **Diferencial declarado**.
3. **Cohere Rerank** — é o que o TAPI recomenda, e o Diferencial do projeto era justamente não usar.
   Pago.

**A decisão não é minha e não vai ser tomada por inércia.** A opção 2 salva o critério 2 e fere o
Diferencial; a 1 preserva o Diferencial e rebaixa o critério 2. As duas são defensáveis, e a
diferença entre elas é de **peso 20 contra peso 5** — o que sugere a 2, com o Diferencial reescrito
para "o RAG roda na stack NVIDIA no que ela ainda oferece: o embedding". Fica registrado como
recomendação, não como feito.

**O que este episódio já provou, e vale para a defesa na banca:** a arquitetura aguentou. Provedor
isolado em `src/config.py`, nenhum agente conhecendo a NVIDIA, e um smoke test que nomeia a
capacidade morta em 30 segundos. Três EOLs em três meses e o custo de cada um foi **medido em
horas, não em dias** — e nesta terceira o corpus nem precisou ser tocado.

---

## D-065 — "Cohere é pago" era falso, e as duas alternativas ao fornecedor único caíram por narrativa

**Data:** 27/08/2026 · **Sessão 07** · corrige D-015 · levantado por questionamento do Vinícius

D-015 descartou o Cohere Rerank em 22/08 com duas razões: *"é pago"* e *"quebraria a narrativa de
rodar tudo na stack NVIDIA"*. **A primeira é falsa**, e era verificável naquele dia:

| | trial (grátis) | production (pago) |
|---|---|---|
| volume | **1.000 chamadas/mês**, todos os endpoints | pay-as-you-go |
| Rerank | **10 req/min** | 1.000 req/min |
| cobertura | Command + Embed + **Rerank 3.5** | idem |
| restrição | **vedada a uso comercial/produção** | livre |

Processo seletivo não é uso comercial, então a trial key sempre foi legítima aqui.

**O que isso revela é maior que o erro de fato.** Na mesma decisão, o cross-encoder local foi
descartado por *"perde o argumento do Diferencial"* — motivo explicitamente narrativo, e D-046 já
tinha marcado essa linha como *"a única do log onde uma história venceu uma propriedade técnica"*.

Com esta correção, a leitura certa é mais dura: **as DUAS alternativas ao fornecedor único foram
descartadas por narrativa** — e uma delas com um fato falso por cima. Não foi uma linha ruim no
log, foi um padrão. E o resultado está medido: em 25/08 o projeto ficou sem contingência, e em
27/08 ficou sem reranker nenhum.

**Erro de método, nomeado:** D-015 tratou "é pago" como fato assumido e não o verificou, enquanto o
mesmo dia media margem de reranker com quatro casas decimais. **O rigor foi aplicado à escolha
técnica e não à premissa que eliminou as alternativas** — e é a premissa que decide o espaço de
opções.

### Os limites da trial batem em coisas concretas, e isso não é objeção — é planejamento

- **1.000 chamadas/mês.** Uma avaliação completa do RAG gasta ~67 chamadas de rerank; um
  `python -m src.graph` gasta ~20. Trabalhável por 13 dias, mas a disciplina de n=3 do projeto come
  ~200 numa tacada.
- **10 req/min no Rerank.** Um run do grafo faz ~20 chamadas sequenciais: **~2 minutos de throttle**.
  Num vídeo com teto de 7 minutos e demo ao vivo, é material. **A verificar antes de o roteiro
  depender disso.**
- **O avaliador precisa de chave própria.** Melhor que a NVIDIA hoje — chave grátis sai na hora,
  modelo aposentado não volta com chave nenhuma —, mas ainda é dependência externa entre o
  repositório e alguém conseguir executá-lo, e o eliminatório nº 3 é sobre executar.

### O que fica em aberto, de propósito

A decisão do passo 7 **não é tomada aqui**. O que esta decisão faz é devolver o Cohere ao conjunto
de opções, de onde ele nunca deveria ter saído, e corrigir os três lugares que afirmavam o
contrário: D-015, a linha do Diferencial no `CLAUDE.md` e a frase de D-046.

**A hipótese que a próxima sessão deve avaliar, e que é filha do método deste projeto:** não
escolher um só. Cross-encoder local como default — o repositório roda sempre, sem chave, sem quota,
sem EOL — e Cohere atrás de env var como o braço que o TAPI recomenda, com **as duas linhas na
tabela de ablação** ao lado de "sem rerank". É `--truncar-pool` aplicado ao fornecedor, e responde
"por que não Cohere?" com número em vez de narrativa — que é exatamente o que faltou em 22/08.

---

## D-066 — O code review derrubou uma correção desta sessão e mostrou dois campos que eram código morto

**Data:** 27/08/2026 · **Sessão 07, `/code-review`** · 15 achados · **11 pagos, 4 registrados**

Como em D-057, os que importam não são polimento — são afirmações desta sessão que estavam erradas.

### 1. D-063 quebrou a rastreabilidade que existe para proteger (achado nº 1)

A correção de `dores_enderecadas` estreitou a **declaração** para a dor de origem e deixou o
**lastro** saindo de TODAS as dores validadas. Resultado reproduzido:

```
dores_enderecadas : ['observabilidade']
evidências citadas: ['nosso CUSTO de nuvem dobrou', ...]
```

Uma recomendação que **declara uma dor e cita a evidência de outra**, impressa sob o rodapé *"toda
conclusão acima aponta para o documento que a sustenta"*. Antes de D-063 as duas listas concordavam
por construção; **a correção tornou a divergência possível e nada a impedia.**

Corrigido com `lastro = dores or validadas`: o lastro segue a declaração quando ela existe, e volta
ao conjunto validado quando a citação não veio de uma dor — o que preserva o que D-063 comprou
(nenhuma recomendação some). Dor validada sempre tem evidência, porque `avaliar()` devolve
`validada=False` quando não há; logo `dores` não-vazia implica lastro não-vazio.

**A lição:** D-063 foi a única mudança de comportamento desta sessão que entrou **sem flag, sem
teste e sem braço de harness** — enquanto a mesma sessão exigia critério fixado antes do código para
tudo o mais. O único caminho que exercita `recommendation.node` é `--motor ponta-a-ponta`, que custa
API e hoje nem roda. **Quatro testes novos** (achado nº 9) fecham isso com zero chamada.

### 2. `motivo_confianca` era código morto na configuração que roda (achado nº 5)

D-059 afirmou que o campo *"fica em produção, porque não é métrica"*. **Ele só era preenchido dentro
do braço da flag**, que é `False` por default — o campo novo em `state.py` e a linha nova do briefing
nunca executavam. A afirmação era falsa no momento em que foi escrita.

Corrigido: o braço de produção também preenche o motivo, dizendo o que o `min()` faz e sobre
quantas afirmações — o que torna o defeito de D-059 **visível na saída** em vez de só documentado.

### 3. O raio de regressão do Classifier estava mal declarado (achado nº 2)

O docstring afirmava que *"o degrau 1 mantém a semântica de `pontos == 0`"*. **Não mantém:** o
degrau 1 inclui `n_profundos >= 1` enquanto o `2a` exige `>= 3`. Uma startup com 1 ou 2 marcadores
de infraestrutura e nenhum outro sinal era `non-AI` e passa a `AI-enabled` — saindo de
`fora-do-funil` e fazendo o `nvidia_rag` gastar API por dor. **Nenhuma das 8 fixtures cai nesse
caso, e é por o placar NÃO medir isso que precisava estar escrito.**

### 4. A régua de exclusão media pela metade o lado que criou para medir (achado nº 6)

`exclui: true` checava só `rotulo in rotulos` — nunca que **nenhum rótulo errado** também disparou.
É exatamente o defeito que D-048 pagou (startup recusada por "cripto" ao falar em custo por token),
sobrevivendo dentro da régua escrita para pegá-lo. Agora exige `rotulos == {rotulo}`. E
`validar_exclusoes()` passou a checar rótulo inexistente, campo faltando e **par mínimo incompleto**
— sem isso um typo em `rotulo:` viraria um falso negativo fantasma permanente (achado nº 7).

**Correção de honestidade junto:** o cabeçalho contava 6 casos "de documento real" incluindo um
derivado de `tests/test_grafo.py`. Agora são três categorias: **5 de fixture, 1 derivado de teste,
8 sintéticos.**

### 5. Instrução contaminada, de novo, e no arquivo carregado em toda sessão (achados nº 8, 14, 15)

A tabela de Stack do `CLAUDE.md` ainda apresentava `rerank-qa-mistral-4b` como *"(o único vivo)"* e
`meta/llama-3.1-8b-instruct` como o LLM vigente — vinte linhas acima do aviso *"nunca usar esses
seis nomes"*, adicionado pela mesma sessão. `src/config.py` e `.env.example` seguem com os dois
nomes mortos como default. E a linha nova da tabela de EOL tinha ficado **sem o `>` do blockquote**,
o que a jogaria para fora da caixa de aviso no GitHub — no arquivo em que o critério 7 é avaliado.

Tudo corrigido, com os defaults mantidos e **anotados**: trocá-los por um palpite não medido seria
pior que falhar alto, que é o que o smoke test já faz em 30 segundos.

### Registrados e NÃO pagos, com o motivo

- **A dedup do `nvidia_rag` faz `dores_enderecadas` sub-declarar** (nº 11). Uma página recuperada
  por duas dores guarda só o `dor_origem` da primeira, então uma citação que responde `custo` **e**
  `latencia` declara só `custo`. D-063 trocou uma **super**-declaração por uma **sub**-declaração, e
  isso não estava registrado. Fica registrado. Pagar exige `dor_origem` virar lista, o que muda o
  contrato de `CitacaoRAG`.
- **`profundidade_tecnica` contorna o juiz de D-053** (nº 4). Com `--juiz`, evidência que o juiz
  reprovou volta pela porta do eixo 1. Não pago porque a rubrica está **reprovada e desligada**;
  anotado no módulo para o caso de ela ser promovida.
- **`_perfil_de_um_trecho` duplica o helper de `tests/test_elegibilidade.py`** (nº 13). Real, e a
  hora de unificar é quando `elegibilidade()` mudar de corpus — que é justamente a decisão que
  D-061 deixou em aberto.

**Estado depois das correções:** `pytest` **52 passed, 1 failed** (53 testes; a falha é o 404 do
reranker, não o código). A régua de produção continua **idêntica à linha de base** — nenhuma
correção do review mexeu no placar, que é o que se espera de correção de rastreabilidade.

---

## D-067 — O LLM dos agentes é `nemotron-3-nano-30b-a3b`, escolhido por ELIMINAÇÃO medida

**Data:** 28/08/2026 · **Sessão 08, Bloco 0A** · substitui D-012 · **12 dias da entrega, 10 do vídeo**

D-064 recomendou `nvidia/mistral-nemo-minitron-8b-8k-instruct` **por nome**, com base em ele
aparecer em `GET /v1/models`. **Ele devolve HTTP 404.** A recomendação nunca foi testada — é o
mesmo erro de método que D-065 nomeou dois dias antes, agora cometido dentro da própria correção.

### Os 10 candidatos, sondados um a um com chamada real

| resultado | quantos | quais |
|---|---|---|
| **HTTP 404** | 7 | `mistral-nemo-minitron-8b-8k`, `mistral-nemo-12b`, `llama-3.1-nemotron-70b`, `mistral-7b-v0.3`, `granite-3.0-8b`, `gemma-3-12b-it`, `phi-3.5-moe` |
| **inutilizável** | 2 | `nemotron-3.5-lightning-30b-a3b` (HTTP 400, depois **timeout de 300 s**) · `mistral-nemotron` (200 em **35 s**, e **HTTP 500** no structured output) |
| **utilizável** | **1** | **`nvidia/nemotron-3-nano-30b-a3b`** — ~650 ms, absteve corretamente nos dois métodos |

**Todos os 10 estavam listados no catálogo.** A escolha não é preferência: é o único que sobrou.

**O que a troca custou:** uma variável (`LLM_MODEL`) em `.env`, `.env.example` e `src/config.py`.
Nenhum agente mudou, porque nenhum agente conhece o provedor. A costura de D-001 pagou pela
terceira vez.

**O que ela NÃO conserta, e é o ponto:** abstenção (D-040), `json_schema` (D-047) e o juiz (D-056)
foram produzidos pelo modelo morto. Trocar o modelo **invalida** esses números em vez de
consertá-los. O destino de cada um está em D-069.

**Alternativa descartada:** Grok, que a liga sugeriu e que portanto está pré-autorizado. Não foi
descartado por mérito — **não foi testado**, porque a chave ainda não existe. Fica registrado como
não medido, e não como pior, que é a distinção que D-065 cobrou.

---

## D-070 — O catálogo é vitrine, não inventário: estar em `/v1/models` não é estar vivo

**Data:** 28/08/2026 · **Sessão 08** · generaliza o achado de D-067 · `scripts/sondar_catalogo.py`

**9 dos 10 candidatos sondados estavam LISTADOS em `GET /v1/models` e 9 não serviam.** A listagem
respondeu 200 com 83 modelos e não é evidência de disponibilidade de nenhum deles.

Isso muda o procedimento, não só um fato:

1. **Nenhuma decisão de modelo pode citar a listagem como prova.** Só chamada real conta. D-064
   citou, e errou o substituto que recomendou.
2. **O catálogo encolhe entre execuções.** 84 modelos em 27/08, **83** em 28/08 — um dia. E dois
   modelos que responderam em 27/08 pararam de responder em 28/08. Não é um evento de EOL com data:
   é erosão contínua.
3. **`scripts/sondar_catalogo.py` fica versionado**, separado do smoke. Os dois respondem perguntas
   diferentes: o smoke pergunta *"a config vigente funciona?"* e precisa **falhar alto**; a
   sondagem pergunta *"o que existe para substituí-la?"*. O próprio docstring do smoke já dizia,
   sobre paths de rerank, que varrer candidatos *"mascararia uma regressão futura"* — o argumento
   vale para modelos, e é por isso que são dois arquivos e não um.

**Reconfirmado na mesma sondagem:** 9 combinações de path × modelo de reranking, **todas 404/410**,
e zero modelos com `rank` no nome entre os 83. Não há reranker no catálogo da NVIDIA — o que leva
a D-068.

**O valor disto para a banca não é a lista de modelos mortos, é a régua:** o projeto passou a medir
uma propriedade do FORNECEDOR — volatilidade de catálogo — com um instrumento versionado, em vez de
descobri-la por acidente a cada `pytest` quebrado. Três EOLs (18/05, 25/08, 27/08) e uma erosão
diária, com data e método.


## D-068 — O passo 7 passa a ser o Cohere Rerank, e o provedor vira configuração

**Data:** 28/08/2026 · **Sessão 08, Bloco 0B** · fecha o que D-064 e D-065 deixaram em aberto ·
substitui D-015

O reranking da NVIDIA morreu em 27/08 e **não há substituto**: reconfirmado em 28/08 com 9
sondagens de path × modelo (todas 404/410) e **zero modelos com `rank` no nome** entre os 83 do
catálogo. O passo 7 não tinha para onde ir dentro do fornecedor.

### Por que o Cohere, e por que isto é uma correção de método e não uma escolha nova

D-015 o descartou em 22/08 por *"é pago"* — **falso**, há trial key gratuita (D-065) — e por
*"quebraria a narrativa"*. **Nenhum argumento medido contra ele existiu em momento algum**, porque
ele nunca foi testado. E o TAPI o recomenda **nominalmente**, na seção 5.3, na mesma lista de
Qdrant/PostgreSQL/BM25. Voltar a ele é alinhamento com o enunciado, não desvio.

O requisito técnico que ele precisa satisfazer é específico deste projeto e elimina a maior parte
das alternativas de prateleira: **as perguntas são em português e o corpus da NVIDIA é em inglês**,
então todo par (consulta, passagem) do passo 7 é **crosslingual**. `rerank-v3.5` é multilíngue.
Foi essa mesma propriedade que sempre justificou o NeMo Retriever.

### A variável que faltava não era o modelo — era o fornecedor

`ConfigRerank` ganhou `provedor`, com três valores:

| valor | papel |
|---|---|
| `cohere` | **produção** |
| `nvidia` | preservado como registro do que rodou até 27/08; é como se testa, em 30 s, se voltou |
| `nenhum` | **degradação graciosa**: o passo 7 sai do caminho e a resposta vira a ordem da híbrida |

A costura de D-001 isolava o *modelo* atrás de env var. A terceira morte mostrou o limite disso:
**trocar o modelo só resolve se existir outro modelo.** Em 27/08 não existia.

**`nenhum` NÃO é uma linha nova na tabela de ablação, e a distinção importa.** A tabela já tem a
linha sem rerank: são os motores `denso` e `hibrido`. O provedor `nenhum` existe para o *runtime* —
quem clonar o repositório sem chave nenhuma roda, em vez de receber um stack trace. É a metade
executável do eliminatório nº 3, e ele **é uma conjunção**: *"projeto que não executa **e** cujo
vídeo não demonstra funcionamento real"*. Verificado no TAPI, e é o que permite não pagar 900 MB
de `torch` mais 1,1-2,3 GB de pesos por um fallback local.

Medido: com `--rerank-provedor nenhum`, o motor `rerank_hibrido` devolve **exatamente** os números
da híbrida (95% / 100% / 79% / 79%) e score 0,0000. O no-op é no-op de verdade.

### A escala do score mudou, e isso NÃO reabre o limiar

    NVIDIA  ->  `logit` cru, faixa medida de -11,00 a +11,94, quantizado em 1/16
    Cohere  ->  `relevance_score` normalizado em [0, 1]

D-035 mediu que **nenhum** corte sobre score separa quem tem resposta de quem não tem, e a
abstenção mora no passo 8 como campo estruturado (D-040). Aquele resultado era sobre a ORDEM não
separar as classes, não sobre a faixa numérica — trocar a escala não o afeta. O que a troca exige é
mais modesto: os scores de rerank anteriores a 28/08 são de outra unidade e **não se comparam
linha a linha** com os novos. r@k e e@k continuam comparáveis, porque medem posição.

### Alternativa descartada, e com o custo medido

**Cross-encoder local** (`bge-reranker-v2-m3` ou `jina-reranker-v2-base-multilingual`): implementado
como provedor? **Não.** Medido o preço antes de decidir: `torch` são **74 MB** no macOS arm64 mas
**900 MB** no Linux x86_64 da máquina de quem avalia, mais 27 pacotes novos, mais **1,1 a 2,3 GB**
de pesos. Ele trocaria uma dependência de rede em *runtime* por uma de ~3 GB na *instalação*.

Isso não o mata como ideia — ele é a única opção sem chave, sem quota e sem EOL, e continua sendo
a resposta certa se a trial do Cohere apertar. Mas ele entra **medido ou não entra**, que é
exatamente a régua que D-065 cobrou. Fica registrado como **não medido**, não como pior.

### O que continua sendo um risco, e não se resolve aqui

O Cohere é outro serviço hospedado. A diferença material é que é produto comercial com SLA, não
catálogo de preview — mas a lição das três mortes é que **componente hospedado é passivo do
entregável**, e trocar de hospedeiro não zera isso. O provedor `nenhum` é o que limita o estrago.

---

## D-071 — `revenda` vira o prefixo `revend`: um TRADE-OFF aceito, não uma melhora dos dois lados

**Data:** 28/08/2026 · **Sessão 08, Bloco 1** · fecha o que D-061 deixou explicitamente para decidir

| lado | antes | depois |
|---|---|---|
| falso **negativo** (excluídas corretamente) | 6/7 | **7/7** |
| falso **positivo** (passaram corretamente) | 3/7 | **2/7** |

**A troca piora um dos lados, e isso precisa estar escrito assim.** Ela fecha o vazamento
silencioso que a régua achou em 27/08 (*"Somos revendedores autorizados"* passava pelo filtro,
porque `revenda` não é prefixo de `revendedor`) e cria um falso positivo novo em *"Nossos clientes
revendem os relatórios gerados pela plataforma"*.

**O que autoriza a troca não é o placar — é a assimetria de D-057.** O falso positivo aparece no
briefing e alguém o corrige; o falso negativo não aparece em lugar nenhum: a startup inelegível
entra na recomendação e ninguém fica sabendo. É precisamente por isso que `--exclusoes` **nunca
soma os dois números** — uma "acurácia" única aqui teria mostrado 9/14 antes e 9/14 depois, e
concluído que nada mudou.

### O helper duplicado NÃO foi unificado, e o motivo é o gatilho

O achado nº 13 de D-066 registrou que `_perfil_de_um_trecho` (harness) duplica `_perfil` (testes),
e definiu o gatilho: *"a hora de unificar é quando `elegibilidade()` mudar de corpus"*. **O corpus
não mudou** — a correção de corpus foi medida e **reprovada** na sessão 07, e o que mudou aqui foi
um termo. O gatilho não disparou.

Somado a isso: os dois helpers têm assinaturas diferentes por razões legítimas de cada lado (o de
teste é variádico, o do harness recebe um trecho), e unificá-los criaria uma dependência de
`scripts/` para `tests/` que hoje não existe. Fica duplicado, com o gatilho intacto.


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
