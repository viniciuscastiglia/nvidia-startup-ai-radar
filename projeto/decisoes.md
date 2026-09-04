# Log de decisões de arquitetura

**Uma entrada por decisão, escrita no momento em que ela é tomada.**

**Para que serve:** para que a decisão continue **revisável**. Uma escolha sem a alternativa
descartada ao lado não é revisável — daqui a duas semanas, mudar de ideia custa refazer a análise
inteira, e a tendência vira manter a escolha por inércia. Este arquivo é também a camada de
referência do projeto: o `CLAUDE.md` não guarda número nenhum e aponta para cá; **60 docstrings em
`src/` e `scripts/` citam D-0NN**. Apagar uma entrada quebra ponteiro.

**Para quem se escreve:** para quem abrir o repositório sem ter estado na sessão — inclusive você
daqui a seis meses. Não para uma plateia que vai avaliar. A diferença tem consequência de forma:
**quem escreve para ser avaliado escreve a defesa inteira; quem escreve para o leitor futuro
escreve a decisão.** Ver D-078.

## Formato

```
## D-NNN — Título curto
**Data:** DD/MM/AAAA · revisado DD/MM (D-0XX)
**Decisão:** o que foi escolhido.
**Alternativas descartadas:** o que mais estava na mesa.
**Motivo:** por que esta e não as outras. Qual o trade-off aceito.
**Reversível?** fácil / caro / irreversível — e o que dispararia a revisão.
**Revisto:** o que uma medição posterior derrubou. Só quando existe.
```

O campo **Alternativas descartadas** é o mais importante: sem ele a decisão não tem como ser
revisitada sem refazer a análise do zero.

## A regra de manutenção (D-073, D-078)

**Este arquivo guarda a decisão, não o caderno de laboratório.** Um número só fica se ele é verdade
sobre o sistema que roda hoje; se o instrumento que o produziu morreu, fica a **conclusão** em uma
linha, e só quando ela sobrevive ao instrumento. O histórico completo está no git — que é o que
garante o append-only, não o tamanho do arquivo.

**Disciplina de tamanho (D-078).** Uma entrada normal cabe em ~15 linhas: decisão, alternativa,
motivo, reversibilidade. Passar muito disso é sinal de que se está narrando o percurso em vez de
registrar o resultado — e o percurso já está no git. O teste é direto: **corta tudo que o leitor
futuro não precisa para decidir se mantém ou reverte a escolha.**

---

## D-001 — Python 3.12 em vez do 3.14 do sistema
**Data:** 22/08/2026
**Decisão:** ambiente conda dedicado com Python 3.12.
**Alternativas descartadas:** usar o `python3` do sistema (Anaconda, 3.14.6).
**Motivo:** 3.14 é recente demais para o ecossistema. Bibliotecas com dependências compiladas
(drivers de Postgres, tokenizers, clientes de vector DB) frequentemente ainda não publicaram wheel
para 3.14, o que força build a partir do fonte e custa horas de depuração que não têm nada a ver
com o projeto.
**Reversível?** Fácil — é só recriar o ambiente.

---

## D-002 — Provedor de LLM, embedding e rerank atrás de variáveis de ambiente
**Data:** 22/08/2026
**Decisão:** `src/config.py` expõe `LLM`, `EMBEDDING` e `RERANK` lidos do `.env`. Nenhum agente
conhece o nome "NVIDIA" — todos recebem `base_url` + `modelo`.
**Alternativas descartadas:** instanciar o cliente da NVIDIA direto em cada agente.
**Motivo:** o risco nº 1 do `plano.md` é os créditos grátis do build.nvidia.com não sustentarem 8
agentes rodando dezenas de vezes por dia. A abstração custa ~100 linhas hoje; descobrir na véspera
que os créditos acabaram e ter que mexer em 8 agentes custa o projeto.
**Reversível?** Fácil, mas a assimetria importa: adicionar depois é caro, remover é trivial.
**Revisto:** a costura cobre o LLM e — desde D-068 — o **fornecedor** do rerank. Ela **não** cobre o
embedder: trocar o modelo muda o espaço vetorial e invalida o corpus indexado. Env var não é pin de
dependência (D-046).

---

## D-003 — `langchain-openai` como cliente, não `langchain-nvidia-ai-endpoints`
**Data:** 22/08/2026
**Decisão:** falar com a NVIDIA pelo cliente OpenAI, trocando só o `base_url`.
**Alternativas descartadas:** `langchain-nvidia-ai-endpoints`, o SDK oficial da integração.
**Motivo:** os endpoints NIM são OpenAI-compatible por design (`contexto/03` §1) — é literalmente o
argumento de venda do produto. Usar o cliente genérico (a) tira uma dependência, (b) faz o código de
D-002 funcionar com qualquer provedor sem `if`, e (c) demonstra no vídeo a própria tese do NIM:
"migrar não exige mudar código". Trade-off: perde-se açúcar sintático específico da NVIDIA.
**Reversível?** Fácil — é trocar a classe do cliente em um lugar só.
**Revisto:** o item (b) deixou de ser hipótese em 28/08 — foi o que permitiu trocar o passo 7 de
fornecedor sem tocar em nenhum agente (D-068).

---

## D-004 — conda para o ambiente + `requirements.txt` pinado
**Data:** 22/08/2026 · fecha a pendência **P-07**
**Decisão:** ambiente conda `case-nvidia` (Python 3.12.13) para desenvolver, `requirements.txt` com
versões exatas (`pip freeze`) para reprodução.
**Alternativas descartadas:** `uv` (mais rápido, lockfile melhor) · Poetry (gestão mais completa).
**Motivo:** ambos exigem que quem for avaliar instale um gerenciador a mais antes de rodar o projeto;
`requirements.txt` roda em qualquer Python. O critério aqui não é elegância de tooling — é atrito de
reprodução para o avaliador, que conta no critério 7. Trade-off aceito: `requirements.txt` não é
lockfile de verdade (não trava transitivas por hash).
**Reversível?** Fácil.

---

## D-005 — Smoke test como script versionado com asserções semânticas
**Data:** 22/08/2026
**Decisão:** `scripts/smoke_nvidia.py`, em HTTP cru, que além de checar HTTP 200 verifica: se a
dimensão Matryoshka pedida é a devolvida, se o embedding separa relevante de irrelevante **em
português**, se funciona **crosslingual** (consulta PT × passagem EN) e se o reranker coloca a
passagem certa no topo.
**Alternativas descartadas:** `curl` descartável no terminal · passar por `langchain-openai`.
**Motivo:** três razões. (1) Um teste que só checa 200 não prova nada útil — a pergunta real é se o
modelo funciona em português e entre idiomas, porque a base NVIDIA é em inglês e os documentos das
startups em português; se o crosslingual falhasse, a arquitetura do RAG mudaria. (2) HTTP cru torna
a falha inequívoca: é do endpoint, não da biblioteca. (3) Vira evidência reproduzível para o
avaliador.
**Reversível?** Irrelevante — é ferramenta de apoio, não arquitetura.
**Revisto:** foi este script que diagnosticou os três EOLs (D-013, D-046, D-064). O valor dele não
está no dia em que passa, está no dia em que falha.

---

## D-006 — Fan-in do grafo por `defer=True`, retry e isolamento de erro por nó
**Data:** 22/08/2026 · revisado 23/08 (D-024)
**Decisão:** usar recursos do LangGraph que uma chain de prompts não tem: `defer=True` no nó de
Briefing (só executa quando todas as análises paralelas terminaram) e `retry_policy` por nó.
**Alternativas descartadas:** arestas condicionais manuais contando quantas análises voltaram ·
try/except dentro de cada nó · nenhum cache.
**Motivo:** o TAPI justifica LangGraph por "estado, transições condicionais, checkpoints, retry e
intervenção humana". Se o projeto usa LangGraph só como executor linear, a escolha vira decorativa e
o critério 1 fica em nível 2. `defer` resolve o fan-in sem contador manual; `retry_policy` cobre
falha transitória de LLM.
**Reversível?** Fácil, um parâmetro por nó.
**Revisto:** esta entrada foi escrita como intenção e ficou lida como descrição do que existe. O
isolamento de erro real entrou só em **D-024**; `cache_policy` **nunca foi implementado**, e de
propósito — os nós de hoje são heurística em memória, não há o que cachear.

---

## D-007 — Topologia: subgrafo de análise + fan-out por `Send`
**Data:** 22/08/2026 · fecha a pendência **P-05**
**Decisão:** o grafo pai tem 4 nós (`query_planner` → `retriever` → `analisar_startup` →
`briefing`). O Retriever emite um `Send` por startup para um nó-wrapper que invoca um **subgrafo
compilado** com as 5 etapas de análise. O fan-in acontece no reducer `operator.add` de
`EstadoRadar.analises`, e o Briefing usa `defer=True`.
**Alternativas descartadas:**
(a) **Lote** — cada nó itera sobre todas as startups internamente. O prompt cresce com N e a
qualidade da extração cai; uma startup com dado ruim derruba as outras; o retry só existe no nível
do nó. Pior: é exatamente o que uma chain simples faria, o que tornaria a escolha do LangGraph
decorativa — nível 2 no critério 1.
(b) **Fan-out direto para o Extractor**, sem subgrafo. Mesmo ganho de paralelismo e retry, mas o
grafo vira 8 nós mais um leque de N branches: o diagrama fica poluído no README e no vídeo, e testar
uma etapa isolada dá mais trabalho.
**Motivo:** (c) é a única opção em que a escolha do LangGraph é *necessária* em vez de estética.
Além disso o subgrafo roda sozinho no pytest, e o diagrama do pai cabe num slide de 4 caixas — o que
importa porque o vídeo tem teto de 7 minutos. Trade-off aceito: uma camada de abstração a mais e
**dois** diagramas para explicar em vez de um.
**Reversível?** Média. Voltar para (b) é remover o wrapper e religar arestas; voltar para (a)
exigiria remover os reducers e reescrever os 5 nós de análise.

---

## D-008 — TypedDict para o estado do grafo, Pydantic para o que trafega dentro
**Data:** 22/08/2026
**Decisão:** `EstadoRadar` e `EstadoAnalise` são `TypedDict` com `Annotated[..., operator.add]` nos
campos que acumulam. Todos os payloads (`Afirmacao`, `PerfilStartup`, `Diagnostico`, `Recomendacao`,
`AnaliseStartup`) são modelos Pydantic.
**Alternativas descartadas:** estado inteiro como modelo Pydantic · estado inteiro como dict solto.
**Motivo:** os dois lados da fronteira têm exigências opostas. O estado precisa aceitar atualização
**parcial** — um nó devolve `{"perfil": x}` e o LangGraph funde; com Pydantic como estado, todo nó
teria que reconstruir o objeto inteiro. Já os payloads atravessam a fronteira do LLM, onde validar é
o ponto: `Literal` fechado faz o classificador devolver exatamente `AI-native | AI-enabled | non-AI`
ou levantar erro de validação que o `retry_policy` trata — em vez de "meio AI-native" passando
adiante. Dict solto perderia as duas coisas.
**Reversível?** Fácil no sentido mecânico, caro na prática: mudaria a assinatura dos 8 nós.

---

## D-009 — Evidência é o átomo do estado, não um campo adicionado no fim
**Data:** 22/08/2026
**Decisão:** `Afirmacao` — a unidade que todo agente produz — não existe sem `list[Evidencia]`, e
`Evidencia` guarda o **trecho exato**, não só o `documento_id`. `PerfilStartup`, `Diagnostico`,
`Elegibilidade` e `Recomendacao` são compostos de `Afirmacao`.
**Alternativas descartadas:** um campo `fontes: list[int]` no fim de cada saída · uma tabela de
auditoria separada, preenchida em paralelo ao raciocínio.
**Motivo:** o TAPI exige rastreabilidade **duas vezes** (§5.2 e §5.5). Um campo opcional no fim de
cada modelo é exatamente o que não sobrevive a cinco saltos até o Briefing — em algum nó alguém
devolve a conclusão sem a fonte e ninguém percebe. Fazendo do tipo, deixar de citar vira erro de
validação. Guardar o trecho e não só o id permite o briefing citar literalmente e o avaliador
conferir sem abrir o banco. Trade-off: modelos mais verbosos e prompts que pedem o trecho junto.
**Reversível?** Irreversível na prática — é a espinha do estado.

---

## D-010 — Evidence Validator anota e rebaixa; quem barra é o Recommendation
**Data:** 22/08/2026
**Decisão:** o Validator preenche `confianca` e `validada` em cada `Afirmacao` e **nunca deleta**. O
bloqueio acontece uma camada adiante: o Recommendation não emite prioridade alta apoiada só em
afirmação de `confianca=baixa`. `Elegibilidade` segue a mesma disciplina, separando
`motivos_exclusao` (a base **prova** que é consultoria) de `requisitos_nao_verificados` (a base
**não prova** que tem developer).
**Alternativas descartadas:** o Validator descartar afirmações sem fonte suficiente.
**Motivo:** pela regra 4 de `contexto/02` §6, ausência de sinal ≠ sinal negativo. Deletar destrói
informação que o humano precisa — "não conseguimos confirmar que têm time técnico" é justamente o
que o gerente do Inception quer saber antes de ligar. E separar as duas camadas dá uma
responsabilidade a cada agente em vez de concentrar julgamento num só.
**Reversível?** Fácil.

---

## D-011 — As oito dores do TAPI viram enum fechada
**Data:** 22/08/2026
**Decisão:** `Dor` é um `Literal` com os oito valores que o TAPI lista (custo, latência,
escalabilidade, governança, privacidade, avaliação, observabilidade, dependência de fornecedor). O
Extractor só pode emitir uma dessas; a tabela "dor → tecnologia" de `contexto/03` §4 casa por essa
chave.
**Alternativas descartadas:** dor como texto livre gerado pelo LLM.
**Motivo:** é o que separa um motor de recomendação de um LLM improvisando associação. Com enum
fechada, a recomendação é uma junção auditável entre o que foi observado na startup e a tabela de
tecnologias — dá para explicar no vídeo por que uma tecnologia apareceu. Com texto livre, a única
resposta possível é "o modelo achou que combinava".
**Nota factual:** o TAPI lista **oito** dores; nosso destilado em `contexto/01` e `contexto/03` dizia
"sete". Corrigido nos dois arquivos.
**Reversível?** Fácil — acrescentar valor à enum é aditivo.

---

## D-012 — Adotar a stack NVIDIA inteira, com os modelos que existem hoje
**Data:** 22/08/2026 · fecha a pendência **P-01** · revisado 27/08 (D-064), 28/08 (D-067, D-068)
**Decisão:** LLM dos agentes, embedding e reranking todos no build.nvidia.com.
**Alternativas descartadas:** NVIDIA só para embedding e reranking, com outro provedor para os LLMs
dos agentes.
**Motivo:** as três capacidades responderam e ~30 chamadas de teste não esbarraram em limite. Adotar
tudo dá o argumento mais forte do vídeo — *"o sistema roda na própria stack que ele recomenda"* — e
empurra o critério 2 junto do Diferencial. O fallback continua existindo em D-002.
**Ressalva registrada na hora:** ~30 chamadas não é teste de limite de crédito.
**Reversível?** Fácil, por env var.
**Revisto:** **a decisão não sobreviveu inteira.** Hoje só o **embedding** roda na stack NVIDIA. O
reranking migrou para o Cohere em 28/08 porque o catálogo NVIDIA ficou sem reranker nenhum (D-064,
D-068). O LLM continua NVIDIA, mas por eliminação medida, não por escolha (D-067).

---

## D-013 — Os modelos que o TAPI cita estão mortos; achei os atuais medindo
**Data:** 22/08/2026 · revisado 25/08 (D-046)
**Decisão:** trocar `llama-3.2-nv-embedqa-1b-v2` e `llama-3.2-nv-rerankqa-1b-v2` — que a
documentação de junho e o `contexto/03` original citavam — pelos substitutos vivos à época.
**Alternativas descartadas:** assumir que era problema de credencial e pedir key nova · assumir que
o `contexto/` estava certo e insistir no nome documentado.
**Motivo:** o embedding devolveu **HTTP 410 Gone**, não 401 nem 404. A distinção resolveu o
diagnóstico sozinha: 401 seria credencial, 404 seria nome errado, 410 é recurso **retirado** — e o
chat com a mesma key já tinha passado, o que eliminava credencial. O corpo confirmou:
*"This endpoint has reached its end of life on 2026-05-18T00:00:00Z"*.
**Por que isso é o achado mais valioso do primeiro dia:** é evidência direta de que a stack foi
verificada em vez de copiada da documentação. O TAPI foi escrito em junho, os endpoints morreram em
maio, e um projeto que só copiasse os nomes do enunciado **não executaria**.
**Reversível?** N/A — é constatação de fato, não escolha.
**Revisto:** os substitutos escolhidos aqui morreram com o mesmo 410 **três dias depois** (D-046).
Esta entrada concluiu que *"o TAPI está desatualizado"*. Havia uma segunda conclusão disponível,
mais cara e mais útil: **o catálogo aposenta modelos em cadência de meses, e o projeto inteiro está
montado nele.** Um EOL é anedota; dois é a taxa de falha do fornecedor.

---

## D-014 — Embedding com `dimensions=1024` via Matryoshka
**Data:** 22/08/2026 · fecha a pendência **P-02** · revisado 25/08 (D-046)
**Decisão:** `nvidia/llama-nemotron-embed-vl-1b-v2` pedindo explicitamente 1024 dimensões.
**Alternativas descartadas:**
- **`nemotron-3-embed-1b`** — separa melhor (0,5241 vs 0,1137), mas **rejeita `dimensions` com HTTP
  400**: fica preso em 2048. Re-testado em 25/08: os mesmos dígitos, e continua recusando.
- **`nv-embedqa-e5-v5`** — 1024 nativas e o mais rápido, mas o **crosslingual falha**: 0,3107 contra
  0,3096 de irrelevante é ruído numérico, não separação semântica.
- **Aceitar as 2048 nativas** e indexar com `halfvec(2048)`.
**Motivo:** duas restrições se cruzam e só um modelo satisfaz as duas. (1) **pgvector recusa índice
HNSW acima de 2000 dimensões** no tipo `vector` — verificado no psql; `halfvec(2048)` aceita, mas ao
custo de meia precisão. (2) A base NVIDIA é em inglês e os documentos das startups em português,
então **recuperação crosslingual não é luxo, é o caminho principal** do RAG. O modelo adotado é o
único que trunca para 1024 **e** tem crosslingual real (0,4280 contra 0,0049 de irrelevante).
**Reversível?** Média: mudar a dimensão exige re-embedar o corpus e recriar a coluna.
**Em aberto:** *"1024 vs 768 vs 384, a decidir com medida"* nunca foi resolvido, e qualquer sweep
agora precisa rodar na stack nova.

---

## D-015 — Reranker text-only, não o multimodal
**Data:** 22/08/2026 · fecha a pendência **P-03** · revisado 25/08 (D-046), 27/08 (D-065), 28/08 (D-068)
**Decisão à época:** o reranker text-only da NVIDIA.
**Alternativas descartadas:**
- **a variante VL (multimodal)** — é o que o tutorial recente da NVIDIA usava, mas separou muito
  menos no mesmo teste: margem de **3,24** contra **12,94** do text-only, com latência praticamente
  igual. O corpus do RAG é texto puro; o ganho do VL é entender imagem, e ele paga esse ganho em
  precisão no texto. Escolher o VL porque "é o mais novo" seria decidir por recência.
- **Cohere Rerank** — descartado por *"é pago e quebraria a narrativa de rodar tudo na stack NVIDIA"*.
- **Cross-encoder local** (BGE, Jina) — descartado por *"perde o argumento do Diferencial"*.
**Reversível?** Foi declarada fácil ("duas linhas do `.env`"). Subestimou: trocar o reranker obriga a
re-medir janela, escala de logit e a régua inteira.
**Revisto — esta é a decisão que envelheceu pior, e o motivo é de método, não de sorte:**
1. **"O Cohere é pago" é FALSO, e era verificável em 22/08** (D-065). Há trial key gratuita cobrindo
   Rerank. O motivo que sobrava era narrativo.
2. **O cross-encoder local caiu por "perde o argumento do Diferencial"** — uma história vencendo uma
   propriedade técnica.
3. Ou seja: **as duas alternativas ao fornecedor único foram descartadas por narrativa, uma delas com
   um fato falso em cima.** Foi isso que deixou o projeto sem contingência em 25/08 e sem reranker
   nenhum em 27/08. O passo 7 é Cohere desde 28/08 (D-068) — o que o TAPI recomendava desde sempre.

---

## D-016 — pgvector para o denso, BM25 em processo para o léxico
**Data:** 22/08/2026 · fecha a pendência **P-04**
**Decisão:** vetores densos no Postgres com pgvector; busca lexical do RAG NVIDIA com Okapi BM25 em
processo (`bm25s`). A busca lexical sobre os **documentos das startups** é caso diferente e usa
`tsvector` do próprio Postgres.
**Alternativas descartadas:** **Qdrant** (recomendado pelo TAPI, sparse vectors nativos, RRF pronta)
· **`ts_rank_cd` do Postgres** como o "BM25" da busca híbrida.
**Motivo:** três razões, em ordem de peso. (1) `ts_rank_cd` **não é BM25** — é cobertura de termos,
sem saturação de frequência nem normalização por comprimento de documento. Chamar aquilo de BM25 no
vídeo seria impreciso e o avaliador pode perguntar. `bm25s` dá Okapi de verdade, com `k1` e `b`
ajustáveis — e ajustável significa que o harness do passo 9 tem o que medir. (2) O corpus do RAG é
pequeno e **estático**: reconstruir o índice na ingestão custa segundos. (3) O pgvector já estava
instalado, e Qdrant custaria uma peça de infra a mais para quem for avaliar.
**Onde a decisão se reverteria:** se o corpus crescesse uma ordem de grandeza ou passasse a ser
atualizado com frequência, índice BM25 em memória vira problema e o Qdrant ganha.
**Nota sobre os dois problemas de recuperação:** documentos de startup ficam no `tsvector` porque a
busca lexical ali anda junto de filtro estruturado (setor, estágio, porte) e o corpus cresce — SQL é
a ferramenta certa. São problemas diferentes, ferramentas diferentes.
**Reversível?** Média.

---

## D-017 — Postgres.app para desenvolver, docker-compose para quem avaliar
**Data:** 22/08/2026 · fecha a pendência **P-08**
**Decisão:** os dois. `DATABASE_URL` aponta para o Postgres.app local em desenvolvimento; o
repositório versiona um `docker-compose.yml` com `pgvector/pgvector:pg17`.
**Alternativas descartadas:** só Postgres.app (o avaliador não tem) · só Docker (subir Docker Desktop
a cada sessão é atrito diário).
**Motivo:** os dois públicos têm restrições opostas. Quem desenvolve quer o banco já de pé; quem
avalia quer um comando só. Custa ~20 linhas de YAML e o schema é o mesmo arquivo nos dois caminhos.
Atrito de reprodução conta no critério 7.
**Reversível?** Fácil.

---

## D-018 — Stubs que produzem evidência REAL, não texto inventado
**Data:** 22/08/2026
**Decisão:** os nós-stub casam o vocabulário de sinal de `contexto/02` §5 contra as frases reais dos
documentos e devolvem o **trecho literal** como `Evidencia`. Nenhum stub inventa texto. E dois nós
não são stub nenhum: o **Retriever** (SQL sobre `tsvector`) e o **Evidence Validator** (as 5 regras
de `contexto/02` §6 são lógica pura).
**Alternativas descartadas:** stubs que devolvem objetos hard-coded só para o grafo compilar.
**Motivo:** o que precisava ser provado não era que a extração é boa — era que a **rastreabilidade
sobrevive aos cinco saltos** até o Briefing. Um stub com texto inventado compilaria igual e não
provaria nada; o teste `test_toda_recomendacao_tem_evidencia` passaria sobre dados falsos.
**Reversível?** N/A — os stubs são substituídos por LLM mantendo a assinatura.

---

## D-019 — Diagramas do grafo como Mermaid em texto, não PNG
**Data:** 22/08/2026
**Decisão:** `docs/grafo-pai.mmd` e `docs/subgrafo-analise.mmd` via `draw_mermaid()`.
**Alternativas descartadas:** `draw_mermaid_png()`, que é o que a documentação do LangGraph sugere de
imediato.
**Motivo:** `draw_mermaid_png()` chama a API externa `mermaid.ink` — vira dependência de rede para
gerar um artefato de build, e quebra offline. O GitHub renderiza Mermaid nativamente, então o `.mmd`
aparece como diagrama no README sem imagem intermediária, e continua legível em diff. Bônus: o
diagrama gerado mostra `defer = True` no nó de Briefing, o que torna D-007 visível no desenho.
**Reversível?** Fácil.

---

## D-020 — Limitações conhecidas dos stubs, registradas em vez de escondidas
**Data:** 22/08/2026
**Decisão:** registrar o que a heurística erra, com a causa, em vez de ajustar palavra-chave até a
saída parecer boa.
**O que estava errado, e por quê:**
1. **Falso positivo de inelegibilidade na Axenya** — o site dela diz *"Integramos consultoria, dados
   e operação clínica em uma única plataforma"*. Ela não é uma consultoria: **absorve** a função de
   consultoria num produto, que é o wedge da Sequoia (`contexto/02` §1). Casar substring não
   distingue "somos uma consultoria" de "substituímos a consultoria".
2. **Todas as empresas acusam quase todas as 8 dores** — os gatilhos são termos comuns em qualquer
   texto de negócio.
3. **Doutor-AI saiu AI-enabled apesar de linguagem de autopilot pura** — a palavra "plataforma"
   acionou o contador de copilot.
4. **Confiança baixa em tudo**, porque muitos documentos não têm `data_publicacao` — comportamento
   **correto** da regra 3, não bug.
**Motivo de registrar em vez de corrigir:** os três primeiros são exatamente o argumento de por que
este trabalho precisa de LLM com evidência e validação, e não de regex. Um sistema de palavra-chave
produz erro **confiante** — a Axenya foi reprovada com uma justificativa que soa plausível e cita a
fonte certa. É o melhor material de "antes e depois" possível para o vídeo, e some se eu ajustar a
lista de termos até a saída ficar bonita.
**Revisto:** o item 1 continua **aberto** em 31/08 — D-048 e D-071 estreitaram o casamento, mas a
Axenya segue recusada. É julgamento de sujeito, não fronteira de palavra (D-052). O item 2 foi
**refutado** como diagnóstico: sobre 8 fixtures diversas o Extractor produz 8 conjuntos distintos —
era artefato de uma base com 3 startups, todas de saúde. O que sobrevive é a **precisão** (D-052).

---

## D-021 — Campo estruturado sem fonte literal vira `null`, não valor plausível
**Data:** 22/08/2026
**Decisão:** nos YAMLs do seed, só ficam preenchidos os campos que aparecem **literalmente** nos
documentos coletados. A auditoria zerou 6 dos 12 campos estruturados das 3 empresas iniciais.
**Alternativas descartadas:** manter os valores obtidos por inferência ou por resumo automático de
página, marcando-os com um flag de confiança.
**Motivo:** a auditoria achou casos concretos. `Laura.tamanho_time = 80` veio de *"pretendia expandir
de 65 para 80 até o final de 2021"* — que é **plano**, não fato, e de 2021. `Axenya.ano_fundacao =
2020` não aparece em documento nenhum da base — e `ano_fundacao` alimenta o filtro de elegibilidade
do Inception, que testa "menos de 10 anos".
O ponto decisivo é assimétrico: **`null` dispara comportamento correto, valor errado não dispara
nada.** Com `null`, o Briefing reporta *"ano de fundação não consta na base — verificar"*, que é uma
pendência acionável. Com um ano plausível e errado, o sistema afirma elegibilidade com confiança e
ninguém revisa. É a regra 4 do Evidence Validator aplicada aos campos estruturados.
**Consequência de método, que vale mais que a correção:** `scripts/coletar.py` (texto bruto por
`curl` + parser) é fonte confiável; **resumo automático de página não é** e não deve preencher campo
do banco. Vale para a M3 — é lá que o atalho tentaria voltar.
**Reversível?** Fácil — é só reabrir cada URL e conferir.

---

## D-022 — `thread_id` novo por execução; retomar é opt-in
**Data:** 23/08/2026
**Decisão:** o CLI gera `cli-<uuid4>` a cada execução e imprime o id; `--thread <id>` retoma um run
existente.
**Alternativas descartadas:** manter `thread_id: "cli"` fixo · zerar os canais acumuladores no início
de cada run · trocar o reducer de `analises` por sobrescrita.
**Motivo:** era um bug, não uma preferência. Com o id fixo, a segunda execução do mesmo comando
devolvia a mesma startup **duas vezes** no briefing. A causa não é o reducer: `thread_id` é a
identidade da **conversa**, não do processo. Invocar de novo no mesmo thread não recomeça — o
checkpointer restaura os canais e o `operator.add` soma em cima do anterior. Isso é o comportamento
**correto** de retomada; o erro foi usar retomada como default. As outras duas alternativas
consertariam o sintoma quebrando a semântica.
**Onde isso aparecia:** rodar o comando duas vezes gravando o vídeo.
**Reversível?** Fácil.

---

## D-023 — Fan-out vazio roteia para o Briefing, não para o silêncio
**Data:** 23/08/2026
**Decisão:** `distribuir()` devolve `"briefing"` quando o Retriever não casa nenhuma startup, e o
`path_map` passa a listar `["analisar_startup", "briefing"]`. O Briefing ganhou um caso zero que
reporta o motivo e sugere como alargar a busca.
**Alternativas descartadas:** o Retriever levantar exceção · o CLI checar `startups == []` antes de
imprimir · deixar como estava, tratando "sem resultado" como erro.
**Motivo:** com `[]`, nenhuma tarefa é agendada; e como o `briefing` só era alcançável pela aresta
vinda de `analisar_startup`, ele **nunca executava**. `defer=True` não cobre isso — ele ATRASA uma
tarefa já agendada, não agenda uma que não foi. O ponto de produto: "não encontrei nada, e aqui está
por quê" **é uma resposta do sistema**. Levantar exceção transformaria um resultado legítimo em
falha; checar no CLI colocaria regra de apresentação fora do grafo, e a interface teria que repetir a
checagem. É a mesma disciplina de D-010 e D-021.
**Reversível?** Fácil.

---

## D-024 — `error_handler` por nó em vez de `try/except` em volta do subgrafo
**Data:** 23/08/2026
**Decisão:** cada um dos 6 nós do subgrafo recebe `error_handler=registrar_falha`, que registra
`nó: Tipo: mensagem` em `erros` e devolve `Command(goto=END)`. O `try/except` do wrapper permanece,
rebaixado a terceiro nível.
**Alternativas descartadas:** manter só o `try/except` do wrapper · `try/except` dentro de cada nó ·
deixar o handler seguir o fluxo normal em vez de saltar para o END.
**Motivo:** o `try/except` em volta de `SUBGRAFO.invoke()` entrega a garantia que D-006 prometeu —
uma startup ruim não derruba as outras — mas **descarta tudo que já tinha sido computado**: o invoke
levanta, `final` nunca é atribuído, e a startup volta com `perfil=None`. Com `error_handler`, as
escritas dos super-steps anteriores já estão nos canais. Medido: falha no classifier devolve
`{'perfil': 'perfil-2', 'erros': ['classifier: ValueError: dado ruim']}` em vez de `{}`. Isso muda o
que o gerente do Inception recebe: "extraímos o perfil, a classificação falhou" é acionável; "esta
empresa falhou" não é. `goto=END` e não seguir o fluxo porque sem diagnóstico as etapas seguintes
produziriam recomendação sem base — que é o que D-009 existe para impedir.
**Os três níveis, cada um pegando uma coisa diferente:** `retry_policy` cobre falha transitória
(timeout, 5xx); `error_handler` cobre falha persistente da etapa; o `try/except` cobre falha da
própria máquina do subgrafo.
**Nota sobre retry e erro de validação:** retry **não** resolve `ValidationError` do Pydantic. A
chamada é determinística: repetir o mesmo prompt tende a dar o mesmo erro. O que resolve é reprompt
com a mensagem de validação de volta ao modelo.
**Reversível?** Fácil — é um parâmetro por nó.

---

# Sessão 02-04 — RAG NVIDIA (M2), os 9 passos do pipeline

## D-025 — Chunking estrutural por seção, com banda de tamanho e breadcrumb prefixado
**Data:** 23/08/2026
**Decisão:** a unidade de chunk é a **seção do documento** (`h1/h2/h3` no HTML, `#` ATX e setext no
markdown), passada por duas normalizações — **fundir** seções irmãs abaixo de um piso e **dividir**
seções acima de um teto — e indexada com o **breadcrumb prefixado**:
`NVIDIA NIM > Boost Throughput With NIM\n\n<texto>`. Guarda-se `texto` (limpo, é o que vira
`CitacaoRAG.trecho`) separado de `texto_indexado` (com breadcrumb, é o que é embedado). O primeiro
elemento do breadcrumb é **sempre o nome da tecnologia**, vindo do metadado de curadoria.
**Alternativas descartadas:** **janela fixa 800 chars / 15% overlap** (não some — vira o braço de
controle medido, D-027) · **semântico por similaridade de embeddings** · **um chunk por tecnologia**
· **proposições atômicas extraídas por LLM**.
**Motivo:** medi o corpus antes de decidir. Três números mandaram na escolha:
1. **As páginas têm formas opostas.** NIM: 51 seções em 9.909 chars = **~194 chars por seção**.
   README do TensorRT-LLM: 8 seções em 27.060 = **~3.383**. Um chunk por heading daria fragmento
   inútil num extremo e bloco grande demais no outro — por isso **as duas normalizações são caminho
   principal**, cada uma num tipo de documento, e não tratamento de caso de canto.
2. **Os headings não nomeiam o produto.** Os `h3` do NIM incluem `Benefits`, `Models`, `Features`.
   Uma janela fixa corta a bullet `- Quantização: FP8, FP4, INT4-AWQ` e a separa para sempre de
   "TensorRT-LLM": o denso ainda recupera por "quantização", mas o **BM25 por "TensorRT-LLM" não
   recupera**, e o LLM que ler o chunk não tem como atribuir. Isso é perda de **atribuição**, não só
   de contexto — e atribuição é o 7º campo obrigatório do TAPI.
3. **O semântico por embeddings custaria ~1.500 chamadas só para decidir fronteiras**, e é técnica
   desenhada para prosa corrida: este corpus é bullet e tabela, onde a similaridade entre frases
   consecutivas é ruído, não sinal de fronteira. "Chunking semântico" no TAPI **não obriga** a essa
   técnica; respeitar a estrutura que o autor escreveu é semântico no sentido que importa.
As proposições por LLM foram descartadas por **risco, não por custo**: o LLM reescreveria o corpus,
e alucinação na ingestão envenena a base de evidências inteira.
**Reversível?** Fácil por construção — é o que D-027 existe para garantir.

---

## D-026 — Chunker escrito à mão, sem `langchain-text-splitters`
**Data:** 23/08/2026
**Decisão:** ~80 linhas próprias em `src/rag/chunking.py`.
**Alternativas descartadas:** `RecursiveCharacterTextSplitter` / `MarkdownHeaderTextSplitter`.
**Motivo:** é decisão de **defensabilidade**, não de "não inventado aqui". O eliminatório nº 4 é
*"código integralmente gerado sem compreensão"* — e a diferença entre "escolhi fundir irmãs sob o
pai comum porque medi 194 chars por seção" e "o splitter fez isso" é exatamente o que a banca cobra.
Some-se que a biblioteca **não estava instalada**: a alternativa custaria uma dependência nova para
entregar menos controle. A regra de fundir-com-breadcrumb-do-pai-comum não existe pronta em nenhum
dos dois splitters.
**Reversível?** Fácil — mesma assinatura, é trocar a implementação.

---

## D-027 — `estrategia` como coluna, não como constante: a alternativa descartada vira controle
**Data:** 23/08/2026
**Decisão:** `chunks_nvidia` tem coluna `estrategia` e `UNIQUE (estrategia, documento_url, ordinal)`.
As duas estratégias coexistem na mesma tabela; a busca filtra por `estrategia`. `chunk_fixo()` é
gravado como `fixo-800`.
**Alternativas descartadas:** uma estratégia por vez, escolhida por constante no código,
re-ingerindo o corpus quando quisesse comparar.
**Motivo:** sem isso, D-025 é uma afirmação. Com isso, é um número. É a diferença entre dizer ao
avaliador *"escolhi chunking estrutural"* e mostrar *"estrutural dá recall@3 100%, janela fixa dá
84%, no mesmo gabarito"* — que é literalmente a descrição do nível 4 do barema. O custo é uma coluna
e ~15 linhas.
**Efeito colateral aceito:** o índice HNSW cobre as duas estratégias, então filtrar por `estrategia`
é pós-filtro. Irrelevante a algumas centenas de linhas; viraria problema num corpus uma ordem de
grandeza maior.
**Reversível?** Fácil — `DELETE WHERE estrategia = '...'`.

---

## D-028 — Fonte por tecnologia: markdown bruto no GitHub, HTML nas páginas de produto
**Data:** 23/08/2026
**Decisão:** o manifesto `data/nvidia/fontes.yaml` declara o `formato` de cada fonte. GitHub é lido
em `raw.githubusercontent.com/.../README.md`; páginas de produto em HTML. A ingestão tem **piso de
qualidade** — mínimo de caracteres e de headings — que **falha alto**, com o nome da tecnologia na
mensagem.
**Alternativas descartadas:** HTML uniforme para tudo · deixar a ingestão aceitar o que vier.
**Motivo:** medido, não deduzido. O texto extraído de `github.com/NVIDIA/TensorRT-LLM` começa com
*"Uh oh! There was an error while loading… Go to file… Last commit message"* — é o chrome do GitHub,
que renderiza o README por JS. O `raw.githubusercontent.com` devolve **27.060 chars de markdown
limpo**. Mesma fonte, qualidade incomparável. O piso existe porque a mesma varredura achou **4 URLs
das 18 sem conteúdo utilizável**: API Catalog (28 chars, é SPA), cuDF (558), cuML (1.911, zero
headings), Triton docs (2.753). Sem o piso, essas quatro entrariam como chunks vazios e o RAG
responderia "não sei" sobre cuDF sem ninguém entender por quê.
**Reversível?** Fácil — é uma linha no manifesto por fonte.

---

## D-029 — Guardar `embedding_bruto vector(2048)` sem índice ao lado do `vector(1024)` indexado
**Data:** 23/08/2026 · **verificado por medição no mesmo dia**
**Decisão:** duas colunas. `embedding vector(1024)` com índice HNSW é a que a busca usa;
`embedding_bruto vector(2048)` fica **sem índice**, só para o harness derivar 384/768/1024 por
truncagem local.
**Alternativas descartadas:** só `vector(1024)`, re-embedando o corpus para comparar dimensões.
**Motivo, com número:** embedei o mesmo texto pedindo 2048 e pedindo 1024/768/384, truncei o de 2048
localmente e renormalizei. `cos(api, truncagem_local)` = **0,99999996 nas três dimensões**. A
promessa Matryoshka se confirma — o sweep de dimensão passa a custar **zero chamada de API**.
Dois achados de brinde, do mesmo teste, que viraram fato de arquitetura:
- **os vetores voltam já normalizados** (norma L2 = 1,000063), então cosseno e produto interno são
  equivalentes aqui;
- **o embedder aceita entre 6.144 e 8.192 tokens** de entrada — muito acima de qualquer chunk
  desejável, então o limite do modelo **não** é o que fixa o teto de D-025.
**Custo:** ~8 KB por chunk. Verificado em psql que `vector(2048)` armazena normalmente e que só o
**índice** HNSW recusa acima de 2000 dimensões.
**Reversível?** Fácil — `DROP COLUMN` quando o sweep terminar.
**Consequência em D-014:** a reversibilidade que ela registrou como "média — mudar a dimensão exige
re-embedar" passa a ser **fácil**, pela equivalência medida aqui.

---

## D-030 — Gabarito ancorado no documento-fonte, não no chunk
**Data:** 23/08/2026
**Decisão:** cada pergunta de `data/avaliacao/gabarito.yaml` aponta para a **URL do documento** que a
responde. `recall@k` = "algum dos k primeiros chunks veio do documento certo". A `frase_ancora` é
opcional e habilita uma variante estrita: "e o chunk contém a frase".
**Alternativas descartadas:** ancorar em `id` de chunk · ancorar só na frase exata.
**Motivo:** ancorar no chunk amarraria a métrica a uma estratégia de chunking — e comparar
estratégias é justamente o que D-027 existe para permitir. Um gabarito preso a ids de chunk teria
que ser reescrito a cada mudança de banda, o que na prática significa nunca mudar a banda.
**Por que o gabarito é escrito na sessão 02 e não depois:** é preciso ler as 18 páginas para curar
as fontes de qualquer jeito. Escrever a pergunta durante essa leitura é quase de graça.
**Reversível?** Fácil — é dado versionado, não código.

---

## D-031 — Busca densa e `recall@k` entram na sessão 02, não depois
**Data:** 23/08/2026
**Decisão:** a sessão que entrega chunking entrega junto `buscar_denso()` e `scripts/avaliar_rag.py`
com `recall@k`.
**Alternativas descartadas:** manter o harness para a sessão de otimização.
**Motivo:** a sessão decide chunking e dimensão. Sem instrumento, ela decide por argumento e
descobre por medição depois — que é exatamente o que se quer evitar. Mover o *dado* (gabarito) sem
mover a *função que o consome* fazia metade do movimento.
**Reversível?** N/A — é decisão de sequenciamento.

---

## D-032 — D-025 confirmada por medição, e `recall@3` é a métrica que discrimina
**Data:** 23/08/2026 · **é o resultado, não a intenção**
**Decisão:** manter `estrutural-v1` como estratégia de produção. Comparação com o braço de controle,
20 perguntas, recuperação densa pura, 1024 dimensões:

| k | estrutural frouxo | fixo-800 frouxo | estrutural estrito | fixo-800 estrito |
|---|---|---|---|---|
| 1 | 89% | 84% | 68% | 58% |
| **3** | **100%** | **84%** | **79%** | **68%** |
| 5 | 100% | 100% | 84% | 74% |

**O que os números dizem, incluindo o que não dizem:**
1. **`recall@5` satura e não serve para decidir** — 100% nos dois braços. Com 16 documentos e k=5 a
   pergunta é fácil demais. Reportar só o k=5 esconderia a diferença inteira.
2. **k=3 é o ponto de discriminação: 100% contra 84%.**
3. **O estrito separa mais que o frouxo em todo k.** Faz sentido: o frouxo só pergunta se o
   documento certo apareceu, e a página do TensorRT-LLM tem 27 mil caracteres — recuperar qualquer
   pedaço dela não prova que o pedaço responde.
4. **A q19 fez o que foi desenhada para fazer.** Ela pergunta por um trecho que está na página do NIM
   mas cujo texto destaca "TensorRT-LLM" e nunca repete "NIM". Em k=1 os **dois** braços erram; em
   k=3 o estrutural acerta e o fixo continua errando. É a validação medida do argumento central de
   D-025, e também o limite dele: o breadcrumb leva o chunk certo para a zona onde o reranker pode
   promovê-lo, não para o topo sozinho.
**Reversível?** É reprodutível com `python scripts/avaliar_rag.py`.
**Instrumento:** medido com o embedder de 23/08, morto em 25/08. **Não re-medido na stack atual** —
o que sustenta a conclusão é a comparação *entre os dois braços sob o mesmo instrumento*, que a
troca de embedder afeta igualmente dos dois lados.

---

## D-033 — Abstenção não sai de limiar sobre o score denso
**Data:** 23/08/2026 · **achado que mudou o rumo da M2**
**Decisão:** o sistema **não** decide "não sei" comparando `score_denso` com um limiar.
**Alternativas descartadas:** limiar sobre a similaridade densa — que era o caminho óbvio e o que eu
teria implementado sem medir.
**Motivo — medido, e o resultado é o contrário do esperado:** a q20 do gabarito não tem resposta na
base (pede o preço da licença do AI Enterprise, que a página não publica). Os três chunks que ela
recuperou são **topicamente perfeitos** — AI Enterprise, licenciamento, como começar — e nenhum
contém preço. E o score do primeiro é **mais alto que o pior acerto verdadeiro do gabarito**. As
distribuições se sobrepõem, então **não existe limiar** que abstenha na q20 sem descartar respostas
corretas.
**A razão é conceitual, não um defeito do modelo:** similaridade de embedding mede **pertinência de
tópico**, não **existência de resposta**. Uma pergunta bem formulada sobre um assunto que a base
cobre casa bem com a base — exatamente por ser bem formulada.
**Reversível?** N/A — é um achado.
**Revisto:** a hipótese que esta decisão deixou para a sessão seguinte — *"o cross-encoder julga se a
passagem RESPONDE, o que é pergunta diferente"* — foi testada e **refutada** (D-035).

---

## D-034 — `TETO_TOKENS = 450` fica, e a justificativa dele estava falsa
**Data:** 24/08/2026 · revisado 24/08 (auditoria), 28/08 (D-068)
**Decisão:** manter `TETO_TOKENS = 450` e **reescrever a justificativa**. O comentário antigo dizia
*"450 cabe com folga na janela típica de um cross-encoder (512)"* — essa janela não existia no modelo
em uso.
**Alternativa descartada:** manter o comentário e seguir. Descartada porque o eliminatório nº 4 é
sobre defender decisões: um número certo (450) sustentado por um fato falso (janela de 512) é pior
que um número errado, porque a banca pergunta pelo raciocínio e não pelo valor.
**O que ficou estabelecido, e sobrevive à troca de reranker:**
- **nenhum dos dois motores restringe o teto.** O embedder aceita 6.144-8.192 tokens (D-029) e todo
  reranker que este projeto usou aceita muito mais que 450. O teto é **escolha de precisão de
  recuperação**, não limite técnico.
- **caber na janela não é o mesmo que pontuar bem nela.** Com texto real do corpus, o score da
  passagem-alvo cai conforme o chunk cresce, a cobrança começa entre ~380 e ~560 tokens e depois
  **satura**. Isso sustenta os 450 e fecha a faixa de busca de um eventual sweep em ~120-560.
**A lição de método, que vale mais que o número:** a primeira versão deste teste afogava a
frase-resposta em enchimento que falava de **outro produto**. Ele media *"o chunk ficou off-topic"*,
não *"o chunk ficou maior"* — variável de confusão, no teste desenhado justamente para isolar
tamanho. Refeito com chunks vizinhos do mesmo documento, que é o que um teto maior de fato produz.
**Reversível?** N/A — é medição.
**Instrumento:** os logits e a janela de 8.192 eram do reranker de 24/08, morto em 27/08. O passo 7
é Cohere desde 28/08, com janela >32k e score em [0,1] (D-068).

---

## D-041 — `Passagem` interna, `CitacaoRAG` de contrato: dois tipos, não um
**Data:** 24/08/2026
**Decisão:** o pipeline de recuperação (`src/rag/`) trabalha com `Passagem` — dataclass com
`chunk_id`, `texto`, `texto_indexado`, `caminho_secao`, `documento_url`. A conversão para
`CitacaoRAG` acontece **só na borda**, em `para_citacao()`.
**Alternativas descartadas:** acrescentar `chunk_id` e `texto_indexado` ao próprio `CitacaoRAG` ·
casar os rankings pelo texto do trecho.
**Motivo:** a fusão precisa reconhecer que o item no ranking denso e o no lexical são o **mesmo
chunk**. Casar por texto é frágil (qualquer normalização quebra) e caro; o id vem do banco de graça.
O que decidiu contra pôr os campos em `CitacaoRAG` foi **onde ela mora**: em `src/state.py`, dentro
do estado do grafo. `chunk_id` e `texto_indexado` são detalhes da recuperação — o breadcrumb existe
para o embedder e o reranker lerem, não para o agente. Mantendo a fronteira, trocar a fusão ou o
reranker **não propaga para o estado do grafo**, que é a peça mais cara de mexer depois.
**Reversível?** Fácil — é tipo interno, nada fora de `src/rag/` o conhece.

---

## D-036 — BM25 variante `lucene`, e a tokenização que dobra acento
**Data:** 24/08/2026 · revisado 24/08 (auditoria)
**Decisão:** `bm25s` com `method="lucene"`, `k1=1.2`, `b=0.75`, sobre `texto_indexado`, com
tokenizador próprio que **dobra acento**, **preserva o ponto entre alfanuméricos** e **não usa
stemmer**.
**Alternativas descartadas:** `method="robertson"`, o BM25 do artigo original.
**Motivo:** só 2 dos 3.063 termos do vocabulário teriam IDF negativo pela fórmula do artigo — mas são
`nvidia` e `ai`, e **14 das 24 consultas contêm um dos dois**. Sob `robertson` esses tokens ficariam
inertes; sob `lucene` contribuem pouco e positivo.
**Os outros três lados da decisão:**
- **`k1` e `b` explícitos, não no default da biblioteca.** D-016 justifica `bm25s` por eles serem
  ajustáveis; deixá-los implícitos entregaria o argumento sem entregar a coisa.
- **Dobrar acento não é higiene, é requisito:** o corpus é em inglês e as consultas em português.
  Sem a dobra, `métricas` e `metrics` nunca casam.
- **Score zero é ausência, não evidência fraca** — significa que nenhum termo da consulta ocorre no
  chunk. Deixá-lo entrar poluiria o pool da fusão com ruído ranqueado. É o que faz a q18 devolver
  lista vazia, e o braço lexical dizer "não tenho nada" é resposta correta.
**Reversível?** Fácil — `METODO`, `K1`, `B` e o tokenizador são constantes de um módulo só.
**Revisto — o argumento original desta decisão estava ERRADO para a biblioteca em uso.** Ela dizia
que o Okapi original **puniria** o chunk por conter a marca (IDF de `nvidia` = −2,4227).
`bm25s/scoring.py:178` trava o IDF de Robertson em zero, e `allow_negative` não é passado de lugar
nenhum: medido no índice real, `nvidia` e `ai` pontuam exatamente **+0,0000**. O Okapi original
**neutraliza** o termo, não o pune. E **o recall é idêntico nas duas variantes** — a escolha não tem
consequência medida neste corpus. A decisão fica; o argumento ficou mais estreito.

---

## D-037 — Fusão por RRF, soma ponderada como controle
**Data:** 24/08/2026 · revisado 25/08 (D-046), 28/08 (D-068)
**Decisão:** `fundir_rrf` é o motor de produção, com `K`, `peso_denso` e `peso_lexical` explícitos;
`fundir_soma` existe implementada e medida como **braço de controle** (padrão de D-027). Default:
**RRF, `K=10`, denso 1.0, lexical 0.3**.
**Alternativas descartadas:** só soma ponderada · só RRF · não implementar o braço lexical.
**Motivo:** RRF é o default do Elastic, Qdrant e OpenSearch, e isso resolve a pergunta na banca em
uma frase — mas não é a razão. A razão é **D-033**: a magnitude do score denso **não é calibrada**;
a q20, que não tem resposta na base, recupera com score mais alto que o pior acerto verdadeiro. Uma
fusão que consome magnitude consome um sinal que já medimos ser não confiável. **RRF só olha
posição.** A soma ponderada foi implementada e medida assim mesmo, e a normalização é parâmetro
porque ela é a decisão escondida dentro da decisão: `minmax` faz o 1º colocado valer 1,0 *por
construção* — ela **fabrica** confiança exatamente onde o sistema precisa abster-se.
**`K` é parâmetro e não a constante 60 da literatura:** com `K=60` e listas de 20 as contribuições
vão de 1/61 a 1/80 — **31% de amplitude** —, e o RRF degenera em "aparece nas duas listas?". A
varredura confirma: `K=60` é pior ou igual a `K=10` em toda a grade, estritamente pior em 3 dos 4
pesos. Corpus pequeno e pool curto é onde esse defeito morde.
**A varredura custou zero chamada de API:** as listas densa e lexical são recuperadas uma vez por
consulta e reaproveitadas; RRF e soma são funções puras delas. Grade inteira em 13 segundos —
mesmo truque de D-029. **Nenhuma configuração de fusão bate a linha de base densa; a melhor empata.**
**O que eu NÃO fiz, e é decisão:** não subi o peso lexical até a métrica melhorar, nem troquei de
gabarito. As duas coisas seriam ajustar a régua ao resultado.
**Reversível?** Fácil — `peso_lexical=0.0` reduz a híbrida ao denso puro exatamente.
**Revisto — a história do braço lexical mudou três vezes, e é por isso que ela fica escrita:**
1. **24/08:** depois do reranker, o léxico contribuía **zero** — `rerank_denso` e `rerank_hibrido`
   davam os seis números idênticos.
2. **25/08 (D-046):** com o reranker novo a identidade **quebrou**, e o ganho tinha nome: a **q17**,
   cuja âncora (`Evaluator`, nome de produto em inglês numa pergunta em português) o denso não
   recupera de jeito nenhum. Isolado pelo braço de controle `--truncar-pool`: a vantagem vinha do
   **pool maior**, não da reordenação da fusão.
3. **28/08 (D-068):** com o Cohere, **os dois braços empatam de novo** — ele não promove a q17.
**A conclusão que sobrevive às três:** o ganho do braço lexical era propriedade **do reranker**, não
da fusão. É a segunda vez que ampliar o instrumento derruba uma afirmação sobre o léxico. O
argumento vivo para mantê-lo é outro, e é o de D-043: a consulta real do sistema carrega **nome
literal** vindo das evidências da startup, que é onde o BM25 ganha — e isso continua **não medido**,
porque exigiria um gabarito de consultas nesse formato.

---

## D-038 — O reranker lê `texto_indexado`, com o breadcrumb
**Data:** 24/08/2026 · revisado 25/08 (D-046)
**Decisão:** o cross-encoder recebe `texto_indexado` (breadcrumb prefixado), não `texto`.
**Alternativa descartada:** `texto` puro — o mesmo campo que vira `CitacaoRAG.trecho`, o que teria a
vantagem de "o reranker lê exatamente o que é citado", uma coisa a menos para explicar.
**Motivo:** reranquear o texto puro **descartaria no passo 7 a correção feita no passo 3**. O chunk
que responde a q19 cita "TensorRT-LLM" com destaque e nunca repete "NIM"; é o breadcrumb
`NVIDIA NIM > ...` que diz ao cross-encoder de que produto aquilo fala — e atribuição é o 7º campo
obrigatório do output do TAPI. Medido nas duas variantes: empatam em recall@1, e o breadcrumb
**sobe o score da âncora em 9 das 17** perguntas.
**Efeito colateral medido e aceito:** o breadcrumb também sobe o score da q20, que não tem resposta,
piorando a margem de abstenção. Irrelevante, porque **nenhuma das duas variantes separa** (D-035).
**Reversível?** Fácil — é qual campo entra no payload.
**O que o passo 7 entrega hoje, e é o argumento da decisão:** o embedder atual sozinho já dá os 95%
de recall@1 que antes exigiam o reranker. **O ganho migrou do frouxo para o estrito** — o rerank não
move mais r@1, e move e@3 de 79% para 95%. Isso deixa o argumento mais limpo, não mais fraco: **o
reranker existe para achar o CHUNK que responde, não o documento.**
**Não re-medido:** a decisão em si (`texto_indexado` vs `texto` puro) não foi re-testada na stack
atual. O mecanismo que a justifica não depende do modelo, mas o número é de 24/08.

---

## D-039 — O gabarito ganha perguntas SEM resposta, de regimes diferentes, com prova executável
**Data:** 24/08/2026
**Decisão:** o gabarito passa de 20 para **24 perguntas — 19 com resposta e 5 sem**. Cada
`sem_resposta` carrega `regime`, `justificativa_ausencia` (prosa, obrigatória) e `termos_ausentes`
(opcional, verificado por `--validar`).
**Alternativa descartada:** manter uma única pergunta sem resposta e registrar a ressalva de n=1.
**Motivo:** a conclusão mais consequente da M2 — *"nenhum limiar separa abstenção"* — é uma afirmação
sobre **sobreposição de duas distribuições**, e com n=1 de um lado não há distribuição, há um ponto.
Pior: a q20 foi escrita para ser o caso difícil, então ela podia estar **exagerando** a sobreposição
e condenando um mecanismo que funcionaria. (Ampliar mostrou o contrário — ver D-035.)
**Dois regimes, de propósito:** `topicamente_perfeita` (a base fala do assunto com autoridade e só
não tem o fato pedido) e `topicamente_ausente` (o assunto não está na base). A segunda existe para
provar que **a fronteira entre as duas é observável**: um sistema que abstém só nela não aprendeu a
abster-se — aprendeu a reconhecer assunto estranho, que é outra coisa e muito mais fácil.
**`termos_ausentes` é a prova executável, o espelho de `frase_ancora`.** Se qualquer termo declarado
ocorrer no corpus, `--validar` falha. Verificado com **fronteira de palavra e não substring** — e
essa distinção nasceu de um erro real: `ILIKE '%SLA%'` reportava `SLA` como presente porque casa
dentro de "tran**sla**tion".
**A prosa é obrigatória e o termo não, e isso é decisão.** Há ausências que nenhuma string prova: a
da q20 é a de um **número**, e não existe termo cuja falta demonstre que um preço não está publicado.
Onde o termo serve, ele é prova; onde não serve, a curadoria escreve o argumento e assina embaixo.
**A pergunta que mais importa é a q21** — *"a NVIDIA tem algum programa específico para startups no
Brasil?"*. É a pergunta que o **usuário real deste sistema** faria. Se o sistema inventar um
benefício regional, inventa para a única pessoa que saberia na hora que é falso.
**Reversível?** Fácil — é dado versionado, não código.

---

## D-035 — A hipótese de D-033 está REFUTADA: o reranker também não abstém
**Data:** 24/08/2026 · revisado 25/08 (D-046) · **contraria o que a sessão apostava**
**Decisão:** o sistema **não** decide "não sei" por limiar sobre score algum — nem sobre a cosseno
densa, nem sobre o logit do cross-encoder. A abstenção sobe para o **passo 8, a geração** (D-040).
**Motivo, medido no gabarito com 5 perguntas sem resposta:**

| motor | pior acerto | pior sem-resposta | margem |
|---|---|---|---|
| denso | 0,2640 | 0,4891 (q23) | **−0,2251** |
| cross-encoder | −7,1641 | +3,8398 (q23) | **−11,0039** |

**A margem é negativa nos dois motores, e continuou negativa depois da troca dos dois modelos** — o
que é a evidência mais forte que esta conclusão tem: **não era artefato de um modelo.**
**A q23 é a demonstração.** Ela pergunta *"o TensorRT-LLM é mais rápido que o vLLM? Em quantos por
cento?"* e recebe um dos scores mais altos do gabarito inteiro. O cross-encoder está certo no que
ele mede: o chunk cita "TensorRT-LLM, vLLM ou SGLang" na mesma frase, e é a passagem mais relevante
do corpus para aquela pergunta. Ela só não contém a comparação.
**A razão é conceitual: relevância não é responsibilidade.** O bi-encoder mede pertinência de
tópico; o cross-encoder mede relevância do par, que é mais fino e ainda é relevância. Distinguir
"fala do assunto" de "contém o fato pedido" exige **ler a passagem procurando a coisa específica** —
e o único componente do pipeline que lê é o gerador.
**Ampliar a amostra PIOROU a margem, e isso justificou D-039 sozinho.** Com n=1 a margem densa era
−0,1879; com n=5, −0,2810 na mesma stack. O n=1 estava **subestimando** o problema, não exagerando.
**Alternativa registrada como não testada:** um critério **relativo** dentro da consulta (gap entre
1º e 2º) em vez de limiar global. Não testei porque, com 5 perguntas sem resposta, calibrar um
segundo hiperparâmetro seria sobreajuste declarado.
**Reversível?** N/A — é um achado.

---

## D-042 — A consulta do NVIDIA RAG Agent sai da dor observada, não de um dicionário
**Data:** 24/08/2026 · corrigida por D-043
**Decisão:** `src/agents/nvidia_rag.py` perde a `BASE_PROVISORIA` de 8 dores → 8 tecnologias e passa
a chamar `pipeline.buscar_com_rerank()` **uma vez por dor observada**.
**Alternativas descartadas:** manter o dicionário · consultar uma vez só, concatenando as dores.
**Motivo — o dicionário não era simples demais, era DESLIGADO.** Com ele, as 16 páginas ingeridas,
chunkadas, embedadas e indexadas **não mudariam uma vírgula da recomendação**. O critério 2 vale 20
pontos e viraria decoração. **Uma consulta POR DOR e não uma só** porque dores diferentes recuperam
tecnologias diferentes; concatenar produziria uma consulta média que não é a de ninguém, e o
reranker receberia um pool sem foco. O custo é linear no número de dores, e o teto de 8 da rubrica o
limita naturalmente.
**Por que este nó NÃO gera texto**, mesmo com `pipeline.responder()` pronto: quem o consome é o
Recommendation, que precisa dos **trechos com scores** para cruzar com o perfil, não de um parágrafo
já redigido. Redigir aqui e reinterpretar lá perderia a evidência no meio do caminho. A geração com
citação é para quando um **humano** faz a pergunta — ela entra pela interface.
**Reversível?** Fácil — é o corpo de um nó.
**Revisto:** a consulta que esta decisão montou (`DorObservada.texto` + `stack_declarada`) estava
quebrada nas duas metades, e D-043 mediu e corrigiu.

---

## D-040 — O passo 8 entra na M2: geração com citação e abstenção estruturada
**Data:** 24/08/2026 · revisado 25/08 (D-046), 28/08 (D-069) · fecha os 9 passos do TAPI
**Decisão:** `src/rag/geracao.py` implementa o passo 8 — o LLM lê os top-k reranqueados e devolve
`RespostaRAG` com `texto`, `abstencao: bool`, `motivo_abstencao` e `indices_citados`. Todo acesso a
LLM passa por `src/llm.py`, sempre com `with_structured_output(..., method="json_schema")`.
**Alternativas descartadas:** adiar a geração para a M4 · `method="function_calling"` ·
`method="json_mode"` · abstenção como prosa a interpretar.
**Por que o passo 8 entrou aqui:** depois de D-035 a abstenção ficou **sem outro lugar para morar** —
nenhum limiar funciona, e o único componente que lê a passagem é o gerador. E a regra *todo
incremento é medido* deixou de ser obstáculo quando D-039 ampliou o gabarito: **acurácia de
abstenção sobre 24 perguntas é contagem pura**, sem LLM-as-judge e sem rubrica de fidelidade.
**`json_schema` e não `function_calling` — medido na armadilha.** Mesmo modelo, mesmo prompt,
`temperature=0`, na q23:

| método | resultado |
|---|---|
| `function_calling` | `abstencao=False` · **"o TensorRT-LLM é mais rápido que o vLLM em 30%"** |
| `json_mode` | não faz parse — o modelo devolve JSON com outro shape |
| **`json_schema`** | **`abstencao=True`** · "a passagem não fornece informação sobre..." |

A leitura provável é que `function_calling` adiciona pressão para PREENCHER os campos da ferramenta.
**Detalhes de desenho, e cada um é uma decisão:**
- **Citação por ÍNDICE, não por URL escrita na prosa.** Índice fora da faixa é erro detectável por
  código; URL no meio de um parágrafo não é. Rastreabilidade precisa ser verificável.
- **Abstenção é campo booleano**, não frase que alguém depois classificaria com regex — D-021.
- **Zero passagens não chama o LLM.** Não há o que ler; pedir ao modelo que decida sobre o vazio é
  exatamente onde ele inventaria.
**A instrução de idioma no prompt não é ajustar a régua ao resultado.** O gerador leu *"high
transcription accuracy for Arabic, English, ..., **Portuguese**"* e respondeu *"não há menção
explícita à língua portuguesa"*. Acrescentei que os trechos estão em inglês, a pergunta vem em
português, e traduzir para comparar faz parte do trabalho. Isso declara um fato de arquitetura
(D-014: corpus EN, consulta PT). A versão inaceitável seria *"se perguntarem sobre português, diga
que o Riva suporta"*.
**Reversível?** Fácil — é um módulo e um prompt.
**Revisto — a afirmação central desta decisão está REFUTADA.** Ela dizia: *"15 oportunidades de
alucinar e zero alucinações; o sistema erra sempre para o lado de não responder"*. Em 25/08, na
q23 — a mesma pergunta-armadilha que serve de prova de que `json_schema` é o método certo — o
sistema respondeu **"o TensorRT-LLM é mais rápido que o vLLM em 60%"**, com citação de fonte errada,
sob `json_schema`. Um contraexemplo basta para derrubar uma afirmação de impossibilidade. A defesa
muda de *"o método impede a alucinação"* para *"o método reduz a frequência"* — e D-047 mediu isso.
**A citação é o ponto fraco, e fica registrado como tal:** `indices_citados` erra com frequência não
desprezível. A resposta sai acompanhada de todas as passagens lidas em `RespostaRAG.citacoes`, então
nada sai sem fonte anexada — mas *qual* trecho sustenta *qual* afirmação ainda não é confiável.
**A abstenção está resolvida; o "de onde veio" não.**
**O que NÃO foi medido:** fidelidade da prosa ao contexto. Exigiria LLM-as-judge ou anotação humana,
e as duas trazem uma régua que também precisaria ser validada. Declarado como não medido em vez de
alegado.
**Instrumento — RE-MEDIDO EM 02/09, e a dívida de D-069 está paga (fecha P-15).** A faixa de
**20-22/24** era do LLM que morreu em 27/08. No modelo atual (`nemotron-3.5-lightning-30b-a3b`) e no
corpus pós-D-082 (175 chunks):

| | modelo morto (3 execuções) | **02/09, modelo atual** |
|---|---|---|
| respondeu, das que têm resposta | — | **18/19** |
| absteve, das que NÃO têm | — | **5/5** |
| **acurácia de abstenção** | 20-22 / 24 | **23/24 = 96%** |

**O único erro está no lado seguro, e isso importa mais que o número.** A q09 foi **abstenção
indevida**, não alucinação: o modelo recusou porque *"os trechos contêm informações sobre detecção de
comportamento anômalo e digital fingerprinting, mas não mencionam o uso de GPU para essa finalidade"*
— leitura defensável do que as passagens de fato dizem. Para um sistema cuja promessa inteira é
*"nada é afirmado sem evidência"*, errar para o lado de não responder é o modo de falha certo.

**O que isto NÃO revoga:** a refutação acima continua de pé. A q23 alucinou uma vez em 25/08, e uma
execução limpa não desfaz um contraexemplo — a defesa segue sendo *"o método reduz a frequência"*, não
*"o método impede"*. E `indices_citados` continua sendo o ponto fraco: nesta execução as 18 respostas
citaram a fonte certa, o que é bom sinal e **não** é medição de fidelidade da prosa, que segue
declarada como não medida.

---

## D-043 — A consulta do RAG sai do RÓTULO da dor + das EVIDÊNCIAS, não do `texto` da dor
**Data:** 24/08/2026 · corrige D-042 sem revogá-la
**O que a medição achou.** As duas metades da consulta de D-042 estavam quebradas:
1. `DorObservada.texto` **não é a linguagem da startup** — o Extractor o preenchia com um template
   fixo, `f"Sinal de dor em {dor} encontrado nos documentos"`. Existiam OITO consultas possíveis no
   sistema inteiro.
2. `perfil.stack_declarada` **não é preenchida por nenhum produtor**. O ramo `if not stack` era o
   único que executava.

Medido sobre três startups reais:

| | antes (D-042) | depois (D-043) |
|---|---|---|
| tecnologias que chegam ao Recommendation | **idênticas nas três startups** | uma lista diferente por startup |
| braço lexical nas consultas do grafo | **0 resultados** nas 8 consultas possíveis | vota em 6 das 7 dores |

Ou seja: D-042 tinha reintroduzido o `BASE_PROVISORIA` como constante disfarçada, agora pagando
embedding e rerank por dor por startup. **A startup não entrava na conta.**
**Decisão:** a consulta passa a ser `rótulo da dor + trechos de dor.evidencias + stack`. O rótulo é a
âncora tópica; **os trechos são a frase LITERAL do documento da startup**, que `Evidencia.trecho`
guarda desde D-018 — é o que faz duas startups com a mesma dor recuperarem coisas diferentes.
**Alternativa descartada:** fazer o Extractor preencher `stack_declarada`. É a correção "certa", mas
é reescrever o Extractor, e as evidências já entregam nome literal hoje sem tocar naquele agente.
**Segunda decisão, no mesmo nó — a lista sai INTERCALADA por dor, não concatenada.** O Recommendation
corta em `TETO_RECOMENDACOES = 3`. Concatenada dor a dor, esse corte é POR DOR: as três recomendações
saem todas da primeira dor e as outras somem em silêncio. Intercalando com `zip_longest`, o corte
pega o 1º colocado das três primeiras dores — que é o que a regra 4 de `contexto/03` §4 ("não
empilhar tecnologia") quer dizer.
**Terceira, pequena:** `CitacaoRAG` ganha `dor_origem`, carimbado por `nvidia_rag` e não pelo
pipeline — `src/rag/` continua sem conhecer o conceito de dor, que é o que mantém D-041 de pé.
**Reversível?** Fácil.

---

## D-044 — O harness de avaliação mede a configuração que a produção roda
**Data:** 24/08/2026
**O problema, em uma frase:** `scripts/avaliar_rag.py` declarava os **próprios** defaults de fusão e
truncava o pool antes do rerank; `src/rag/pipeline.py` fazia diferente nos dois pontos.
Custo já pago por essa divergência, e não é hipotético:
1. O comando documentado como *a* ablação **não reproduzia a tabela publicada**. Quem fosse
   reproduzir o repositório encontrava outros números — num projeto cujo argumento inteiro é "está
   medido".
2. O `--geracao` truncava a fusão em 20 e a produção não trunca. A q17 foi medida num pipeline **em
   que a passagem-âncora não existia**, e D-040 registrou o diagnóstico errado.
**Decisão:** `POOL_PADRAO`, `K_RRF_PADRAO`, `PESO_DENSO_PADRAO` e `PESO_LEXICAL_PADRAO` são
**importados de `src.rag.pipeline`**, não redeclarados; e o pool **não é truncado** antes do rerank.
**A alternativa era defensável, e por isso isto é decisão e não correção.** Manter o harness
truncando de propósito o preservava como braço de controle da pergunta "vale a pena mandar a união
inteira ao reranker?". O que decidiu foi o risco: **um controle que é o default silencioso não é
controle, é divergência.** `--truncar-pool` restaura a truncagem e se pede pelo nome.
**Efeito colateral bom:** os imports tardios de `fusao`, `lexical`, `rerank` e `geracao` saíram. Eles
existiam para "`--motor denso` rodar antes de a fusão existir", uma razão de ordem de sessão que
expirou. **Um comentário que descreve uma proteção que não protege é pior que nenhum comentário.**
**Reversível?** Fácil.

---

## D-045 — O modelo recebe um schema estreito; `RespostaRAG` é montado em código
**Data:** 24/08/2026 · achado do code review
**O que estava acontecendo.** `geracao.gerar()` mandava ao modelo o schema inteiro do contrato —
incluindo `citacoes: list[CitacaoRAG]` com todo o `$defs`, um campo que a linha seguinte do código
**descarta**. E arrastava junto uma coisa que a sessão não tinha percebido: **o docstring de uma
classe Pydantic vira o `description` do JSON Schema, ou seja, vira PROMPT.** O de `RespostaRAG` é
prosa de decisão — cita margens e números de decisão. Isso é documentação para quem lê o
repositório, e é ruído quando endereçado ao modelo.
**Medido:** 2.690 chars de schema por chamada contra 524 do tipo estreito — **80% menor**, com o
mesmo `required`.
**Decisão:** `SaidaGerador`, local a `src/rag/geracao.py`, com os quatro campos que o MODELO decide e
docstring curto escrito PARA O MODELO. `RespostaRAG` continua sendo o contrato e continua montado em
código.
**Alternativa descartada:** manter `RespostaRAG` na chamada e só encurtar o docstring. Resolvia
metade — deixava de pé um campo cujo valor é descartado, que o modelo pode gastar tokens preenchendo
e que, com uma passagem longa, é caminho para estourar `max_tokens` e devolver JSON truncado.
**A regra que fica, e vale para os nove agentes:** todo schema que vai para `with_structured_output`
é interface **com o modelo**, não com o repositório. **Docstring de schema é prompt.**

---

# Sessão 05-06 — o segundo EOL, e a régua dos agentes

## D-046 — A stack de recuperação morreu pela SEGUNDA vez; o embedder é o VL, e o empate é o motivo
**Data:** 25/08/2026 · **é o resultado, não a intenção**
**O fato.** Em **25/08/2026 às 09:00Z** a NVIDIA aposentou os dois motores do RAG deste projeto com
HTTP 410. Medido na hora: `pytest` caiu para 39 passed / 1 failed, e dos seis comandos de avaliação
que o `CLAUDE.md` documenta **só `--validar` continuou rodando**, porque é o único que não toca a
API. **Nenhum número publicado saía de comando nenhum.**
**Decisão:** `nvidia/llama-nemotron-embed-vl-1b-v2` com `dimensions=1024`.
**Alternativa descartada:** `nvidia/nemotron-3-embed-1b` a 2048 nativas.
**Motivo — e este é um empate resolvido por regra escrita ANTES de medir:** adotar o `nemotron-3` só
se (a) a margem crosslingual dele batesse a do VL por **≥ 1,5x** e (b) a truncagem local 2048→1024
preservasse a separação, já que ele recusa `dimensions=1024` e a coluna indexada é `vector(1024)`.
- **(a) falhou:** 0,4323 / 0,3801 = **1,14x**, contra o 1,5x exigido.
- **(b) passou:** truncar para 1024 não só preserva como **melhora** a margem. Registro porque é
  contra-intuitivo e porque é a metade da regra que o candidato descartado venceu.

**O `nemotron-3` é melhor nesta sonda e mesmo assim não foi escolhido — isso é o ponto, não um
detalhe.** Ganhar por 1,14x não paga o custo arquitetural: adotá-lo significa preencher
`vector(1024)` por truncagem local, e a coluna indexada passaria a conter um vetor cuja equivalência
com o pedido à API **não é verificável neste modelo**, porque ele recusa o parâmetro. Trocar uma
propriedade medida (D-029) por uma suposição, para ganhar 14%, é o negócio que a regra existia para
recusar.
**Dois controles que reproduziram de sessões anteriores:** o `nemotron-3` deu os mesmos dígitos que
D-014 registrou três dias antes, em outro processo; e `cos(api_1024, trunc_local_1024) = 0,99999996`,
o mesmo valor de D-029 no modelo morto. **D-029 sobrevive intacta.**
**Consequência de schema: nenhuma.** Foi o desempate.
**Reversível?** Média — re-embedar os 381 chunks são ~25 chamadas e é barato; o que não é barato é a
**régua**, que precisa ser re-medida junto.
**A leitura que D-013 não fez, e é o achado desta decisão:** D-013 registrou o mesmo 410 em maio e
concluiu que *o TAPI está desatualizado*. Havia uma segunda conclusão disponível: **o catálogo de
preview aposenta modelos em cadência de meses, e este projeto inteiro está montado nele.** A
mitigação que existia — *"provedor configurável por env var"* — protege a camada que não precisava
de proteção: o LLM é intercambiável, mas trocar o **embedder** invalida os 381 vetores. **A
configurabilidade de `src/config.py` nunca cobriu este caso**, e a linha entrou na tabela de riscos
só depois do segundo EOL.

---

## D-047 — `json_schema` fica, com n=5: a decisão estava certa e o argumento estava errado
**Data:** 25/08/2026 · revisado 28/08 (D-069)
**O que estava aberto.** D-040 escolheu `method="json_schema"` com **uma pergunta e uma execução por
método**, contra um passo que a mesma decisão declara não-determinístico — e a escolha virou
`METODO_ESTRUTURADO` em `src/llm.py`, o portão único dos nove agentes.
**Decisão: `json_schema` fica.** Medido com n=5 na q23: **4/5** contra 0/5 (`function_calling`) e
0/5 (`json_mode`).
**O que muda é o ARGUMENTO, e é por isso que isto é decisão nova e não uma nota.** D-040 afirma que
o método *impede* a alucinação. Não impede: 1 em 5. A defesa passa a ser **"reduz de 3/3 para 1/5 na
pergunta desenhada para induzi-la"** — afirmação sobre frequência, que é a que os números sustentam.
**Consequência para os agentes:** o número que eles herdam é **4/5, não 5/5**. Nenhum agente pode
tratar a saída estruturada como garantida; a checagem de sanidade por código continua obrigatória.
**Reversível?** Fácil — é uma constante em `src/llm.py`.
**Revisto — a diferença que esta decisão mediu DESAPARECEU no modelo novo** (D-069, n=15): 14/15
contra 15/15. **A propriedade era do MODELO, não do método.** `json_schema` permanece por
continuidade e porque `json_mode` continua quebrado — não porque proteja mais.

---

## D-048 — `"token"` sai da lista de cripto, e a exclusão casa por fronteira de palavra
**Data:** 25/08/2026 · revisado 27/08 (D-057)
**O defeito, e ele produzia saída errada em produção.** `EXCLUSOES["cripto"]` continha `"token"` e o
casamento era substring. `SINAIS_TECNICOS` do Extractor inclui `"tokens por segundo"`, então uma
frase sobre custo de inferência virava evidência técnica e disparava *"exclusão por 'cripto'"*.
**Qualquer startup que falasse em "custo por token" era reportada NÃO ELEGÍVEL ao Inception, pelo
motivo errado** — no filtro que o projeto declara como Diferencial.
**O gatilho já estava dentro do repositório e ninguém via:** `tests/test_grafo.py` monta um documento
com *"reduzindo latência e custo por token em produção"*. Aquela startup de teste era reprovada em
toda execução do `pytest` desde a sessão 01, e **o filtro do Diferencial não tinha um único teste**.
**Decisão, em duas partes independentes:** (1) **`"token"` sai** — é ambíguo entre cripto e
inferência de LLM, e o contexto que os separa não cabe numa lista de termos; entram
`"tokenização de ativos"`, `"security token"`, `"nft"`. Medido: o caso de tokenização em blockchain
continua excluído — por `blockchain`. Remover não abriu buraco. (2) **o casamento exige fronteira de
palavra** — a mesma correção que D-039 exigiu no gabarito do RAG, onde `ILIKE '%SLA%'` casava dentro
de "tran(**sla**)tion".
**Alternativa descartada — só a fronteira, mantendo `"token"`:** não resolve, `\btoken\b` casa
"custo por token" igualzinho. A fronteira conserta a *classe* do defeito; o termo ambíguo precisava
sair de qualquer jeito, e confundir as duas coisas deixaria o bug de pé com aparência de consertado.
**Alternativa descartada — janela de coocorrência:** mais poderosa e mais cara de defender, e
desnecessária depois de medir que `blockchain` já pega o caso. Regra que não muda nenhum resultado
medido é complexidade sem preço.
**Escrito em red-green**, e o teste vem **em par** com `test_tokenizacao_em_blockchain_continua_excluindo`
— um teste sozinho aqui é satisfeito pela pior correção possível (apagar a regra de cripto).
**Revisto:** a fronteira estava ancorada dos **dois** lados, o que **desligou o plural**:
`\bconsultoria\b` não casa "consultorias". D-048 trocou um falso positivo visível por um falso
negativo silencioso — a troca ruim. Corrigido em D-057: âncora **só no início**.

---

## D-049 — `Elegibilidade.evidencias` deixa de nascer vazia: a exclusão aponta para o trecho
**Data:** 25/08/2026
**O defeito.** `Elegibilidade.evidencias` nascia `[]` e nunca era preenchida, enquanto
`motivos_exclusao` afirmava *"o termo X aparece nos documentos"* e o Briefing imprimia tudo sob o
rodapé *"Toda conclusão acima aponta para o documento que a sustenta"*. **Era a única conclusão do
sistema sem `list[Evidencia]`**, contra a convenção de D-009.
**A causa era de desenho, não distração:** a função concatenava os trechos numa string só antes de
procurar os termos. Depois do `in`, a informação de *qual* trecho continha o termo já tinha sido
destruída.
**Decisão:** o laço percorre **evidência a evidência**, e o primeiro par (termo, evidência) que casa
produz o motivo **e** anexa a `Evidencia` que o sustenta.
**Alternativa descartada — anexar todas as evidências do perfil:** faria o teste passar e seria
falso. "Evidência que sustenta esta exclusão" e "tudo que a base tem sobre a empresa" são coisas
diferentes; a segunda dá aparência de lastro sem apontar nada.

---

## D-050 — A régua dos agentes: 8 fixtures, e uma só entra se flipar uma decisão que nenhuma outra flipa
**Data:** 25/08/2026
**O problema.** A base tinha 3 startups e as 3 eram `AI-native`. **Um classificador que devolvesse
`"AI-native"` incondicionalmente passava em 3 de 3.** Não existia número capaz de distinguir um
Extractor com LLM do casador de substring. O critério 2 chegou a nível 4 porque teve régua desde o
primeiro dia; os critérios 1 e 3 — **40 pontos** — não tinham nenhuma.
**Critério de seleção, e ele é o argumento:** *uma fixture só entra se flipar pelo menos uma decisão
que nenhuma fixture existente flipa.* Sob essa regra, 3 + **5 novas = 8**: RD Station (`AI-enabled`,
copilot puro) · SunnyHUB (`non-AI`, zero termo técnico) · Freedom AI (**mirage PMF** — alega "LLM
própria" sem uma linha que sustente) · Deal (`elegivel: false` por consultoria, o caso que
`contexto/03` §2 pede por escrito) · Maritaca AI (`maturidade alta` → quadrante `ja-otimizada`, que
existia só no papel).
**Ficaram FORA de propósito, e o corte é decisão:** exclusão por idade (é `if` aritmético sobre campo
estruturado — virou teste unitário) e as regras 2 e 4 do Evidence Validator (já têm teste unitário, e
uma fixture "documento de um tipo só" **violaria a validação do próprio `seed.py`** — criar fixture
que quebra o validador para exercitar o validador é dívida, não cobertura).
**Regra de curadoria, porque estas fixtures rotulam empresas reais.** Toda `url_fonte` é real e
resolve. O rótulo é afirmação sobre **o que a base pública prova**, não sobre a empresa.

---

## D-051 — O gabarito mora na fixture, e "não decide" é resultado com coluna própria
**Data:** 25/08/2026
**Onde mora:** bloco `gabarito:` em `data/seed/*.yaml`, ao lado do `perfil_alvo`.
**Alternativa descartada:** arquivo separado espelhando o gabarito do RAG. Perdeu porque o `seed.py`
já garante que este material **não vai para o banco** (se fosse, o Classifier enxergaria a resposta),
e uma empresa nova passaria a exigir edição em dois arquivos, com risco de dessincronia por nome.
**Cada campo aceita três formas, e a terceira é a que faltava:** valor → **decide**; lista →
**ambíguo** (bater um não é acerto limpo); `null` → **não medido** (sai do denominador). A saída
publica sempre `acertos / decididos (+A ambíguos, +N não medidos)`.
**O que se conta, e cada linha é uma decisão:**
- **elegibilidade** exige o bool **e o RÓTULO do motivo** — recusar pelo motivo errado é erro
  nomeado, não acerto. É o defeito que D-048 pagou.
- **dor — precisão é a manchete**, porque o modo de falha do stub é emitir demais. O recall é
  secundário: um extrator que emite as 8 dores faz 100% por construção.
- **dor proibida** é falha **nomeada**, com startup e dor. "Errou 0,3" não é acionável.
- **evidência literal**: todo `trecho` ocorre **verbatim** no documento citado. Zero API.
- **quadrante não é contado** — é função pura já testada, e contá-lo inflaria o número contando os
  dois eixos duas vezes.
**A linha de base trivial é obrigatória na tabela** (`--baseline`): sempre `AI-native`, stack
`baixa`, todas as 8 dores, sempre elegível. É o `denso puro` deste critério, e **nenhum número de
agente vai para a documentação sem ela ao lado**.
**`--validar` já se pagou antes de medir qualquer coisa:** apontou que o gabarito da Freedom não dava
veredito para `latencia`. A regra "toda dor precisa de veredito explícito, inclusive 'ambígua'"
existe para que omissão não vire silenciosamente um zero.

---

## D-052 — O que a régua mediu no primeiro dia: três achados, e um corrigiu o diagnóstico do projeto
**Data:** 25/08/2026 · revisado 27/08 (D-057) · zero chamada de API
**Achado 1 — o stub é PIOR que o classificador trivial no rótulo do TAPI.** É o número que justifica
a sessão inteira, e não era observável com 3 fixtures todas AI-native. Com a régua corrigida por
D-057, **o casador perde em quatro dos cinco campos** e só ganha em dor (precisão 49% × 32%,
discriminação 8/8 × 1/8). **O valor dele está inteiro na EXTRAÇÃO; a camada de classificação em cima
é pior que constante.**
**Achado 2 — a discriminação REFUTA metade do diagnóstico do próprio projeto.** A documentação
afirmava que o Extractor *"produz o mesmo conjunto de dores para toda startup"*. Sobre 8 fixtures
diversas, ele produz **8 conjuntos distintos de 8**. A afirmação era verdadeira sobre a base que
existia — 3 startups, todas de saúde — e generalizava um artefato da amostra. O que **sobrevive** é o
outro lado: a precisão é de 49%, e são as dores ERRADAS que poluem a consulta, não a falta de
variação. É a segunda vez no projeto que ampliar a amostra derruba uma conclusão tirada com n
pequeno; a primeira foi D-039.
**Achado 3 — o filtro do Inception exclui por MENÇÃO, não por identidade, e derruba o prospect
prioritário.** **Axenya** é recusada por *"Integramos **consultoria**, dados e operação clínica"* —
ela **usa** consultoria, não **é** uma consultoria. **Freedom AI** é recusada porque um **parceiro**
é *"auditoria, **consultoria** e tributos"* — a palavra não se refere à startup. **Deal** é recusada
corretamente: *"A Deal **é a consultoria** de IA"*.
**Fronteira de palavra NÃO resolve este caso**, e é isso que o separa de D-048: lá o termo era
ambíguo entre domínios; aqui o termo é o certo e o **sujeito** é outro.
**Decisão: não consertar com heurística nova, e o motivo não é preguiça.** Um padrão de identidade
(`"é uma consultoria"` casa, `"integramos consultoria"` não) resolveria os três casos medidos e
introduziria um risco pior — **falso negativo silencioso**: se a frase que afirma a identidade não
estiver entre as evidências recortadas, a Deal deixa de ser excluída e o Diferencial para de
funcionar sem ninguém notar. **Falso positivo aparece no briefing; falso negativo não aparece em
lugar nenhum.**
**Achado 4, da mesma família de D-048 — substring no Extractor.** `'rag'` casa dentro de "co(rag)em";
`'sla'` casa dentro de "legi(sla)ção" — literalmente o erro que D-039 achou no gabarito do RAG.
**ABERTO em 31/08:** o achado 3 nunca foi pago. É julgamento de sujeito, que é exatamente o que o
juiz do Extractor faz — e D-072 mostra que ele passou a funcionar no modelo novo.

---

## D-053 — Extractor: heurística gera CANDIDATO, LLM julga — e o teto do casador é 100%
**Data:** 25/08/2026 · portão escrito ANTES de medir
**Três desenhos avaliados:**
**A — uma chamada por startup, schema largo (`PerfilStartup` inteiro). DESCARTADA.** Viola D-045:
seis campos heterogêneos num schema só diluem a instrução. O motivo real, porém, é a citação: pedir
ao modelo o `trecho` **junto com** a conclusão convida paráfrase, e todo o projeto repousa em
`Evidencia.trecho` ser literal.
**B — fan-out interno, uma chamada por dimensão, schema estreito.** Cumpre D-045; custa 32 chamadas
por medição. Fica como plano B, promovível por medida.
**C — candidato por heurística, julgamento por LLM. ESCOLHIDA.** `SINAIS_*` e `GATILHOS_DOR`
continuam existindo, **rebaixados de decisor a gerador de candidatos**. O LLM recebe só as frases
candidatas — nunca as páginas — e decide se a frase sustenta a dor. Quatro razões:
1. **É impossível o LLM inventar citação.** `Evidencia.trecho` continua vindo do recorte por `str`.
   Mesma disciplina de `indices_citados` em D-040 — o modelo devolve referência, não fonte.
2. **Contexto pequeno por chamada.**
3. **Ataca a métrica que está quebrada** — a régua mediu precisão 49% e recall 100%: o problema é
   emitir demais. C aumenta precisão sem mexer no recall.
4. **Degrada com graça** — com a API fora do ar, volta ao comportamento de hoje em vez de parar.
**O custo honesto de C foi MEDIDO, e ele não existe.** A objeção legítima é que o recall fica preso
ao vocabulário de `contexto/02` §5. `--validar` mede esse teto sem gastar chamada: **12/12 = 100%**
das dores esperadas têm candidato. Não há recall a comprar ampliando gatilhos.
**Alternativas descartadas, com a resposta pronta para banca:**

| pergunta | resposta |
|---|---|
| *"Por que não fine-tuning?"* | 8 fixtures rotuladas é few-shot, não treino. E o TAPI pede sistema multi-agente, não modelo treinado |
| *"Por que não NER/spaCy para a stack?"* | O que falta não é entidade, é julgamento sobre a entidade: *"usamos GPT-4"* e *"self-hospedamos um modelo em GPU"* têm as mesmas entidades e significados opostos |
| *"Por que não um modelo maior?"* | Medir com o que está configurado na régua primeiro. Modelo de preview carrega a mesma classe de risco de EOL que já matou a stack três vezes |
| *"Por que não o LLM lendo os 3 documentos inteiros?"* | Contexto, mais paráfrase de citação. D-034 mediu julgamento caindo com passagem longa |

---

## D-054 — A dívida do Extractor vem antes do filtro de chunk, e a ordem sai do CUSTO DA RÉGUA
**Data:** 25/08/2026
**Decisão:** atacar o **Extractor** antes do filtro de recomendabilidade no chunk.
**Motivo, e o primeiro é o que vale na banca:**
1. **A ordem é decidida pelo custo da RÉGUA, não pela força da hipótese.** O filtro de chunk exigiria
   um gabarito de *recomendação* — para 8 startups × N dores, qual das 16 tecnologias é a certa —,
   que não existe e é curadoria de especialista. O Extractor tem régua barata: quem lê o documento
   anota `dores_esperadas` e `dores_proibidas` em minutos.
2. **O argumento causal é assimétrico.** O filtro de chunk age DEPOIS da consulta: consulta genérica
   com filtro remove os chunks de navegação e devolve outros chunks genéricos — melhora a aparência
   sem tocar a causa. O contrário vale: consulta específica melhora tudo que vem depois, **inclusive**
   a taxa de chunk de navegação no topo.
3. O recuperador faz r@1 de 95% quando a consulta é boa. O suspeito não é ele.

---

## D-055 — O critério de empate do Extractor, fixado ANTES da medição
**Data:** 25/08/2026 · escrito antes de rodar
**Empate** = o Extractor com LLM, contra a linha de base de D-052: não bate a **precisão de dor**
(49%) por margem ≥ **0,15**, **e** não leva a **discriminação** a ≥ **6 conjuntos distintos de 8**.
Como o casador já faz 8/8, esse braço está satisfeito por construção — **a decisão fica inteira na
precisão**, o que é consequência do achado 2 de D-052, não uma facilidade concedida.
**Se empatar:** o juiz **não entra em produção**. A frase de defesa é a mesma que D-046 escreveu
sobre o `nemotron-3-embed`: *"medi que o LLM não bate o casador de substring nesta base, com este
modelo; o gargalo é outro"*.
**Motivo de existir:** é a única razão pela qual a conclusão sobre o juiz é defensável. **A margem
existia antes do número** — sem ela, 58% teria virado "melhorou" e o juiz teria entrado.
**A lacuna, registrada duas vezes depois (D-060, D-072):** D-055 **nunca fixou guarda de recall**.
Fixar a margem sem calcular todos os lados é fixar um número, não um critério.

---

## D-056 — O juiz do Extractor EMPATOU no 8b e não entrou em produção
**Data:** 25/08/2026 · **reaberto e reprovado o veredito em D-072**
**Decisão à época: `USAR_JUIZ_LLM = False`.** Medido em três execuções, a precisão de dor ficou em
**50-62%** contra o alvo de **64%** fixado em D-055 — nem o melhor caso alcançava.
**O juiz é reportado em FAIXA, com três execuções, e isso não é excesso de zelo:** é a regra que a
M2 aprendeu — *número de geração se reporta em três execuções ou não se reporta*. A primeira redação
desta decisão publicou 58% como se fosse **o** número, com n=1, no mesmo projeto que criou D-039 para
resolver exatamente isso do outro lado.
**O que a medição comprou mesmo empatando:** a opção C ficou validada como **desenho** — o teto de
recall do casador é 100%, a evidência continua literal em 100% dos trechos. **E o gargalo mudou de
lugar e ganhou nome:** depois do juiz, `confianca` continuava 0/6 e `classe` 3/7 — ou seja, **o
problema não estava mais no Extractor**.
**O ACHADO TÉCNICO, e ele vale mais que o número: enumerar modos de falha no prompt ensinou o modelo
a recitá-los.** A primeira instrução listava os três erros da busca por palavra-chave e fechava com
*"na dúvida, reprove"*. Resultado: precisão **22%**, e cinco das oito startups viraram `non-AI`.
Duas amostras diagnosticaram:
- **Maritaca** — o modelo escreveu que a frase *"pode ser interpretado como preocupação com
  otimização de inferência"* e concluiu, **na mesma resposta**, que *"não há nenhuma frase que
  sustente"*. O raciocínio contradiz a conclusão.
- **Doutor-AI** — o motivo devolvido foi, palavra por palavra, a **regra nº 2 do próprio prompt**.
  Ele não aplicou a regra — copiou.
**Um ajuste, declarado como único e aceito qualquer que fosse o resultado:** critério POSITIVO
primeiro, o viés *"na dúvida, reprove"* removido, e a exigência de que o motivo CITE a frase julgada.
Precisão foi de 22% para 58%.
**A lição, num modelo pequeno:** uma lista de erros a evitar funciona como um menu de desculpas
prontas. **O prompt precisa dizer o que APROVAR**; o que reprovar vem depois e curto.
**Alternativa não exercida:** ajustar o prompt uma terceira e quarta vez até passar de 64%. Isso não
é medir, é ajustar ao gabarito. **Um ajuste, com o diagnóstico escrito antes, é correção; três é
sobreajuste com outro nome.**
**Nota do casador, que ficou:** o desempate copilot/autopilot passou de `>=` para `>`. Empate não é
evidência de autopilot; é ausência de evidência.
**Revisto:** o veredito era sobre um modelo de **8B que morreu dois dias depois**. Mesmo código,
mesmo prompt, modelo novo: **83-96%** de precisão, e o modo de falha da recitação **não reapareceu**
(D-072).

---

## D-057 — O code review derrubou três afirmações da sessão, e uma era a régua medindo errado
**Data:** 25/08/2026 · `/code-review` · 8 achados, 6 pagos
**Achado 1 — a fronteira de palavra de D-048 estava ancorada dos DOIS lados, e isso desligou o
plural.** `\bconsultoria\b` **não casa** "consultorias" — a forma comum em texto institucional. D-048
trocou um falso positivo visível por um **falso negativo silencioso**, que é a troca ruim, e o
comentário afirmava o contrário. **Correção: âncora só no início.** Dois testes, um por lado.
**Achado 3 — a justificativa do desempate copilot/autopilot citava uma medição que não existe.** Eu
li a lista de TERMOS distintos que casaram como se fosse a contagem de EVIDÊNCIAS. Medido depois:
`>=` e `>` dão **o mesmo placar**. A mudança fica, por argumento **conceitual** e declarado como tal
— dizer que compra métrica seria inventar um ganho no arquivo que existe para defender decisões.
**Achado 6 — a régua estava medindo `motivo_exclusao` errado, e o número publicado era enganoso.**
`motivo_exclusao: null` era tratado como "não medido" mesmo quando o gabarito dizia `elegivel: true`
— ou seja, quando o motivo esperado é **nenhum**. Consequência: Axenya e Freedom, recusadas pelo
rótulo errado, apareciam numa coluna limpa de 1/1. **E isso muda a leitura da sessão:** com a régua
corrigida, o casador perde do trivial em **quatro dos cinco campos**. É uma afirmação mais forte e
mais útil que a anterior, e **só apareceu porque a régua foi auditada**.
**Achado 5 — D-049 guardava a evidência da exclusão e o briefing não a imprimia**, sob o rodapé
"toda conclusão aponta para o documento que a sustenta" — o defeito que D-049 existia para fechar,
sobrevivendo na única saída que o sistema produz.
**Achado 7 — precisão indefinida contada como zero.** "Não previu" não é "previu tudo errado", e o
recall já pune esse caso.
**Achado 8 — `--validar` prometia "ZERO API" e não cumpria com `--juiz`.** Pior que o custo: com o
juiz ligado, o número medido deixa de ser o **teto do casador** e vira o recall do juiz — outra
grandeza com o mesmo nome.

---

# Sessão 07-08 — o terceiro EOL, as duas reprovações, e a stack de volta

## D-058 — O critério de sucesso do Classifier e do Evidence Validator, fixado ANTES do código
**Data:** 27/08/2026 · escrito antes de a primeira linha ser alterada
**Por que existe por escrito:** **o alvo aqui não é "melhorou"** — nos dois campos o sistema perde do
classificador trivial, então "melhorou" pode significar continuar perdendo.
**Os alvos:** `classe` **≥ 5/7** *e* nenhuma perda entre Deal, RD Station e SunnyHUB · `confianca`
**≥ 4 acertos absolutos** *e* taxa sobre decididos ≥ 50%.
**Por que duas condições em cada um, e não uma taxa:**
- Em `classe`, porque os 4 erros são **unidirecionais** (todos `AI-native` saindo `AI-enabled`). Uma
  regra mais frouxa compra `AI-native` barato e o preço aparece na SunnyHUB — emitir `AI-native` para
  uma empresa de painel solar é *"o falso positivo mais caro que este projeto pode cometer numa
  demonstração"*. Subir de 3 para 5 perdendo a SunnyHUB seria vitória na tabela e derrota na demo.
- Em `confianca`, porque **a taxa é gamificável pelo denominador**: responder dentro de um conjunto
  ambíguo tira a fixture do denominador sem acertar nada. É o que o casador faz para chegar a 0/**6**
  enquanto o trivial é medido sobre **8**. Exigir acertos absolutos fecha essa porta.
**As guardas — não são alvo, são veto:** `maturidade ≥ 6/7` · `dor precisão ≥ 49%` · `recall = 100%`
· `discriminação 8/8` · `elegivel ≥ 5/7` · `motivo_exclusao ≥ 5/7` · `pytest` verde. **Se qualquer
guarda cair, a mudança sai — mesmo que o campo-alvo tenha passado.** É a lição de D-048.
**O que fazer se empatar:** (1) os dois campos são julgados **independentemente** — julgar em bloco
deixaria um campo carregar o outro; (2) empate ou derrota, a mudança **não entra**; (3) **um ajuste
só**, declarado como único antes de rodar; (4) **o gabarito não muda para o sistema passar** — um
valor só pode ser alterado com argumento escrito a partir de `contexto/02`, **nunca a partir do
resultado medido**. *Auditar é legítimo; auditar depois de ver o placar não é.*
**A linha de controle, e por que ela existe:** **a mesma aritmética com o limiar em 3** — a correção
de um caractere. Medida **antes** de a aritmética ser substituída. Se a rubrica em degraus não bater
o limiar-3, ela não paga a complexidade que introduz. É o papel de `--truncar-pool` em D-037.
**A ordem de medição tem três passos, e o motivo é atribuição:** o desenho de `confianca` lê
`diagnostico.evidencias`, que o Classifier preenche. Mexer no Classifier move `confianca` junto — e
uma medição em que as duas mudanças entram ao mesmo tempo não consegue dizer de quem é o delta.

---

## D-059 — A confiança do diagnóstico sai da evidência DO DIAGNÓSTICO — e mesmo assim perde do trivial
**Data:** 27/08/2026 · alvo fixado em D-058 · **REPROVADA, fica atrás de flag**
**O defeito:** `diagnostico.confianca` era `min()` sobre `perfil.afirmacoes`, e essa property inclui
TODAS as `dores_observadas`. Com 7 dores na Axenya, sempre existe um elo fraco: `alta` era
**estruturalmente inalcançável** e o campo saía `baixa` para as oito fixtures. **Não era impreciso,
era constante.** E a consequência ia na direção errada: **um Extractor que achasse MAIS dores reais
BAIXAVA a confiança do diagnóstico** — a métrica de um agente se movendo contra a melhoria de outro.
**A correção:** aplicar `avaliar()` sobre uma `Afirmacao` sintética montada com
`diagnostico.evidencias`. O argumento é da **rubrica**, não do gabarito: a regra 2 fala de
corroboração entre TIPOS de documento *da conclusão*, e a regra 5 fala do *output* carregar a
confiança. O `min()` sobre o perfil inteiro era uma terceira coisa, herdada do stub, que ninguém
decidiu.
**O resultado, contra o alvo de ≥ 4 acertos absolutos:** trivial **3/8**, produção 0/6, com a
correção **2/6**. **O defeito estrutural sumiu** — `alta` volta a ser alcançável e o campo deixa de
ser constante — **e mesmo assim perde de responder "alta" para todo mundo.** Não entra:
`CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO = False`, ligável por `--confianca-diagnostico`.
**O achado vale mais que o número: o gargalo mudou de lugar, e não é mais o validator.** Quatro dos
seis erros são casos em que o diagnóstico se apoia em **um documento só, ou em nenhum** — a SunnyHUB
não tem evidência anexada porque nenhum sinal disparou. **O validator está relatando fielmente a
espessura da evidência que o Classifier produziu.** Melhorar isso é fazer o Classifier anexar
evidência mais larga, e isso é trabalho do Extractor, que recorta uma frase por documento.
**Alternativas descartadas:**
- **`min()` sobre um subconjunto nomeado** — continua sendo `min()` sobre conjunto de tamanho
  variável, então preserva a monotonicidade perversa em escala menor; e duplicaria "o que sustenta o
  diagnóstico" em dois lugares. Duas fontes da mesma verdade divergem.
- **Média ponderada** — inventa uma escala numérica que a rubrica não tem, esconde o caso "uma
  afirmação forte e cinco fracas", e deixa de ser explicável em uma frase: `avaliar()` devolve um
  motivo citável, uma média não devolve nada.
- **Tirar `dores_observadas` da property `afirmacoes`** — parece a correção óbvia e quebraria o
  sistema **em silêncio**: `afirmacoes` é o que o validator varre para ANOTAR cada dor, e o
  Recommendation filtra por `d.validada`. **A property tem dois consumidores com necessidades
  diferentes; a correção é separar os consumidores, não mutilar a property.**

---

## D-060 — A rubrica em degraus empata com um caractere, e o teto que faltava explica por quê
**Data:** 27/08/2026 · alvo fixado em D-058 · **REPROVADA, fica atrás de flag**
**O defeito:** o eixo 1 era `pontos = 2·autopilot + 2·dado_proprietário + 1·técnica`, com `>= 4` para
`AI-native`. Os pesos 2/2/1 **não vinham da rubrica** — `contexto/02` §4 lista os sinais como um
conjunto, sem hierarquia — e o limiar exigia na prática autopilot **E** dado proprietário, porque
profundidade técnica sozinha valia 1. Por isso a Maritaca (quantização QAT, MoE, MFU em B200) saía
`AI-enabled`.
**O que foi medido — três degraus declarados, sem aritmética:** (1) nenhum sinal de IA no caminho
crítico → `non-AI`; (2) a empresa OPERA a própria IA, bastando **um** de profundidade técnica ≥ 3
marcadores **ou** autopilot + dado proprietário → `AI-native`; (3) resto → `AI-enabled`. O `2b` é
exatamente o que a aritmética já deixava passar, então a mudança é aditiva e **zero grau de liberdade
foi introduzido** — nada para calibrar contra o gabarito.
**O resultado:** trivial 4/7 · **controle `pontos >= 3`: 4/7** · produção 3/7 · **rubrica: 4/7**.
Recupera a Maritaca, não perde nenhuma das três guardadas, e **empata com o trivial E com a linha de
controle**, que é a mesma aritmética com um caractere trocado. Não entra: `RUBRICA_EM_DEGRAUS = False`.
**O erro desta sessão não foi a rubrica, foi a barra ter sido fixada sem o teto.** O harness tinha
`teto_do_casador` para dores desde D-053 e **nenhum teto equivalente para `classe`**. Calculado
depois: **sete das oito fixtures têm profundidade ZERO**, então o degrau `2a` nunca poderia mover
mais de uma fixture, e o máximo alcançável era **4/7 — exatamente o placar do trivial**. **O alvo de
5/7 era inalcançável por construção, e isso era calculável antes de medir.**
**A lição:** D-055 ensinou a fixar a margem antes de medir; esta sessão aprendeu que **fixar a margem
sem calcular o teto é fixar um número, não um critério**. `teto_do_degrau_2a` entrou no harness.
**E o teto diz para onde ir:** o gargalo de `classe` não está na regra de decisão, está no
**vocabulário** — três das quatro fixtures `AI-native` não têm um único marcador de infraestrutura.
Ou os documentos coletados não contêm o sinal (trabalho de curadoria, M3), ou a lista `PROFUNDOS` não
cobre como uma healthtech descreve a própria stack (trabalho de rubrica). **Nenhuma se resolve
mexendo no limiar.**
**Duas coisas ficam em produção, porque nenhuma é métrica:** `profundidade_tecnica()` usado pelos dois
eixos (o número passou a existir uma vez só — mexer nele para consertar a classe mexeria na
maturidade no mesmo movimento, o que torna a calibração **visível** em vez de silenciosa); e
`extractor.frases` pública, para que o Classifier use o MESMO recorte — duas regexes criariam duas
definições de "trecho literal", e `--validar` só verifica enquanto houver uma.
**Nota de método: uma medição foi contaminada por bytecode obsoleto.** A troca de `>= 4` por `>= 3`
**preserva o tamanho do arquivo**, e o `git checkout` devolveu um mtime que o `.pyc` já tinha
registrado — o Python serviu bytecode do limiar-3 com o fonte dizendo 4. Só foi pego porque o número
se mexeu onde era estruturalmente impossível. **Toda medição passou a ser precedida de limpeza do
`__pycache__`.**

---

## D-061 — A régua de exclusão entra, a correção NÃO — e a régua achou um falso negativo em produção
**Data:** 27/08/2026 · `data/avaliacao/exclusoes.yaml` + `--exclusoes`
**O entregável é a régua, não a correção.** D-052 adiou a correção do filtro por assimetria de risco,
e a decisão estava certa e era **argumentada, não medida** — a base tinha UMA fixture exercitando o
lado positivo, o que é anedota. Agora são 14 casos em **pares mínimos**: mesmo termo, sujeito
diferente. 5 vêm de fixture, 1 é derivado de teste, **8 são sintéticos e estão declarados como tais**
— passar sintético por real seria a desonestidade que D-021 barrou no seed.
**Os dois números nunca são somados.** Um filtro que exclui tudo tem zero falso negativo; um que não
exclui nada tem zero falso positivo. Uma acurácia única premiaria os dois e esconderia a assimetria
que motivou o arquivo.
**O que a régua achou na PRIMEIRA execução, e ninguém sabia:** *"Somos revendedores autorizados"*
**passa pelo filtro do Inception**. `"revenda"` não é prefixo de `"revendedores"`. E o comentário do
código afirmava o contrário. É a mesma classe do achado 1 de D-057 — comentário descrevendo
comportamento que o código não tem — e **sobreviveu à auditoria que D-057 fez de D-048**, porque não
havia régua que exercitasse `revenda`. **É a terceira vez neste projeto que ampliar o instrumento
derruba uma afirmação escrita** (D-039, D-052, agora esta).
**A correção de corpus foi medida e NÃO entra, apesar de fazer 7/7 nas fixtures.** Restringir
`elegibilidade()` a `descricao_curta` conserta Axenya e Freedom — e deixa a régua de casamento
**idêntica à produção**. Ele não resolve discriminação de sujeito: **ele evita as frases onde o
problema acontece.** O 7/7 é comprado lendo um campo de uma linha, curado à mão: `descricao_curta` é
opcional por tipo (empresa sem o campo nunca seria excluída, por nada) e **não é texto coletado, é
redação de curadoria** — a correção do Diferencial passaria a ser propriedade da minha curadoria, não
do sistema, e a régua estaria medindo a curadoria. **Que 7/7 nas fixtures não baste é o ponto — foi
para isso que a segunda régua existe.**
**Nota sobre o critério, e é um defeito de método:** o critério dizia *"zero falso negativo NOVO"* e,
entre parênteses, *"nenhum caso do lado exclui pode passar"*. As duas leituras divergem, porque foi
escrito sem saber que **já existia** um falso negativo em produção. **Um critério fixado antes de
conhecer a linha de base pode ser ambíguo justamente onde importa.**

---

## D-062 — A M3 fecha em 30 empresas, em duas camadas, e a coleta é sessão própria
**Data:** 27/08/2026
**A decisão é 30** — o piso do TAPI. Hoje são 8.
**O argumento começa admitindo o que joga contra:** o barema **não tem linha para tamanho de base**.
Pela lógica de "a sessão marginal rende onde há pontos", 22 empresas a mais compram zero. O que
decide contra isso é que **`30 a 50` está escrito no requisito**, e o barema pontua "nível 2 = cumpre
o mínimo". Ficar visivelmente abaixo de um número escrito no TAPI é perda **não recuperável** em dois
critérios (1 e 7), e não é recuperável por qualidade: nenhuma explicação no README transforma 8 em
"cumpriu a M3".
**A estrutura é em duas camadas, e é ela que faz a hora pagar duas vezes:** **8 com bloco
`gabarito:`** (as atuais — são a régua dos critérios 1 e 3, e **só elas movem número**; gabarito é
curadoria cara e o valor marginal da nona fixture rotulada é menor que o da primeira) · **22 como
dado**, sem gabarito · **3-4 das 22 escolhidas adversarialmente** (uma consultoria de IA real, uma
revenda, uma non-AI), que viram caso real da régua de D-061, hoje coberta só por frase sintética. É a
única parte da coleta que compra ponto de critério, e sai de graça.
**Timebox de 3h, com piso declarado em 20.** Se estourar, para onde estiver e o número entra no README
com o argumento — a regra 5 do `plano.md`: *"corte o número de empresas, não o rigor"*.
**Alternativas descartadas:** 25 e 20 — as duas economizam 1-2h e as duas exigem justificar no README
por que o requisito não foi cumprido. **O texto de justificativa carrega mais risco que as 2h que ele
economiza**, num critério que vale 10 pontos e é lido por quem também leu o TAPI.
**Revisto (D-078):** o argumento acima é de perda de nota, e ele não se sustenta mais. **A decisão
continua sendo 30, por uma razão melhor:** 8 fixtures **não discriminam**. A régua satura, e o
gargalo de vocabulário do Classifier (P-12) é insolúvel nesse tamanho porque não há variedade
linguística suficiente para separar os casos — D-060 já mostrou que o gargalo não é a regra de
decisão. O piso de 30 deixa de ser obediência ao requisito e vira o tamanho mínimo em que a
medição significa alguma coisa.

---

## D-063 — `dores_enderecadas` deixa de ser tautológico: duas perguntas, duas listas
**Data:** 27/08/2026 · revisado 27/08 (D-066)
**O defeito:** o filtro era `any(c.tecnologia == citacao.tecnologia for c in citacoes)` — e como
`citacao` **pertence** a `citacoes`, a condição é sempre verdadeira. `dores_enderecadas` listava
**todas** as dores validadas em toda recomendação, sugerindo no briefing que cada tecnologia endereça
tudo.
**Por que a correção de uma linha não servia:** `evidencias` derivava da MESMA lista. Estreitar as
duas juntas faria recomendação cuja dor de origem não passou pelo validator **sumir** — mudando
quantas recomendações o sistema emite, que é comportamento medido por teste.
**O que entrou é a separação:** *"de quais dores tiro EVIDÊNCIA"* e *"quais dores DECLARO
endereçadas"* são perguntas diferentes e agora são listas diferentes. O lastro continua largo —
nenhuma recomendação some — e a declaração passa a ser só a dor que puxou aquela citação, que é o que
`CitacaoRAG.dor_origem` sabe desde D-043.
**Revisto (D-066):** a correção **tornou possível uma divergência que antes não existia** — uma
recomendação que declara uma dor e cita a evidência de outra, sob o rodapé de rastreabilidade.
Corrigido com `lastro = dores or validadas`. **A lição:** D-063 foi a única mudança de comportamento
daquela sessão que entrou **sem flag, sem teste e sem braço de harness**, enquanto a mesma sessão
exigia critério fixado antes do código para tudo o mais.

---

## D-064 — TERCEIRO EOL, em 27/08: o LLM e o reranker morreram
**Data:** 27/08/2026 · descoberto pelo `pytest` · **13 dias da entrega, 11 do vídeo**
**O fato:** `meta/llama-3.1-8b-instruct` devolveu **410** e `nvidia/rerank-qa-mistral-4b` devolveu
**404** — o LLM dos agentes e o último reranker do catálogo. Terceira morte em três meses, **dois
dias** depois da anterior.
**A notícia boa, e ela é grande:** o **embedder sobreviveu**. Era o único cuja morte invalidaria os
381 vetores e exigiria re-embedar mais re-medir a régua inteira. **O corpus ficou intacto.**
**O tamanho honesto do estrago, critério a critério:**
- **Critério 2 (RAG, 20 pts):** o motor de produção não roda sem reranker. **A linha de base
  sobrevive** — o denso puro faz 95% r@1 e 100% r@3 sozinho; o que o reranking comprava era o
  critério estrito. O sistema continua respondendo; perde a camada que o levava ao teto.
- **Critérios 1 e 3 (agentes, 40 pts): quase intactos.** Os agentes são determinísticos e o juiz
  estava desligado. `pytest`: 48 passed, 1 failed — a única falha era o 404 no rerank.
- **O que perde valor de prova:** toda medição de geração — abstenção, `json_schema`, o juiz. Foram
  produzidas por um modelo que não existe mais. **Trocar o LLM não as conserta: invalida.**
**Decisão deixada EM ABERTO de propósito**, com as opções e o custo de cada uma. Fechada em D-067
(LLM) e D-068 (rerank).
**O que este episódio já provou, e vale para a banca:** **a arquitetura aguentou.** Provedor isolado
em `src/config.py`, nenhum agente conhecendo a NVIDIA, e um smoke test que nomeia a capacidade morta
em 30 segundos. Três EOLs e o custo de cada um foi **medido em horas, não em dias**.
**Revisto:** esta decisão recomendou um substituto **por nome**, com base em ele aparecer em
`GET /v1/models`. **Ele devolve 404** (D-067) — o mesmo erro de método que D-065 nomeou dois dias
antes, cometido dentro da própria correção.

---

## D-065 — "Cohere é pago" era falso, e as duas alternativas ao fornecedor único caíram por narrativa
**Data:** 27/08/2026 · corrige D-015 · levantado por questionamento do Vinícius
D-015 descartou o Cohere Rerank em 22/08 com duas razões: *"é pago"* e *"quebraria a narrativa de
rodar tudo na stack NVIDIA"*. **A primeira é falsa, e era verificável naquele dia:** a trial key
gratuita cobre Command, Embed e **Rerank 3.5**, com 1.000 chamadas/mês e 10 req/min no Rerank, vedada
a uso comercial — e processo seletivo não é uso comercial.
**O que isso revela é maior que o erro de fato.** Na mesma decisão, o cross-encoder local foi
descartado por *"perde o argumento do Diferencial"* — motivo explicitamente narrativo. Com esta
correção, a leitura certa é mais dura: **as DUAS alternativas ao fornecedor único foram descartadas
por narrativa, e uma delas com um fato falso por cima.** Não foi uma linha ruim no log, foi um
padrão. E o resultado está medido: em 25/08 o projeto ficou sem contingência, e em 27/08 sem reranker.
**Erro de método, nomeado:** D-015 tratou "é pago" como fato assumido e não o verificou, **enquanto o
mesmo dia media margem de reranker com quatro casas decimais**. O rigor foi aplicado à escolha
técnica e não à **premissa que eliminou as alternativas** — e é a premissa que decide o espaço de
opções.
**Os limites da trial batem em coisas concretas, e isso é planejamento, não objeção:** 1.000
chamadas/mês (uma avaliação completa do RAG gasta ~67; a disciplina de n=3 come ~200 numa tacada) ·
**10 req/min no Rerank**, que num run do grafo vira minutos de throttle e **decide o roteiro do
vídeo** · e o avaliador precisa de chave própria — melhor que a NVIDIA (chave grátis sai na hora,
modelo aposentado não volta com chave nenhuma), mas ainda é dependência externa, e o eliminatório
nº 3 é sobre executar.

---

## D-066 — O code review derrubou uma correção da sessão e achou código morto
**Data:** 27/08/2026 · `/code-review` · 15 achados · 11 pagos
**1. D-063 quebrou a rastreabilidade que existe para proteger** — ver D-063.
**2. `motivo_confianca` era código morto na configuração que roda.** D-059 afirmou que o campo *"fica
em produção, porque não é métrica"*. **Ele só era preenchido dentro do braço da flag**, que é `False`
por default: o campo novo em `state.py` e a linha nova do briefing **nunca executavam**. A afirmação
era falsa no momento em que foi escrita. Corrigido: o braço de produção também preenche o motivo, o
que torna o defeito de D-059 **visível na saída** em vez de só documentado.
**3. O raio de regressão do Classifier estava mal declarado.** O docstring afirmava que o degrau 1
mantinha a semântica de `pontos == 0`. **Não mantém** — uma startup com 1 ou 2 marcadores de
infraestrutura e nenhum outro sinal era `non-AI` e passa a `AI-enabled`, saindo de `fora-do-funil` e
fazendo o `nvidia_rag` gastar API. **Nenhuma das 8 fixtures cai nesse caso, e é por o placar NÃO
medir isso que precisava estar escrito.**
**4. A régua de exclusão media pela metade o lado que criou para medir.** `exclui: true` checava só
que o rótulo esperado disparou — nunca que **nenhum rótulo errado** também disparou. É exatamente o
defeito que D-048 pagou, **sobrevivendo dentro da régua escrita para pegá-lo**.
**5. Instrução contaminada, no arquivo carregado em toda sessão.** A tabela de Stack do `CLAUDE.md`
ainda apresentava os dois modelos mortos como vigentes, **vinte linhas acima do aviso "nunca usar
esses seis nomes" adicionado pela mesma sessão.** Este é o modo de falha recorrente do projeto e
reapareceu depois — ver D-073.
**Registrados e NÃO pagos, com o motivo:** a dedup do `nvidia_rag` faz `dores_enderecadas`
**sub**-declarar (uma página recuperada por duas dores guarda só a primeira `dor_origem`) — D-063
trocou uma super-declaração por uma sub-declaração, e pagar exige `dor_origem` virar lista, o que
muda o contrato de `CitacaoRAG`.

---

## D-067 — O LLM dos agentes é `nemotron-3-nano-30b-a3b`, escolhido por ELIMINAÇÃO medida
**Data:** 28/08/2026 · substitui D-012 no que toca ao LLM
**Decisão:** `nvidia/nemotron-3-nano-30b-a3b`.
**Os 10 candidatos, sondados um a um com chamada real:** **7 deram HTTP 404** · **2 inutilizáveis**
(um alterna HTTP 400 com timeout de 300 s; outro responde em 35 s e devolve HTTP 500 no structured
output) · **1 utilizável** — este, ~650 ms, abstendo corretamente nos dois métodos.
**Todos os 10 estavam listados no catálogo.** A escolha não é preferência: **é o único que sobrou.**
**O que a troca custou:** uma variável em `.env` e `src/config.py`. **Nenhum agente mudou**, porque
nenhum agente conhece o provedor — a costura de D-002 pagou pela terceira vez.
**O que ela NÃO conserta:** abstenção (D-040), `json_schema` (D-047) e o juiz (D-056) foram
produzidos pelo modelo morto. **Trocar o modelo invalida esses números em vez de consertá-los** — o
destino de cada um está em D-069.
**Alternativa descartada:** Grok, que a liga sugeriu e que está pré-autorizado. **Não foi descartado
por mérito — não foi testado**, porque a chave ainda não existe. Fica registrado como não medido, e
não como pior, que é a distinção que D-065 cobrou.

---

## D-070 — O catálogo é vitrine, não inventário: estar em `/v1/models` não é estar vivo
**Data:** 28/08/2026 · generaliza o achado de D-067 · `scripts/sondar_catalogo.py`
**9 dos 10 candidatos sondados estavam LISTADOS em `GET /v1/models` e 9 não serviam.** A listagem
respondeu 200 com 83 modelos e **não é evidência de disponibilidade de nenhum deles**.
Isso muda o procedimento, não só um fato:
1. **Nenhuma decisão de modelo pode citar a listagem como prova.** Só chamada real conta. D-064
   citou, e errou o substituto que recomendou pelo nome.
2. **O catálogo encolhe entre execuções.** 84 modelos em 27/08, **83** em 28/08 — um dia. E dois que
   respondiam em 27/08 pararam de responder. **Não é um evento de EOL com data: é erosão contínua.**
3. **`sondar_catalogo.py` fica versionado, separado do smoke.** Os dois respondem perguntas
   diferentes: o smoke pergunta *"a config vigente funciona?"* e precisa **falhar alto**; a sondagem
   pergunta *"o que existe para substituí-la?"*. Varrer candidatos dentro do smoke **mascararia uma
   regressão futura** — por isso são dois arquivos.
**O valor disto para a banca não é a lista de modelos mortos, é a régua:** o projeto passou a medir
uma propriedade **do FORNECEDOR** — volatilidade de catálogo — com um instrumento versionado, em vez
de descobri-la por acidente a cada `pytest` quebrado. Três EOLs (18/05, 25/08, 27/08) e uma erosão
diária, com data e método. **É isto, e não "usamos a stack NVIDIA", o Diferencial do projeto.**

---

## D-068 — O passo 7 passa a ser o Cohere Rerank, e o provedor vira configuração
**Data:** 28/08/2026 · substitui D-015 · fecha o que D-064 e D-065 deixaram em aberto
**Decisão:** `rerank-v3.5` do Cohere em produção; `ConfigRerank` ganha **`provedor`**.
**Por que o Cohere, e por que isto é correção de método e não escolha nova:** D-015 o descartou por
*"é pago"* — falso — e por *"quebraria a narrativa"*. **Nenhum argumento medido contra ele existiu em
momento algum, porque ele nunca foi testado.** E o TAPI o recomenda **nominalmente**, na mesma lista
de Qdrant/PostgreSQL/BM25. Voltar a ele é alinhamento com o enunciado, não desvio.
**O requisito técnico é específico deste projeto:** as perguntas são em português e o corpus da NVIDIA
é em inglês, então **todo par do passo 7 é crosslingual**. `rerank-v3.5` é multilíngue — foi essa
mesma propriedade que sempre justificou o NeMo Retriever.
**A variável que faltava não era o modelo — era o fornecedor.** A costura de D-002 isolava o *modelo*
atrás de env var; a terceira morte mostrou o limite: **trocar o modelo só resolve se existir outro
modelo.** Em 27/08 não existia. Os três valores: `cohere` (produção) · `nvidia` (preservado como
registro; é como se testa em 30 s se voltou) · `nenhum` (**degradação graciosa** — o passo 7 sai do
caminho e a resposta vira a ordem da híbrida).
**`nenhum` NÃO é uma linha nova na tabela de ablação**, e a distinção importa: a tabela já tem a linha
sem rerank, que são os motores `denso` e `hibrido`. `nenhum` existe para o **runtime** — quem clonar o
repositório sem chave roda, em vez de receber um stack trace. É a metade executável do eliminatório
nº 3, que **é uma conjunção**: *"projeto que não executa **e** cujo vídeo não demonstra funcionamento
real"*. Medido: com `--rerank-provedor nenhum` o motor devolve **exatamente** os números da híbrida.

### A ablação de produção, medida em 28/08 — é a régua do critério 2

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| denso puro — linha de base | 95% | 100% | 100% | 79% | 79% | 84% |
| lexical (BM25) | 58% | 63% | 74% | 42% | 47% | 63% |
| híbrido (RRF K=10) | 95% | 100% | 100% | 79% | 79% | 79% |
| rerank Cohere sobre denso | 95% | 100% | 100% | 79% | **95%** | 95% |
| **rerank Cohere sobre híbrida — produção** | **95%** | **100%** | **100%** | **79%** | **95%** | **95%** |

**O reranking paga o que sempre pagou: e@3 de 79% → 95%**, que é o critério estrito e o motivo de o
passo 7 existir. **Mas a troca de fornecedor custou duas perguntas, e isso fica escrito porque medir
para si mesmo é o método aqui:** o reranker anterior dava e@1 de 84% (contra 79%) e e@5 de 100%
(contra 95%) sobre a híbrida. **E o braço lexical voltou a não pagar nada** — ver D-037.
**Isso NÃO virou mudança de produção**, e a omissão é decisão: trocar o motor por causa disto exige
critério fixado antes do código (D-055, D-058), e o híbrido custa mais chamadas de rerank — o que
agora importa, porque o teto do Cohere é 10 req/min.
**A escala do score mudou, e isso NÃO reabre o limiar.** D-035 mediu que **nenhum** corte sobre score
separa quem tem resposta de quem não tem. Aquele resultado era sobre a **ordem** não separar as
classes, não sobre a faixa numérica. O que a troca exige é mais modesto: scores de rerank anteriores
a 28/08 são de outra unidade e não se comparam linha a linha; r@k e e@k continuam comparáveis, porque
medem **posição**.
**Alternativa descartada, com o custo medido: cross-encoder local** (`bge-reranker-v2-m3`). `torch` são
74 MB no macOS arm64 mas **900 MB** no Linux x86_64 de quem avalia, mais 27 pacotes, mais **1,1-2,3
GB** de pesos. Ele trocaria uma dependência de rede em *runtime* por uma de ~3 GB na *instalação*.
Isso não o mata como ideia — é a única opção sem chave, sem quota e sem EOL, e é a resposta certa se
a trial apertar. Mas **ele entra medido ou não entra**, que é a régua que D-065 cobrou. Registrado
como **não medido**, não como pior.
**O que continua sendo risco, e não se resolve aqui:** o Cohere é outro serviço hospedado. A diferença
material é ser produto comercial com SLA e não catálogo de preview — mas a lição das três mortes é que
**componente hospedado é passivo do entregável**, e trocar de hospedeiro não zera isso. O provedor
`nenhum` é o que limita o estrago.
### Re-medida em 02/09, depois da re-ingestão de D-082 — e a resposta é "não mudou nada"

D-082 tirou 2 chunks do corpus (177 → 175) e deixou uma dúvida por escrito: *"`e@1 = 79%` é de um
corpus com entulho dentro"*. Re-rodada `avaliar_rag.py` sobre os 175:

| motor | 28/08 (177 chunks) | 02/09 (175 chunks) |
|---|---|---|
| denso · lexical · rerank_denso | idênticos | **idênticos** |
| **rerank sobre híbrida — produção** | 95/100/100 · 79/95/95 | **95/100/100 · 79/95/95** |
| híbrido sem rerank | 79 / 79 / **79** (e@1/e@3/e@5) | **74** / 79 / **84** |

**O caminho de produção não se moveu em nenhuma das seis colunas.** A dúvida de D-082 fica
respondida: os dois chunks removidos eram entulho real, mas nunca ocuparam posição que o gabarito
medisse. O único braço que mexeu é o **híbrido sem rerank**, que troca uma pergunta em e@1 por uma
em e@5 — e ele não é produção.

**O que isto NÃO diz:** nada sobre o passo 8. A abstenção depende do LLM, mudou de modelo em 01/09
e é medida por `--geracao` — **P-15 continua aberta**, e a metade barata (esta) só provou que a
recuperação não precisava dela.

**O teto da trial é pior que a documentação, e isso decide o roteiro do vídeo.** Medido em 28/08: o
429 chega na **4ª** chamada sequencial, `retry-after` vem **ausente**, e a janela de recuperação é de
**~26 s**. Por isso `src/rag/rerank.py` tem limitador proativo (`COHERE_REQ_POR_MIN`, default 10) e
retry — sem eles o grafo não roda. Consequência: **~2-3 min só de rerank num run completo**. A cena do
vídeo é uma consulta com `MAX_STARTUPS` baixo, não o run inteiro.

---

## D-071 — `revenda` vira o prefixo `revend`: um TRADE-OFF aceito, não uma melhora dos dois lados
**Data:** 28/08/2026 · fecha o que D-061 deixou para decidir
**A troca piora um dos lados, e isso precisa estar escrito assim:** falso **negativo** vai de 6/7 para
**7/7**; falso **positivo** vai de 3/7 para **2/7**. Fecha o vazamento silencioso (*"Somos
revendedores autorizados"*) e cria um falso positivo novo em *"Nossos clientes revendem os
relatórios"*.
**O que autoriza a troca não é o placar — é a assimetria de D-057.** O falso positivo aparece no
briefing e alguém o corrige; o falso negativo não aparece em lugar nenhum. **É precisamente por isso
que `--exclusoes` nunca soma os dois números** — uma "acurácia" única teria mostrado 9/14 antes e 9/14
depois, e concluído que nada mudou.
**O helper duplicado NÃO foi unificado, e o motivo é o gatilho:** D-066 definiu que *"a hora de
unificar é quando `elegibilidade()` mudar de corpus"*. O corpus **não mudou** — a correção de corpus
foi medida e reprovada. **O gatilho não disparou.**

---

## D-069 — O que é re-medido e o que é declarado histórico depois da troca de LLM
**Data:** 28/08/2026 · consequência de D-067 · segue o método de D-046
**Trocar o LLM não conserta as medições feitas com o modelo morto — invalida.** Este é o mapa,
**decidido antes de medir** para que o resultado não escolhesse o critério:

| medição | destino | por quê |
|---|---|---|
| `json_schema` × `function_calling` (D-047) | **RE-MEDIDA, n=15** | sustenta a convenção mais transversal do repo |
| abstenção do passo 8 (D-040) | **RE-MEDIR, n=3** | é o número que o vídeo cita, e o passo 8 é entregável |
| juiz do Extractor (D-056) | **SONDA** | está desligado; a sonda decide se vale abrir n=3 |
| tabela do RAG: denso, BM25, híbrida | **continuam válidas** | não tocam rerank nem LLM; o embedder sobreviveu |
| tabela do RAG: linhas com rerank | **RE-MEDIR** | o provedor mudou (D-068) |
| régua dos agentes | **intacta** | determinística, zero LLM — reconferida, idêntica |

As invalidadas ficam preservadas **com modelo e data**.
**O achado colateral, e ele vale mais que o placar.** Numa primeira sonda com um **schema de
brinquedo** (dois campos, docstring genérico), o modelo novo **alucinou** em `json_schema`. Com
`SaidaGerador` e a `INSTRUCAO` reais, faz 10/10. **O que carrega o resultado é o prompt, não o
método** — e a `INSTRUCAO` do passo 8 tem, escrito nela, exatamente o caso da q23: *"pergunta pede uma
comparação entre A e B, o trecho cita A e B juntos mas não os compara → abstencao=true"*. É **D-045
confirmado por um caminho que não foi desenhado para testá-lo**: o docstring do schema é prompt, e
**medir com schema de brinquedo mede o brinquedo**. Vale como aviso de método para qualquer medição
futura de LLM aqui.

---

## D-072 — O juiz do Extractor PASSA o critério de D-055 no modelo novo (n=3)
**Data:** 28/08/2026 · ~156 chamadas · reabre D-056 · **promoção PENDENTE**
**Mesmo código, mesmo prompt, só o modelo mudou** — de `llama-3.1-8b` (morto) para
`nemotron-3-nano-30b-a3b`:

| campo | trivial | produção (casador) | **juiz, n=3 (28/08)** | juiz n=3 (25/08, 8b †) |
|---|---|---|---|---|
| classe | 4/7 | 3/7 | 2-3 / 7 | 2-3 / 7 |
| maturidade_stack | 6/7 | 6/7 | 6/7 | 6/7 |
| confiança | 3/8 | 0/6 (+2 ambíguos) | 0/6 | 0/6 |
| elegível | 6/7 | 5/7 | **6/7 nas três** | 5-6 / 7 |
| motivo_exclusão | 6/7 | 5/7 | **6/7 nas três** | 5-6 / 7 |
| **dor — precisão** | 32% | **49%** | **83-96%** | 50-62% |
| dor — recall | 100% | 100% | 71-79% | 79-96% |
| discriminação | 1/8 | 8/8 | 6-8 / 8 | 8/8 |
| dor proibida emitida | 28 | 10 | **1-2** | 6-9 |

† preservado com modelo e data, como manda D-069. **A linha trivial é obrigatória** (D-051).
**O critério de D-055, verificado literalmente:** alvo de precisão 49% + 0,15 = **64%**; medido **83,
96, 96** — passa nas três, e o **pior caso supera o alvo por 19 pontos**. Piso de discriminação ≥ 6/8;
medido 6, 8, 6. **Não houve empate.**
**O que a mudança de modelo prova, e é maior que o placar.** O juiz de 25/08 e o de 28/08 são o mesmo
código e o mesmo prompt; o resultado vai de reprovado a aprovado com folga. Some-se o achado de D-069
(o mesmo modelo alucina com schema de brinquedo e faz 10/10 com o real): **as conclusões deste
projeto sobre "o LLM não dá conta" eram sobre um modelo de 8B, não sobre a abordagem.** E o modo de
falha que D-056 nomeou — o modelo recitando os modos de falha do prompt — **não reapareceu**.
**O que NÃO se resolve:** `confianca` continua 0/6 em todos os braços (o defeito é o `min()` do
validator, D-059) · `classe` piora de 3/7 para 2-3/7 · **`recall` cai de 100% para 71-79%** — o juiz
descarta dores erradas e leva junto ~1 em 4 das certas.
**A lacuna do critério, que é a mesma de D-060: D-055 nunca fixou guarda de recall.** Pela letra, ele
não é obstáculo. Mas promover fingindo que uma métrica não caiu 25 pontos seria desonesto — e
**reprovar agora por causa dela seria mudar o critério depois de ver o placar**, que é exatamente o
que D-055 existe para impedir. **A régua de qualquer critério futuro precisa nomear todas as métricas
que podem se mover, não só a alvo.**
**O argumento a favor de promover, e ele é a assimetria de D-057:** uma dor falsa no briefing produz
uma **conversa errada** com a startup e contamina a credibilidade do documento inteiro — o sistema
hoje diz que a SunnyHUB, de energia solar, tem dor de observabilidade de IA porque leu *"monitoramento
do sistema fotovoltaico"*. Uma dor faltando é uma oportunidade não mencionada; nada do que está
escrito fica errado. **Erro por omissão é recuperável; erro por afirmação, não.**
**A promoção fica PENDENTE.** `USAR_JUIZ_LLM` segue `False`. **Registrar a medição não é promover** —
e esta linha existe para que a diferença fique explícita no log.

---

## D-073 — O log guarda a decisão, não o caderno de laboratório
**Data:** 31/08/2026 · muda a regra de manutenção do `guia-de-trabalho.md`
**Decisão:** `decisoes.md` deixa de ser append-only **no arquivo** e passa a sê-lo **no git**. Uma
entrada por decisão, no formato de 5 campos, com o **fato corrente** — as camadas de "Atualização"
são consolidadas no corpo, e o que uma medição posterior derrubou vira uma linha `**Revisto:**`.
**Um número só fica se é verdade sobre o sistema que roda hoje.** Se o instrumento que o produziu
morreu, fica a **conclusão**, e só quando ela sobrevive ao instrumento.
**Alternativas descartadas:**
- **Manter o append-only literal.** O arquivo tinha 3.367 linhas e 16 blocos de correção empilhados:
  para saber o fato corrente de D-034 era preciso ler três camadas. Um arquivo cuja função declarada é
  *"resposta pronta quando o avaliador perguntar por que não X"* exigia arqueologia.
- **Mover as medições para um `medicoes.md`.** Rejeitada por ser pior que apagar: nasceria com ~1.800
  linhas de números produzidos por **três gerações de modelos mortos**, com aparência de autoridade.
  Este projeto tem nome para isso — *"instrução contaminada"*, o achado 5 de D-066 — e criar mais um
  lugar onde ela mora seria construir a próxima.
- **Curar por relevância**, mantendo só as decisões "importantes". Rejeitada porque *"importante
  hoje"* é julgado sem saber o que o avaliador vai perguntar, e as decisões de ambiente (D-001, D-004,
  D-017) já são curtas e são resposta pronta sobre reprodução.
**Motivo:** o argumento *"não apago porque o git guarda"* vale igualmente para as duas opções — as
duas são recuperáveis. Manter não compra segurança, compra **presença na árvore de trabalho**, que é
o custo em questão. E o custo não é só de leitura: **medição de instrumento morto é armadilha**, e
este projeto já foi mordido por ela três vezes (D-064 recomendando um modelo morto por nome, D-066
achado 5, e cinco reincidências achadas em 31/08).
**O que NÃO muda:** as decisões continuam sendo escritas **no momento em que são tomadas**, com a
alternativa descartada e o motivo. **Os números de D são identidade e nunca são reciclados** — há 946
referências cruzadas a `D-0NN` em `src/`, `tests/`, `scripts/` e na documentação.
**Reversível?** Sim, e trivialmente: `git show` na revisão anterior devolve as 3.367 linhas.

---

---

## D-074 — O critério do julgamento semântico no Evidence Validator, fixado ANTES do código
**Data:** 31/08/2026 · escrito antes de a primeira linha ser alterada · **alvos CONGELADOS**
· **medido em D-075: REPROVOU**

**Decisão:** mover a pergunta *"a evidência SUSTENTA a afirmação?"* para o **Evidence Validator**,
que marca `validada=False`, em vez de mantê-la no juiz do Extractor, que **deleta** o candidato.

**O defeito, medido e não suposto:** o Extractor emite 34 dores sobre as 8 fixtures e **10 estão
erradas**. O Evidence Validator **não barra nenhuma** (0/10), e a confiança de uma dor errada é
indistinguível da de uma certa. Ele mede a **espessura da evidência** — quantos tipos de documento,
quão recente — e nunca o salto da evidência para a conclusão. *"Monitoramento do sistema
fotovoltaico"* é fonte impecável para uma conclusão errada.

**A forma, pela terceira vez neste projeto:** D-035 achou que *relevância não é responsividade*.
Aqui: ***não contradizer não é sustentar***. As 10 dores erradas não são contraditas pela evidência
— são **neutras** em relação a ela, e por isso uma checagem de *contradição* pegaria zero.

**Por que no Validator e não no Extractor:** `validada` era **estruturalmente `True`** (o único
caminho para `False` era "nenhuma evidência", que o Extractor nunca produz — 34/34 passavam), então
o filtro em `recommendation.py` era um portão que nunca fechava. E o juiz do Extractor viola D-010,
que diz com todas as letras *"ausência de sinal ≠ sinal negativo; nada é DELETADO, só rebaixado"*.

**A hipótese que motivou a decisão:** o juiz custa recall (100% → 71-79%) **porque deleta**; se a
dor sobreviver marcada, a informação não é destruída. *(Refutada em D-075.)*

### A linha de base e o TETO — a medição durável desta entrada

| braço | precisão | recall | discrim | proibidas |
|---|---|---|---|---|
| trivial (D-051) | 32% | 100% | 1/8 | 28 |
| casador — produção | 49% | 100% | 8/8 | 10 |
| **controle barato: sem os 2 gatilhos piores** | **69%** | 100% | 8/8 | 3 |
| juiz no Extractor, deleta (D-072) | 83-96% | **71-79%** | 6-8/8 | 1-2 |
| **TETO — julgamento perfeito** | **100%** | **100%** | **6/8** | **0** |

**Dois achados desta tabela sobrevivem a qualquer braço futuro:**

1. **A barra de D-055 está queimada.** `observabilidade` e `dependencia_fornecedor` causam 7 dos 10
   erros; apagá-los é mudança de 8 caracteres e dá **69%** — acima dos 64% que D-055 fixou como alvo.
   Qualquer critério novo se fixa contra 69%, não contra 49%. (Apagar não é solução: mataria uma das
   8 dores do TAPI e seria ajuste a 8 fixtures. É linha de controle, como `--truncar-pool` em D-037.)
2. **O 8/8 de discriminação de hoje é em parte artefato dos erros.** Com julgamento perfeito ela cai
   para **6/8**. Guardar em 8/8 vetaria um juiz perfeito — o erro de D-060, evitado por calcular o
   teto antes.

### Os alvos congelados

| métrica | onde | alvo |
|---|---|---|
| **precisão de dor** | o que chega ao Recommendation | **≥ 80% nas três execuções** |
| **recall no PERFIL** | `perfil.dores_observadas` | **= 100%, exato** |
| **recall no Recommendation** | depois do filtro `validada` | **≥ 79%** |
| dores proibidas | o que chega ao Recommendation | **≤ 2 nas três execuções** |

**Por que 80% e não 64%:** o controle é determinístico em 69% e o espalhamento entre execuções é de
~13 pontos; 80% exige que a **pior** execução supere o controle por 11 pontos — mais do que a
variação consegue fabricar. **Por que o recall aparece em dois lugares:** é a lacuna que D-055
deixou e que D-060 e D-072 reencontraram — *fixar a barra sem nomear tudo que pode se mover*. A
separação perfil × recommendation é justamente o que distingue "rebaixar" de "deletar".

**Guardas (veto, não alvo):** `maturidade ≥ 6/7` · `elegivel ≥ 5/7` · `motivo_exclusao ≥ 5/7` ·
evidência literal 100% · `pytest` verde · **discriminação ≥ 6/8** · **`classe ≥ 2/7`** — guardada em
2/7 e não 3/7 porque D-060 mediu que o gargalo dela é **vocabulário**, e vetar por um defeito que
esta mudança não causa nem conserta seria vetar pelo motivo errado.

**Pré-condição (passo 0):** a régua tinha de separar `emitida` de `validada` antes de qualquer
mudança de comportamento — `avaliar_agentes.py` contava só as emitidas, e o placar não se moveria.

**Reversível?** Fácil — nasce atrás de flag.

## D-075 — O julgamento de sustentação foi medido, REPROVA no recall, e a colocação não muda nada
**Data:** 31/08/2026 · alvo fixado em D-074 · ~102 chamadas em 3 execuções · **REPROVADA, fica atrás de flag**

| | exec 1 | exec 2 | exec 3 | alvo | |
|---|---|---|---|---|---|
| precisão (validada) | 83% | 81% | 100% | ≥ 80% | passa |
| recall (perfil) | 100% | 100% | 100% | = 100% exato | passa |
| **recall (recommendation)** | **71%** | **75%** | **75%** | **≥ 79%** | **FALHA nas três** |
| discriminação | 7/8 | 6/8 | 7/8 | ≥ 6/8 | passa |
| dores proibidas | 2 | 2 | 0 | ≤ 2 | passa |

Todas as guardas seguraram. **Quatro dos cinco alvos passam nas três execuções; um falha nas três.**
Pela regra de D-074, `JULGAR_SUSTENTACAO = False`. É o quarto braço que o critério deste projeto
reprova, depois de D-056, D-059 e D-060.

### O achado que vale mais que o placar: o custo é da PERGUNTA, não da colocação

Rebaixar (Validator) e deletar (juiz do Extractor) saem **metricamente indistinguíveis** — precisão
81-100% contra 83-96%, recall 71-75% contra 71-79%. O prompt foi reusado **literalmente**
(`INSTRUCAO` e `CRITERIO_DOR` importados do Extractor) exatamente para tornar a atribuição válida:
com prompt idêntico, a diferença observada é atribuível à colocação — e ela é nula.

**Isso refuta a hipótese que motivou D-074.** Perguntar *"a evidência sustenta?"* custa ~25% das
dores certas em qualquer ponto do pipeline. A régua de duas colunas mostra exatamente onde a
hipótese acerta e onde erra: o recall do **perfil** fica em 100% — nada é deletado, o desenho
funciona —, mas o Recommendation filtra por `validada` e a perda reaparece idêntica. **A colocação
mudou onde a informação sobrevive, não se o Recommendation a enxerga.**

### O que fica em produção, porque não é métrica

**`validada` deixou de ser portão morto.** A régua agora mede as duas colunas e **imprime sozinha**
quando elas coincidem — o portão que não filtra virou saída do instrumento em vez de defeito
escondido no código.

### O que a medição abriu

Se o custo é da pergunta, o lugar de atacá-lo é o **consumidor**: `recommendation.py` trata
`validada` como booleano e descarta, enquanto D-010 manda *rebaixar*. Virou P-17 — e D-077 mediu.

**Nota de operação:** as três execuções expuseram chamadas isoladas de ~310 s contra p50 de 6,9 s,
com duração quase idêntica em prompts diferentes — assinatura de travamento do servidor, não de
conteúdo. O `timeout` **não** foi adicionado durante a medição, porque D-074 fixa que a régua não
muda depois do passo 0; entrou depois, como D-076.

**Reversível?** É flag. `avaliar_agentes.py --sustentacao` liga; `--sustentacao` com `--juiz` é
recusado, porque a mesma pergunta em dois pontos paga duas vezes e não atribui.

## D-076 — O `timeout` do LLM sai do literal e vira configuração (P-18)
**Data:** 31/08/2026 · fecha a nota de operação de D-075 · **PROMOVIDA**

D-075 mediu, no portão único dos nove agentes: p50 de **6,9 s** e p90 de 12,2 s contra chamadas
isoladas de **307,6 · 310,1 · 312,6 · 322,6 s**, em prompts DIFERENTES — duração quase idêntica em
prompts diferentes é assinatura de travamento do servidor, não de conteúdo. Sem `timeout` o
`ChatOpenAI` espera para sempre, e uma execução ia de ~4 min a ~20 min.

**`timeout=30` (`LLM_TIMEOUT`), em `src/config.py` e não em `src/llm.py`.** O literal foi a primeira
versão e foi rejeitado: todo o resto do cliente (`base_url`, `api_key`, `modelo`, `temperatura`) lê
de `LLM`, e um número cravado no meio quebraria pela primeira vez a convenção de que provedor só
passa por `src/config.py`.

**O `max_retries` fica no default e isso é decisão, não omissão.** Verificado no ambiente
(langchain-openai 1.6.0 / openai 3.3.1): o wrapper deixa `max_retries=None` e delega, e o cliente
do SDK usa **2** — logo 3 tentativas x 30 s = **~90 s de teto combinado por chamada**, não 30. É o
teto aceito: corta a cauda de ~5 min sem transformar um soluço de rede em veredito.

**O risco que D-075 nomeou continua de pé:** timeout curto vira veredito de sustentação, porque o
caminho de degradação de `sustenta()` devolve `validada=True`. Com o julgamento atrás de flag
desligada, hoje o risco é latente; se `JULGAR_SUSTENTACAO` for ligado, os 30 s entram na medição.

**Alternativa descartada:** `timeout` por chamada, passado nos nós que sabem que são caros. Rejeitada
porque o dado que se tem é do portão (p50/p90 agregados), não por nó — dividir o teto por nó seria
inventar números que ninguém mediu.


## D-077 — A gradação de `validada` no Recommendation está aplicada e é INERTE — em três camadas
**Data:** 31/08/2026 · critério fixado ANTES: recall (recommendation) ≥ 88% com precisão ≥ 80%
· **NÃO PROMOVIDA — código REVERTIDO, P-17 continua aberta**

O código de P-17 fazia a dor não-sustentada entrar como sinal fraco, com `confianca` rebaixada numa
cópia. Sintaxe válida, **e não move nada.** Três camadas, e cada uma sozinha já basta:

1. **Em produção o ramo novo nunca executa.** `JULGAR_SUSTENTACAO = False` desde D-075, e sem o juiz
   o único caminho para `validada=False` é "nenhuma evidência", que o Extractor nunca produz. A
   régua confirma e o próprio instrumento imprime *"as duas colunas são IDÊNTICAS"*.
2. **A `confianca` rebaixada não tem leitor.** `_prioridade()` recebe `diagnostico.confianca` — a do
   DIAGNÓSTICO —, nunca a da dor, e nenhuma outra linha do módulo lê `d.confianca`.
3. **A régua não mede este consumidor.** `avaliar_agentes.py` replica o filtro em vez de chamar
   `recommendation.node()`, então ela espelha o código de ontem. **Esta camada é defeito vivo do
   instrumento**, independente de P-17.

### O achado que vale mais que as três: o critério é inalcançável por este mecanismo

Se as três camadas fossem resolvidas, `validadas` passaria a conter TODA dor observada e a coluna
`validada` colapsaria sobre `emitida` **por construção**. O par vira **recall 100% · precisão 49%**:
passa nos 88% e falha nos 80%, e falha por desenho, não por ajuste. Admitir toda dor não-sustentada
desfaz exatamente o que o juiz comprava (81-100% de precisão em D-075), pelo preço que ele cobrava.

**Logo P-17 exige admissão PARCIAL, e o eixo não é `confianca`.** A separação que D-063 já instalou
é a que serve: a dor fraca pode entrar em `evidencias` (lastro secundário) sem entrar em
`dores_enderecadas` (o que o briefing DECLARA e a régua conta). Não medido; exige critério fixado
antes.

**Alternativa descartada:** mexer em `_prioridade()` junto, para dar leitor à `confianca` da dor.
Rejeitada porque mudaria o instrumento e o objeto na mesma sessão, e a régua de prioridade não
existe.

**Por que reverter em vez de deixar desligado:** uma lista que não filtra nada, dentro do arquivo
cuja história inteira (D-020, D-063) é sobre listas que PARECIAM filtrar, é dívida disfarçada de
progresso — e o achado não precisa do código para existir. `recommendation.py` voltou byte a byte a
c0c6f44.

## D-078 — O barema sai do lugar de função objetivo
**Data:** 01/09/2026 · muda documentação e comentário, **zero comportamento**

**Decisão:** o que ordena o trabalho deste projeto passa a ser **o defeito do sistema, medido pelo
custo que ele impõe a quem ia usá-lo** — o gerente de Startups & VCs da NVIDIA Brasil, e quem abre
o repositório para entender ou rodar. O barema continua registrado como especificação em
`contexto/01-tapi.md` e sai de todo arquivo que decide prioridade.

**O defeito que isso corrige estava escrito, não era clima:** `plano.md` mandava parar de melhorar
o RAG — *"Não rende mais: o critério 2 está em nível 4 e para lá"* — e `sessao-atual.md` ordenava a
fila *"em ordem de quanto movem a nota"*. O `CLAUDE.md`, carregado em toda sessão, abria com "onde
os pontos realmente estão", o que reinjetava a priorização por peso a cada sessão nova.

**A prova de que a bússola estava errada é imediata:** sob a pergunta nova, o RAG tem `e@1 = 79%`
(D-068) — **a primeira citação não contém a âncora uma vez em cinco**. É defeito que o usuário
sente, e era invisível para um placar que já marcava teto.

**Três mecanismos, e o segundo é o que deformava o texto:**
1. o barema decidindo o que se constrói e **quando se para**
2. **o avaliador como destinatário** — *"alternativas descartadas é literalmente a pergunta que o
   avaliador vai fazer"*. Quem escreve para ser avaliado escreve a defesa inteira; quem escreve
   para o leitor futuro escreve a decisão. É a causa do inchaço deste log
3. "nível 4" como teto — chegou a docstring de produção (`nvidia_rag.py`, `fusao.py`,
   `avaliar_agentes.py`)

**Alternativa descartada: reescrever o histórico deste arquivo**, para que as 77 decisões
parecessem sempre orientadas a produto. Rejeitada porque é fabricar registro — o mesmo defeito,
invertido. Muda só o que governa o futuro: o cabeçalho, a tabela de pendências, e as três entradas
que eram caderno de laboratório. Argumento vivo que se apoiava no barema é **re-argumentado**, não
editado — ver a linha `Revisto:` de D-062.

**Medido antes de decidir quanto cortar do log:** 68 das 77 decisões são citadas de fora dele —
**60 pelo código-fonte**, 30 pelo `CLAUDE.md`, que não guarda número e aponta para cá. O log é
camada de referência, não decoração: **cortar por volume quebraria ponteiro.** O que sobrava era
tamanho de entrada, não número de entradas: D-074, D-075 e D-077 somavam 247 linhas, todas órfãs,
todas registrando trabalho que não deixou traço no sistema. Comprimidas para 154, com decisão,
achado sobrevivente e alternativa preservados.

**O que NÃO muda:** o TAPI continua sendo especificação de cliente — LangGraph, os 9 passos, os 7
campos, 30-50 startups, o vídeo, o prazo. O método de trabalho sobrevive inteiro (explicar antes de
codar, alternativa registrada, nada entra sem ser lido, subagentes evitados): muda **a razão**, não
a prática — e sobreviver à troca de razão é a prova de que ele era bom. **Prazo continua sendo
restrição**, e ordena o *quanto*; nunca o *quê*.

**Reversível?** Fácil e quase irrelevante — não há código envolvido. O que não é reversível de graça
é o hábito: o viés reapareceu **dentro desta mesma sessão**, na proposta de antecipar o README
"como prova visível de que a virada é real". Mesmo mecanismo, outra plateia — o README não é o
sistema, e antecipá-lo não melhoraria nada. Recusada, e registrada aqui porque a recaída é o modo
de falha esperado desta decisão.


## D-079 — O quarto EOL, e a correção do achado de D-070: "listado mas morto" eram TRÊS coisas
**Data:** 01/09/2026 · descoberto por rodar o smoke, não por ler o código

**O fato:** `nvidia/nemotron-3-nano-30b-a3b` (o LLM de D-067) morreu às **09:00 UTC de 01/09**, e
desta vez o fornecedor disse com todas as letras — é a primeira vez que este projeto captura a
mensagem:

```
HTTP 410  {"title":"Gone","detail":"The model 'nvidia/nemotron-3-nano-30b-a3b' has reached
           its end of life on 2026-09-01T09:00:00Z and is no longer available."}
```

**Decisão:** `LLM_MODEL` passa a `nvidia/nemotron-3.5-lightning-30b-a3b` — 1 vivo de 10 sondados,
sucessor da mesma família, e passa na pergunta-armadilha de D-047 (abstém em `json_schema` **e**
`function_calling`). Smoke de volta a **3/3**.

**A CORREÇÃO DE D-070, e ela é o que vale mais aqui.** D-070 concluiu que *"o catálogo lista
modelos que devolvem 404 — é vitrine, não inventário"*. Ler o **corpo** das respostas, e não só o
status, mostra que a conclusão somava três coisas distintas:

| assinatura | significado |
|---|---|
| `410` + `"end of life on <ISO>"` | **morte real**, anunciada, com data. Não volta |
| `404` + `"Function '<uuid>': Not found for account"` | **entitlement**: o modelo existe e roda; a conta não alcança |
| `404 page not found` (texto puro) | o nome não existe |

Dos 9 que não serviam em 01/09, **1 era morte e 7 eram falta de acesso**. Contar juntos inflava o
risco de EOL do projeto **por um fator de 7** — e decisão de arquitetura tomada sobre esse número
seria tomada sobre ruído. A formulação correta é mais forte: **`GET /v1/models` devolve o catálogo
GLOBAL, não o que a conta pode chamar.**

**O que decide o acesso, medido em 19 sondagens:** **ser modelo próprio da NVIDIA é condição
necessária, não suficiente.** Terceiros: 0 vivos em 12 (Mistral, Meta, Google, IBM, Microsoft, 01-ai,
adept, ai21, aisingapore). Próprios: 3 vivos em 7 — e `nvidia/cosmos-reason2-8b` é próprio e está
fora. Consequência prática: **candidato a substituto só vale a pena sondar entre os `owned_by:
nvidia`.**

**O que NÃO existe, e é o que mais importa saber: aviso prévio.** Medido nos dois canais possíveis —
a listagem expõe só `id/object/created/owned_by`, sem campo de depreciação; e a resposta de um
modelo **vivo** não traz `Sunset` nem `Deprecation` (RFC 8594). **Só a chamada real informa, e
informa depois.** Logo a mitigação não é prever, é detectar rápido e trocar barato: 4 s de
`smoke_nvidia.py` mais uma env var. **Rodar o smoke antes de gravar o vídeo e antes de entregar
não é zelo — é a única defesa que existe.**

**O instrumento foi atualizado junto:** `sondar_catalogo.py` classifica os três casos, extrai a data
de EOL do corpo e imprime o aviso sobre a ausência de aviso prévio. Deixou de responder "morreu?" e
passou a responder "por que não serve?".

**Aberto, e não medido:** o modelo novo emite raciocínio dentro de `content` (`reasoning_content`
espelhado). A saída estruturada passa, mas é mudança de comportamento — **toda medição de D-072,
D-074 e D-075 foi feita no modelo morto e precisa ser refeita antes de valer** (vira o passo 1 da
próxima sessão).

**Reversível?** Uma env var, e é a quarta vez que isso se paga. O que mudou em relação às três
anteriores: nenhuma sessão foi gasta reconstruindo — o provedor isolado em `src/config.py` (D-002)
transformou EOL de fornecedor em troca de configuração.


## D-080 — A QUARTA assinatura: vivo, porém acima do relógio — e o smoke chamava isso de morte
**Data:** 02/09/2026 · descoberto por rodar o smoke na revisão do plano, não por ler o código

**O fato, medido:** `nvidia/nemotron-3.5-lightning-30b-a3b` — escolhido ontem por D-079 — **não
morreu**. Ele responde HTTP 200 e ficou lento. `smoke_nvidia.py` imprimia
`chat completion [FALHOU] ReadTimeout` e fechava em **2/3**.

| sonda | resultado |
|---|---|
| nome inexistente | HTTP 404 em 0,4 s |
| `nemotron-3-nano` (morto, D-079) | HTTP 410 em 0,4 s, com a data no corpo |
| **o modelo de produção** | **HTTP 200**, primeiro token em 27–68 s |
| 8 chamadas reais por `src/llm.py` | **0 falhas**, mediana **51 s**, faixa 17–88 s |

O transporte está intacto — o 404 e o 410 voltam em 0,4 s. O que estourou foi o relógio.

**A correção do catálogo de D-079.** As três assinaturas (410 = morte · 404+uuid = entitlement ·
404 puro = inexistente) descrevem só respostas que CHEGAM. Faltava a quarta, e ela é a única que
não tem status HTTP próprio: **vivo, porém acima do relógio.** Um timeout deixa de ser conclusão e
passa a ser gatilho de `diagnosticar_chat()`, que sonda o transporte antes do modelo e classifica
pela resposta real.

**Por que isto era o defeito mais caro em aberto:** o `CLAUDE.md` manda rodar o smoke antes de
gravar o vídeo e antes de entregar, e o chama de *"a única defesa que existe"*. Lido pela doutrina
de ontem, o resultado de hoje seria **um quinto EOL** — e a conduta seria migrar de modelo a 5 dias
do vídeo, sem que nada tivesse morrido. **O instrumento que existe para detectar morte estava
produzindo morte falsa.**

**Três mudanças:**
1. **`LLM_TIMEOUT` 30 → 120.** Com 30 s, **5 de 8 chamadas estouram a primeira tentativa** e só
   completam pelo `max_retries=2`: uma chamada de 88 s é 30 (falha) + 30 (falha) + ~28 (sucesso).
   O timeout curto não protegia de nada — **triplicava o relógio e escondia a latência real atrás
   de retries silenciosos**. Revisa o "~90 s de teto combinado" de D-076, cujo raciocínio estava
   certo para uma latência que deixou de valer.
2. **O smoke ganha o estado `LENTO`**, separado de `PASSOU` e de `FALHOU`. Conta como capacidade OK
   — a capacidade existe — e imprime a conduta: *"NÃO é EOL, não migre o modelo."* Volta a 3/3.
3. **`diagnosticar_chat()` reusa `_classificar` de `sondar_catalogo.py`.** Duas definições de
   "morto" no mesmo repositório divergem — é o argumento de D-059 contra duplicar verdade.

**O que mais foi medido junto, e retira um risco em aberto de D-079:** o modelo emite raciocínio
dentro do `content` **no caminho cru** (`"Here's a thinking process:"`), mas
`with_structured_output(method="json_schema")` devolve só o schema, validado. **O caminho de
produção não é afetado**, e o smoke agora anota isso onde a confusão aconteceria.

**Alternativa descartada: trocar o modelo.** É o reflexo que quatro EOLs em três meses
construíram, e aqui ele estaria errado — não há substituto (0 vivos de 10 na sondagem de hoje) e
não há nada a substituir. **Migrar por timeout mal lido teria gasto uma sessão para piorar o
sistema.** É o custo exato que este registro existe para evitar da próxima vez.

**Alternativa descartada: fazer `LENTO` reprovar o smoke** (código de saída ≠ 0). Rejeitada porque
o smoke é porteiro de gravação e entrega: reprovar uma capacidade que funciona convida a ignorar o
instrumento, que é como um alarme perde a função.

**Reversível?** Sim, e barato — uma env var e um estado a mais no relatório. O que não é reversível
é a lição de método: **"o instrumento falhou" e "a coisa medida falhou" são afirmações diferentes,
e o smoke não sabia dizer qual das duas estava fazendo.**


## D-081 — O radar de startups de IA descartava a palavra "IA", e o briefing não dava sinal
**Data:** 02/09/2026 · achado por rodar o grafo na revisão do plano · **bug de correção, em dois lugares**

**O fato:** `query_planner.py` filtrava os tokens da consulta por `len(t) > 2`. **"ia" e "ai" têm
dois caracteres.** A consulta-bandeira do produto saía sem o termo que a define:

| consulta | `palavras_chave` antes | depois |
|---|---|---|
| `"startups de IA"` | **`[]`** | `['ia']` |
| `"quais empresas usam AI"` | **`[]`** | `['ai']` |
| `"startups brasileiras de saúde usando IA"` | `['saúde']` | `['saúde', 'ia']` |

**O modo de falha é pior que o bug.** Com a lista vazia, `SQL_BUSCAR` cai em `tsq = ''`, todos os
filtros ficam nulos, e a consulta devolve os `max_startups` primeiros **em ordem alfabética** — que
o briefing então imprime sob o mesmo cabeçalho de um resultado legítimo. Não havia exceção, não
havia aviso, e a saída era indistinguível de um acerto. **Medido:** a consulta devolvia
`Laura Networks`, que não casa "ia" em **nenhum** dos seus três documentos; depois da correção ela
sai, e entram as que casam.

**O bug estava em DOIS lugares, e achar só um teria sido pior que não achar nenhum.**
`db._para_tsquery` tinha o mesmo `len > 2`. Corrigir só o Query Planner faria "ia" entrar no plano
e morrer na montagem do tsquery — com a consulta *parecendo* consertada e o teste do plano passando.

**A correção, e ela é conceitual:** um filtro de TAMANHO estava fazendo o trabalho de uma lista de
STOPWORDS. Funciona para "de"/"em"/"os" e falha exatamente nas siglas, que são curtas e são o sinal
mais denso que uma consulta técnica carrega. Os dois filtros passam a ter razões distintas:

- **Query Planner** — decisão semântica: o piso vira `len > 1` e quem decide o que é palavra vazia
  é `VAZIAS`, que ganhou as funcionais de dois caracteres (`de`, `do`, `da`, `em`, `no`, `na`, …).
- **`_para_tsquery`** — sanitização sintática: descarta fragmento vazio do split, e nada mais.

**A segunda correção é a que impede a próxima:** `PlanoDeBusca.discrimina()` responde *"existe algum
critério que estreite a base?"*. O Retriever registra em `erros` e o **Briefing anuncia no
cabeçalho** — não no rodapé, e não só no caso zero, porque o caso perigoso é justamente aquele em
que o sistema devolve cinco empresas. **O defeito nunca foi o resultado errado; foi o resultado
errado ser indistinguível do certo.**

**Alternativa descartada: pôr "ia"/"ai" numa lista branca** e manter `len > 2`. É de duas linhas e
teria funcionado hoje. Rejeitada porque não corrige a causa — a próxima sigla de duas letras que
importe (`ml`, `nl`, `cv`, `dl`) cai no mesmo buraco, e uma lista branca de tokens mágicos é
exatamente o "código mágico" que o método deste repositório proíbe.

**Alternativa descartada: fazer plano sem critério devolver zero startups.** Seria honesto e é
tentador, mas trata `"me mostre as empresas da base"` como erro quando é pedido legítimo. Devolver
**com o aviso** preserva o caso de uso e mata o silêncio, que era o defeito real.

**Rede nova:** `tests/test_query_planner.py`, 14 testes — o agente estava entre os **dois sem
nenhum teste** (o outro é o `extractor`), e a régua dos agentes também não o cobre. Suíte: 53 → 67.

**O que isto diz sobre a revisão de 01/09:** a fila tinha `query_planner` em 6º de 8, descrito como
lacuna de completude — *"sem teste e sem régua"*, `estrategia_analise` constante morta. Era um bug
de correção na primeira pergunta que o usuário faz. **Nenhuma leitura de código o encontrou em duas
sessões; uma execução o encontrou em um minuto.**


## D-082 — O que o gerente lê primeiro era entulho de página, case de outra empresa e o próprio programa
**Data:** 02/09/2026 · três correções que saíram de UMA execução do grafo

**O sintoma, na saída real:** a `justificativa_tecnica` — um dos 7 campos obrigatórios do TAPI e o
primeiro que o gerente lê — vinha de `citacao.trecho`, o chunk recuperado **cru**. Rodando o grafo,
ela saiu como um case da **Iguazio** ao recomendar Inception à Doutor-AI e à Laura Networks.

**Três causas distintas, e a fila as tratava como uma só.** A fila e P-10 diagnosticavam o defeito
como *"`justificativa_negocio` precisa sair do LLM"*. Medido, era outro campo e outras causas:

**1. O Inception é o PROGRAMA, não uma tecnologia a adotar.** Saía como recomendação de verdade —
*"prioridade media · complexidade media · ação: agendar conversa técnica sobre NVIDIA Inception"* —
no mesmo briefing que já traz `NVIDIA Inception: ELEGÍVEL` logo acima. `NAO_SAO_TECNOLOGIA` em
`nvidia_rag.py` filtra na saída do nó.
**Alternativa descartada: tirar a página do corpus.** Era o plano inicial e teria quebrado a régua:
**quatro das 24 perguntas do gabarito dependem dela** — q10 (`"10 years"`, que é a regra de idade da
M4), q11 (`"free program"`) e as provas de ausência q21 e q24. A distinção é de **papel**: fonte de
conhecimento sim, produto a recomendar não. Por isso a lista mora no nó, não em `fontes.yaml`.

**2. Entulho de página indexado.** `limpar_linhas` mata menu por TAMANHO e não alcança
consentimento, formulário e widget, que vêm em prosa longa. Estavam no índice: o chunk 324 era 272
tokens de markup de um chatbot da Adobe (`FAB BUTTON`, `AEM HTTPS`, `@author vpanapaku`), e o 15
era formulário de manutenção. `descartar_boilerplate` filtra por MARCADOR observado, **por linha e
nunca por chunk** — dos 7 chunks que casavam "cookie|Sign In|Apply Now", **só 3 eram entulho**, e um
filtro por chunk teria apagado *"Inception is a free program that guides AI startups…"*, que é
conteúdo bom e fonte provável da q11. **A sujeira era a linha, não o chunk.** Corpus: 177 → 175.
Só no caminho HTML: num README, `<a href` dentro de bloco de código é conteúdo.

**3. `ano_fundacao` ausente em 5 de 8 — e a auditoria de 22/08 tinha ERRADO em três.** A doutrina
das fixtures é boa (*"só entra o que aparece literalmente"*); a aplicação falhou. Varrendo os
documentos por frase de fundação: Axenya *"Fundada em 2020"*, Laura *"Em 2016, ele **fundou** a
Laura"* — a fixture afirmava que 2016 era "início de operação, não fundação", e o verbo da frase é
"fundou" — e Freedom *"Criada entre setembro de 2024 e janeiro de 2025"*. Deal e RD Station seguem
`null` **de propósito**, com a razão já registrada nas próprias fixtures. 3 → 6 de 8.

**O caso de borda que isso revelou, e é achado de método:** Laura fundada em 2016 faz 10 anos em
2026, e a regra é *"menos de 10 anos"*. O documento dá o **ano**, não o mês — a idade real está
entre 9,7 e 10,7. `elegibilidade()` faz `date.today().year - ano_fundacao` e exclui em `>= 10`, o
que é **decisão de precisão sobre dado que não a sustenta**. O gabarito passou a
`elegivel: [true, false]`, o idioma que a base já usava em `confianca`: sai do denominador em vez de
premiar ou punir uma precisão inexistente. Efeito na régua: `elegivel` 5/7 → **4/6 + 1 ambíguo**,
sem nenhuma reprovação nova. O operador de borda vira **P-20**.

**O QUE NÃO FOI RESOLVIDO, e ficou MEDIDO:** rodando de novo depois das três correções, a
`justificativa_tecnica` ainda sai como *"Join our ecosystem of startups, partners, and developers"*
(NVIDIA Healthcare) e como *"Writer / Startup Pens Generative AI Success Story With NVIDIA NeMo"* —
**o case de outra empresa, de novo, em duas tecnologias que não são o Inception.** Ou seja: o padrão
é do CORPUS inteiro, não daquela página. E **não há assinatura estrutural para pegá-lo** — esses
chunks vivem sob breadcrumbs genéricos (`NVIDIA NeMo > NVIDIA NeMo`), enquanto só 2 chunks da base
têm palavra de vitrine no caminho de seção, e não são os ofensores. Logo não é filtro de higiene:
**é a decisão de projeto P-10**, e ela agora tem o mecanismo medido em vez de um sintoma anedótico.

**Reversível?** As três, sim. A 1 e a 3 são dados; a 2 é uma lista de marcadores e uma re-ingestão.


## D-083 — Rodar o sistema vira regra, porque a leitura de código falhou três vezes no mesmo dia
**Data:** 02/09/2026 · muda o método de trabalho, **zero comportamento**

**Decisão:** toda sessão que mexe em comportamento executa `python -m src.graph` antes de fechar e
**lê a saída**. Entra no `CLAUDE.md`, que é carregado em toda sessão, e no `guia-de-trabalho.md`.

**A evidência, e ela é do mesmo dia.** As sessões de 31/08 e 01/09 auditaram o sistema por leitura —
código, `grep`, conferência contra a spec — e produziram uma fila de trabalho. A revisão de 02/09
rodou o grafo **uma vez** e achou três defeitos que nenhuma das duas tinha visto:

1. **`query_planner` descartava "ia" e "ai"** — filtro `len(t) > 2`, em **dois** lugares. A consulta
   `"startups de IA"` saía com `palavras_chave=[]` e o sistema imprimia um briefing confiante sobre
   uma fatia alfabética da base (D-081).
2. **Entulho de página indexado** — 272 tokens de markup de um chatbot da Adobe, recuperáveis (D-082).
3. **`justificativa_tecnica` citando outra empresa** — case da Iguazio ao recomendar para a
   Doutor-AI (D-082).

**Por que a leitura não pegava, e é isto que generaliza:** nas três, **cada linha está correta
isoladamente.** `len(t) > 2` é um filtro razoável; o pipeline de limpeza faz o que promete;
`justificativa_tecnica=citacao.trecho` é a atribuição óbvia. O defeito mora na **interação** entre a
regra e o dado real — e dado real só aparece rodando. Os três produziam saída **confiante e errada**,
sem exceção e sem teste vermelho: `pytest` estava em 53/53 com os três presentes.

**O corolário:** suíte verde não é evidência de que o sistema funciona, é evidência de que não
regrediu naquilo que já se sabia testar. **A saída é o instrumento.**

**Alternativa descartada: exigir teste novo para cada defeito, em vez de execução.** É o reflexo
certo depois do fato e não ajuda antes dele — nenhum dos três seria escrito como teste por quem não
sabia que existiam. O teste fixa o que já se descobriu; a execução é o que descobre.

**Alternativa descartada: rodar só antes de entregar.** Concentra a descoberta no dia em que não há
tempo de corrigir. Por isso a regra é **por sessão**, e o plano final põe um portão de execução em
todos os dias de 03 a 07/09.

**Reversível?** É método, não código. O que a torna difícil de abandonar é o custo medido do
contrário: três defeitos de produto, dois deles no campo que o usuário lê primeiro, passando por
duas auditorias.


## D-084 — "efeito no vídeo" sai do lugar de critério de decisão técnica
**Data:** 02/09/2026 · muda o método de trabalho, **zero comportamento** · levantado pelo Vinícius

**A decisão:** impacto no vídeo **não ordena decisão técnica**. Ele é restrição de entrega — como o
prazo — e restrição diz *quanto* se faz, nunca *o quê*. Entra no `CLAUDE.md`, ao lado de D-083.

**A evidência, e ela está escrita no próprio plano.** `plano.md` §5 comparava as três opções de
P-10 numa tabela cujas colunas eram *"custo"* e ***"efeito no vídeo"***, e concluía contra a opção
(b) porque *"5 startups × 3 recs ≈ 12 min, e o vídeo tem 7"*. A sessão de hoje repetiu a régua sem
questioná-la ao apresentar a decisão.

**Por que é o mesmo erro de D-078, com outra roupa.** D-078 tirou o barema do lugar de função
objetivo — *"peso de critério não é bom critério de priorização"*. A cadeira ficou vazia e **o
vídeo sentou nela cinco dias depois**. O padrão é o mesmo: um artefato de avaliação ocupando o
lugar do que ordena o trabalho, que é o defeito na mão de quem usa o sistema.

**O custo concreto, e não é purismo:** uma razão justificada pelo vídeo **vence em 07/09**. Depois
de gravar, a decisão fica sem fundamento. E na arguição — que é eliminatória — *"não cabia nos 7
minutos"* é resposta fraca, enquanto *"o gerente esperaria 12 minutos por um briefing"* é forte.
Mesmo número, prazo de validade diferente.

**O que muda quando P-10 é recomparada sem o vídeo**, e é aqui que se vê que a correção tem dente:

| critério | (a) determinístico | (b) o LLM redige |
|---|---|---|
| conserta o defeito medido | sim | sim |
| **latência que o gerente sente ao clicar** | nenhuma | ~51 s por recomendação; ~2,5 min mesmo para uma startup |
| **robustez** — hoje o grafo roda com zero chamada de LLM em produção, e foi isso que o fez sobreviver ao 4º EOL | preserva | põe o único modelo vivo de 10 no caminho do campo que o gerente lê primeiro |
| **reversibilidade** | é pré-requisito de (b): alimentar o LLM com depoimento de marketing produz depoimento bem escrito | aditiva, cabe atrás de flag depois |

**A conclusão não muda — a força e a validade mudam.** Sob o vídeo, (b) era *"inviável"*. Sob
latência de produto, (b) é *"cara e exigiria UI assíncrona"*: pior, não impossível. E o argumento
que de fato pesa contra (b) não era nenhum dos dois — **é o fornecedor único**, que estava
enterrado na tabela. Uma régua errada não estava só exagerando: estava escondendo o argumento bom.

**Alternativa descartada — registrar só em `decisoes.md`, sem tocar no `CLAUDE.md`.** O arquivo já
tem 17 KB e é carregado em toda sessão, então cada linha nova custa. O que decide contra é que
**D-078 já estava no log e não segurou**: o erro voltou em cinco dias, por outra porta. Log é
consulta; `CLAUDE.md` é o que está na mesa sem ninguém procurar.

**Reversível?** É método, não código.

---

## D-085 — O filtro do Inception recusava quem devia entrar: menção vira identidade, e a borda de idade sai do denominador
**Data:** 02/09/2026 · fecha **P-13** (aberta desde 25/08) e **P-20** (aberta em 02/09)

**Como apareceu:** rodando o grafo (D-083). As duas empresas da consulta saíram
`NVIDIA Inception: NÃO ELEGÍVEL` — numa ferramenta cujo trabalho é achar startups para o Inception.
A **Axenya**, prospect de maior prioridade da base, porque a home dela diz *"Integramos consultoria,
dados e operação clínica"*. A **Laura Networks**, porque *"fundada em 2016, 10 anos"*.

**Por que isto passou na frente de P-10 na fila:** a justificativa mal escolhida **degrada** a
saída, e o gerente ainda tem a URL para clicar. Um `NÃO ELEGÍVEL` errado **inverte a decisão** — e
ele não tem como saber que está errado. É a pergunta do `CLAUDE.md` aplicada literalmente.

### P-13 — o veto de terceiro

`elegibilidade()` excluía se **qualquer** termo aparecesse em **qualquer** evidência. Medido:
falso positivo **2/7**. Os cinco erros tinham o mesmo defeito — o termo descreve **outra empresa**.

**O sinal já estava escrito, pelo curador, nas notas de `exclusoes.yaml`:** *"o sujeito é um
PARCEIRO"*, *"a empresa é CLIENTE de consultoria"*, *"quem revende é o CLIENTE"*, *"USO, não
identidade"*. Implementar o princípio que a régua já documentava não é ajustar ao gabarito.

**A decisão: veto por marcador de terceiro, com ESCOPO DE FRASE.** O casador lexical não muda; o
que entra é `_fala_de_terceiro`, que anula a ocorrência quando **toda** frase em que o termo aparece
tem marcador de terceiro. Basta uma frase limpa para o veto não valer.

**O escopo de frase é a parte que generaliza; a lista de marcadores é a parte ajustada aos casos —
e essa distinção é a honestidade desta decisão.** Todo caso de `exclusoes.yaml` é uma frase só, então
um veto **global** sobre o trecho marcaria 14/14 e pareceria igualmente correto. Trecho de evidência
é **parágrafo**: com veto global, *"Somos uma consultoria de IA. Nossos clientes são bancos."*
escaparia do filtro, em silêncio — o modo de falha assimétrico de D-057. Esse par não está na régua
e está em `tests/test_elegibilidade.py`, nos dois sentidos de ordem das frases.

**Alternativa descartada — âncora de identidade (`somos|é uma <termo>`):** a régua a chama de
*"armadilha do desenho recomendado"* e planta o contra-exemplo, *"Como **nossa consultoria** de IA
para empresas gera resultados"* — identidade por possessivo, que a âncora perde. E há razão
estrutural: um veto só **remove** exclusão, então o falso negativo não pode regredir por construção;
uma âncora reescreve os dois lados de uma vez.

**Alternativa descartada — olhar só `setor` e `descricao_curta`:** move a decisão do documento para
o curador, contra *"nada é afirmado sem evidência"* — e nas empresas novas da M3 esses campos são
preenchidos por quem escreve a fixture.

**A colisão que quase passou:** `terceirizad` era marcador natural e ficaria **anulando**
`EXCLUSOES["consultoria"] = [… "desenvolvimento terceirizado" …]`. Ficou fora, com teste.

### P-20 — a borda da idade

`date.today().year - ano_fundacao` tem precisão de **ano**; a regra é *"menos de 10 anos"*. A idade
real cai numa faixa de 12 meses, e a faixa cruza o limite **exatamente** quando
`idade == IDADE_MAXIMA`. Fora dali não há dúvida: `> 10` é real ≥ 10,x; `< 10` é real ≤ 9,x.

**Decisão:** `>` exclui · `==` vira **pendente**, com a faixa impressa (*"entre 9 e 10 anos — o
documento dá o ano, não o mês"*) · `<` passa. Mesmo idioma do gabarito (`elegivel: [true, false]`):
sai do denominador em vez de fingir precisão. **Alternativa descartada — guardar o mês:** não consta
nos documentos de 6 das 8 fixtures, e inferi-lo é o que D-021 barrou.

### Medido, com o critério fixado ANTES

O portão declarado antes de escrever o código foi *"falso positivo ≥ 6/7, falso negativo 7/7 sem
regressão"*.

| | antes | depois |
|---|---|---|
| `--exclusoes` falso **negativo** (o silencioso) | 7/7 | **7/7** |
| `--exclusoes` falso **positivo** (o que aparece no briefing) | 2/7 | **7/7** |
| `avaliar_agentes.py` · `elegivel` | 4/6 + 1 amb | **6/6** + 1 amb |
| `pytest` | 67 | **75** |
| `classe` · `stack` · `confianca` · precisão/recall de dor | 3/7 · 6/7 · 0/6 · 49%/100% | **idênticos** |
| grafo, Axenya | `NÃO ELEGÍVEL` por 'consultoria' | **ELEGÍVEL** |
| grafo, Laura Networks | `NÃO ELEGÍVEL` por idade | **ELEGÍVEL**, borda como pendente |

**A ressalva que vai junto do número:** são **14 casos**, 8 deles sintéticos. Que o veto generalize é
**hipótese**, não medição. O que está medido é que ele implementa o princípio que o curador já tinha
escrito, e que o caso fora da régua — duas frases — passa.

**Reversível?** Sim, as duas: uma lista de marcadores e um operador de comparação.

---

## D-086 — `justificativa_tecnica` deixa de ser o chunk cru: a régua primeiro, o seletor depois
**Data:** 02/09/2026 · fecha **P-10** · abre **P-21**

**O estado anterior:** `justificativa_tecnica = citacao.trecho` — o chunk **inteiro**, mediana de
**803 caracteres**, do qual o briefing imprime os 150 primeiros. Então o que o gerente lia era *o
começo do chunk*, e a estrutura deste corpus é `TÍTULO / conteúdo`: ele lia o título.

**A medição de partida, sobre um run real (2 startups × 3 recomendações): 1 de 6 servia.** As outras
cinco foram um case da **Writer**, um CTA (*"Join our ecosystem…"*), um menu (*"Learn More /
- Documentation / - FAQs"*), um índice de links e prosa institucional.

### A régua veio antes, e foi commitada antes

`data/avaliacao/justificativas.yaml` — `random.sample(175, 30)`, `seed=20260902`, sobre a estratégia
de produção. **Rotulado antes de o seletor existir e commitado em separado**, que é o que o torna
teste em vez de espelho. 21 casos com alvo; os 9 sem alvo saem do denominador — punir o seletor por
não achar o que não existe mede a amostra.

**A linha trivial deste critério é *"os 150 primeiros caracteres"*, e ela não é fraca** — metade dos
chunks começa por frase boa. É o `denso puro` deste critério (D-051), e o harness a recalcula do
texto, não do meu rótulo.

### Dois níveis, porque são dois defeitos empilhados

**1. Nível de PASSAGEM (`nvidia_rag`).** Todo chunk de uma tecnologia compartilha a URL da página,
então a deduplicação por URL decidia **qual texto representa aquela tecnologia** — por posição do
reranker, que ordena por relevância à consulta, não por servir de justificativa. Vencia o chunk 81
do NeMo (quatro linhas de case da Writer e do Arize) enquanto o chunk 58 da **mesma página** diz o
que o NeMo faz. Deduplicar virou **escolher**. `TRECHOS_POR_DOR` 3 → 8, com **zero chamada de API a
mais**: `reranquear` pontua a união inteira e só depois fatia por `top_n`.

**2. Nível de SPAN (`recommendation`).** Mesmo na página certa, o campo era o chunk inteiro.
`melhor_trecho` escolhe o bloco de linhas consecutivas de maior **densidade** de marcador técnico,
com orçamento de 320 caracteres. Densidade e não contagem: dividir pelo comprimento faz uma frase
curta e densa ganhar de uma página morna, que é o que se quer de uma justificativa.

**O que o seletor NÃO faz: decidir relevância.** Quem escolhe a tecnologia continua sendo o
cross-encoder, que tem régua (`e@k`, D-068). A heurística decide só o que sabe julgar — qual texto
serve de justificativa. A posição do grupo vem do melhor colocado; **os scores acompanham o texto
escolhido**, porque um score que descreve um chunk que ninguém vê não descreve nada.

### Medido

| | antes | depois |
|---|---|---|
| régua, linha trivial (150 primeiros) | — | **12/21 = 57%** |
| régua, `melhor_trecho()` | — | **15/21 = 71%** |
| justificativas que servem, num run de 2 startups | **1/6** | **4/6** |
| tamanho do campo | chunk inteiro (mediana 803) | ≤ 320 |
| `pytest` | 75 | **81** |
| `avaliar_agentes` (classe · stack · confiança · elegível · precisão) | 3/7 · 6/7 · 0/6 · 6/6 · 49% | **idênticos** |

**DUAS COISAS QUE PRECISAM ESTAR ESCRITAS, PORQUE SÃO CONTRA MIM:**

1. **Eu afirmei um portão de "≥ 18/21" DEPOIS de ver o primeiro placar.** Ele nunca foi escrito nem
   comunicado antes. O critério que estava de fato fixado, no plano aprovado, é *"o seletor só entra
   se bater a linha trivial"* — e ele bate. Reivindicar alvo não registrado é a versão exata do
   defeito que este projeto vigia desde D-055; fica registrado como erro cometido, não evitado.
2. **Houve UMA revisão do seletor, declarada antes e limitada de propósito.** Ela acrescentou três
   marcadores de convite observados nas falhas (`learn how`, `visit`, `watch`) e **não tocou nas
   âncoras**. O placar não se moveu (15/21 nas duas medições) — mudou *quais* spans são escolhidos.
   Três das seis falhas restantes (#34, #253, #285) são **âncora estreita minha**: o seletor escolheu
   um span tecnicamente bom que não era a frase que eu tinha eleito. **Alargá-las depois de ver a
   falha seria ajustar ao gabarito, então elas continuam contando como erro.** O 71% é, por isso,
   um piso.

### O que NÃO entrou, e por quê

**A limpeza de "entulho de página, rodada 2" estava no plano e foi CANCELADA por evidência.** O plano
mandava acrescentar `Learn More`, `Documentation`, `Getting Started Guide`, `Examples`, `FAQs` a
`RUIDO_FRASE`. Inspecionados os **três** chunks do corpus que casam esses marcadores, **nenhum é
entulho**: o 127 tem o parágrafo real sobre telemetria do Guardrails, o 180 são release notes com
número medido (*"24,000 tokens per second"*, *"2.4x more Llama-70B throughput"*) e o 342 explica as
três formas de instalar o Morpheus. E o casamento de `RUIDO_FRASE` é por **substring**: `documentation`
mataria *"See the documentation for the quantization API"*. Era diagnóstico errado — o defeito nunca
esteve no corpus, esteve em entregar o chunk inteiro. **Conteúdo que sai da limpeza nunca mais volta**,
e esta teria saído por um sintoma cuja causa era outra.

**Alternativa descartada — (b), o LLM redigir:** continua **aberta**, com o critério corrigido por
D-084 (latência que o gerente sente, não minutos de vídeo), a decidir com a interface na frente.
Depois de D-086 ela também ficou mais barata e melhor: o LLM receberia um span selecionado em vez de
um chunk com título de case na frente.

### P-21, aberta por esta sessão

Das duas justificativas que **ainda não servem**, uma é de outro escopo: **NVIDIA Morpheus — spear
phishing e digital fingerprinting — recomendado para a dor de PRIVACIDADE de uma healthtech.** Não é
defeito de texto, é de **qual tecnologia**: a recuperação casa `privacy`/`security` sem saber o
domínio. Nenhum seletor de trecho conserta isso, e nada mede relevância de recomendação hoje.

**Reversível?** Sim. Os dois níveis são funções puras com teste, e `TRECHOS_POR_DOR` é uma constante.

---

## D-087 — O segundo provedor de LLM NÃO será construído, e o risco real muda de componente
**Data:** 02/09/2026 · alinhamento com a liga, relatado pelo Vinícius · fecha o item 1 de `plano.md` §3.3

**O que foi alinhado:** apresentada a arquitetura à liga — os dois subgrafos e o papel de cada
agente —, o ponto do catálogo perecível foi levantado. A resposta: **se o modelo morrer, não é
problema grave**, porque a avaliação olha **como a arquitetura foi construída**, e o provedor é
*"só uma linha de chave de API"*.

**Decisão: o fallback (Grok, pré-autorizado em D-067) NÃO entra.** A hora que ele custaria vai para
a base e para a interface. **Alternativa descartada — construí-lo mesmo assim:** seria seguro contra
um risco que quem avalia declarou não pontuar, num projeto em que a interface ainda tem zero byte e
é **pré-requisito do eliminatório nº 3**. Escolher blindagem sobre entregável a 5 dias do vídeo é
priorizar por medo, não por defeito.

**E A FRASE DA LIGA ESTÁ CERTA — PARA O LLM. É ONDE ELA NÃO SE APLICA QUE IMPORTA.** Verificado no
código em 02/09, e esta é a parte que muda o que se defende:

| componente | está no caminho do grafo? | contramedida | "só uma chave"? |
|---|---|---|---|
| **LLM** (`src/llm.py`) | **NÃO.** `USAR_JUIZ_LLM`, `JULGAR_SUSTENTACAO` e `CONFIANCA_DA_EVIDENCIA` são `False` **por medição** (D-056, D-059, D-075), e o grafo nunca chama `responder()` | não precisa | **sim** |
| **Cohere rerank** | sim, passo 7 | **existe e é medida**: `RERANK_PROVEDOR=nenhum` degrada para a híbrida, número a número (D-068) | quase |
| **Embedder** | **SIM, em toda consulta** — `busca.py:122`, dentro de `buscar_denso_bruto` | **NENHUMA** | **NÃO** — troca o espaço vetorial e invalida os **377** vetores; é `reembedar.py` mais re-medir a régua inteira (D-046). *O "381" corrigido em D-089* |

**A folga veio no componente que já não carregava peso.** O que sobrou sem plano B é o **embedder**,
e ele é o único cuja morte para o sistema em vez de degradá-lo. Isto não é motivo para construir
nada hoje — é o que se responde quando perguntarem qual é o risco, e é resposta melhor que
*"temos fallback"*.

**Consequência de produto, e ela é positiva: o passo 8 fica mais seguro de expor na interface.**
`responder()` é o único lugar em que o LLM apareceria numa demo, e era isso que o tornava arriscado.
Com o risco de EOL declarado como não-pontuado, a caixa de pergunta à base NVIDIA vira **candidata a
cena do vídeo** em vez de passivo: ela recusa responder quando não sabe — **23/24 = 96%** medido hoje,
com o único erro no lado seguro (D-040) — e mostra a fonte quando sabe. Entra em **P-06** como opção.

**O que esta decisão NÃO cobre, e fica dito:** o alinhamento é sobre a **morte do modelo**. O
eliminatório nº 3 do TAPI — *"projeto que não executa e cujo vídeo não demonstra funcionamento
real"* — continua escrito na especificação e continua valendo. Por isso **`smoke_nvidia.py` antes de
gravar e antes de entregar continua sendo regra** (D-079): ele custa 4 segundos e cobre os três
componentes, não só o que a liga dispensou.

**Reversível?** Trivialmente — `src/config.py` já isola o provedor; o que não foi feito é escrever
as ~30 linhas do segundo.

## D-088 — A auditoria do plano contra a fila de 01/09: três itens sem dono, e um critério banido que voltou
**Data:** 03/09/2026 · auditoria pedida pelo Vinícius antes de abrir a sessão do dia · **zero mudança de comportamento** · abre **P-22**

**O que motivou.** A sessão de 02/09 documentou tudo que fez, e as réguas **conferem**: re-rodadas em
03/09 com `__pycache__` limpo, deram `pytest 81 passed`, smoke `3/3`, agentes `3/7 · 6/7 · 0/6 · 6/6`,
exclusões `7/7 · 7/7`, justificativas `12/21 → 15/21` — idênticos ao registrado. **Nenhum número
documentado é falso.** A auditoria procurou o inverso: o que a fila de 01/09 mapeava e o `plano.md`
não herdou.

### 1. `justificativa_negocio` não estava em lugar nenhum (vira P-22)

Item 4 da fila de 01/09. **Zero ocorrências em `plano.md`**, e nunca foi P-número. `recommendation.py:63`
tem texto curado para **5 das 16** tecnologias; as outras 11 caem num fallback formulaico que o próprio
comentário chama de stub e adia **"para a M4"** — fase que não existe em nenhum arquivo vivo do projeto.
**A dívida não estava atrasada: estava sem dono.**

E é o **campo 3 dos 7 obrigatórios** do TAPI, vizinho exato do campo que D-086 consertou. A varredura
de completude de 02/09 passou por ele sem vê-lo, porque verificou que *"os 7 campos existem em
`Recomendacao`"* — **existência, não qualidade.** É a fresta que toda varredura de presença deixa.

**Destino: FAZER em 05/09**, na tarde, sob a regra de corte. Curadoria das 11 restantes (~1 h,
determinístico, zero latência, e `test_justificativa_negocio_fala_da_tecnologia_recomendada` já é a
rede), **ou** o campo declara por escrito que é derivado da dor. O que não pode continuar é **prometer
curadoria e entregar fórmula**.

### 2. A P-21 nasceu dizendo que não há gabarito, e o TAPI dá um

A ficha dizia *"nada o mede hoje"*. Verdade sobre o código, **falso sobre o material**:
`contexto/01-tapi.md:143` lista **7 regras de exemplo** — pares setor/dor → tecnologia esperada — e a
fila de 01/09 já as apontava como *"gabarito pronto"*. A regra `Saúde → Clara, MONAI, NIM, NeMo
Guardrails, AI Enterprise` cobre **4 das 8 startups** da base (Axenya, Doutor-AI, Laura, e saúde
corporativa) e **reprova exatamente o caso que abriu a P-21**: Morpheus não está na lista.

**A ressalva que decide, e fica junto:** das 7 regras, só 1 ou 2 têm startup na base de hoje — não há
robotics nem dados tabulares. **O gabarito engorda com a base**, o que amarra a P-21 ao item da base
de 03/09, não à interface.

### 3. Três justificativas do plano se apoiam em números de modelo morto — e agora está escrito

D-059 (27/08), D-060 (27/08) e D-072 (28/08) foram medidas no `nemotron-3-nano-30b-a3b`, morto em
01/09 (D-079). O handoff daquele dia escreveu que **não valem até serem refeitas no modelo vivo**, e
só `--geracao` foi refeita (23/24, D-040). O plano voltou a usá-las: **P-12** aceita citando o teto de
D-060, **P-11** fecha citando o braço de D-059, **P-09** cita o placar do juiz.

**Decisão: ACEITAR o não-re-medir, e dizer isso no documento.** ~200 chamadas a um modelo de mediana
51 s, a 4 dias do vídeo, para decidir promoções que o plano já decidiu não fazer. **O que muda por
estar escrito é a frase da defesa:** *"o juiz passou o critério em 28/08, no modelo anterior, e não
foi re-medido"* — não *"o juiz passa"*.

### 4. "Muda o que o vídeo mostra" tinha voltado, sete linhas acima de onde D-084 limpou

`plano.md` §3.3 item 2 seguia pedindo *"P-10: qual das três opções"*, com prazo **hoje** — P-10 fechou
em 02/09 — e com a coluna de razão *"muda o que o vídeo mostra"*. **D-084 limpou a tabela da §5 e não
a linha da §3.3.** É a terceira aparição do padrão de D-078: o critério banido volta pela porta que a
limpeza anterior não fechou.

**O que isso ensina sobre a própria correção:** banir um critério exige **varrer o documento inteiro
pelo texto dele**, não corrigir o lugar onde ele foi notado. Um `grep` por *"vídeo"* no `plano.md`
teria achado isto em 02/09, no mesmo minuto.

### O erro que esta auditoria cometeu, e fica registrado

Afirmei que a ACEITAR da P-09 *"promete um número que não existe"*. **Existe:** D-072, 28/08, precisão
`83-96%` contra alvo de `64%`, no log. Eu li *"`--juiz` segue não coletado"* da `sessao-atual.md` — que
é sobre a **re-medição** — como se fosse sobre a medição. O achado verdadeiro é o do item 3, e é **mais
fraco** do que eu havia afirmado: não é número inventado, é número válido de instrumento morto.
**Foi o Vinícius quem pediu a reconferência antes de autorizar a edição** — o quinto achado caiu ali.

**Alternativa descartada:** empurrar as quatro correções para a sessão de documentação de 06/09.
Rejeitada porque o `plano.md` é o primeiro arquivo que toda sessão abre e três dos quatro defeitos
**desviam trabalho** — um manda decidir o que já foi decidido, outro esconde um gabarito que existe, o
terceiro deixa um campo obrigatório fora da fila. Corrigir agora: 15 min. Manter: uma sessão inteira
orientada por um mapa errado.

## D-089 — O teste de clone limpo: o sistema roda do zero, e a execução achou 4 defeitos que a leitura não acharia
**Data:** 03/09/2026 · clone real do GitHub, ambiente novo, banco novo · **nada foi consertado nesta sessão, de propósito**

**O protocolo, e ele importa:** `git clone` do **remoto** (não cópia local, para pegar o que só
existe na minha máquina), conda 3.12 novo, `.env` **apenas** com o que o `.env.example` documenta,
banco `case_nvidia_clone` separado do de produção. Cada linha abaixo é comando e saída, não leitura.

### O que FUNCIONA — e isto fecha um eliminatório

| passo | resultado |
|---|---|
| `pip install -r requirements.txt` em Python **3.12.13** novo | **exit 0**, zero conflito nos 57 pinos |
| `psql -f scripts/init_db.sql` em banco novo | **exit 0** · 3 tabelas · `vector`, `pg_trgm`, `unaccent` |
| `seed.py --verificar-urls` | **24/24 URLs em 200** · 8 startups · 24 documentos — confirma que o seed é auto-contido sem `data/raw/` |
| `ingerir_nvidia.py` | **175 estruturais + 202 de controle = 377**, 16 tecnologias — **a mesma contagem do corpus medido** |
| `avaliar_rag.py --validar` | **24/24 válidas** contra o corpus baixado hoje |
| `python -m src.graph` | **exit 0**, briefing completo, com evidência e URL em toda conclusão |

**"Projeto que não executa" deixa de ser risco por suposição.** Um clone do repositório público roda
ponta a ponta hoje.

### O que NÃO está escrito — a lista que vira o README de 06/09

1. **O repositório não sabe criar o próprio ambiente.** Não há `environment.yml`, `pyproject.toml`
   nem Makefile. O `conda activate case-nvidia` do `CLAUDE.md` pressupõe um ambiente que ninguém
   além de mim tem, e **a versão do Python existe só como comentário** (`CLAUDE.md:179`).
2. **`createdb case_nvidia` não está em lugar nenhum.** `init_db.sql` **não** cria o banco, e o
   comando documentado (`psql -d case_nvidia -f ...`) falha em máquina nova. Eu precisei saber disso.
3. **O caminho Docker é bom e a `DATABASE_URL` dele não está escrita.** O compose sobe
   `postgres:postgres@localhost:5433`; o `.env.example` traz `localhost:5432` sem usuário; o
   `CLAUDE.md` diz *"ajustar `DATABASE_URL`"* **sem dar a string**.
4. **`COHERE_REQ_POR_MIN`, confirmado mecanicamente:** das **17** env vars lidas por `config.py`, é a
   **única** ausente do `.env.example` — e nenhuma documentada deixou de ser lida. O item do plano
   estava correto e completo.

### O que a EXECUÇÃO achou, e a leitura não acharia (D-083 de novo)

**1. O corpus DERIVOU em menos de 24 horas — agora medido, não temido.** Mesma contagem (175
estruturais), **hash diferente**. A página do TensorRT-LLM rolou a lista de posts: entraram
`[08/29] ADP Balance Strategy` e `[09/02] Accelerating Video Generation…`, e entrou lixo novo
(`✨ ➡️ link`). **O gabarito sobreviveu — 24/24 — porque a deriva bateu em RUÍDO, não em âncora.**
Isso muda a natureza do item "as 16 fontes não estão cacheadas": não é risco hipotético para a
semana que vem, é **deriva diária observada**, e a próxima pode pegar uma âncora. Cada dia sem cache
afasta o corpus da web do corpus que produziu os números de D-068.

**2. O briefing do usuário imprime um ponteiro interno de decisão.** `evidence_validator.py:210`
monta, e `briefing.py:258` imprime, a linha: *"mínimo sobre as 9 afirmações do perfil, incluindo 6
dor(es) observada(s) — **ver D-059** para por que este agregado é o defeito que a régua mede em
0/6"*. A intenção era honesta (*"o defeito NOMEADO em vez de escondido"*), mas **o gerente lê isso, e
o vídeo mostra isso**. Sharpen direto na **P-11**: o campo não é só sem informação, ele vaza nota de
engenharia para dentro do entregável.

**3. O seletor de D-086 é atraído por barra de badges.** A `justificativa_tecnica` de uma
recomendação saiu como `Sensor simulation pipelines… / GitHub Workflows Documentation / Python |
PyTorch`. A heurística é **densidade de marcador técnico** — e `Python | PyTorch | NumPy` é a linha
mais densa da página inteira. **Não é regressão** (D-086 mediu 4/6 servindo, e este é outro run), é
o **mecanismo** da falha restante, agora com evidência e chunk de origem.

**4. Quatro números que já não são verdade sobre o sistema que roda hoje** (contra D-073):
`CLAUDE.md:144` e a tabela de risco de **D-087** dizem **381 vetores** — são **377**; a linha da
**P-18** diz `LLM_TIMEOUT=30 / ~90 s` — roda **120** desde D-080; `plano.md` §7 diz `src/` com
**3.783 linhas** — são **4.208**.

### Por que nada foi consertado aqui

A sessão do dia é em plan mode, à parte. **O clone limpo é instrumento de descoberta, e consertar
dentro dele misturaria achado com correção** — o mesmo motivo pelo qual a régua de D-086 foi
commitada antes do seletor. Os quatro achados entram no plano com dia; os dois de código (2 e 3) são
da sessão do dia, não desta.

**Alternativa descartada:** rodar o clone só até `pip install`, para poupar API. Rejeitada — os
quatro achados **estão todos depois da instalação**, e três deles só aparecem com o grafo rodando.
Um teste de clone que para antes de executar teria confirmado exatamente o que a leitura de código
já dizia, que é a falha que D-083 nomeou.

---

## D-090 — A base vai a 30, e as fontes boas não eram as que a documentação dizia
**Data:** 03/09/2026 · executa D-062 · **8 → 30 startups, 24 → 93 documentos, 93/93 `url_fonte`**

**A M3 fechou.** 30 startups, 93 documentos, **toda `url_fonte` resolve**. Distribuição por tipo:
50 notícia · 33 site · 7 blog · 2 release · 1 vaga.

**O metadado passou por uma varredura própria, e ela achou o que a curadoria manual perdeu:**
`ano_fundacao` foi de **12 para 18 de 30** e `localizacao` de 5 para 9, procurando padrão de
frase (`Fundada em`, `Criada em`, gentílico) em vez de ler documento por documento. Cada
achado foi conferido pelo SUJEITO da frase antes de entrar — e três foram REJEITADOS por isso:
o `2004` da Produzindo Certo é a ONG Aliança da Terra; o `Buri, interior de São Paulo` da
iRancho é a origem dos ANIMAIS, não a sede; o `agro paulista` dela é o family office
investidor. **O que segue `null` segue `null` de propósito** — a Solinftec diz *"criada há 18
anos"*, que é idade e não ano, então o Briefing reporta *"requisito não verificado"*, e é
verdade. **O ganho é concreto:** com `2007` literal, a **Agrotools** passou a sair
`NÃO ELEGÍVEL` com o motivo escrito — *"fundada em 2007, 19 anos"* — em vez de um `?`.
**E uma nota de curadoria de 22/08 foi CORRIGIDA por evidência:** a da Axenya dizia *"NÃO
consta o rótulo da rodada"*, e o documento `site` dela diz *"rodada Serie A da Axenya"* — a
nota antiga tinha olhado só as notícias. Por ser fixture de gabarito, a mudança foi tratada
como material medido: critério fixado antes, e a régua reproduziu inteira.

**O que ordenou a fila não foi contagem — foi consulta que devolvia zero.**
1. **fintech (5)** e **agro (8)**: as duas consultas que devolviam **zero** em 03/09.
2. **voz/call center (3)**, **robótica (4)** e **dados tabulares** (Agrotools): as três regras de
   exemplo do TAPI sem startup (D-088). Cada uma que entrou tornou a **P-21** medível.
3. **As cinco chaves de `SETORES` que estavam VAZIAS** — `logística`, `jurídico`, `indústria`,
   `educação`, `varejo`. Isto só apareceu porque a base cresceu: **o planner tinha oito setores
   no vocabulário e cinco não casavam empresa nenhuma.** É o mesmo defeito de `"fintechs"`
   devolvendo zero, em cinco lugares ao mesmo tempo. **Hoje as 10 chaves têm empresa.**

**As quatro exclusões do Inception ganharam caso REAL, e antes só tinham frase sintética:**
consultoria (Deal, já existia) · **capital aberto → Zenvia** (Nasdaq) · **cripto → Liqi**
(stablecoin BRLD) · **> 10 anos → Agrotools**. O valor do filtro está na recusa, e
recusa medida com frase que eu mesmo escrevi não é recusa medida.

> **CORREÇÃO DE 03/09 (D-097):** a redação original desta linha dizia *"Agrotools e Solinftec"*, e
> **contradizia o parágrafo sete linhas acima**, que explica corretamente por que a Solinftec fica
> `null`. Ela sai **ELEGÍVEL** na varredura das 30 — verificado no run de produção. A exclusão por
> idade tem **um** caso real. A Solinftec é outra coisa, e mais interessante: é o **caso-limite da
> política de literalidade**, uma empresa de 18 anos que o sistema deixa passar de propósito
> porque o documento dá idade e não ano.

**O QUE CUSTA A CURADORIA NÃO É A EMPRESA — É O 3º DOCUMENTO.** `seed.py` exige 3 documentos e
**≥ 2 tipos distintos**. Achar a empresa é barato; achar a terceira peça é o gargalo. Quatro
empresas boas caíram **depois de coletadas**, cada uma por um motivo diferente:
- **Aro** (fintech de agente de crédito, 2 matérias ótimas) — `aro.com.br` é de uma **fabricante
  de embalagens metálicas desde 1943**. O portão de curadoria pegou; a pressa não teria pego.
- **Creditas** — 3 matérias, **um tipo só**; o site devolve 221 caracteres e todo caminho dá 404.
- **alt.bank** — `/sobre` e `/guard` devolvem **os mesmos 7.843 caracteres da home**: é SPA. Usar
  os dois seria fabricar diversidade documental — 3 documentos que são 1.
- **ESGreen** — e esta dói: os documentos dizem que ela **já é membro do NVIDIA Inception** e
  treinou modelo próprio na infraestrutura da NVIDIA. Só existem 2 documentos públicos dela.

**A DESCOBERTA QUE MUDA A ROTA, E FOI MEDIDA, NÃO LIDA.** `04-ecossistema-br.md` ordena os
veículos por **disponibilidade** (grátis, sem paywall) e elege o Brazil Journal *"melhor veículo
para este projeto"*. Rodando `coletar.py` neles, a ordem que importa é outra:

| domínio | antes | depois | mecanismo |
|---|---|---|---|
| braziljournal.com | **48** | **4.110** | o único `<main>` é uma tarja de teaser; os 9 `<article>` são cards |
| agfeed.com.br (agro) | **384** | **7.122** | não há `<main>`; o 1º `<article>` é o card de chamada |
| startups.com.br | 5.062 | 5.390 | — |
| mobiletime.com.br | 5.553 | 6.163 | — |
| portal.clientesa.com.br | 3.245 | 4.649 | — |

`extrair()` fazia `find("main") or find("article") or body` — **preferência por tipo de tag,
desempatada pela ORDEM no documento**. Trocado por **o maior bloco** entre `main`, `article` e
`body`. As duas melhores fontes do país para agro e para negócios estavam mortas para este
pipeline, e ninguém sabia porque ninguém tinha rodado.
**Alternativa descartada:** restringir a curadoria aos 3 domínios que já funcionavam — economiza
15 min e custa o setor agro inteiro.
**Por que é barato:** `coletar.py` é auxiliar de CURADORIA, não caminho de execução. Nenhum agente
o chama, `seed.py` lê YAML, e os `conteudo_texto` já congelados não mudam. **Não move um número.**

**O CUSTO DESSA MUDANÇA É REAL E FOI PAGO À MÃO: teaser de terceiro.** O bloco maior traz post
relacionado junto. Foi construído um auditor (`MARCADORES`, 80+ manchetes de terceiros observadas)
que varre as 30 fixtures. **Primeira passada: 11 ocorrências em 4 fixtures.** As 5 minhas foram
corrigidas por recorte. As outras **6 estavam na base desde 22/08** — `"Dell: Crise de
componentes"` e `"ASUS quer estar entre os líderes"` dentro da **Axenya** e da **Doutor-AI**,
colhidas pelo seletor antigo e nunca vistas. Um segundo auditor conferiu que **nenhuma fixture
cita outra empresa da base**. Hoje: **zero ocorrências**.
**A limpeza das duas antigas foi tratada como mudança em material MEDIDO:** critério fixado antes
— *só entra se `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1 · 49%/100% ·
discriminação 8/8` reproduzirem inteiros*. Reproduziram. O lixo era **inerte para a régua e vivo
para o briefing**, que é exatamente o que D-086 e D-089 vinham perseguindo.

**D-062 SÓ EXISTIA EM PROSA, E ISSO ERA MENSURÁVEL.** As 22 novas entram como DADO, sem gabarito.
Mas `avaliar_agentes.py` engolia `data/seed/*.yaml` inteiro, e quebrava de dois jeitos — um
barulhento e um silencioso:
- `--validar` saía com **exit 1**, uma linha por fixture nova;
- **a precisão despencava sem avisar.** Sem `dores_esperadas`, `esperadas` vira conjunto vazio e a
  fixture entra na média como `0.0`. **Contrafactual medido:**

| | classe | precisão | recall | discriminação |
|---|---|---|---|---|
| régua filtrada por `gabarito` (o que entrou) | 3/7 | **49%** | 100% | 8/8 |
| todas as fixtures (o comportamento anterior) | 3/7 | **24%** | 100% | 15/16 |

**`classe` e `recall` ficam IDÊNTICOS** — nada no placar acusaria. A régua seguiria imprimindo um
número com cara de medição, pela metade. **Corrigido:** `regua = [f for f in fixtures if
f.get("gabarito")]` alimenta `validar`, `medir` e os dois tetos.
**`evidencia_literal` ficou sobre as 30, de propósito:** ela não pergunta ao gabarito, pergunta se
todo trecho citado ocorre **verbatim** no documento — o modo de falha mais provável de 69
documentos colados numa sessão. **Passou nas 30.** E não foi só sorte: as fixtures novas foram
montadas por **script que fatia o arquivo do `coletar.py` por número de linha**, nunca
redigitadas. Paráfrase é impossível por construção.

**UM DEFEITO DE RASTREABILIDADE, ACHADO PELO PRÓPRIO PORTÃO.** `seed.py --verificar-urls` reprovou
a **Laura Networks**, fixture da base desde 22/08. Medido: `HEAD` entra em laço de redirect;
**`GET` responde 200 com 63 mil caracteres**. A página está viva. O verificador já sabia que
*"alguns servidores recusam HEAD"* e caía para `GET` — **mas só quando a recusa vinha como STATUS
≥ 400. Quando vem como EXCEÇÃO, o `except` de fora engolia a tentativa e o fallback nunca
rodava.** Falso NEGATIVO de rastreabilidade é pior que falso positivo: manda o curador trocar uma
fonte legítima. Agora só falha quando os DOIS métodos falham, e o log diz qual respondeu.

**`SETORES` ganhou `voz` e `robótica`** — e a chave TEM de ocorrer literal na coluna `setor`,
porque `buscar_startups` filtra com `s.setor ILIKE '%<chave>%'`. **É a armadilha que fazia
"fintechs" devolver zero, uma casa adiante:** `setor: agtech` não casaria a consulta "agro". Por
isso os rótulos saíram `agro — agricultura digital`, `voz e call center`, `varejo — operação de
lojas`.

**O QUE A EXECUÇÃO MOSTROU, E A LEITURA NÃO MOSTRARIA (D-083):**
1. **P-12 deixou de ser um número e virou uma cena.** A **Core AI** — empresa cujo produto É
   modelo de crédito com IA — sai `non-AI`, e com ela Conta Simples e Iniciador. Não é regressão:
   é o gargalo de vocabulário que D-060 mediu, agora legível. **É D-078 confirmado por dado novo:**
   8 fixtures não discriminavam o bastante para isso aparecer.
2. **O seletor de D-086 continua atraído por mobília de página.** Na NeMo saiu *"More Customer
   Stories / View All Blogs / View All Sessions"*; na TensorRT-LLM, linha de changelog do README
   com emoji. Mecanismo de D-089, em dado novo. **Munição para (b) em 04/09.**
3. **P-22 ganhou exemplo concreto:** `NEGOCIO` é indexado por TECNOLOGIA, não por dor. NeMo
   recomendada para a dor `custo` traz o texto de `avaliação`.
4. **A Ecotrace saía `NÃO ELEGÍVEL` por 'cripto'** — ela rastreia boi com blockchain. Virou D-091.
5. O ponteiro `ver D-059` segue impresso no briefing do usuário (P-11, uma linha, 05/09).

**ERRO DE MÉTODO MEU, MEDIDO E REGISTRADO:** **47 de 159 fetches (30%) voltaram vazios**, quase
todos de **chutar caminho de URL** (`/sobre`, `/quem-somos`, `/carreiras`) em vez de buscar a URL.
Usei busca para achar empresa e adivinhação para achar documento — os dois pedem busca. Custou
~25 min e é a primeira coisa a corrigir se a base voltar a crescer.

**Alternativa descartada para o número:** forçar 30 com empresas de 2 documentos. Rejeitada —
`seed.py` reprovaria, e afrouxar o piso de 3 documentos trocaria a única promessa que o sistema
faz (rastreabilidade) por uma linha de contagem.

---

## D-091 — `blockchain` sai da lista de cripto, `stablecoin` entra: a lista estava errada nas duas direções
**Data:** 03/09/2026 · achado pela execução sobre a base nova (D-090) · repete a forma de D-048

**O defeito, achado rodando o grafo:** a **Ecotrace** — agtech que rastreia boi e soja — saía
**`NÃO ELEGÍVEL` por 'cripto'**, porque `EXCLUSOES["cripto"]` continha `"blockchain"`. Numa
ferramenta cujo trabalho é achar startups para o Inception.

**É D-048 de novo, com outra palavra.** D-048 tirou `"token"` da lista porque o termo é ambíguo
entre cripto e inferência de LLM, e *"custo por token"* derrubava qualquer startup de
infraestrutura. `blockchain` tem a **mesma forma: é nome de TECNOLOGIA, não de IDENTIDADE.**

**Por que o veto de terceiro (D-085) não alcançava:** ele responde *"de quem a frase fala?"* — e
aqui a frase fala mesmo da própria empresa. A pergunta que faltava é outra: **"ser isto DEFINE a
empresa?"**. São dois eixos de erro diferentes, e a lista tinha o segundo.

**O ERRO QUE EU COMETI NO MEIO DO CONSERTO, E ELE VALE MAIS QUE O CONSERTO.** Antes de remover
`blockchain`, escrevi na régua um caso-rede para garantir que a Liqi (cripto de verdade)
continuaria excluída. **Escrevi a frase eu mesmo**, já contendo `"tokenização de ativos"`. A régua
deu **8/8** — e a Liqi REAL saiu **ELEGÍVEL** no grafo. Uma rede tricotada em volta da resposta.
**É exatamente por isso que `origem` é campo obrigatório em `exclusoes.yaml`**, e eu passei por
cima da própria regra do arquivo. Os dois casos hoje são **frases LITERAIS** de `data/seed/liqi.yaml`.

**O que o caso real revelou, e é maior que o termo:** a Liqi diz literalmente no site
*"Infraestrutura para sua empresa oferecer **criptomoedas**, stablecoins e tokens de ativos"* —
e `criptomoeda` **já estava na lista**. Ela passou assim mesmo. **Motivo: `elegibilidade()` varre
`perfil.afirmacoes[*].evidencias[*].trecho`, não o documento.** O filtro só enxerga o que o
Extractor por acaso citou. A exclusão da Liqi funcionava **por acidente**: `blockchain` caiu num
trecho de evidência, `criptomoeda` não. **Isso vira P-23** — não se conserta hoje, porque mudar o
que `elegibilidade()` lê é alteração de arquitetura em componente medido a 4 dias do vídeo.

**A correção, nas duas direções:** sai `blockchain` (tecnologia); entram **`stablecoin`** (emitir
stablecoin é identidade, sem ambiguidade) e **`ativos virtuais`** (o termo LEGAL brasileiro, Lei
14.478/SPSVAs, literal nos documentos). **A lista estava errada dos dois lados: tinha um termo de
tecnologia excluindo quem não é cripto, e não tinha os termos que nomeiam quem é.**

**Critério fixado ANTES, e o caso entrou na régua antes do conserto** — a régua caiu para `7/8` no
lado do falso positivo, apontando a Ecotrace, e só então o termo saiu:

| | falso negativo | falso positivo |
|---|---|---|
| antes | 7/7 | 7/7 |
| com os casos reais novos, antes do conserto | 8/8 | **7/8** |
| depois | **9/9** | **8/8** |

E o resto não se moveu: `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1 · 49%/100%` ·
justificativas `12/21` trivial e `15/21` seletor · `pytest` 81 passed. No grafo: **Liqi
`NÃO ELEGÍVEL` por `stablecoin`, com evidência e fonte; Ecotrace `ELEGÍVEL`.**

**Alternativa descartada:** manter `blockchain` e exigir um segundo termo cripto na mesma frase.
Rejeitada por ser regra mais complicada para o mesmo efeito — e porque D-048 já tinha estabelecido
o precedente de **remover o termo ambíguo** em vez de qualificá-lo.


---

## D-092 — `parceria entre`: o veto de terceiro estava certo, faltava a preposição
**Data:** 03/09/2026 · achado LENDO um briefing inteiro, não por grep (D-083)

**O defeito:** a **Automni** — deep tech de robôs móveis autônomos — saía **`NÃO ELEGÍVEL` por
'consultoria'**, e a evidência impressa era *"destacando a **parceria entre** a Davinci -
Consulting & Tech e a Automni"*. O termo está no **nome de uma parceira**.

**D-085 previu exatamente este caso** — a nota dele diz *"o sujeito é um PARCEIRO"* — e pôs
`parceria com` em `MARCADORES_DE_TERCEIRO`. A frase real diz `parceria ENTRE`. **O escopo de
frase, que é o que faz o veto generalizar, estava certo; faltou a variante da preposição.**
Não é falha do desenho: é o custo declarado dele. Lista de marcadores OBSERVADOS só cobre o que
já se viu, e é por isso que ela precisa de base grande — com 8 fixtures esta variante não existia.

**Caso REAL na régua antes do conserto**, como em D-091: o lado do falso positivo caiu para
**9/10**, apontando a Automni, e só então o marcador entrou. Depois: **9/9 e 9/9**, com 9 dos 18
casos vindo de fixture. E o briefing ficou mais verdadeiro em vez de mais permissivo — a Automni
continua `NÃO ELEGÍVEL`, agora **só pelo motivo certo**: *"fundada em 2014, 12 anos"*.

**O que NÃO foi consertado, e fica escrito:** o site da Automni também traz, numa lista de
entregas, o bullet *"Consultoria especializada para implantação e operação"* — serviço dela
mesma. É a forma do caso Axenya (*"Integramos consultoria..."*), que D-085 resolveu com o marcador
`integramos`. Aqui não há marcador nenhum: é um bullet solto, e a frase sozinha não diz de quem é
o serviço. **Distinguir "vendo consultoria como parte da entrega" de "sou uma consultoria" não é
lista de palavras — é leitura de contexto.** Hoje ele não dispara porque não caiu em trecho de
evidência (P-23), o que é sorte, não desenho.

---

## D-093 — A cota mensal do Cohere ACABOU, e a contingência foi medida
**Data:** 03/09/2026 · **causa: as execuções desta própria sessão**

**O fato, com a mensagem do fornecedor:** `HTTP 429` com
*"You are using a Trial key, which is limited to **1000 API calls / month**"*. Não é o teto de
10 req/min de D-068, que recupera em ~26 s — é a **cota do mês**, e `retry-after` vem ausente.

**A causa é minha e fica registrada:** a sessão de 03/09 rodou o grafo ~15 vezes e o `pytest`
5 vezes, e **cada run do grafo faz 20-30 chamadas SEQUENCIAIS de rerank** (D-068). Foram
centenas de chamadas para verificar a base — trabalho legítimo, com um custo que ninguém estava
contando. **O que faltava era um contador**, e nenhum dos instrumentos do projeto olha para o
saldo: `smoke_nvidia.py` valida as 3 capacidades da stack NVIDIA e não toca no Cohere.

**A contingência existe por desenho e foi MEDIDA agora, não suposta:**
- `RERANK_PROVEDOR=nenhum` — o grafo roda ponta a ponta, emite recomendações com evidência e
  fonte, e o filtro do Inception decide igual.
- **`pytest`: 81 passed em 6,5 s**, contra 150-460 s com o Cohere ligado. **O throttle era o
  gargalo do suite inteiro** — e isso ninguém sabia porque ninguém tinha rodado sem ele.
- O que se perde está medido em D-064/D-068: o **denso puro faz 95% r@1 e 100% r@3** sozinho. O
  reranking comprava o critério estrito, não a capacidade de responder.

**O que isso decide, e é decisão do Vinícius:**
1. **Assumir que a cota NÃO volta antes de 09/09.** "1000/mês" pode ser mês corrido da criação da
   chave — não dá para saber sem o dashboard, e planejar contando com isso é o mesmo erro que
   D-015 cometeu ao assumir que "Cohere é pago" sem verificar.
2. **O vídeo de 07/09 grava com `RERANK_PROVEDOR=nenhum`, e isso é vantagem narrativa, não
   desculpa:** o provedor está isolado em `src/config.py` desde o começo, e trocar por env var é
   exatamente o que três EOLs (D-013, D-046, D-064) compraram. Mostrar o sistema rodando com o
   passo 7 desligado **demonstra a arquitetura** — e o número honesto ao lado é `95% r@1` do
   denso puro.
3. **`avaliar_rag.py` não pode ser re-medido** nos braços com rerank. Os números de D-068 seguem
   válidos como história; re-medição fica bloqueada por fornecedor, como já aconteceu em D-073.

**Alternativa descartada: abrir outra trial key.** É contornar o limite do fornecedor por outra
porta, e o TAPI é um processo seletivo — a resposta honesta na arguição (*"a cota acabou e o
sistema roda sem o passo 7, aqui está a medição"*) vale mais que uma demo que depende de burlar
um teto. **Alternativa em aberto para o Vinícius:** chave de produção paga, se ele quiser o
caminho completo no vídeo.

**Regra operacional que nasce daqui:** antes de qualquer sessão que rode o grafo em série,
`RERANK_PROVEDOR=nenhum` é o **default de desenvolvimento**. O Cohere entra quando se quer medir
o passo 7, e aí a chamada é deliberada — a mesma disciplina de `--juiz` e `--truncar-pool`.

---

## D-094 — A varredura das 30 de uma vez: `capital aberto` era B3-cêntrica, e eu criei um falso positivo consertando cripto
**Data:** 03/09/2026 · **o método é a decisão**

**O QUE MUDOU FOI COMO EU PROCUREI.** D-091 e D-092 saíram de LER briefings — e ler briefing é
amostragem. Depois do terceiro achado da mesma forma (conceito certo, vocabulário estreito),
parei de amostrar e escrevi uma varredura que roda `extractor` + `elegibilidade()` **nas 30 de
uma vez, sem grafo e sem API**, e imprime o veredito de cada uma numa tabela. **Ela achou dois
casos na primeira execução, e um deles eu tinha acabado de criar.**

**ACHADO 1 — `capital aberto` era B3-CÊNTRICA, e isso era o caso COMUM, não o exótico.**
A lista tinha `"listada na b3"` e `"ipo concluído"`. A **Zenvia** está na **Nasdaq desde 2021** e
saía **ELEGÍVEL**. Metade das brasileiras que abrem capital lista fora: Nubank, VTEX e PagSeguro
na NYSE, StoneCo, XP e Zenvia na Nasdaq. A frase *"Listada na Nasdaq, a companhia registrou um
crescimento de 126% no Ebitda"* está literalmente num trecho de evidência — o filtro tinha tudo
para vê-la e não tinha a palavra.
**Descartado `"listada na"` genérico:** casaria *"listada na Forbes"*, e o veto de terceiro não
ajuda — ele responde de QUEM a frase fala, não o que ela significa. Entraram as bolsas por nome
mais `companhia aberta` (o termo do direito societário) e `abriu capital`.

**ACHADO 2 — EU CRIEI UM FALSO POSITIVO EM D-091, E A VARREDURA O PEGOU NO MESMO DIA.**
Ao pôr `stablecoin` na lista de cripto, a **Iniciador** — infraestrutura de Open Finance e Pix —
passou a ser recusada por *"disputada por gigantes de cartões e pelo **mercado de stablecoins**"*.
O termo nomeia o **mercado**, como contexto competitivo. **Não é nenhuma das duas categorias que
D-085 previu:** não é "outra empresa" (categoria 1) nem "somos consumidores" (categoria 2). É uma
terceira forma de sujeito, e virou a **categoria 4** de `MARCADORES_DE_TERCEIRO`.
**Descartado `"mercado de"` genérico:** *"atuamos no mercado de criptomoedas"* É identidade, e o
marcador genérico a vetaria — trocando um falso positivo VISÍVEL por um falso negativo
SILENCIOSO, que D-052 nomeou como o pior dos dois.

**A régua, com os dois lados e casos REAIS, ao longo do dia:**

| momento | falso negativo | falso positivo | casos |
|---|---|---|---|
| início de 03/09 | 7/7 | 7/7 | 14 (5 de fixture) |
| D-091 (cripto: `blockchain` sai, `stablecoin` entra) | 9/9 | 8/8 | 17 |
| D-092 (`parceria entre`) | 9/9 | 9/9 | 18 |
| **D-094 (Nasdaq + mercado de stablecoin)** | **10/10** | **11/11** | **21 (11 de fixture)** |

**De 5 casos de fixture para 11.** A régua deixou de ser majoritariamente sintética.

**O VEREDITO DAS 30, e ele está certo empresa por empresa:** 4 por **idade** (Agrorobótica 2015,
Agrotools 2007, Automni 2014, JetBov 2015) · 1 **consultoria** (Deal) · 1 **cripto** (Liqi) ·
1 **capital aberto** (Zenvia). As outras 23 passam, **incluindo Ecotrace e Iniciador**, que eram
os dois falsos positivos do dia.

**A LIÇÃO DE MÉTODO, E ELA É A DECISÃO:** três defeitos da mesma forma escaparam de duas sessões
de auditoria e de dezenas de greps. **O que os achou foi rodar o componente sobre a base
inteira** — 30 empresas, um `print` por empresa, zero API, poucos segundos. D-083 diz *"rode o
sistema"*; isto é o corolário: **rode-o sobre TUDO, não sobre uma amostra**, porque a amostra
esconde exatamente o caso que você não imaginou. E o mais importante: **a varredura pegou um
defeito MEU, introduzido 40 minutos antes.** Instrumento que só confirma o que você espera não é
instrumento.

**Alternativa descartada:** parar depois de D-092, já que a régua estava 9/9 e 9/9. Rejeitada —
a régua mede o que está NELA, e os dois defeitos deste registro não estavam. **Régua verde não é
prova de ausência; é prova sobre os casos que alguém pensou em escrever.**

---

## D-095 — A base de 30 mede a P-12 pela primeira vez: `AI-native` 1, `AI-enabled` 20, `non-AI` 9
**Data:** 03/09/2026 · varredura das 30, zero API · **medição, não promoção** (D-078)

**Um radar de startups AI-native que acha 1 AI-native em 30.** É a primeira vez que este número
existe: com 8 fixtures a régua dizia `classe 3/7`, o que é placar contra gabarito e não diz nada
sobre a **distribuição**. A base de 30 diz.

| classe | n | quadrante |
|---|---|---|
| AI-enabled | **20** | prospect-de-evolucao |
| non-AI | **9** | fora-do-funil |
| AI-native | **1** (JetBov) | sweet-spot |

**ACHADO 1 — o degrau `2a` é inalcançável para o gênero de documento da base, e agora tem número.**
`PROFUNDOS` tem 13 marcadores (`cuda`, `gpu`, `tensorrt`, `triton`, `vllm`, `quantiz`,
`self-hosted`, `on-premise`, `inferência`, `latência`, `throughput`, `mlops`, `observabilidade`) e
o degrau exige **≥ 3 distintos**. Medido nas 30: **29 têm ZERO. Só a Maritaca AI tem 3.**

**ACHADO 2 — a hipótese óbvia foi TESTADA E REFUTADA.** `04-ecossistema-br.md` diz que *"a vaga é
o documento mais honesto sobre a stack real"*, e a base tem **1 vaga em 93 documentos**. Parecia a
causa. Não é:
- **página índice de carreiras**: 0 marcadores em 3 testadas (Tractian, Zenvia, Conta Simples) —
  ela LISTA vagas, não as descreve;
- **descrição individual de vaga**, que é o que o texto queria dizer: **1 de 7** vagas reais da
  Zenvia tem marcadores, e são **2** — abaixo do limiar de 3.

**A leitura honesta do achado 2 é desconfortável e importante:** talvez o classificador esteja
CERTO sobre profundidade. Se nem a vaga de engenharia de uma empresa listada na Nasdaq fala de
inferência, quantização ou serving, é porque a empresa realmente não opera essa camada — ela
consome API. **Que é exatamente a tese do TAPI**, a pergunta norteadora deste projeto: *startups
que dependem só de wrappers de LLM*. O sistema pode estar medindo a realidade do ecossistema.

**MAS O RÓTULO `non-AI` ESTÁ ERRADO, E ISSO É OUTRA COISA — vira P-24.** Em produção
(`RUBRICA_EM_DEGRAUS = False`, reprovada em D-060) a regra é
`pontos = 2·autopilot + 2·dado_proprio + 1·sinal_tecnico`, e `pontos == 0 -> non-AI`. Medido:

| empresa | modelo_entrega | dado próprio | sinal técnico | pontos | classe |
|---|---|---|---|---|---|
| **Core AI** | copilot | 0 | 0 | 0 | **non-AI** |
| **Visio.AI** | **VAZIO** | 0 | 0 | 0 | **non-AI** |
| Maritaca AI | copilot | 0 | 1 | 1 | AI-enabled |
| JetBov | autopilot | 1 | 1 | 5 | AI-native |

A **Core AI** tem "AI" no nome, 5 dores de IA extraídas com evidência, e uma matéria que diz
*"usa inteligência artificial para criar modelos de crédito"* e *"usamos agentes de AI para
automatizar toda a operação"*. Ela sai **`non-AI`** porque **três detectores do Extractor voltaram
vazios**. A aritmética do classificador está sendo fiel; quem não viu foi a extração.

**O PRINCÍPIO QUE ISSO VIOLA JÁ ESTÁ ESCRITO NESTE REPOSITÓRIO, EM OUTRO COMPONENTE.**
`Elegibilidade` separa `motivos_exclusao` de `requisitos_nao_verificados`, e o docstring diz:
*"'a base não prova que tem developer' é diferente de 'a base prova que é consultoria'. Só o
segundo exclui."* É a regra 4 do Evidence Validator — **ausência de sinal não é sinal negativo**.
**O classificador faz exatamente o contrário:** detecção falha vira `non-AI`, que é uma AFIRMAÇÃO
positiva sobre a empresa — *"esta empresa não usa IA"* — emitida sem nenhuma evidência que a
sustente. E ela tem consequência: `non-AI` → `fora-do-funil` → **zero recomendações**. Nove
empresas saem do funil por silêncio da extração.

**NÃO FOI CONSERTADO, e a razão é a mesma de D-062:** as 22 novas entram **como dado, sem
gabarito**. Ajustar detectores até a Core AI "sair certa" é calibrar contra o meu próprio
julgamento sobre fixtures que eu mesmo curei hoje — o erro que D-062 existe para impedir, e o
mesmo que eu já cometi uma vez hoje com a paráfrase de D-091. **Medir não é promover** (D-078).
O que muda é a frase da defesa: não *"o classificador acerta 3/7"*, e sim **"o classificador não
distingue 'sem sinal de IA' de 'não achei sinal de IA', e isso tira 9 de 30 empresas do funil"**.

**Alternativa descartada:** ampliar `PROFUNDOS` com termos de mais alto nível (`machine learning`,
`modelo próprio`, `visão computacional`) para "consertar" a distribuição. Rejeitada por dois
motivos: (1) a lista é o eixo de **profundidade de infraestrutura**, e diluí-la com termos de
aplicação apaga a distinção que o eixo 2 existe para medir; (2) seria calibração contra as 22 sem
gabarito. Se um dia for feito, o critério vem antes, e sobre fixtures rotuladas.

---

## D-096 — Mobília de página virava citação de evidência, e a checagem passou a morar no `seed.py`
**Data:** 03/09/2026 · achado LENDO o briefing do portão, na última passada

**O que o gerente estava lendo.** A recusa de elegibilidade da Liqi vinha assim:

```
x exclusão por 'cripto': o termo 'stablecoin' aparece nos documentos falando da própria empresa
    "Pular para o conteúdo / Pular para o menu / Liqi lança stablecoin em reais “com pedigree”..."
```

**Skip-link de acessibilidade dentro da citação que sustenta uma recusa.** `coletar.py` mata menu
residual por TAMANHO (`limpar_linhas`), e estas passam por serem frases curtas — mas não curtas o
bastante. Medido nas 30: **89 ocorrências em 23 fixtures** de `Pular para o conteúdo`,
`Copiar Link?`, `Leitura:`, `Tags:`, `no seu e-mail`.

**Tratado como mudança em material MEDIDO**, porque 3 das 23 são fixtures de gabarito: critério
fixado antes — *só entra se `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1 ·
motivo 6/6 · 49%/100% · discriminação 8/8 · proibidas 10` reproduzirem inteiros, e a evidência
literal continuar ok nas 30*. Reproduziram.

**A limpeza teve DUAS formas, e a segunda quase escapou.** A primeira passada removeu linhas cuja
`.strip()` batia com a lista — 53 linhas. Sobraram 35 porque o `yaml.safe_dump` escreve a primeira
linha do escalar **na mesma linha da chave**: `conteudo_texto: 'Pular para o conteúdo`. O filtro
comparava a linha inteira e não via. Uma delas ainda usava aspas duplas com `\n` escapado.
**Lição pequena e cara:** filtro que compara linha bruta não conhece a serialização; a única prova
é reabrir o arquivo pelo parser e comparar.

**A CHECAGEM FICOU NO `seed.py`, E O LUGAR É A DECISÃO.** Duas alternativas descartadas:
- **`src/rag/limpeza.py`** — é onde "parece" que deveria estar, e é onde NÃO pode: aquele módulo é
  compartilhado com `ingerir_nvidia.py`, e mexer nele mudaria o corpus de **175 chunks**,
  invalidando o gabarito de 24 perguntas por um problema que não é dele.
- **um script de auditoria à parte** — dependeria de alguém lembrar de rodar. `seed.py
  --so-validar` já é o portão obrigatório de toda fixture nova.

Entrou também `citacoes_cruzadas()`, como **AVISO e não falha**: ela pergunta se alguma fixture
cita OUTRA empresa da base — o defeito de D-086/D-089 — mas menção legítima existe (uma matéria de
fintech pode citar o Nubank). Quem decide é o curador; o script garante que ele VEJA.

**Teste negativo feito, porque checagem que nunca falha pode estar quebrada:** reintroduzi
`Copiar Link?` numa fixture e o validador reprovou com a mensagem certa; restaurada, passa.

---

## D-097 — A revisão de 03/09: o que a auditoria confirmou, o que ela refutou, e o reranker sem fallback
**Data:** 03/09/2026 · revisão da sessão 15:01→18:23 (D-090 a D-096) · **verificada por execução**

A sessão de 03/09 rodou mais de duas horas seguidas sem revisão externa e mexeu em base, código e
log. A pergunta era direta: **houve alucinação?** A resposta importa registrar inteira, porque as
duas metades ensinam coisas diferentes.

**NÃO HOUVE ALUCINAÇÃO DE DADOS, E ISTO FOI MEDIDO, NÃO LIDO.** Para cada um dos 93 documentos,
três trechos literais tirados de 25%/50%/75% do `conteudo_texto` foram buscados na `url_fonte`
VIVA. Resultado: **39 das 50 notícias batem 3/3, e nenhuma bate 0/3.** As divergências se
concentram em documento `site`, que é página dinâmica, e nenhuma tem forma de texto inventado.
Também reproduziram exatos: as contagens (30/93, 50·33·7·2·1), D-095 (`AI-native` 1 · `AI-enabled`
20 · `non-AI` 9), o `pytest` de D-093 (81 em 6,5 s), as 10 chaves de `SETORES` com empresa, a
evidência literal das 7 recusas e as 5 frases que sustentam D-091/D-092/D-094.

**O QUE A REVISÃO REFUTOU, E ELE ERA O "DEFEITO" MAIS GRAVE DA LISTA.** O primeiro run mostrou
**NVIDIA Healthcare (ex-Clara) recomendado para a Solinftec**, uma agtech. Parecia o achado do
dia. Era artefato de ter rodado com `RERANK_PROVEDOR=nenhum`: com o passo 7 ligado, a Solinftec
recebe **NVIDIA Isaac** — e ela fabrica robô agrícola. **Regra que sai disto: nenhum defeito de
recomendação pode ser julgado com o rerank desligado.** O modo barato de D-093 é para desenvolver,
não para avaliar o que o gerente veria. Duas outras acusações minhas caíram do mesmo jeito — um
"404" que era URL que eu havia montado errada, e "5% das evidências decapitadas" que era detector
meu somando truncamento normal com o defeito (o número honesto é **1,7%**).

**O PASSO 7 TEM FORNECEDOR ÚNICO — E ISTO NÃO É ACHADO NOVO, É D-013 QUE NUNCA FOI REVERTIDO.**
A primeira redação desta entrada anunciava *"o fallback da NVIDIA MORREU"* como descoberta da
revisão. **Está errada, e o erro foi apanhado pelo Vinícius**, que respondeu *"é impossível esse
modelo ter morrido"* e mandou verificar. Verificado, o quadro é este:

- **O reranker da NVIDIA está morto desde 2026-05-18, e o D-013 registrou isso no PRIMEIRO DIA
  do projeto** — mesmo modelo (`llama-3.2-nv-rerankqa-1b-v2`), mesmo `410`, mesma data no corpo.
  Foi essa morte que trouxe o Cohere. Anunciá-la em setembro como novidade é não ter lido o
  próprio log.
- **`404` NÃO É MORTE, e o repositório já sabia disso** (D-070/D-079): o corpo diz
  *"Function …: **Not found for account** …"* — é **entitlement**. Juntei os `404` com o `410`
  e chamei o conjunto de "9 caminhos mortos". Só os que respondem `410` estão mortos.
- **A sonda NÃO tinha defeito.** Cheguei a "corrigir" `sondar_catalogo.py` supondo que o nome
  antigo devolvesse `404` e que ela estivesse medindo a própria digitação. **Medido: os dois
  nomes devolvem `410` idêntico** — o `410` vem do PATH, não do nome do modelo. A mudança foi
  descartada, e fica a lição: *conserto sem defeito medido é ruído, e o comentário que eu já
  tinha escrito nela afirmava um `404` que não existe.*

**O que sobra de verdadeiro, e basta:** `src/config.py` oferece três provedores de rerank e
**`nvidia` não é opção desde maio**. Com a cota do Cohere esgotada (D-093), houve horas em 03/09
com o passo 7 sem nenhum provedor vivo. Uma key nova restabeleceu o Cohere (`smoke_nvidia.py`
3/3). O quadro é **fornecedor único, sem rede** — e o valor disso para a arguição não é o susto,
é que a arquitetura de provedor isolado em `src/config.py` foi comprada por quatro EOLs medidos,
não por princípio.

### Os quatro consertos

**1. Mobília de página virava justificativa técnica de venda.** É a metade que D-096 deixou viva:
aquela decisão limpou as fixtures de startup e **recusou mexer em `src/rag/limpeza.py`** para não
invalidar os 175 chunks e o gabarito de 24 perguntas — razão que continua válida. O corpus NVIDIA
seguiu sujo, e saiu impresso: `Download Examples Documentation / CUDA | Docker`, `SDG for Agentic
AI / AI Agents`, `📗 DIY notebook: ➡️ link`, e um convite para o **Slack do RAPIDS** como argumento
técnico de venda.

O conserto é em `src/agents/justificativa.py`, **na penalidade e não no corpus** — local,
reversível, sem mover um vetor. Duas categorias novas, reconhecidas por **FORMA e não por
vocabulário**, e a distinção é a decisão: penalizar as PALAVRAS do mural exigiria penalizar
`inference` e `quantization`, que são justamente o conteúdo que se quer.
- `ENTRADA_DE_FEED` — a forma `* [2024/07/09]`, que é o mural de novidades do README do
  TensorRT-LLM. Pesa 3, como vitrine: as duas são a página falando de si.
- `EMOJI_DECORATIVO` — pesa **2**, e o número saiu de uma contagem: **dos 175 chunks de produção,
  11 têm emoji e os 11 são banner ou mural**, 10 do TensorRT-LLM e um do NeMo Guardrails
  (`✨✨✨ 📌 The official documentation is available at…`). Zero prosa técnica. Peso 1 perdia para
  a densidade — `✅ Deploy the optimized models with Triton Inference Server` soma três marcadores
  técnicos e é, ainda assim, item de mural.
- Mais quatro marcadores em `CONVITE`, pelo mesmo critério da revisão de D-086: só entra
  convite/navegação POR CATEGORIA. `feel free to` e `file an issue` são convite de COMUNIDADE,
  categoria que faltava; `quick-start guide` e `download examples` são navegação.

**O efeito maior foi onde eu não tinha planejado, e é o que valida a escolha do lugar:**
`pontuar()` é compartilhado com `melhor_da_pagina()` em `nvidia_rag`, então a penalidade age
também **no nível de PASSAGEM** — o defeito que o docstring de D-086 nomeia e que recorte interno
nenhum resolve. Medido: o mural do TensorRT-LLM foi de **vencedor da página a −11,61**, o pior de
16 chunks, e quem passa a representá-la é `Quantized models on Hugging Face: FP8, FP4`.

**Portão, fixado ANTES:** `--justificativas` tinha de não cair de **15/21**. Ficou em 15/21 — o
conserto tirou mobília sem mexer no placar, que é exatamente o que se queria: **o alvo era a
saída, não a régua.** Subir a régua mexendo em detector seria calibrar contra o gabarito.

**2. Pontuação órfã: 62 parágrafos que eram só um ponto.** Resto de nome próprio que a coleta
apagou. A regra nova no `seed.py` é **por FORMA** — parágrafo sem nenhum alfanumérico — e não por
lista, e a diferença para `MOBILIA_DE_PAGINA` está escrita lá: as 4 variantes medidas (`.`, `!`,
`’.`, `).`) não caberiam numa lista sem que a quinta escapasse.

**A LIÇÃO DE D-096 ME PEGOU, E A MESMA FRASE SERVE:** *filtro que compara linha bruta não conhece
a serialização.* A primeira passada **quebrou `agrorobotica.yaml`** — a linha era `).'`, cujo
`strip()` tem 3 caracteres sem alfanumérico, e a `'` era o **delimitador de fim do escalar YAML**.
Removi a aspa junto. Duas proteções entraram e ficam: **nunca apagar linha que contenha `'`**, e
**só escrever o arquivo se ele continuar carregando pelo parser**. A prova final compara o texto
reaberto com o antigo menos exatamente os parágrafos de pontuação.

Tratado como material MEDIDO (3 das 30 são fixtures de gabarito), critério fixado antes: *só entra
se `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6 · motivo 6/6 · 49%/100% · discriminação
8/8 · proibidas 10 · exclusões 10/10 e 11/11 · justificativas 15/21 · 7 recusas · 81 testes`
reproduzirem inteiros.* Reproduziram.

**3. O nome próprio sumia na coleta — e o conserto tem duas chamadas, não uma.** `coletar.py`
extraía com `get_text(separator="\n")`, que põe TODO elemento em linha própria, inclusive o
inline. Na frase real, `afirma o CEO da <strong>Agrotools</strong>.` virava três nós, e
`limpar_linhas` descartava `Agrotools` por ser de uma palavra e não terminar em pontuação. **A
ironia é exata: o nome morre e o "." sobrevive**, porque o ponto termina em pontuação. Medido nas
30: **62 parágrafos de pontuação órfã e 203 terminando em preposição pendurada, em 62 dos 93
documentos.**

**`.unwrap()` sozinho NÃO conserta — e eu quase commitei achando que sim.** Ele tira a tag, mas o
BeautifulSoup deixa os `NavigableString` separados e o `\n` continua entrando. É `.smooth()` que
funde os nós adjacentes. Medido na mesma URL: `afirma o CEO da` / `.` → **`afirma o CEO da
Agrotools.`**; e em 5 URLs reais das fixtures (Core AI, Ecotrace, Tractian, Liqi, Teachy), que
hoje carregam 6, 15, 11, 12 e 12 lacunas, a coleta nova produz **0**.

**O QUE ISTO NÃO CONSERTA, E PRECISA ESTAR DITO:** as 93 fixtures já coletadas. O nome apagado não
está mais no texto delas — recuperá-lo exige re-coletar e re-recortar à mão, incluindo as 8 de
gabarito. A 6 dias da entrega, mexer em material medido por **1,7% das citações** é o troco
errado. A frase decapitada (`"…afirma o CEO da"`) fica como **limitação conhecida**; o resíduo
visível, que é o que chega ao gerente, o portão do `seed.py` remove.

**4. Dois erros de documentação da própria sessão.**
- **D-090 se contradizia sobre a Solinftec.** Ele explica corretamente por que ela fica `null` (o
  documento diz *"Criada há 18 anos"* — idade, não ano) e **sete linhas abaixo** a lista como caso
  real de exclusão por `> 10 anos`. `CLAUDE.md` repetia a segunda. Ela sai **ELEGÍVEL**,
  verificado no run de produção. A exclusão por idade tem **um** caso real (Agrotools). A
  Solinftec é melhor do que um segundo caso: é o **caso-limite da política de literalidade**, uma
  empresa de 18 anos que o sistema deixa passar de propósito, reportando *"requisito não
  verificado"* em vez de inventar um ano.
- **`PagSeguro` estava na bolsa errada.** O comentário que justifica ter tirado a lista de
  `capital aberto` do B3-centrismo dizia *"PagSeguro, StoneCo, XP e Zenvia na Nasdaq"*. PagSeguro
  (PAGS) listou na **NYSE** em 24/01/2018 — foi o maior IPO da NYSE desde o Snap. Zero efeito em
  código; erro factual em material de defesa, no exato ponto que o comentário existe para provar.

### O que a revisão deixa aberto

**P-25 — as 93 fixtures têm 203 frases decapitadas, e elas não voltam sem re-coleta.** Custo real:
re-coletar e re-recortar 93 documentos à mão, com re-medição da régua inteira depois, porque 8 são
gabarito. Efeito hoje: 1,7% das citações. Fica registrado para depois da entrega — e `coletar.py`
já está consertado, então a próxima fixture nasce limpa.

---

## D-098 — Dois instrumentos de varredura, e a razão de eles não serem réguas
**Data:** 04/09/2026 · dívida de registro da sessão da manhã, paga à tarde
**Decisão:** `scripts/varrer_classes.py` e `scripts/medir_confianca.py` entram no repositório
como **instrumentos de leitura sobre a base inteira**, não como réguas.

**Por que existem.** É o corolário de D-083 que D-094 escreveu ao criar `varrer_elegibilidade.py`:
*rode o sistema* → **rode-o sobre TUDO, não sobre uma amostra**. Ler briefing é amostragem — dá
para ler três empresas, não trinta. `varrer_elegibilidade.py` fez isso para o filtro do Inception
e achou dois defeitos na primeira execução. Faltavam os outros dois eixos do Classifier: a
**classe** e a **confiança**.

**Por que não são réguas, e isto é a decisão e não um detalhe.** Régua tem gabarito, e o gabarito
deste projeto são 8 fixtures (D-062) — as 22 novas entraram como DADO, sem anotação, justamente
para não calibrar contra o próprio julgamento. Um instrumento que imprime as 30 **não pode**
virar placar sem desfazer D-062. Então ele imprime uma tabela para um humano LER, e o que ele
mede sobre gabarito fica em `avaliar_agentes.py`, com o denominador certo.

**Alternativa descartada — pôr as duas varreduras dentro de `avaliar_agentes.py` como flags.**
Seria menos arquivo, e é o que a simetria sugere. Mas `avaliar_agentes.py` é a régua: tudo que
mora lá tem denominador de gabarito e é lido como placar. Uma tabela das 30 dentro dela seria
lida como "o sistema acerta X de 30" no dia em que alguém tivesse pressa — e a corrupção
silenciosa que D-090 mediu (precisão caindo de 49% para 24% sem o filtro de gabarito) mostra que
essa confusão custa caro e não avisa.

**O que cada um respondeu, no dia em que foi escrito:**
- `varrer_classes.py` → **D-095/P-24**: `AI-native` 1 · `AI-enabled` 20 · `non-AI` **9**, as nove
  com zero detector e 2 a 7 dores de IA extraídas pelo mesmo Extractor.
- `varrer_classes.py --custo-desenhos` → **refutou uma afirmação feita por inferência** ("consertar
  a P-24 custa 1 ponto de `classe`"): vale para o desenho A (`3/7 → 2/7`) e **não** para o B
  (`3/7 → 3/7`). Foi o que tornou D-101 decidível.
- `medir_confianca.py` → **refutou a hipótese que D-059 deixou escrita e ninguém testou por 8
  dias**: *"melhorar isso é fazer o Classifier anexar evidência mais larga"*. Os quatro braços,
  contra o alvo que **D-058 fixou antes de medir — 4 acertos absolutos em 6**, com o trivial
  fazendo 3:

  | braço | o que é | acertos |
  |---|---|---|
  | A | produção hoje: `min()` sobre o perfil inteiro | **0** |
  | B | D-059: evidência do diagnóstico | 2 |
  | C | B + evidência LARGA — **a hipótese de D-059** | **2, idêntico a B** |
  | D | C + datas de publicação preenchidas | **3** |
  | — | linha trivial (responde sempre `alta`) | 3 |

  **NENHUM braço passa o alvo de 4**, e C == B mata a hipótese: evidência mais larga não move o
  campo. **O que move é a recência** — o braço D é o único que sobe, e ele depende de
  `data_publicacao`, ausente em **86 dos 93 documentos** porque `coletar.py` não captura data
  nenhuma. É o que liga este defeito ao da regra 2/3 desligada: **são o mesmo defeito visto de
  dois lados**, e consertar `confianca` é consertar a coleta (P-25).

**Nota de método, e ela é o motivo de esta entrada existir com atraso:** os dois scripts entraram
citando `(D-098)` no docstring antes de D-098 existir. Um arquivo que aponta para uma decisão que
não foi escrita é a mesma classe de defeito que D-097 apanhou — a documentação afirmando algo que
o repositório não tem. O número foi honrado em vez de reaproveitado.

---

## D-099 — O filtro do Inception rodava DEPOIS de quem consome o resultado dele
**Data:** 04/09/2026 · achado por execução, não por leitura · zero régua se move
**Decisão:** `elegibilidade` passa a rodar **antes** de `nvidia_rag` e de `recommendation` no
subgrafo; e empresa NÃO ELEGÍVEL **mantém** as recomendações, agora **rotuladas e rebaixadas**.

**O DEFEITO, na tela, num run real de 04/09** (`python -m src.graph "startups de fintech
AI-native"`, com `RERANK_PROVEDOR=cohere`):

```
  NVIDIA Inception: NÃO ELEGÍVEL
    x exclusão por 'cripto': o termo 'stablecoin' aparece nos documentos falando da própria empresa
  ...
    ação       : Agendar conversa técnica sobre NVIDIA Morpheus com o time de engenharia da Liqi
```

Sete linhas separam a recusa da instrução de agendar a conversa. `src/graph.py` tinha
`recommendation -> elegibilidade`: o motor rodava antes do filtro e **não tinha como saber**.

**E não havia dependência nenhuma sustentando essa ordem.** `briefing.node_analise` lê só
`state["startup"]` e `state["perfil"]`, ambos prontos depois do `extractor`. O nó estava no fim
porque foi o último a ser escrito — defeito de ORDEM, não de motor. Uma aresta.

**A DECISÃO DE PRODUTO, que é do Vinícius e não é técnica:** empresa recusada **continua
recebendo** recomendação, com o cabeçalho `!! FORA DO INCEPTION — abordagem comercial direta` e
prioridade forçada a `baixa`.

**Alternativa descartada — suprimir as recomendações da recusada.** É a leitura mais alinhada com
o propósito declarado ("o sistema existe para captar PARA o Inception") e ainda economizaria
chamada de API no fornecedor único do passo 7. Caiu por um fato da base: **a JetBov é a única
`AI-native` das 30 e o único `sweet-spot` que o sistema encontrou — e é NÃO ELEGÍVEL por idade
(2015, 11 anos).** Sob supressão, o melhor prospect do radar sai da tela em branco. E **4 das 7
recusas são por idade**, que diz respeito ao programa, não à empresa: consultoria, capital aberto
e cripto dizem o que a empresa É; idade diz apenas qual porta ela não alcança.

**Segunda alternativa descartada — tratar diferente por MOTIVO de recusa** (idade mantém, regra de
programa suprime). É mais correta que a escolhida e foi recusada por custo de defesa: introduz uma
regra nova, não pedida pelo TAPI, que teria de ser justificada na arguição. A escolhida se defende
com uma frase que o repositório já usa em dois lugares.

**POR QUE A ESCOLHIDA É A COERENTE, e é o mesmo argumento de D-101:** é **D-010 aplicada às
recomendações**. *"O Validator anota e rebaixa, e nunca deleta — deletar destrói informação que o
humano precisa."* `Elegibilidade` já opera assim, com `x` (provado) e `?` (não provado). Suprimir
a recomendação seria o Recommendation deletando. **Anota, rebaixa, e quem decide é o gerente.**

**Efeito colateral verificado e desejado:** `briefing.node` ordena as seções pela MENOR prioridade
de cada empresa. Com a recusada em `baixa`, ela **afunda para o fim do relatório** — no run de
verificação, a Liqi saiu de primeira para última, e a Ume (elegível) passou a abrir o briefing.

**Verificação:** `pytest` 87 passed · `avaliar_agentes` `classe 3/7 · stack 6/7 · confianca 0/6 ·
elegivel 6/6 · 49%/100%`, idêntico · `varrer_elegibilidade` as mesmas 7 recusas. Nenhuma régua se
move, porque nenhuma régua olhava a ordem — que é exatamente o motivo de o defeito ter durado.
Dois testes novos: um ESTRUTURAL sobre o grafo compilado (`elegibilidade` antes de
`recommendation`) e um de comportamento. O estrutural existe porque o comportamental não pegaria
a regressão: um estado montado à mão no pytest não tem a ordem do grafo.

---

## D-100 — Três defeitos no texto que chega ao gerente, e nenhum aparecia em teste verde
**Data:** 04/09/2026 · achados lendo o briefing inteiro, não o código
**Decisão:** consertar os três. São o entregável, não o motor.

**1. O relatório afirmava uma CAUSA FALSA.** `briefing.py` imprimia
*"nenhuma — sem evidência validada que sustente uma recomendação"* para **toda** lista vazia.
Medido em 04/09: **Conta Simples, Core AI e Iniciador têm 3, 5 e 7 dores VALIDADAS** — e a régua
confirma que o filtro `if d.validada` não barra nada (D-074). A causa real era o corte de funil em
`recommendation.py`. Um relatório que afirma a causa errada é **pior** que um que não afirma
nenhuma, porque o gerente age sobre ela — e o rodapé da página promete *"toda conclusão acima
aponta para o documento que a sustenta"*.
**O conserto:** a causa viaja no estado (`motivo_sem_recomendacao`), preenchida por quem decidiu
não recomendar. **Alternativa descartada — o briefing inferir a causa** a partir do quadrante e das
citações: reconstruiria no consumidor uma decisão que o produtor já tomou, e ficaria errada de
novo no dia em que `recommendation` ganhasse um caminho novo.

**2. Um ponteiro de decisão INTERNA dentro do relatório executivo.**
`evidence_validator.py` montava e o briefing imprimia, **uma vez por empresa**:
*"— ver D-059 para por que este agregado é o defeito que a régua mede em 0/6"*.
Entrou em 27/08 (`git log -S "ver D-059"` → `6fae6c5`), **deliberadamente**, para tornar o defeito
visível em vez de escondido. **A intenção estava certa e a SUPERFÍCIE estava errada:** o gerente de
Startups & VCs lia uma referência ao log deste repositório, e o vídeo mostraria isso.
A regra 5 de `contexto/02` §6 pede que o output carregue a confiança **e o motivo dela**; ela não
pede o número da decisão que discute o motivo. O texto passa a terminar em *"o elo mais fraco
decide"*, que é a mesma informação sem o ponteiro.
**Alternativa descartada — deixar de imprimir `motivo_confianca`.** Apagaria a regra 5 junto e
devolveria o briefing ao estado que D-066 corrigiu: `(confiança baixa)` sem dizer qual regra
produziu o grau. O defeito continua NOMEADO onde quem mexe no código o lê.

**3. Dois dos SETE campos obrigatórios do TAPI cortados no meio da palavra.**
`[:150]` cru produzia `"...NVIDIA NIM™ microse"` e `"...é a passagem citada da documentaçã"`, sem
sinal de que havia mais texto — um leitor não distingue *"o campo acabou assim"* de *"foi
truncado"*. Na mesma linha, o segundo defeito: `justificativa_tecnica` sai de `melhor_trecho`, que
devolve um span de chunk de página web, e a **quebra de linha crua** desmontava a coluna.
`_resumir()` corta em fronteira de palavra, colapsa `\s+` e fecha com `…`.

**O que os três têm em comum, e é o registro que importa:** nenhum aparecia em teste verde, e
nenhum foi achado lendo código. Os três saíram de LER um briefing inteiro — a mesma lição que
D-083 comprou em 02/09 e D-094 ampliou em 03/09. **`pytest` verde nunca foi evidência de que o
relatório está correto: ele não lê o relatório.**

---

## D-101 — `non-AI` continua sendo emitido; o que muda é o que acontece depois
**Data:** 04/09/2026 · fecha a P-24 (D-095) · **critério fixado ANTES de medir**
**Decisão:** o Classifier passa a marcar `sinal_verificado=False` quando nenhum detector dispara, e
`derivar_quadrante` só corta do funil o `non-AI` **constatado**. O rótulo não muda.

**A VIOLAÇÃO, e ela é de um princípio que este repositório escreveu no dia 2.** A rubrica define
`non-AI` por uma propriedade **positiva** (`contexto/02` §4): *"o produto não depende de IA… sem IA
no caminho crítico da entrega de valor"*. Isso é constatação, e constatação exige evidência. O
código emitia esse rótulo quando `pontos == 0` — quando **não encontrou sinal**. A rubrica pede
*"constatamos que não há IA"*; o código entregava *"não achei sinal de IA"*.

E a regra 4 do Evidence Validator (`evidence_validator.py:12`, D-010) diz, desde 22/08:
*"ausência de sinal != sinal negativo → nada é DELETADO, só rebaixado"*. `Elegibilidade` a obedece
há semanas, separando `motivos_exclusao` (a base PROVA) de `requisitos_nao_verificados` (a base NÃO
PROVA), e só o primeiro exclui. **O Classifier era o componente que a contrariava.**

Medido nas 30 (`varrer_classes.py`): **9 empresas com zero detector, todas com 2 a 7 dores de IA
extraídas com evidência pelo mesmo Extractor** — e todas indo para `fora-do-funil` → zero
recomendação. A **Core AI**, cujo produto É modelo de crédito com IA, sumia do funil em silêncio.

**ALTERNATIVA DESCARTADA — `indeterminado` como quarta classe (o "desenho A").** É semanticamente
mais limpa, e custa **duas** coisas, não uma:
1. **Medida:** `classe` cai de **3/7 para 2/7** (`varrer_classes.py --custo-desenhos`), porque a
   SunnyHUB também tem zero detector e passaria a divergir de um gabarito que diz `non-AI`.
2. **Não medida, e maior:** o TAPI nomeia **três** classes. Uma quarta no output é desvio de
   especificação — defensável, mas é uma defesa a mais, e ela não compra nada além do que o
   desenho escolhido compra. O escolhido custa `3/7 → 3/7`, **medido antes de ser implementado**.

**POR QUE ISTO NÃO CONTRARIA O ACEITAR DA P-24, que dizia "consertar exige gabarito".** Aquela
razão foi escrita antes da medição que separa os dois desenhos, e ela protege corretamente **os
detectores**: ajustar `PROFUNDOS`, pesos ou limiares até a Core AI "sair certa" é calibrar contra
o próprio julgamento sobre fixtures curadas pela mesma pessoa (D-062). **Este conserto não toca em
detector nenhum e não introduz um único grau de liberdade** — é a mesma regra `pontos == 0`, com
outro destino. Não há nada para calibrar, e é por isso que a régua não se move: era previsível
antes de rodar, e foi previsto.

**CRITÉRIO DE ACEITAÇÃO, FIXADO ANTES DE MEDIR** (parte 1, que decide sozinha): nenhuma piora em
`classe 3/7` · `maturidade_stack 6/7` · `confianca 0/6` · `elegivel 6/6` · precisão ≥ 49% ·
recall 100% · as mesmas 7 recusas em `varrer_elegibilidade` · `pytest` verde.
**Resultado: todos idênticos, `pytest` 87 passed.**

**E A LINHA TRIVIAL, QUE D-051 TORNA OBRIGATÓRIA E QUE A PRIMEIRA REDAÇÃO DESTA DECISÃO OMITIU:**

| campo | trivial (sempre `AI-native`, todas as 8 dores) | produção |
|---|---|---|
| `classe` | **4/7** | 3/7 |
| `maturidade_stack` | 6/7 | 6/7 |
| `confianca` | **3/8** | 0/6 |
| precisão de dor | 32% | **49%** |
| discriminação | 1/8 | **8/8** |

**O sistema PERDE de uma constante em `classe` e em `confianca`, e ganha em precisão e
discriminação.** Escrever "classe 3/7" sem essa coluna é exatamente o que D-051 existe para
impedir — *"sem ela, 49% de precisão parece bom em vez de 17 pontos acima de emitir tudo"*, e o
inverso também vale: 3/7 parece um placar até se ver que responder sempre a mesma coisa faz 4/7.
D-101 **não move nenhum dos dois lados**; a tabela está aqui porque a frase da defesa precisa
dela, não porque a decisão dependa dela.

**Como isto foi apanhado, e o registro vale mais que a correção:** por um `/code-review high`
disparado em 04/09 sobre o commit ERRADO — ele revisou o documento da manhã, não este código. Achou
assim mesmo, porque o defeito era **herdado**: o documento da manhã tinha removido a comparação com
o trivial, e eu escrevi a decisão a partir dele sem repor. Um revisor com o alvo trocado achou o
que eu não achei com o alvo certo. O `non-AI` CONSTATADO continua indo para
`fora-do-funil` — `tests/test_grafo.py:110` seguiu verde **sem edição**, e isso é a evidência de
que a mudança é aditiva, não uma reescrita da rubrica.

**O PREÇO, DECLARADO E AINDA NÃO MEDIDO:** as nove entram no funil, e uma delas — a **SunnyHUB**,
energia solar — é `non-AI` de verdade. É o mesmo preço que `Elegibilidade` já paga e **reporta** na
Solinftec, que sai ELEGÍVEL com *"requisito não verificado"* porque o documento diz "há 18 anos" e
não um ano. A troca é deliberada: **um falso negativo SILENCIOSO por um falso positivo ANOTADO** —
a direção que D-052 e D-057 já escolheram por escrito, porque o silencioso não aparece em lugar
nenhum. **A parte 2 do critério** (o ruído das nove, medido contra as 7 regras do TAPI) fica para
05/09, e ela não pode reverter esta decisão: se as nove pontuarem pior, a resposta é apertar o
rebaixamento que elas já carregam, não voltar ao estado que viola o princípio.

**CUSTO DE LATÊNCIA E DE API: ZERO, e isto foi verificado e não suposto.** A régua de D-084 é
*defeito · latência que o usuário sente · robustez · reversibilidade*, e a preocupação óbvia seria
"nove empresas a mais no funil = nove vezes mais chamada no fornecedor único do passo 7". **Não é o
caso:** `nvidia_rag` sempre rodou para TODAS as empresas — o corte de funil acontecia depois dele,
em `recommendation`. O que as nove ganham é o aproveitamento de citações que já eram recuperadas e
jogadas fora. Medido: o mesmo run de 5 empresas, mesma consulta, levou **3m30 antes e 3m27 depois** — a primeira redação desta linha dizia *"3m27 e 3m27"*, que é mais forte do que a medição sustenta.

**Na tela, ao fim:**
```
  Classificação : non-AI   (confiança baixa)
  Quadrante     : PROSPECT DE EVOLUÇÃO — a conversa é sair do wrapper
    ? sinal de IA NÃO VERIFICADO — nenhum dos 3 detectores disparou neste documento;
      5 dor(es) de IA extraída(s) com evidência. O rótulo acima é o que a regra
      produziu, não o que a base constatou
```

**O PREÇO FOI VISTO NA TELA, E ELE EXPÕE UM DEFEITO QUE JÁ EXISTIA.** Rodando o grafo sobre **28
das 30** (`"todas as startups"`, `MAX_STARTUPS=30`, rerank ligado): **9 seções com `? sinal de IA
NÃO VERIFICADO`, ZERO com `FORA DO FUNIL`, zero seção sem recomendação, e as 45 recomendações
dessas nove e das sete recusadas saíram em `prioridade baixa`** — os números batem um a um com
`varrer_classes.py` e `varrer_elegibilidade.py`, com a Zenvia contada nos dois grupos.

A SunnyHUB é o caso a ler, e ela **não** mostra um defeito de D-101: mostra um defeito de
EXTRAÇÃO que D-101 tornou visível. Ela recebe `NeMo Guardrails` para a dor de `observabilidade`,
com lastro em *"Seguro contra danos, **monitoramento** e troca de equipamentos"* — monitoramento
de placa solar lido como observabilidade DE IA. **É literalmente o exemplo que o docstring de
`JULGAR_SUSTENTACAO` (D-074) usa para explicar por que "não contradizer não é sustentar"**, e a
flag está `False` porque foi reprovada em D-075. Antes de D-101 essa dor era extraída, validada e
**descartada em silêncio** junto com a empresa; agora ela aparece com `?` e prioridade `baixa`.
**A troca é essa, e ela é a que o projeto já escolheu duas vezes:** um erro que se vê custa menos
que um erro que não deixa rastro.

**E o caso que decidiu D-099 apareceu junto, na mesma execução:**
```
  JETBOV
  Classificação : AI-native   (confiança baixa)
  Quadrante     : SWEET SPOT — AI-native com stack imatura: melhor prospect
  NVIDIA Inception: NÃO ELEGÍVEL
    x exclusão por idade: fundada em 2015, 11 anos (o programa exige menos de 10)
  Recomendações (3):
    !! FORA DO INCEPTION — abordagem comercial direta, não captação para o programa.
```
Sob a alternativa descartada, este bloco teria três linhas e nenhuma recomendação — o único
`sweet-spot` das 30 saindo em branco.

**`varrer_classes.py` mudou de papel junto:** era o instrumento que DIAGNOSTICOU a P-24 e passou a
LER o quadrante real, com uma verificação que falha alto se alguma empresa sem detector voltar a
`fora-do-funil`. Um instrumento que descreve um sistema que não existe mais é pior que instrumento
nenhum, porque parece medido.


---

## D-102 — Os quatro números soltos de 04/09 ganham instrumento, e eu repeti o defeito que diagnostiquei
**Data:** 04/09/2026 · fim da sessão · zero API

**Decisão:** `scripts/medir_cobertura.py`, com `--terceiro`.

**O QUE ACONTECEU, E É SOBRE MÉTODO, NÃO SOBRE O NÚMERO.** A sessão da manhã escreveu, na §5 do
`achados-04-09.md`: *"dois NÃO foram salvos e precisam ser reescritos pela sessão de plano"* — os
scripts que mediram a cobertura de `elegibilidade()` e os marcadores `PROFUNDOS`. **A sessão da
tarde reescreveu os dois em heredoc inline, usou os números, e não salvou nenhum.** Quatro
medições ficaram assim: a cobertura de 10,6%, o `7 → 13` da varredura ampla, os `PROFUNDOS` por
fixture e as 86/93 datas — e **duas viraram número em `decisoes.md`** (a linha da P-23) e no plano.

Um número no log sem comando que o derrube é **afirmação, não medição**. É a mesma classe de
defeito que D-091 custou uma sessão e que D-097 apanhou. Diagnosticá-lo de manhã e repeti-lo à
tarde é o registro mais útil desta entrada.

**AS TRÊS MEDIÇÕES, E A DECISÃO QUE CADA UMA CARREGA:**

1. **Cobertura conta trechos ÚNICOS, não a soma bruta** — e isso é decisão, não detalhe. A soma
   bruta dá **11,0%**; os únicos dão **10,6%**. Uma frase que sustenta duas afirmações não amplia
   o que o filtro enxerga. O script imprime os dois e marca o bruto como *"não é cobertura"*,
   porque foi exatamente aí que a verificação de 04/09 divergiu do documento da manhã.
2. **O custo do conserto óbvio é `7 → 13`**, com **6 recusas novas** e **zero sumindo** — varrer
   mais nunca remove exclusão. Mas o argumento que decide não é a contagem: `--terceiro` imprime,
   frase a frase, **por que o veto de terceiro quebra por construção**. `_fala_de_terceiro` é um
   `all()`, e cada ocorrência a mais é outra chance de falhar. A Iniciador é o caso limpo: uma
   frase TEM o marcador `mercado de stablecoin` e a outra não tem nenhum — o veto colapsa.
3. **`PROFUNDOS` e as datas** ficam juntos porque são a mesma constatação em dois eixos: 7 de 8
   fixtures com ZERO marcador contra um degrau que exige 3, e `data_publicacao` ausente em **86 de
   93**. Os dois dizem que o gargalo é o DADO, não a regra.

**Alternativa descartada — pôr as três em `avaliar_agentes.py --exclusoes`.** É onde mora a régua
do filtro do Inception, e a simetria puxa para lá. Mas `--exclusoes` tem gabarito e mede os dois
lados com denominador; isto aqui não tem resposta certa declarada — **julgar quais das 6 recusas
novas são falso positivo é ler a frase impressa**, e é trabalho de humano. Misturar as duas coisas
faria uma tabela de leitura virar placar, que é a razão inteira de D-098.

**Alternativa descartada — não salvar, porque "os números já estão no log".** É a que eu já tinha
tomado por omissão, e ela é o defeito.


## Decisões pendentes

| # | Decisão | Estado |
|---|---|---|
| ~~P-01~~ | ~~Provedor de LLM dos agentes~~ | **D-067** — `nvidia/nemotron-3-nano-30b-a3b`, por eliminação medida |
| ~~P-02~~ | ~~Modelo de embedding e dimensão~~ | **D-046** — `llama-nemotron-embed-vl-1b-v2`, `dimensions=1024` |
| ~~P-03~~ | ~~Reranker~~ | **D-068** — Cohere `rerank-v3.5`, provedor por env var |
| ~~P-04~~ | ~~Banco vetorial~~ | **D-016** — pgvector para o denso, `bm25s` em processo para o léxico |
| ~~P-05~~ | ~~Topologia do grafo~~ | **D-007** — subgrafo de análise + fan-out por `Send` |
| ~~P-07~~ | ~~Gerenciamento de dependências~~ | **D-004** — conda + `requirements.txt` pinado |
| ~~P-08~~ | ~~Como o Postgres sobe para quem avaliar~~ | **D-017** — os dois |
| **P-06** | **Framework de frontend** | aberta. É a única superfície pela qual alguém que não lê código julga o sistema. O escopo sai da pergunta de produto — o que o gerente precisa ver, e em que ordem, para abordar a startup no dia seguinte — não de um orçamento de esforço |
| **P-09** | **Promover o juiz do Extractor?** | D-072 passou o critério; falta decidir a lacuna de recall (100% → 71-79%) |
| ~~P-10~~ | ~~Régua do motor de recomendação~~ | **D-086** — a régua existe (`--justificativas`, 30 chunks, amostra semeada, rotulada antes do seletor) e o seletor bate a linha trivial: **15/21 vs 12/21**. Num run real, justificativas que servem: **1/6 → 4/6**. A parte de RELEVÂNCIA da recomendação virou **P-21** |
| **P-11** | **O `min()` da confiança** | 0/6 constante. Barato, mas exige critério fixado antes — uma tentativa já foi reprovada (D-059). **METADE FECHADA em 04/09 (D-100):** o ponteiro `ver D-059` saiu do texto do usuário. **E a hipótese de D-059 foi REFUTADA (D-098):** o braço C de `medir_confianca.py` — evidência mais larga — dá 2, idêntico ao B. O que move o campo é a recência, e ela depende de `data_publicacao`, ausente em **86 dos 93 documentos**. O `min()` fica: consertá-lo hoje é consertar a coleta, que é P-25 |
| ~~P-16~~ | ~~Julgamento semântico no Evidence Validator~~ | **medido e REPROVADO em D-075** — 4 de 5 alvos passam, o recall no Recommendation falha nas três execuções |
| **P-17** | **`recommendation.py` trata `validada` como booleano** | **D-077: a gradação total foi aplicada e é INERTE** — flag desligada, `confianca` sem leitor, régua espelhando o código antigo. E o critério (recall ≥ 88% com precisão ≥ 80%) é inalcançável assim: admitir tudo dá 100%/49%. Falta a admissão PARCIAL, por `dores_enderecadas` e não por `confianca` |
| ~~P-18~~ | ~~`src/llm.py` sem `timeout`~~ | **D-076** — `LLM_TIMEOUT` por tentativa, `max_retries=2` do SDK mantido. **O valor subiu para 120 em D-080**, porque com 30 s cinco de oito chamadas estouravam a primeira tentativa: teto combinado ~360 s (D-089) |
| **P-12** | **`classe`: vocabulário ou curadoria?** | D-060 mostrou que o gargalo não é a regra de decisão. Exige base ampliada |
| ~~P-13~~ | ~~Exclusão por menção vs. identidade~~ | **D-085** — veto de terceiro com escopo de frase. Falso positivo 2/7 → **7/7**, falso negativo 7/7 sem regressão |
| **P-14** | **Quatro campos são calculados e nada os lê** | `estrategia_analise` e `exige_sinais_ia` (Query Planner), `score_recuperacao` (Retriever), `motivo_validacao` (Evidence Validator). Não é código morto — é capacidade anunciada e não entregue: a arquitetura publicada promete *"critérios de busca + estratégia de análise"*. Ou o subgrafo passa a lê-los, ou o diagrama para de prometê-los |
| ~~P-15~~ | ~~Re-medir a abstenção do passo 8~~ | **D-040, re-medida em 02/09** — **23/24 = 96%** no modelo atual e no corpus pós-D-082, contra 20-22/24 do modelo morto. O único erro é abstenção indevida, não alucinação |
| ~~P-20~~ | ~~O operador de borda da idade~~ | **D-085** — a borda (`idade == IDADE_MAXIMA`) vira **pendente** com a faixa impressa, não exclusão. Guardar o mês foi descartado: não consta em 6 das 8 fixtures |
| **P-21** | **Relevância da tecnologia recomendada** | aberta por D-086. Morpheus (spear phishing, digital fingerprinting) recomendado para a dor de privacidade de uma healthtech: a recuperação casa `privacy`/`security` sem conhecer o domínio. **Nenhum seletor de trecho conserta isto** — é o motor de recomendação. **O gabarito, porém, existe e não é meu:** as 7 regras de exemplo do TAPI (`contexto/01-tapi.md:143`) são pares setor/dor → tecnologia esperada, e a regra `Saúde →` cobre 4 das 8 startups da base e reprova este caso. Falta o harness — e a cobertura, que só cresce com a base (D-088) |
| **P-22** | **`justificativa_negocio` é stub em 11 de 16 tecnologias** | aberta pela auditoria de 03/09 (D-088). `recommendation.py:63` cura texto para **5 das 16**; as outras 11 caem num fallback formulaico que o próprio comentário chama de stub e adia "para a M4" — fase que não existe mais em arquivo vivo nenhum. É o **campo 3 dos 7 obrigatórios** e o vizinho do campo que D-086 consertou |
| **P-25** | **As 93 fixtures têm 203 frases decapitadas, e elas não voltam sem re-coleta** | aberta por D-097. `coletar.py` apagava o nome próprio que vinha em tag inline — `afirma o CEO da <strong>Agrotools</strong>.` virava `"afirma o CEO da"` + `"."`. **A raiz está consertada** (`unwrap` + `smooth`, medido: 0 lacunas em 5 URLs reais), então toda fixture nova nasce limpa, e a pontuação órfã já saiu das 30. **O que fica é a frase sem sujeito**, em 62 dos 93 documentos. Recuperá-la exige re-coletar e re-recortar à mão, incluindo as 8 de gabarito, com re-medição da régua inteira depois. **Efeito medido hoje: 1,7% dos trechos de evidência** (5 de 298) — o troco não fecha a 6 dias da entrega. Depois da entrega |
| ~~**P-24**~~ | ~~`non-AI` é o default de detecção falha~~ | **FECHADA em 04/09 (D-101).** `Diagnostico.sinal_verificado` é o par que `Elegibilidade` já tinha, aplicado ao rótulo: `non-AI` continua sendo emitido — o TAPI nomeia três classes — e só o **constatado** é cortado do funil. **Custo medido antes de implementar: `classe 3/7 → 3/7`**, contra `3/7 → 2/7` do desenho com quarta classe. O ACEITAR anterior dizia *"consertar exige gabarito"*: aquilo protege os DETECTORES, e este conserto não toca em nenhum nem introduz grau de liberdade. **Fica aberta a parte 2 do critério** — o ruído das 9 que passaram a entrar no funil, a medir contra as 7 regras do TAPI em 05/09 |
| **P-23** | **`elegibilidade()` só enxerga o que o Extractor citou** | aberta por D-091. Ela varre `perfil.afirmacoes[*].evidencias[*].trecho`, não o documento. Medido no caso real: a Liqi diz *"oferecer criptomoedas, stablecoins e tokens"* no site, `criptomoeda` **já estava na lista**, e ela passou — porque a frase não caiu em nenhum trecho de evidência. **O filtro do Inception, que é o Diferencial declarado do projeto, tem cobertura igual à do casador de dores, e isso não estava escrito em lugar nenhum.** A correção óbvia (varrer `conteudo_texto`) **quebra `_fala_de_terceiro` POR CONSTRUÇÃO**, e esse é o argumento forte, medido em 04/09: o veto exige que **toda** ocorrência do termo caia em frase com marcador, então cada caractere a mais é outra chance de o `all()` falhar. Na Iniciador, o trecho de evidência tem 1 ocorrência de `stablecoin`, coberta por `mercado de stablecoin`; o documento inteiro tem 2, e a segunda não tem marcador nenhum — o veto colapsa. **Medido (`medir_cobertura.py`, D-102): as recusas vão de 7 para 13 em 30**, e ao menos 4 das 6 novas são falso positivo claro (TideWise por *"Dados da consultoria Fortune Business Insights"*; BemAgro por *"a revenda goiana MM Agro"*). **E o lado silencioso também apareceu:** a varredura ampla recusa a **Produzindo Certo**, que *"oferece serviços de consultoria, gestão e verificação"* — a própria empresa. Hoje ela passa por SORTE, não por desenho. Não cabe a 3 dias do vídeo; o que cabe é estar escrito, e agora está com os dois lados |
| **P-19** | **O sweep do RAG (dimensão, banda de chunk, `k1`/`b`)** | **reaberta por D-078.** Estava cortado porque "o critério 2 já está no teto" — razão inválida. A razão candidata para manter o corte é outra e precisa ser dita: com 24 perguntas de gabarito, grade fina ajusta ao gabarito em vez de generalizar. O que joga contra o corte é `e@1 = 79%` (D-068): a primeira citação erra 1 vez em 5. Re-decidir junto com a base ampliada |
