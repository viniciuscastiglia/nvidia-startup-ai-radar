# Plano final — 02/09 a 09/09/2026

**Entrega: 09/09 às 23:59 · Vídeo: 07/09.** Restam **7 dias**, **5 até o vídeo**.

> **Visão visual deste plano:** [Os últimos sete dias](https://claude.ai/code/artifact/b6d37462-6743-43c1-ac6d-da5a15af7839) — mesma informação, para ler de relance.
>
> **Este documento é a fonte única do que falta.** Todo item aberto do projeto aparece aqui com um
> destino: **FAZER** (com dia), **ACEITAR** (com a justificativa que vai para a defesa) ou
> **DECIDIR** (é do Vinícius). **Se não está aqui, não existe.** O histórico está em `decisoes.md`.

---

## 1. Estado verificado — medido em 02/09, não suposto

| verificação | resultado |
|---|---|
| `smoke_nvidia.py` | **3/3 (1 LENTO)** — o chat responde HTTP 200, mediana **51 s**, faixa 17–88 s |
| `pytest -q` | **81 passed** (era 53 em 01/09, 67 no início de 02/09) |
| `python -m src.graph` | roda ponta a ponta, **as duas empresas ELEGÍVEIS**, zero chamada de LLM em produção |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel **6/6**+1amb · precisão 49% · recall 100%` |
| `avaliar_agentes.py --exclusoes` | `7/7` falso negativo · **`7/7`** falso positivo (era 2/7 — D-085) |
| `avaliar_agentes.py --justificativas` | linha trivial `12/21` · seletor **`15/21`** (D-086) |
| corpus RAG | **175 chunks** estruturais (era 177) · 16 tecnologias · gabarito de 24 perguntas |
| base | **8 startups**, 24 documentos · `ano_fundacao` em 6 de 8 |
| catálogo NVIDIA | **0 vivos de 10** sondados · o modelo de produção é o único que responde |

**A regra que 02/09 comprou caro:** leitura de código não substitui execução. Duas sessões de
auditoria estática não acharam o bug do `query_planner`, o entulho no corpus, nem a
`justificativa_tecnica` errada. Uma execução achou os três em uma hora.
**Toda sessão que mexe em comportamento roda o grafo antes de fechar.**

---

## 2. Os cinco critérios ELIMINATÓRIOS — nenhum é ponto, todos são porta

Isto não estava no plano até 02/09 e é o que mais importa: falhar em qualquer um destes anula o
resto do trabalho, independente de qualidade.

| eliminatório (TAPI, p.10) | coberto por | risco hoje |
|---|---|---|
| Entrega fora do prazo sem alinhamento | §3.3 item 4 — **o canal de submissão não é conhecido** | **ABERTO** |
| Ausência do vídeo | 07/09, portão inegociável | controlado |
| **Projeto que não executa e cujo vídeo não demonstra funcionamento real** | o TAPI exige a demo **pela interface web** — logo a interface **não é os 5 pontos do critério 4, é a porta do eliminatório** | **ALTO** — zero byte hoje |
| **Código integralmente gerado sem compreensão: o candidato precisa explicar as decisões de arquitetura do próprio projeto** | §4.1, novo | **ALTO** — 82 decisões, e D-080/081/082 saíram hoje de uma sessão com IA |
| Plágio | autoria própria, decisões registradas com alternativa | controlado |

> **A releitura que muda a ordem do plano:** a interface deixou de ser "a superfície que um
> não-engenheiro julga" e passou a ser **pré-requisito do vídeo**, que é pré-requisito da entrega.
> Por isso a regra de corte de 05/09 sacrifica README e profundidade — nunca a interface.

## 3. Inventário completo — todo item aberto tem destino

### 3.1 FAZER — 16 itens, cada um com dia

| item | o que é | dia | pronto quando |
|---|---|---|---|
| ~~**P-10**~~ | **FEITO em 02/09 (D-086).** Régua rotulada antes do seletor; seletor `15/21` vs trivial `12/21`; num run real, justificativas que servem **1/6 → 4/6**. O case da Writer sumiu | ~~03/09~~ | ✅ |
| **Base 8 → 30** | `"fintechs"` e `"agro"` devolvem **zero**. 27% do piso do TAPI | **03/09** | as duas consultas devolvem resultado; `seed.py --verificar-urls` passa |
| **P-15 + `avaliar_rag`** | o corpus mudou em D-082 — `e@1=79%` é de um corpus com entulho dentro | **03/09** (background) | tabela nova registrada, com a ressalva de denominador |
| **P-06 + interface** | zero byte. Única superfície que um não-engenheiro julga | **04–05/09** | consultar → ver → recomendações com evidência → exportar |
| **Testes ausentes** | **três** módulos sem teste: `extractor.py` (249 linhas, primeiro nó, alimenta todos), `rag/geracao.py` (**o passo 8 do TAPI**, onde mora a abstenção de D-040) e `db.py` (o SQL da recuperação) | **05/09** | os três com teste; a abstenção do passo 8 coberta |
| **P-11** | `confianca` é **0/6 constante** — campo do briefing com zero informação | **05/09** | ou promove o braço de D-059 (2/6), ou o campo para de ser impresso |
| **P-21** | **novo (D-086):** Morpheus (spear phishing) recomendado para a dor de **privacidade** de uma healthtech. Não é texto, é **qual tecnologia** — e nada mede relevância de recomendação | **05/09** | ou ganha régua, ou vira ACEITAR escrito |
| ~~**P-20**~~ | **FEITO em 02/09 (D-085).** A borda vira `pendente` com a faixa impressa | ~~05/09~~ | ✅ |
| ~~**P-13**~~ | **FEITO em 02/09 (D-085).** Veto de terceiro com escopo de frase: falso positivo **2/7 → 7/7**, falso negativo 7/7 sem regressão | ~~05/09~~ | ✅ |
| **P-14** | 4 campos calculados que ninguém lê — capacidade anunciada e não entregue | **06/09** | ou o subgrafo os lê, ou o diagrama e o README param de prometê-los |
| **README** | diz "a definir" para decisões tomadas e "Em breve" para como rodar | **06/09** | alguém clona e roda sozinho, sem perguntar nada |
| **Diagramas `.mmd`** | são de 23/08 e nunca foram regenerados; entram em "Repositório e documentação" e P-14 diz que prometem campos sem leitor | **06/09** | `python scripts/diagramas.py` roda e o resultado bate com o grafo compilado |
| **Docstrings mentem** | `query_planner`, `briefing` e `recommendation` ainda se declaram **"STUB DA SESSÃO 01"**. Dois são escolhas deliberadas e medidas, não trabalho inacabado — e um avaliador que lê "STUB" conclui projeto incompleto | **06/09** | nenhum módulo se declara stub sem ser um |
| **As 16 fontes do RAG não estão cacheadas** | `ingerir_nvidia.py` **baixa ao vivo** das 16 URLs. Se uma mudar ou sair do ar até a avaliação, o corpus de quem clonar **não é o corpus medido** — e o gabarito de 24 perguntas aponta URL e frase-âncora específicas, então `avaliar_rag.py` quebra na mão do avaliador | **06/09** | cache em `data/nvidia/cache/`, com `--refetch` para atualizar. Clone limpo reproduz o corpus medido sem depender da rede |
| **`.env.example` incompleto** | `COHERE_REQ_POR_MIN` é lido por `config.py` e **não está documentado** — quem tem chave paga não descobre que pode subir o teto de 10 req/min | **06/09** | toda env var lida está documentada |
| **Roteiro do vídeo** | ≤ 7 min, exige ensaio | **06/09** | roteiro escrito e uma tomada de teste feita |
| **Gravar o vídeo** | obrigatório. Único prazo imóvel | **07/09** | arquitetura + RAG + demo funcional gravados |

### 3.2 ACEITAR — 4 itens, com a justificativa que vai para a defesa

Não são esquecimento. São escopo fechado por escrito, e cada um tem a razão pronta:

| item | por que fica de fora |
|---|---|
| **P-12** — `classe` 3/7 | D-060 calculou o **teto: 4/7**, porque 7 das 8 fixtures têm profundidade técnica zero. O gargalo é vocabulário, não a regra. E a base nova entra **como dado, sem gabarito** (D-062), então a régua não se move nem com 30 empresas. Mexer no limiar seria calibrar contra o gabarito |
| **P-17** — `validada` booleano | D-077 mediu: a gradação foi aplicada e é **inerte**, e o critério (recall ≥ 88% com precisão ≥ 80%) é **inalcançável** — admitir tudo dá 100%/49%. Falta a admissão parcial por `dores_enderecadas`, que é redesenho do motor. Não cabe em 7 dias sem risco ao vídeo |
| **P-19** — sweep do RAG | Com **24 perguntas** de gabarito, uma grade fina ajusta ao gabarito em vez de generalizar. **Esta é a razão válida** — a antiga ("o critério 2 está no teto") foi anulada por D-078. A re-medição do corpus novo (2.1) fica; o sweep não |
| **P-09** — promover o juiz | **Medir não é promover** (D-078). Promover a 5 dias do vídeo obriga a revalidar classifier, validator e recommendation a jusante. O número entra no log e na defesa; a promoção é um segundo ato, e ele não tem dia |

### 3.3 DECIDIR — 6 itens, e são seus

| # | decisão | por que só você decide | prazo |
|---|---|---|---|
| **1** | **A chave do Grok** | Único caminho fora do `build.nvidia.com`, que já matou 4 modelos. Pré-autorizado pela liga desde 28/08 (D-067). **O bloqueio é a chave, não o código** | **hoje** |
| **2** | **P-10: qual das três opções** | muda o que o vídeo mostra — ver §4 | **hoje** |
| **3** | **P-06: escopo da interface** | sai de "o que o gerente precisa ver", não de esforço. A decidir **na frente do briefing real**, em 04/09 | **04/09** |
| **4** | **Canal de submissão e formato da entrega** · **individual ou em grupo?** | O TAPI **não responde** nenhuma das duas, e "entrega fora do prazo sem alinhamento prévio" é **eliminatório**. Não saber o canal em 09/09 é perder por logística, com o projeto pronto | **hoje** |
| **5** | **Executam o projeto na avaliação, e com chave de quem?** | a conta gratuita não alcança **nenhum** modelo de terceiros (0 vivos em 12), e o catálogo aposentou o LLM em 01/09 sem aviso | esta semana |
| **6** | **O reranker da NVIDIA saiu do ar; migramos para o Cohere**, que o próprio TAPI recomenda (§5.3) — confirmam que é aceitável? | muda a conformidade declarada | esta semana |

---

## 4. O passo a passo, dia a dia

### 4.1 — Arguição diária: 20 minutos, todo dia, do 03 ao 06

**Por que isto é um item do plano e não um conselho:** *"código integralmente gerado sem
compreensão"* é **eliminatório**, e é o critério que mais se degrada quando o ritmo aperta. O
projeto tem **82 decisões**, e três nasceram hoje numa sessão assistida por IA.

**O mecanismo, ao fim de cada dia, antes do portão:** pegar o que mudou naquele dia e responder,
**sem abrir o arquivo**: *o que eu mudei, por quê, e qual alternativa eu descartei e por qual
motivo.* O que não sair fluente volta para `decisoes.md` reescrito com as próprias palavras — o log
existe para isso (D-078), e o texto dele **é o roteiro do vídeo**.

**Prioridade de revisão**, se o tempo apertar: D-007 (topologia) · D-040 (`json_schema`) ·
D-046 (embedder) · D-068 (rerank e ablação) · D-072 (o juiz) · D-079/D-080 (EOL e latência) ·
D-081/D-082 (o que mudou hoje). São as que um avaliador pergunta primeiro.

### 4.2 — Os dias

### 03/09 — os dois defeitos que o gerente sente na cara

**Manhã · P-10 FOI FEITA EM 02/09 (D-086), junto de P-13 e P-20 (D-085).** A manhã fica livre.
Use-a no item mais barato que sobrou: **`avaliar_rag.py` e `--geracao` sobre o corpus pós-D-082**
(P-15) — `e@1 = 79%` ainda é de um corpus com entulho dentro.

**Tarde · base para 30.** Ordem **obrigatória**: fintech → agro → demais setores.
D-062 já dá a estrutura: as 8 atuais mantêm gabarito, as 22 novas entram **como dado**, com
`url_fonte` real. `scripts/coletar.py` puxa o texto, `seed.py --verificar-urls` confere.

> **REGRA DE PARADA: timebox de 3 h.** Parar em 20 com fintech e agro dentro é sucesso — o defeito
> medido foi corrigido. O que não couber vira **decisão escrita**, não silêncio.

**Background (não ocupa ninguém):** `avaliar_rag.py`, `--geracao`, `--sustentacao`.

**30 minutos, no fim do dia · O TESTE DE CLONE LIMPO — antecipado de 06/09.**
`git clone` numa pasta nova, ambiente do zero, `.env` só com o que o `.env.example` documenta,
`init_db.sql`, `seed.py`, `ingerir_nvidia.py`, `python -m src.graph`. **Anotar cada passo em que
foi preciso saber algo que não está escrito.**

> **Por que hoje e não em 06/09:** *"projeto que não executa"* é **eliminatório**, e este é o
> último risco do plano sem limite conhecido. Achado em 03/09 tem 4 dias de conserto; em 06/09
> tem um. É a regra da §7 aplicada a ela mesma.

**PORTÃO 03/09:** o grafo roda; `"fintechs AI-native"` devolve resultado; nenhuma justificativa
técnica cita empresa alheia. *Se P-10 não fechar hoje, ele empurra a base — não a interface.*

### 04/09 — interface, parte 1

**Antes de escolher framework:** rodar o grafo e ler o briefing inteiro. **P-06 sai daí.**
Depois: esqueleto + consulta + lista de empresas com classificação.

**PORTÃO 04/09:** dá para digitar uma consulta e ver empresas na tela.

### 05/09 — interface parte 2 + a faxina medida

Manhã: recomendações com evidência + exportar briefing. **A interface fecha hoje.**
Tarde, **só se a interface estiver fechada**, nesta ordem: teste do `extractor` → P-11 → P-20 → P-13.

> **REGRA DE CORTE:** qualquer item da tarde que não couber é **cortado e registrado**. Nenhum
> deles vale atrasar o vídeo. A interface é entregável; eles são profundidade.

**PORTÃO 05/09:** a demo do vídeo existe e é gravável. *Se não existir, 06/09 vira interface e o
README encolhe para o mínimo verdadeiro.*

### 06/09 — a verdade escrita e o ensaio

README completo (critério: **alguém clona e roda sozinho**) · P-14 (ou os campos ganham leitor, ou
o diagrama para de prometer) · roteiro do vídeo · **uma tomada de teste**.

**PORTÃO 06/09:** README verdadeiro e roteiro cronometrado em ≤ 7 min.

### 07/09 — gravar

**`python scripts/smoke_nvidia.py` ANTES de gravar.** `LENTO` **não é EOL** e não justifica trocar
modelo (D-080). A cena de demo usa **`MAX_STARTUPS` baixo** — um run completo gasta 2-3 min só de
throttle do Cohere (D-068), e o vídeo tem 7.

**PORTÃO 07/09:** vídeo gravado. *Inegociável.*

### 08–09/09 — buffer

Refinar o vídeo, revisar a entrega, **rodar o smoke de novo antes de entregar**. Nada de código novo.

---

## 5. A decisão de hoje: P-10

De onde sai a `justificativa_tecnica`. As três opções, com custo medido:

> **A tabela abaixo foi recomparada em 02/09 (D-084).** A versão anterior tinha uma coluna
> *"efeito no vídeo"* e concluía contra (b) porque *"12 min e o vídeo tem 7"*. Isso é D-078 com
> outra roupa: uma restrição de entrega ocupando o lugar da função objetivo. **A régua abaixo é a
> certa — e ela continua valendo depois de 07/09, que é o teste.**

| critério | **(a) determinístico** | **(b) o LLM redige** | (c) filtro de depoimento |
|---|---|---|---|
| conserta o defeito medido | sim | sim | parcial |
| **latência que o gerente sente ao clicar** | nenhuma | ~51 s por recomendação; ~2,5 min mesmo para **uma** startup | nenhuma |
| **robustez** — hoje o grafo roda com **zero chamada de LLM em produção**, e foi isso que o fez sobreviver ao 4º EOL | preserva | põe o **único modelo vivo de 10** no caminho do campo que o gerente lê primeiro | preserva |
| **reversibilidade** | é **pré-requisito** de (b): alimentar o LLM com depoimento produz depoimento bem escrito | aditiva, cabe atrás de flag depois | — |
| custo | ~2 h · **zero API extra** (o rerank já pontua a união inteira) | ~2 h | ~1 h |
| ressalva | heurística: precisa de instrumento antes | — | **frágil**: D-082 mostrou que não há assinatura estrutural |

> **Recomendação: (a), e ela não compete com (b) — precede.** (a) conserta um defeito; (b) é
> funcionalidade sobre um campo já correto. **O argumento que de fato pesa contra (b) é o
> fornecedor único**, e a coluna do vídeo o estava escondendo. (b) fica **aberta**, com o critério
> certo: a latência que o gerente sente, decidida com a interface na frente.

---

## 6. Riscos, e o que já não é risco

| risco | estado |
|---|---|
| **Fornecedor único de LLM** — 4 EOLs em 3 meses, **0 vivos de 10** hoje | **NÃO MITIGADO. O maior aberto.** `src/config.py` já isola o provedor; falta a chave. **Ação sua, hoje** |
| **Interface escorregar e não haver demo** | **ativo, ponto único de falha.** Mitigado por: começar em 04/09, portão diário, e a regra de corte de 05/09 |
| **A base não chegar a 30** | ativo. Mitigado pela ordem por setor faltante + timebox |
| **Trial do Cohere** (1.000/mês, 10 req/min) | conhecido. Cena do vídeo com `MAX_STARTUPS` baixo |
| **O embedder morrer** | descoberto. Trocá-lo invalida os vetores e exige re-medir a régua inteira |
| ~~Confundir lento com morto~~ | **fechado em D-080** — era real: o smoke reportava `FALHOU` para um modelo vivo |
| ~~Créditos insuficientes~~ · ~~Estado mal modelado~~ | não se materializaram |

## 7. O que ainda pode aparecer — e como isso está limitado

Seria desonesto prometer que nada novo aparece. O que dá para fazer é **limitar onde**:

- **Não vai aparecer em item conhecido:** os 11 P e as dívidas estão todos em §3, com destino, e os
  cinco eliminatórios estão em §2 com o risco de cada um nomeado.
- **Pode aparecer na saída**, porque a saída só se conhece rodando — foi assim que os três defeitos
  de hoje surgiram. **Contramedida: o grafo roda em todo portão diário**, de 03 a 07/09. Um defeito
  achado em 03/09 tem 4 dias de correção; um achado em 06/09 tem um, e por isso a ordem dos dias põe
  produto antes de documentação.
- **Pode aparecer no fornecedor**, sem aviso prévio — é medido que não existe (D-079). Contramedida:
  smoke antes de gravar e antes de entregar, e o provedor isolado em `config.py`.
- **Verificado mecanicamente em 02/09, e limpo:** os 9 passos do pipeline têm módulo · 16
  tecnologias no manifesto e 16 no banco · os 7 campos obrigatórios existem em `Recomendacao` ·
  57 dependências pinadas, nenhum import faltando · `seed.py` é auto-contido (`conteudo_texto`
  inline nas fixtures), então **clone limpo semeia a base sem `data/raw/`**, que é gitignored.
- **NÃO verificado, e fica registrado como tal:** ninguém leu `src/` inteiro (3.783 linhas) — o que
  foi lido saiu do que a execução apontou; e ninguém rodou um clone limpo em máquina nova. **O
  critério "alguém clona e roda sozinho" só vale depois de 06/09, quando for de fato executado.**
- **O que NÃO tem contramedida** é o item 1 de §3.3. Se o modelo morrer e não houver segundo
  provedor, não há plano B. É por isso que a chave é a decisão de hoje.
