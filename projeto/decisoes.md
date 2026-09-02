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
**Instrumento:** a acurácia de abstenção (faixa de 20-22 de 24, em 3 execuções) foi medida no LLM
que morreu em 27/08. **Não re-medida** no modelo atual — é dívida declarada em D-069.

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
| **P-11** | **O `min()` da confiança** | 0/6 constante. Barato, mas exige critério fixado antes — uma tentativa já foi reprovada (D-059) |
| ~~P-16~~ | ~~Julgamento semântico no Evidence Validator~~ | **medido e REPROVADO em D-075** — 4 de 5 alvos passam, o recall no Recommendation falha nas três execuções |
| **P-17** | **`recommendation.py` trata `validada` como booleano** | **D-077: a gradação total foi aplicada e é INERTE** — flag desligada, `confianca` sem leitor, régua espelhando o código antigo. E o critério (recall ≥ 88% com precisão ≥ 80%) é inalcançável assim: admitir tudo dá 100%/49%. Falta a admissão PARCIAL, por `dores_enderecadas` e não por `confianca` |
| ~~P-18~~ | ~~`src/llm.py` sem `timeout`~~ | **D-076** — `LLM_TIMEOUT=30` por tentativa, `max_retries=2` do SDK mantido: ~90 s de teto combinado |
| **P-12** | **`classe`: vocabulário ou curadoria?** | D-060 mostrou que o gargalo não é a regra de decisão. Exige base ampliada |
| ~~P-13~~ | ~~Exclusão por menção vs. identidade~~ | **D-085** — veto de terceiro com escopo de frase. Falso positivo 2/7 → **7/7**, falso negativo 7/7 sem regressão |
| **P-14** | **Quatro campos são calculados e nada os lê** | `estrategia_analise` e `exige_sinais_ia` (Query Planner), `score_recuperacao` (Retriever), `motivo_validacao` (Evidence Validator). Não é código morto — é capacidade anunciada e não entregue: a arquitetura publicada promete *"critérios de busca + estratégia de análise"*. Ou o subgrafo passa a lê-los, ou o diagrama para de prometê-los |
| **P-15** | **Re-medir a abstenção do passo 8** | os 20-22/24 são do modelo morto; D-069 previu n=3 e não foi executado |
| ~~P-20~~ | ~~O operador de borda da idade~~ | **D-085** — a borda (`idade == IDADE_MAXIMA`) vira **pendente** com a faixa impressa, não exclusão. Guardar o mês foi descartado: não consta em 6 das 8 fixtures |
| **P-21** | **Relevância da tecnologia recomendada** | aberta por D-086. Morpheus (spear phishing, digital fingerprinting) recomendado para a dor de privacidade de uma healthtech: a recuperação casa `privacy`/`security` sem conhecer o domínio. **Nenhum seletor de trecho conserta isto** — é o motor de recomendação, e nada o mede hoje |
| **P-19** | **O sweep do RAG (dimensão, banda de chunk, `k1`/`b`)** | **reaberta por D-078.** Estava cortado porque "o critério 2 já está no teto" — razão inválida. A razão candidata para manter o corte é outra e precisa ser dita: com 24 perguntas de gabarito, grade fina ajusta ao gabarito em vez de generalizar. O que joga contra o corte é `e@1 = 79%` (D-068): a primeira citação erra 1 vez em 5. Re-decidir junto com a base ampliada |
