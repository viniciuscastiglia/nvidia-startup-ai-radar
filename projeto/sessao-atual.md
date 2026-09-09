# Pauta corrente — 09/09: ENTREGA às 23:59. O código fechou em 08/09.

> **PRÓXIMO PASSO DEFINIDO: uma AUDITORIA INDEPENDENTE, em sessão nova.**
> A sessão de 08/09 auditou, consertou e verificou os próprios consertos — **não houve checagem
> independente de nada**. Ela produziu D-113 a D-119 e a nota por critério, e essa nota está
> **lacrada** em `projeto/avaliacao-08-09.md` — que é **local e fora do git de propósito**, porque
> nota que o candidato dá a si mesmo não se entrega. Abri-la antes de escrever a sua
> transforma auditoria em confirmação. A seção "onde a auditoria pode ter errado", no fim daquele
> arquivo, é por onde começar.

## 📥 QUANDO A AUDITORIA EXTERNA VOLTAR — leia isto ANTES de consertar qualquer coisa

A auditoria roda em `~/auditoria-radar` (clone descartável, `CLAUDE.md` substituído pela carta do
avaliador, sem memória automática e **sem** a autoavaliação de 08/09). Para trazer o resultado:

```bash
cp ~/auditoria-radar/RELATORIO.md ~/case-nvidia/projeto/auditoria-externa.md
```

*(peça à sessão de auditoria que grave o relatório em `RELATORIO.md` na raiz dela)*

**A REGRA AO RECEBER, E ELA JÁ CUSTOU CARO DUAS VEZES: verifique o achado antes de consertar.**

- Em **03/09**, três achados de uma auditoria caíram na verificação — e um deles era o classificado
  como "o mais grave".
- Em **08/09**, **duas propostas minhas morreram na medição**: o filtro de "proposta de valor" no
  Extractor (só 7% das frases candidatas têm marcador de beneficiário) e a poda de gatilhos por
  polissemia (zero casos nas 8 fixtures do gabarito, logo não moveria régua nenhuma).

**Auditoria produz hipótese, não fato.** Para cada achado, antes de tocar em código:

1. **Reproduza** — qual comando mostra o defeito? Se nenhum mostra, não está provado.
2. **Meça o custo do conserto NA RÉGUA** — `avaliar_agentes.py`, `--exclusoes` e `pytest` custam
   zero API e ~20 s somados. Fixe o critério **antes** de rodar (D-055).
3. **Um conserto por commit**, com a régua rodada depois de cada um. Régua que se move sem
   explicação = `git revert` imediato, sem tentar consertar por cima.

**A BARRA É MAIS ALTA NA VÉSPERA.** Um defeito medido e explicado defende melhor que um conserto
apressado que ninguém mediu — é o que sustenta P-21, P-23 e D-119 hoje. Mudança de produção a esta
altura só entra se: (a) o defeito foi reproduzido, (b) a régua não regride, e (c) a reversão é um
commit.

---

## O que 08/09 fechou — sete decisões, todas verificadas por execução

| decisão | o que mudou |
|---|---|
| **D-113** | o comentário de `USAR_JUIZ_LLM` justificava o `False` com o placar de um modelo **morto em 27/08**, e transmitia *"o LLM não deu conta"* — o oposto do medido. O juiz **passou todos os critérios** em D-072 |
| **D-114** | `COMPLEXIDADE` cobria 5 de 16 tecnologias; as outras 11 caíam no default. **Campo 5 dos 7 obrigatórios** era constante para 69% do catálogo. Agora 15/15 recomendáveis, com razão por linha |
| **D-115** | a Solinftec saía `ELEGÍVEL` com o documento dizendo *"Criada há 18 anos"*. `há N anos` solto acerta **1 de 3** na base — o particípio de criação é obrigatório |
| **D-116** | `LLM_TIMEOUT=120` era menor que a latência real (**mediana 216,9 s hoje**, contra 51 s em D-080). `POST /api/perguntar` devolvia **HTTP 500 após 363 s = 3 × 120** com o modelo VIVO |
| **D-117** | `seed.py --verificar-urls` reprovava uma fonte VIVA por **HTTP 429**. Repetição exata de D-090, na mesma URL |
| **D-118** | NeoSpace e Enter entram (base **32 · 99**). `AI-native` 1 → 2. A Enter saiu `AI-enabled` e **ficou assim** |
| **D-119** | **as 4 `AI-native` do gabarito saem `AI-enabled`** — a distribuição de classe é propriedade do DETECTOR, não da base |

**Varredura de afirmações:** o README prometia `128 testes` e entregava 134; o `CLAUDE.md` afirmava
que a Solinftec era caso-limite ELEGÍVEL, o oposto do que D-115 fez na mesma manhã. Corrigidos.

**Varredura de comandos:** os ~21 anunciados foram rodados; **20 passaram** e o que falhava virou
D-117. As quatro réguas reproduzem: `24/24` no gabarito · `denso 95% r@1 · 79% e@1` · `49%/100%` ·
`38% contra 44%`.

## ✅ O QUE 08/09 (TARDE) FECHOU — a auditoria voltou e foi verificada achado a achado

**D-120** — a contradição da `justificativa_tecnica` está resolvida. As duas réguas mediam
populações diferentes; o defeito é um ponto cego de `pontuar()` (menu de nome de produto = densidade
máxima) e ele contamina **passagem e span**, porque a mesma função decide as duas. Não consertado,
com a razão escrita: não destrava o critério 3 e move a citação. Abre **P-27**.

**D-121** — a auditoria independente: **8 confirmados, 1 refutado (#10), 1 não reproduzido (#8)**,
e **2 confirmados com o diagnóstico errado** (#1 chamava entitlement de morte; #4 tratava latência
do dia como constante). **6 consertos entraram**, um por commit.

**Verificação de sistema, por execução:** `134 passed` · grafo ponta a ponta em **143 s** com
rerank Cohere vivo · interface sobe e serve `/`, `/api/runs`, `briefing.txt` e `run.json` · smoke
**3/3 em 11 s**. Réguas idênticas depois de tudo: `classe 3/7 · stack 6/7 · confianca 0/6` ·
exclusões `10/10 e 11/11` · gabarito `24/24`.

## 🔴 O QUE CONTINUA ABERTO

1. **O VÍDEO — roteiro E gravação, nenhum dos dois existe.** É eliminatório e é o **único item que
   ainda move nota de forma garantida**: 0 → nível 3 vale **+15 pontos**. Os critérios 2, 4 e 6 já
   estão em 4/4 (30 pontos sem folga) e os critérios 1 e 3 pedem redesenho dos agentes.
2. **`run-recomendacoes.json` tem 30 empresas e a base tem 32** (D-118, achado #6 da auditoria).
   Re-rodar custa ~17 min e cota do Cohere, e **pode mover a manchete 38%×44% para qualquer lado** —
   a NeoSpace é `AI-native` e sweet-spot. Critério fixado ANTES, ou não rode.
3. **A cena da abstenção custa 377,6 s** — re-medida em 08/09 pelo caminho de produção, contra os
   510 s anteriores. Continua **não filmável em tempo real**: grave por cima do run commitado em
   `data/runs/exemplo-*.json`.
   > **E o número que engana: o smoke deu chat completion em 6,9 s no mesmo minuto.** O smoke manda
   > prompt trivial pedindo 120 tokens; o passo 8 manda 5 passagens com `json_schema`. **O smoke é
   > instrumento de VIDA, não de latência** — não planeje o vídeo pelo relógio dele.
4. **A interface nunca foi vista por MIM rodando uma consulta ponta a ponta na tela.** A auditoria
   diz que rodou e que os quatro itens funcionam; eu confirmei que ela sobe, serve e exporta. A
   diferença entre relato e execução é a que já derrubou um achado hoje.

## ⛔ DEFEITO MEDIDO SEM CONSERTO DISPONÍVEL — é a defesa, não a pendência

| defeito | causa, medida |
|---|---|
| `classe 3/7`, perdendo da trivial 4/7 | **D-119** — teto do conserto é **+1** (D-060: 7 de 8 fixtures com zero marcador) |
| `prioridade` **nunca** `alta` (0 em 89) | `min()` → `confianca` 0/6 → `data_publicacao` ausente em 86 de 93 (P-11, P-25) |
| `justificativa_tecnica` com mobília de página | **RESOLVIDA em 08/09 (D-120).** As duas réguas mediam populações diferentes: a de 71% é span numa amostra semeada e está certa; a produção falha porque `pontuar()` premia menu de nome de produto (rodapé = **6.38**, o maior score medido) — e a função decide passagem **e** span. Não consertado: move a citação, e o campo não é o que trava o critério 3 (P-27) |
| relevância 38% × 44% | dor a 49% alimenta a consulta (D-105) |
| filtro do Inception vê 10,6% | varrer tudo quebra o veto de terceiro — medido em D-102 |

> **DUAS PROPOSTAS DE 08/09 MORRERAM NA MEDIÇÃO, e ficam registradas porque é o padrão a repetir:**
> o filtro de "proposta de valor" no Extractor (só **7%** das frases candidatas têm marcador de
> beneficiário) e a poda de gatilhos por polissemia (**zero** casos nas 8 fixtures do gabarito, então
> não moveria a régua). Nenhuma das duas entrou.

## 📌 CONTEXTO QUE NÃO MUDOU

- **Não rode `--refetch`** — reescreve o cache e o corpus deixa de ser o medido (D-110)
- **Não julgue recomendação com `RERANK_PROVEDOR=nenhum`** (D-097)
- **Cota do Cohere é escassa** (D-093) — 1.000 chamadas/mês
- **`LENTO` não é EOL** (D-080) — a resposta é subir o relógio, não migrar

---

# O que era a pauta de 07/09 — o histórico abaixo fica

## ✅ O QUE 06/09 (noite) FECHOU — e um dos três itens da pauta anterior CAIU na verificação

> A sessão abriu verificando os três itens da pauta escrita mais cedo. **Dois conferiam, um não.**
> `pytest` **102 → 128** · régua dos agentes **idêntica** · as mesmas **7 recusas**.

| item | o que aconteceu | decisão |
|---|---|---|
| **Cache das 16 fontes** | O corpus entrou no git: `ingerir_nvidia.py` **não toca a rede** sem `--refetch`, e o clone limpo reproduz **175 + 202** offline. `avaliar_rag.py --validar` = **24/24** contra o corpus ingerido do cache. **O teste achou um defeito que nenhuma saída mostrava:** `write_text` grava CRLF e `read_text` traduz para LF, então em **7 das 16** fontes o texto que `--refetch` chunkava não era o que a leitura do cache chunkava | **D-110** |
| **P-26 — o passo 8 ganhou porta** | `POST /api/perguntar` + o botão *"Perguntar à base NVIDIA"*. Verificado por execução com as duas perguntas do gabarito: a **q04** responde citando 2 das 5 que leu; a **q20 ABSTÉM**, com as 5 passagens todas do `AI Enterprise`. E `rag/geracao.py` ganhou os testes que nunca teve — a suíte estava verde com 102 e o módulo da abstenção não tinha nenhum, **porque módulo inalcançável não quebra teste** | **D-111** |
| **P-14 — o planner planeja** | O achado estava numa linha: `estrategia_analise` era **string constante**, então "fazer o subgrafo lê-la" não mudaria nada. Agora `dores_prioritarias` sai da consulta e `nvidia_rag` ordena as dores por ela. **Régua idêntica** (lista vazia é a identidade) **e não inerte**: em 131 pares empresa × dor, **34% trocam a tecnologia** | **D-112** |
| ~~**P-22**~~ | **O ITEM ESTAVA ERRADO.** Ver a seção riscada abaixo: `par curado 9 · frase por dor 119 · FALLBACK 0`. Fechada desde D-104; era correção de documento | — |
| **README + `environment.yml`** | Os 4 buracos do clone limpo (D-089) fechados, a tabela de stack sem os quatro *"a definir"*, e o ponteiro para `projeto/decisoes.md` com o que ele é | — |
| **Docstrings** | `query_planner`, `recommendation` e `briefing` param de se declarar *"STUB DA SESSÃO 01"* — e o texto novo diz **por que** a escolha é medida, não inacabada | — |

### A medição que veio junto, e ela vale além do passo 8 — D-111

Critério fixado **antes** do placar (não-inferioridade nos dois lados, com braço de controle
obrigatório, que é a lição literal de D-109):

| 24 perguntas do gabarito | C `nemotron-3.5-lightning` | B `gpt-oss-120b` (Groq) |
|---|---|---|
| respondeu as que TÊM resposta | 18/19 | **19/19** |
| absteve nas que NÃO têm | 5/5 | 5/5 |
| **acurácia de abstenção** | **23/24 = 96%** | **24/24 = 100%** |

**O Groq PASSA — o oposto exato de D-109, onde ele foi dominado como juiz.** Confirma que
*"gerar-com-abstenção é outra tarefa"* era leitura certa, não ressalva de conveniência.

**A ressalva vai junto e é maior que o placar: a diferença é UMA pergunta em 24.**
Não-inferioridade está demonstrada; superioridade **não**. E o achado que vale mais que a
comparação: **dois provedores independentes chegam a 23-24 de 24 — a abstenção não é propriedade
frágil de um modelo que pode morrer amanhã.**

**`LLM_MODEL` não mudou.** Medir não é promover (D-078), e trocar o provedor de produção contraria
D-087.

---

## 🔜 O QUE SOBRA PARA 07/09 — e é só o vídeo

1. **`python scripts/smoke_nvidia.py` ANTES de gravar.** 4 segundos, e é a única defesa contra os
   dois pontos únicos de falha (embedder e Cohere). `LENTO` **não é EOL** (D-080).
2. **O roteiro do vídeo não foi escrito** — ficou fora do escopo desta sessão, e é o único item de
   produto em aberto. ≤ 7 min.
3. **A cena que este sistema tem e quase nenhum tem:** a **q20** na porta do passo 8 —
   *"qual o preço da licença do NVIDIA AI Enterprise?"* — e o Radar **recusando responder**, com as
   5 passagens que ele leu, todas impecáveis no assunto, na tela. Ela custa uma chamada de LLM.
4. **`RERANK_PROVEDOR=cohere` para gravar** (D-097) e `empresas` **baixo** — um run de 2 empresas
   custou ~2 min medidos hoje.
5. **NÃO rode `--refetch` antes de gravar.** Ele reescreve o cache e o corpus deixa de ser o medido.

### O que continua ACEITO e escrito, com os dois lados medidos

**P-21** (o motor faz 38% contra 44% da linha trivial, causa: precisão de dor em 49%) e **P-23**
(o filtro do Inception vê 10,6% do texto) são redesenho. **Um defeito medido e explicado defende
melhor do que um conserto apressado que ninguém mediu.**

---

## O que era a pauta de 06/09 (manhã) — dois itens conferiram, um caiu

### O que NÃO entra, e a razão

**P-21** (o motor perde da linha trivial, 38% × 44%) e **P-23** (o filtro do Inception vê 10,6%)
são redesenho, e ambos estão medidos dos dois lados. **Um defeito medido e explicado defende
melhor do que um conserto apressado que ninguém mediu** — o 38% vai para a defesa com a causa
junto (precisão de dor em 49%), não escondido.

---

> **06/09 — D-107: A INTERFACE ESTÁ FEITA, e o eliminatório do vídeo tem porta.**
> `python -m src.web` sobe a tela; ela roda o grafo ao vivo e transmite cada nó por SSE.
> As 4 etapas fecharam — consultar → ver empresas com diagnóstico → recomendações com evidência
> clicável → exportar o briefing byte a byte — e entrou a **vitrine do passo 7**, que mostra as
> duas ordens da mesma recuperação. Verificado com run real (`cohere`, 2m18 para 3 empresas),
> `pytest` **102 passed**, e a régua dos agentes **idêntica**.
>
> **O que a vitrine mostrou na primeira execução, e é a P-21 na tela:** para a Agrotools, dor
> `latencia`, a busca híbrida devolve `NVIDIA AI Enterprise` em **1º, 2º e 3º** — a página
> guarda-chuva de D-105 — e o passo 7 traz **Omniverse da 6ª para 1ª e da 23ª para 2ª**.
>
> **O que fica ABERTO e é do dia 06/09:** o README (o clone limpo não sabe criar o ambiente),
> as 3 docstrings que dizem "STUB DA SESSÃO 01", o cache das 16 fontes do RAG, e o roteiro do
> vídeo. **P-14 continua aberta — e a interface NÃO a fechou de propósito:** mostrar
> `estrategia_analise` na tela faria a tela afirmar que aquele campo governou a análise, e
> nenhum nó do subgrafo o lê.

## O que era a pauta até 05/09 — a IA fechou, a interface era o que restava

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

## 🔜 PARA A PRÓXIMA SESSÃO — o RAG e o Grok

> Escrito ao fim da madrugada de 05/09, **antes** de qualquer implementação. Nada aqui virou
> código nem decisão: é o estado de uma investigação que mudou o diagnóstico do sistema, e ela
> não existe em `decisoes.md` porque **nenhuma decisão foi tomada**. A próxima sessão decide.

### 1. O que a investigação achou, e ela contradiz o que eu tinha concluído uma hora antes

O bloco 4 mediu o motor de recomendação em **38% contra 44% da linha trivial**, e a primeira
leitura pôs a culpa na recuperação. **A evidência seguinte diz que o gargalo está ANTES dela.**

Compare as duas perguntas que a mesma máquina recebe:

| | |
|---|---|
| **A régua do RAG** (95% r@1 · 79% e@1) pergunta | *"Que servidor de inferência da NVIDIA faz **dynamic batching** e executa vários modelos ao mesmo tempo?"* |
| **A recomendação** (38%) pergunta | `custo — com a diversificação das fontes de receita — e um controle dos custos… Análise por centros de custos, usuários e categorias de despesas` |

A primeira tem a agulha escrita na pergunta: `dynamic batching` está literal na página do Triton.
A segunda é uma fintech falando de **categorização de despesa em cartão corporativo** — sem uma
única palavra técnica para ancorar. Sem âncora, o recuperador devolve a página de maior
superfície temática, que é a `AI Enterprise`.

**E a dor às vezes nem é real.** Consulta literal capturada da Conta Simples:

```
latencia Emita quantos cartões corporativos precisar, concentre seus gastos em um só lugar
         e gerencie tudo o que acontece em tempo real.
```

Isso não é queixa de latência: é marketing de painel. `GATILHOS_DOR` casou *"tempo real"*.

### 2. As três medições que sustentam isso — todas de 05/09, todas reproduzíveis

| medição | número | comando |
|---|---|---|
| a página guarda-chuva ocupa vaga e nunca ganha | `AI Enterprise` em **17 de 34 pares**, razão de acerto em **0**, ocupando vaga em **11 que erram** | ler `run-recomendacoes.json` |
| ela é 3,1× a própria fatia do corpus | 7% dos chunks, **22%** das recomendações, sob **5 das 8 dores**. Contraste: Guardrails 0,6× sob 2 dores | `psql` + o mesmo json |
| **o corte que aponta o culpado** | regra chaveada por **setor** (vem da curadoria): **10/16 = 62%** · chaveada por **dor** (vem do casador, precisão 49%): **3/18 = 17%** | `--regras-tapi` |

> **O confundidor, declarado:** a regra de setor julga todas as ~3 recomendações da empresa
> (2,94 tecnologias por par medidas); a de dor julga ~1 (1,06). **Não é comparação limpa.** 62
> contra 17 é grande demais para ser só isso, mas quem quiser usar o número na defesa precisa
> dizer a ressalva junto.

**O número que já dizia tudo estava na régua há semanas: a precisão de dor é 49%.** Metade das
dores extraídas não confere com o gabarito, e a recomendação é função da dor.

**Consequência para a ordem do conserto:** mexer no reranking seria consertar a peça que
funciona. **O RAG continua sendo o ponto forte e os 95% continuam de pé** — o que os 38%
mediram pela primeira vez não foi a recuperação isolada, foi a **composição** (extração de dor →
consulta → recuperação). Nenhuma régua anterior atravessava essa fronteira.

**Candidato a D-107**, se a próxima sessão confirmar: *o gargalo do motor de recomendação é a
extração de dor, não a recuperação*.

### 3. O Grok — e aqui eu errei, o repositório estava certo desde 28/08

Eu rodei `sondar_catalogo.py`, que fala **só com a NVIDIA**, e concluí "não existem dois
modelos". A conclusão correta daquele teste era *"a conta NVIDIA alcança 1 de 10"* — ela não
diz nada sobre um segundo provedor. **D-067 registrou em 28/08 que o Grok está pré-autorizado
pela liga e que NÃO foi descartado por mérito: não foi testado, porque a chave não existia.**
`revisao-pontos-cegos.md` já dizia a frase inteira: *"a cadeia certa é entre PROVEDORES… o
bloqueio é a chave, não o código."*

> ~~**Verificado hoje: o custo é três variáveis de ambiente e ZERO código.**~~
> **ERRADO, corrigido em 06/09 por D-108.** O custo era três variáveis **mais duas linhas**, e a
> diferença não era estética: `LLM_API_KEY` alimentava os **três** clientes, então pôr nela a
> chave de um segundo provedor levava **embedding e rerank junto** e matava a busca densa com 401.
> Provado por execução. A verificação de 05/09 leu `src/llm.py` e o comentário de `config.py`, e
> não seguiu `_API_KEY` até os outros dois consumidores — **defeito consertado, e a lição é a de
> D-083: ler o código não é executá-lo.**

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
LLM_API_KEY=gsk_...          # hoje só do LLM; NVIDIA_API_KEY serve embedding e rerank
```

- `src/llm.py` é um `ChatOpenAI` sobre `base_url`/`api_key`/`model`, tudo vindo do config;
- `src/config.py` aceita **`LLM_API_KEY` como nome neutro** — e **desde D-108 ela é só do LLM**,
  que é o que o comentário *"para que trocar de provedor não exija renomear variável"* prometia
  sem cumprir;
- `smoke_nvidia.py` lê tudo de `LLM.*` — **ele já valida qualquer provedor**, sem uma linha.
  Confirmado hoje: **3/3 capacidades OK** com o chat no Groq e o embedding na NVIDIA no mesmo run.

**Para os DOIS rodando juntos** o custo sobe: hoje `LLM` é singleton no config. Precisa de uma
segunda config e de um jeito de o nó pedir qual quer. Pequeno, não zero.

### 4. A consequência que vale mais que o fallback — e é HIPÓTESE, não medição

O modelo atual tem **mediana de 51 s** (D-080), e esse número fechou decisões pelo repositório:

- a opção **(b)** da `justificativa_tecnica` (o LLM redigir) caiu em parte por *"~2,5 min mesmo
  para uma startup"*;
- o **juiz do Extractor** (P-09) custa ~52 chamadas ≈ 45 min de relógio;
- o **passo 8** está fora do caminho do grafo em parte por custo.

**Se o Grok responder em segundos, as três reabrem** — não por mérito técnico novo, mas porque a
régua de D-084 é *latência que o gerente sente*, e o número que as fechou muda de ordem de
grandeza. ~~**Isso não está medido. É a primeira coisa a medir, e custa 4 segundos.**~~

> **MEDIDO em 06/09 (D-108), mesmo prompt e mesmo dia, 5 chamadas cada: mediana de 28,85 s
> (NVIDIA) contra 1,15 s (Groq) — 25×.** Não foi o Grok: a chave da xAI autentica mas o time
> responde `403` com `team_blocked: true`, porque o crédito grátis de $25/mês era do *public beta
> que encerrou no fim de 2024* e a conta nunca teve saldo. Quem entregou o número foi o **Groq** —
> LPU, tier gratuito, outro fornecedor, nome quase idêntico. `json_schema` estrito funciona
> (5/5 parse OK), que era a condição eliminatória de D-040.
>
> **E o número de 51 s deste parágrafo já não valia:** a NVIDIA está **1,8× mais rápida que em
> 02/09**. A latência deste fornecedor é variável de estado, não constante do modelo — **quem
> for reabrir uma decisão citando latência tem de re-medir.**
>
> **O que isso reabre, e o que NÃO reabre:** a aritmética do juiz do Extractor muda de ordem —
> as ~52 chamadas que custavam ~45 min passam a custar menos de 1. **Mas isso é latência, não
> qualidade:** nada mediu se o `gpt-oss-120b` julga tão bem quanto o Nemotron, e trocar o
> provedor de produção contraria D-087, fechado com a liga. Medir o juiz é
> `avaliar_agentes.py --juiz`; promover provedor é outra decisão, e não foi tomada.

### 5. Por que o LLM é a ferramenta certa PARA ESTE gargalo

O juiz LLM do Extractor já existe, atrás de `USAR_JUIZ_LLM`, e D-072 mediu:

| | casador (produção) | com o juiz |
|---|---|---|
| **precisão de dor** | **49%** | **83-96%** |
| recall de dor | 100% | **71-79%** |
| dor proibida emitida | 10 | **1-2** |

É exatamente o número que a §2 apontou como gargalo. **Mas os 83-96% são do
`nemotron-3-nano-30b-a3b`, que a sondagem de hoje confirmou EOL** — o número não vale até ser
refeito no modelo vivo. E o custo declarado continua: **recall cai 25 pontos.** O argumento a
favor está pronto em D-072 (*"erro por omissão é recuperável; erro por afirmação, não"*), e a
promoção é **P-09**, aberta desde 28/08.

**E o que um LLM NÃO conserta:** reescrever a consulta. A dor está errada, não mal escrita —
reescrever *"cartões corporativos… em tempo real"* produz uma consulta de latência fluente e
igualmente errada. O conserto tem que ser não gerar a dor falsa.

### 6. A ordem sugerida para a próxima sessão

```bash
python scripts/smoke_nvidia.py                  # 4 s. VIVE? e em QUANTO TEMPO? decide o resto
python scripts/avaliar_agentes.py --juiz        # ~52 chamadas: precisão de dor no modelo vivo
python scripts/avaliar_rag.py --geracao         # abstenção do passo 8 (23/24 hoje) — ele mente?
python scripts/medir_saida_estruturada.py -n 5  # respeita `json_schema`? é a base de D-040
```

Nenhum toca a cota do Cohere. **Fixar o critério antes de rodar cada um** — e lembrar que
**medir não é promover**.

### 7. O que é decisão sua, não minha

- **Reabrir a D-087?** Ela decidiu em 02/09 que *"o fallback não entra, e a hora vai para a base
  e a interface"* — por **alocação de tempo, não por mérito**. O contexto mudou: a base fechou, e
  o gargalo medido hoje é onde o LLM é a ferramenta. Mas são 2 dias até o vídeo.
- **Apertar o rebaixamento das 9?** A parte 2 do critério de D-101 reprovou (27% contra 43%).
  D-101 diz *"apertar, não reverter"*. Eu medi e parei.
- **A interface.** Continua sendo o **único eliminatório em aberto no produto**, e tem 05/09
  inteiro + a manhã de 06/09. Nada acima vale atrasá-la.

---

### 8. Os outros problemas abertos, para pesquisar com calma

> Verificados um a um em 05/09, não copiados do plano — **um item caiu na verificação**: os
> diagramas `.mmd` NÃO estão desatualizados (`diagramas.py` dá zero diff hoje); `plano.md` foi
> corrigido.

| # | problema | o que é, em uma frase | o que pesquisar |
|---|---|---|---|
| ~~1~~ | ~~**A interface não existe**~~ | **FEITA em 06/09 (D-107)** — `src/web/`, FastAPI + SSE, 9 testes novos | ✅ |
| 2 | **`confianca` é "baixa" nas 30** | é o `min()` sobre ~9 afirmações; basta uma fraca. **Já medido: o que move o campo é a recência, e `data_publicacao` falta em 86 de 93 documentos** | extração confiável de data de publicação: `article:published_time`, JSON-LD `datePublished`, microdata |
| 3 | **O filtro do Inception lê 10,6% do texto** | varre trechos de evidência, não o documento. Varrer tudo quebra o veto de terceiro por construção: **7 → 13 recusas, ≥ 4 falso positivo** | atribuição de sujeito: distinguir *"sou uma consultoria"* de *"cito uma consultoria"* — coreference, entity attribution |
| 4a | **As 16 fontes do RAG não têm cache** | `ingerir_nvidia.py` baixa ao vivo; a deriva já foi MEDIDA (mesma contagem, hash diferente). O gabarito aponta frase-âncora, então `avaliar_rag.py` quebra na mão do avaliador | cache de conteúdo com `--refetch`; decidir o que cachear (HTML cru × texto limpo × chunks) |
| 4b | **O README não ensina a rodar** | 4 buracos do clone limpo: sem `environment.yml`, `createdb` não escrito, `DATABASE_URL` do Docker não escrita, `COHERE_REQ_POR_MIN` | nada: é escrita |
| 5 | **2 módulos sem teste** | **verificado: zero** arquivos de teste citam `rag/geracao.py` (o passo 8, onde mora a abstenção) e `db.py` (o SQL da recuperação). Os 93 verdes dão cobertura aparente | nada: é execução |
| 6 | **4 campos calculados que ninguém lê** | `estrategia_analise`, `exige_sinais_ia`, `score_recuperacao`, `motivo_validacao`. Não é código morto — a arquitetura PUBLICADA promete "estratégia de análise" e o sistema a joga fora | decisão, não pesquisa: ou o subgrafo lê, ou o diagrama para de prometer |
| 7 | **3 docstrings dizem "STUB DA SESSÃO 01"** | `query_planner`, `recommendation`, `briefing` — e dois são escolhas medidas, não trabalho inacabado. Avaliador que lê "STUB" conclui projeto incompleto | nada: 10 minutos, e é risco de nota puro |
| 8 | **Embedder e Cohere sem plano B** | o embedder está em toda consulta e trocá-lo invalida os 377 vetores (re-embedar + re-medir tudo); o Cohere é o único reranker desde maio, trial de 1.000/mês que já estourou. **O Grok não resolve nenhum dos dois** | embedding local como plano B: `sentence-transformers`, BGE-M3 (fala português) |
| 9 | **203 frases sem sujeito nas fixtures** | o coletor apagava nome próprio em tag inline. **Raiz consertada**; o dado velho não. Efeito medido: **1,7%** dos trechos | nada: re-coleta manual, depois da entrega |

**A ordem sugerida, se for para escolher:**

- **antes do vídeo:** a interface (1) e as docstrings (7) — a segunda são 10 minutos e é nota;
- **junto com o README de 06/09:** o cache das fontes (4a), porque *"projeto que não executa na
  mão de quem avalia"* é eliminatório e a deriva já aconteceu uma vez;
- **depois da entrega, por valor de aprendizado:** (3) e (2). As duas são **o mesmo tipo de
  problema** — o sistema decide com lista de palavras onde precisaria entender contexto — e são
  exatamente onde um LLM tem chance de valer a pena.

---

## ⚠️ LEIA PRIMEIRO — o Cohere é ponto ÚNICO de falha no passo 7

**A cota do Cohere foi resolvida com uma key nova** — `smoke_nvidia.py` volta a **3/3 OK** e o
passo 7 roda.

**`RERANK_PROVEDOR=nvidia` não é opção — e isto NÃO é notícia de 03/09.** O reranker da NVIDIA
está morto **desde 2026-05-18**, com `410` e a data no corpo, e **D-013 registrou no primeiro dia
do projeto**: foi essa morte que trouxe o Cohere. A revisão de 03/09 chegou a anunciar isso como
achado novo e **estava errada** (D-097). Os `404` que aparecem no mesmo teste são **entitlement**,
não morte (D-070). O que importa operacionalmente é só isto: **sobrou um provedor**, e em 03/09
houve horas com a cota dele esgotada e o passo 7 sem ninguém.

- **Rode `smoke_nvidia.py` antes de gravar e antes de entregar.** São 4 segundos, e agora ele é a
  única defesa de um ponto único de falha, não só do LLM.
- **`RERANK_PROVEDOR=nenhum` continua sendo o default de DESENVOLVIMENTO** — `pytest` 81 passed em
  6,5 s contra 150-460 s. O que se perde está medido: denso puro faz **95% r@1 e 100% r@3**
  (D-064).
- **MAS NUNCA JULGUE RECOMENDAÇÃO COM ELE DESLIGADO (D-097).** Em 03/09 uma auditoria quase
  registrou como defeito grave o *"NVIDIA Healthcare recomendado para uma agtech"*. Era artefato
  do modo barato: com o passo 7 ligado, a Solinftec recebe **NVIDIA Isaac**, e ela fabrica robô
  agrícola. O modo barato serve para desenvolver, nunca para avaliar o que o gerente veria.
- **Para o vídeo:** o rerank custa ~2-3 min num run completo, então a cena é uma consulta com
  `MAX_STARTUPS` baixo (D-068).

## O que a revisão de 03/09 (noite) achou — D-097

A sessão da tarde foi auditada por execução, não por leitura. **Não houve alucinação de dados:**
três trechos literais de cada um dos 93 documentos foram buscados na `url_fonte` viva, e **39 das
50 notícias batem 3/3, nenhuma bate 0/3**. Contagens, D-095, o `pytest` de D-093, as 10 chaves de
`SETORES` e a evidência das 7 recusas reproduziram exatos.

**Quatro consertos entraram, e um "defeito" foi REFUTADO** (o Healthcare para agtech, acima).

| conserto | efeito medido |
|---|---|
| mobília virava justificativa técnica de venda | o mural do TensorRT-LLM foi de **vencedor da página a −11,61**; `--justificativas` ficou em **15/21**, sem regressão |
| 62 parágrafos que eram só um ponto | saíram das 30 fixtures; portão novo no `seed.py`, **por FORMA** e não por lista |
| o nome próprio sumia na coleta | raiz consertada em `coletar.py` (**`unwrap` + `smooth`** — o primeiro sozinho não faz nada); **0 lacunas** em 5 URLs reais |
| doc contradizia o sistema | a Solinftec **não** é caso de exclusão por idade — ela sai ELEGÍVEL; e PagSeguro está na **NYSE** |

**Fica aberto — P-25:** as **203 frases decapitadas** nas fixtures já coletadas (*"…afirma o CEO
da"*) não voltam sem re-coleta e re-recorte à mão dos 93 documentos, com re-medição da régua
depois. Efeito medido hoje: **1,7% dos trechos de evidência**. Depois da entrega.

## O que 03/09 fechou

**A M3 fechou: a base foi de 8 para 30** (D-090), com **93 documentos** e **93/93 `url_fonte`
resolvendo**. As duas consultas que devolviam zero — `"fintechs"` e `"agro"` — respondem, e
**nenhuma das 10 chaves de `SETORES` devolve zero**: `logística`, `jurídico`, `indústria`,
`educação` e `varejo` estavam vazias e ninguém sabia, porque a base era pequena demais para isso
aparecer.

| verificação, ao fim do dia | resultado |
|---|---|
| `seed.py --verificar-urls` | **30 startups · 93 documentos · 93/93 URLs** |
| `avaliar_agentes.py --validar` | exit 0 · **evidência literal ok nas 30** |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1amb · 49%/100%` — **idêntico ao de antes da base** |
| `--exclusoes` | **10/10** falso negativo · **11/11** falso positivo (era 7/7 · 7/7). Casos vindos de **fixture: 5 → 11** — a régua deixou de ser majoritariamente sintética |
| `varrer_elegibilidade.py` | **novo (D-094):** 7 de 30 recusadas, e cada recusa confere — 4 por idade, 1 consultoria, 1 cripto, 1 capital aberto |
| `--justificativas` | trivial `12/21` · seletor `15/21` — sem regressão |
| `pytest -q` | **81 passed** (com `RERANK_PROVEDOR=nenhum`, em 6,5 s — ver o aviso no topo) |
| `python -m src.graph` | roda em fintech, agro, voz, robótica, indústria, jurídico, educação, varejo |
| **contaminação** | **zero** teaser de terceiro e **zero** mobília de página nas 30 — e as duas checagens entraram no `seed.py --so-validar` (D-096), com teste negativo |

**As 22 novas entram como DADO, sem `gabarito:` nem `perfil_alvo`** (D-062) — e isso agora está
**no código**, não só na prosa. Sem o filtro, a precisão cairia de **49% para 24%** com `classe` e
`recall` idênticos: corrupção silenciosa, medida.

**As 4 exclusões do Inception ganharam caso real:** consultoria (Deal) · **capital aberto →
Zenvia** · **cripto → Liqi** · **> 10 anos → Agrorobótica, Agrotools, Automni e JetBov** (a linha original dizia *"Agrotools e Solinftec"* e contradizia a tabela de consertos deste mesmo arquivo, que registra a Solinftec saindo ELEGÍVEL — corrigido em 04/09). Antes só havia frase
sintética escrita por nós.

## O que 04/09 fechou — os dois consertos que o gerente vê na tela

A sessão da manhã escreveu `projeto/achados-04-09.md` (efêmero, já removido) e **errou três vezes
dentro do próprio documento**. A sessão da tarde **reproduziu tudo antes de escrever plano**, e o
plano vive em `docs/superpowers/plans/2026-09-04-fechamento-ia.md`.

| o que fechou | decisão |
|---|---|
| **O filtro do Inception rodava DEPOIS de quem consome o resultado dele.** Na tela: a Liqi saía `x exclusão por 'cripto'` e sete linhas abaixo recebia *"Agendar conversa técnica com o time de engenharia da Liqi"*. Uma aresta — `elegibilidade` não dependia de nada que rodasse antes dela | **D-099** |
| **Recusada MANTÉM recomendação, rotulada e rebaixada.** Decisão do Vinícius, e o fato que a decidiu: **a JetBov é a única `AI-native` e o único `sweet-spot` das 30 — e é NÃO ELEGÍVEL por idade.** Suprimir apagaria o melhor prospect da tela | **D-099** |
| **Três defeitos no texto que chega ao gerente:** a causa falsa do "zero recomendações" (Conta Simples tem 3 dores VALIDADAS e lia *"sem evidência validada"*), o ponteiro `ver D-059` impresso uma vez por empresa, e os cortes no meio da palavra em dois dos 7 campos do TAPI | **D-100** |
| **`non-AI` deixou de ser o default de detecção falha (P-24 FECHADA).** `sinal_verificado` é o par que `Elegibilidade` já tinha. Custo medido ANTES: `classe 3/7 → 3/7` | **D-101** |
| **Os dois instrumentos de 04/09 ganharam registro** — eles citavam `(D-098)` antes de D-098 existir | **D-098** |

**Verificação:** `pytest` **87 passed** (era 81) · `avaliar_agentes` `classe 3/7 · stack 6/7 ·
confianca 0/6 · elegivel 6/6 · 49%/100%` **idêntico** · `varrer_elegibilidade` **as mesmas 7
recusas** · o grafo rodou com `RERANK_PROVEDOR=cohere` e o briefing foi **lido inteiro**.

**Duas divergências investigadas** contra o que o documento da manhã afirmava: os `10,6%` de
cobertura de `elegibilidade()` são **trechos ÚNICOS** (a soma bruta dá 11,0%), e o conserto amplo
dá **13 recusas, não 11** — e o argumento bom contra ele não é a contagem, é que **varrer o
documento inteiro quebra `_fala_de_terceiro` por construção**, porque o veto exige que TODA
ocorrência tenha marcador.

## O que a madrugada de 05/09 fechou — os blocos 3, 4 e 5, e o número é ruim

**A sessão começou verificando a anterior, e os quatro itens conferem.** A força bruta de D-103
foi refeita nos dois braços (504 combinações), a bateria inteira reproduziu, a injeção de falha
preserva os quatro campos, e a caça a afirmação sem comando achou **três em D-103**.

| bloco | o que fechou | decisão |
|---|---|---|
| **3** | `justificativa_negocio` era **defeito de ÍNDICE**, não falta de texto: `NEGOCIO` chaveado só por tecnologia, com `citacao.dor_origem` disponível desde D-043. Na tela: NIM sob `latencia` dizendo *"reduz o custo por token"*. **2 de 15 → 15 de 15** no mesmo run | **D-104** |
| **4** | A régua das 7 regras do TAPI existe — e **o motor faz 38% contra 44% da linha trivial** | **D-105** |
| **5** | O `PROFUNDOS` alternativo dá **`classe 4/7`** contra a barra de 5/7. **REPROVADO** — e com ele **as duas hipóteses de D-060 estão mortas** | **D-106** |

### O número do bloco 4 é o mais importante da noite, e ele é ruim

**13/34 = 38% do motor contra 15/34 = 44% de um recomendador constante.** O corte que explica:

- onde o conjunto esperado contém uma das 3 dominantes: trivial **15/15 por construção**, motor 7/15
- onde só o domínio resolve: **trivial 0/19**, motor **6/19** — ele é o único que recupera
  Isaac, Omniverse e RAPIDS

**A causa está na distribuição, não no placar:** `NVIDIA NeMo` (21) e `NVIDIA AI Enterprise` (20)
somam **46% das 89 recomendações**. Duas páginas genéricas ocupam metade de um teto de 3 por
empresa. É a P-21 com denominador: **a recuperação casa vocabulário e não domínio.**

**A PARTE 2 DO CRITÉRIO DE D-101 REPROVOU:** as 9 fazem **27%** contra **43%** das 21.
O plano se contradiz no mesmo parágrafo (*"B não sai"* vs *"apertar, não reverter"*); **D-101
resolveu por escrito na direção de apertar**. Não apertei nada — apertar é promover, e a
**decisão é do Vinícius** (D-078). O denominador de 11 é fino: a diferença é de 2 acertos.

### O que a caça a afirmação sem comando achou, e já foi pago

D-102 escreveu *"número sem comando é afirmação, não medição"*. **D-103, a entrada seguinte,
cometeu o defeito três vezes.** As três foram refeitas em 05/09 e **as três reproduzem**:

| afirmação | comando, desde 05/09 |
|---|---|
| `fora-do-funil` inalcançável | `varrer_classes.py --forca-bruta` |
| `media` 30 → 15·15 → **21·9** → 23·7 | `varrer_classes.py --prioridades` |
| falha em `elegibilidade` preserva o trabalho | `pytest -k falha_na_elegibilidade`, **com braço de controle** |

**A que mais faltava era o teste: não existia NENHUM** para `seguir_sem_elegibilidade`. Reverter
o handler de D-099/D-103 deixava a suíte **verde**.

**Ficam sem comando, declarados:** a latência 3m30 → 3m27 e a linha `?` de 110 colunas — as duas
descrevem um estado anterior que não existe mais.

### Dois defeitos meus que a execução pegou, e nenhum apareceria em leitura

1. **As 8 frases novas de D-104 estouravam os 150 do briefing** em sete das oito, e teriam
   chegado ao gerente cortadas — D-100 de volta por outra porta, três decisões depois.
2. **A minha própria força bruta cobria menos do que anunciava:** `extractor.frases` descarta
   trechos com ≤ 40 caracteres, então `n_prof` valia 0 em silêncio e o braço em degraus nunca
   alcançava o degrau 2a. O mesmo erro no teste do bloco 5, que ficou **verde sobre um
   `TypeError`** por não chamar a função que ele guarda.

### O estado ao fim

`pytest` **93 passed** (era 87) · `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6 ·
49%/100%` **idênticos** · trivial `4/7` e `32%` · as mesmas **7 recusas** · **9** com `?` ·
cobertura **10,6%** · **7→13** · grafo rodado com `RERANK_PROVEDOR=cohere` e briefing lido.

**A interface tem 05/09 inteiro + a manhã de 06/09, e é o único eliminatório em aberto no
produto.**

---

## O que ficava para 05/09 à tarde — blocos 3 a 5 do plano (FECHADOS na madrugada)

- **P-22** — `NEGOCIO` indexado por tecnologia; passa a ser por `(tecnologia, dor)`. Na tela hoje:
  NIM sob `latencia` traz *"Reduz o custo por token"*; NeMo sob `custo` traz o texto de avaliação.
- **P-21** — a régua das 7 regras do TAPI. A razão do ACEITAR (*"só 1-2 das 7 regras têm startup"*)
  está **desatualizada**: com 30 empresas são **5 de 7** por setor, e as outras 2 são por dor.
  Ela também é **a parte 2 do critério de D-101** — o ruído das 9 que entraram no funil.
- **`PROFUNDOS`** — a hipótese 2 de D-060, sob protocolo anti-contaminação: lista derivada de
  `contexto/02` §4, **commitada antes de medir**, constante separada atrás de flag.

## O que 03/09 abriu, e é para amanhã

- **O método que achou os defeitos de hoje virou script (D-094):** `varrer_elegibilidade.py`
  roda `extractor` + `elegibilidade()` nas **30 de uma vez**, zero API, e imprime uma tabela para
  LER. Ler briefing é amostragem — dá para ler três empresas, não trinta. **Ela achou dois
  defeitos na primeira execução, e um deles a própria sessão tinha criado 40 minutos antes.**
  É o corolário de D-083: *rode o sistema* → **rode-o sobre TUDO, não sobre uma amostra.**
- **P-23, nova e a mais séria (D-091):** `elegibilidade()` varre **os trechos de evidência**, não
  o documento. A Liqi diz *"oferecer criptomoedas, stablecoins e tokens"* no site, `criptomoeda`
  **já estava na lista de exclusão**, e ela passava — porque a frase não caiu em nenhum trecho
  citado pelo Extractor. **O Diferencial declarado do projeto tem a cobertura do casador de
  dores.** Consertar reintroduz o falso positivo por MENÇÃO que D-085 matou. **Está escrito; não
  se conserta a 4 dias do vídeo.**
- **P-24, e ela é a descoberta técnica do dia (D-095).** A varredura das 30 deu
  `AI-native` **1** · `AI-enabled` 20 · `non-AI` **9**. E `non-AI` sai de `pontos == 0` — de três
  detectores do Extractor voltarem vazios. A **Core AI** (5 dores de IA extraídas, "AI" no nome) e
  a **Visio.AI** (site: *"AI-Native Operating System"*) saem `non-AI` → `fora-do-funil` → **zero
  recomendações**. **É o oposto do princípio que o próprio repositório aplica em `Elegibilidade`**,
  que separa `motivos_exclusao` de `requisitos_nao_verificados`: *ausência de sinal não é sinal
  negativo*. **Não consertei, e a razão é D-062:** ajustar detectores até a Core AI sair certa é
  calibrar contra o meu julgamento sobre fixtures que eu curei hoje.
- **E a hipótese óbvia foi testada e REFUTADA:** 29 das 30 têm **zero** dos 13 marcadores de
  profundidade. Parecia falta de vagas na base (1 em 93 documentos) — mas índice de carreiras dá
  0 marcadores, e **1 de 7 vagas reais** da Zenvia tem, com 2, abaixo do limiar. **Talvez o
  classificador esteja certo sobre profundidade** — se nem a vaga de engenharia de uma empresa da
  Nasdaq fala de inferência ou quantização, a empresa consome API. Que é a tese do TAPI.
- **O seletor de D-086 segue atraído por mobília de página**, agora em dado novo: na NeMo saiu
  *"More Customer Stories / View All Blogs / View All Sessions"*. **Munição para (b) em 04/09.**
- **P-22 ganhou exemplo concreto:** `NEGOCIO` é indexado por TECNOLOGIA, não por dor — NeMo
  recomendada para `custo` traz o texto de `avaliação`. **FAZER em 05/09.**
- **O briefing ainda imprime `ver D-059`** — P-11, uma linha, 05/09.
- **Um falso positivo de `consultoria` que NÃO foi consertado (D-092), e a razão está escrita:** o
  site da Automni traz o bullet *"Consultoria especializada para implantação e operação"* — serviço
  dela mesma, na lista de entregas. É a forma do caso Axenya, mas sem marcador nenhum na frase.
  **Distinguir "vendo consultoria como parte da entrega" de "sou uma consultoria" é leitura de
  contexto, não lista de palavras.** Hoje não dispara porque não caiu em trecho de evidência — o
  que é sorte (P-23), não desenho.
- **8 empresas ficaram a 1-2 documentos do fim** e estão registradas em D-090 com o motivo: Aro,
  Creditas, alt.bank, ESGreen, YouCred, AIDA, PecSmart, iCred. Se a base voltar a crescer, é daí
  que se parte — e **buscando o documento, não chutando caminho de URL**, que foi o erro medido
  do dia (47 de 159 fetches vazios).

## Decisões do Vinícius

- ✅ **A entrega é INDIVIDUAL**, e o formato é **o repositório + o vídeo** (03/09).
- ✅ **O canal de submissão é um formulário que eles enviam** (resolvido em 08/09). **Item
  encerrado — não reabrir.**
- **04/09: escopo da interface (P-06) e se (b) entra** — as duas se decidem com o briefing real na
  frente, e ele existe agora, com 30 empresas em 10 setores.
- O repositório é **público**, então `projeto/` faz parte do entregável — mas só se o README
  apontar para o log. Item 7 do §3.3, junto com o README de 06/09.

## As duas regras que não se negociam

- **RODE O SISTEMA antes de fechar a sessão** (D-083). Em 03/09 ela pagou **cinco vezes**: a Core
  AI saindo `non-AI`; o `NEGOCIO` falando de outra dor; a **Ecotrace recusada por usar blockchain
  para rastrear boi**; a **Automni recusada pelo nome de uma parceira**; e um **falso negativo de
  rastreabilidade** numa fixture de 22/08. **Nenhum dos cinco aparece em leitura de código — e os
  dois últimos só apareceram porque eu LI um briefing inteiro, não porque rodei um grep.**
- **20 minutos de arguição, todo dia** (§4.1). Sem abrir o arquivo: *o que mudei, por quê, e qual
  alternativa descartei.* São **94 decisões**, e as quatro de hoje têm alternativa registrada.

> **A lição de método mais cara do dia está em D-091, e é sobre mim:** escrevi na régua um caso
> "rede" com uma frase **que eu mesmo redigi** já contendo o termo que queria testar. Ela deu 8/8
> enquanto a empresa real passava no grafo. **Rede tricotada em volta da resposta não é rede** —
> é o motivo de `origem` ser campo obrigatório em `exclusoes.yaml`, e eu passei por cima da regra
> do próprio arquivo.
