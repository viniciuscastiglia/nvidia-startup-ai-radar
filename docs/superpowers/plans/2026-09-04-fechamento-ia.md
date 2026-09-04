# Plano — fechamento do sistema de IA, 04/09 e a tarde de 05/09

> **Passo 0 na execução:** salvar este arquivo em `docs/superpowers/plans/2026-09-04-fechamento-ia.md`
> (o modo plano só permite escrever no arquivo de plano; o destino pedido é aquele).
> **Ao fim:** `projeto/achados-04-09.md` sai — ele se declara efêmero e existe para alimentar
> exatamente esta sessão. O que sobrevive vira D-098…D-105 e itens com destino em `plano.md`.
> **RENUMERAÇÃO, feita em 04/09:** `varrer_classes.py` e `medir_confianca.py` já citavam `(D-098)`
> no docstring desde a manhã, para uma decisão que nunca foi escrita. O número foi honrado —
> D-098 é a dos dois instrumentos — e as deste plano andaram uma casa.

---

## Contexto

`projeto/achados-04-09.md` foi escrito pela mesma sessão que fez as medições, e essa sessão errou
três vezes em 04/09. Esta sessão reproduziu a §1 antes de escrever qualquer linha: **tudo reproduz,
com duas divergências investigadas e resolvidas** (registradas abaixo). O run real do grafo, com
`RERANK_PROVEDOR=cohere` como D-097 exige, mostrou os defeitos (a), (e), (f) e (g) na tela — e
**mais quatro que o documento não registra**.

O que ordena este plano não é placar. É o que a §1.1 identifica corretamente: **o repositório
desobedece um princípio que ele mesmo escreveu no dia 2** — *ausência de sinal não é sinal
negativo* (D-010, `evidence_validator.py:12`). O Classifier emite `non-AI` — uma afirmação positiva
sobre a empresa — quando os detectores voltam vazios. Nove empresas de trinta saem do funil por
silêncio da extração, e o briefing informa ao gerente uma causa falsa para isso.

As cinco decisões da §4 foram tomadas pelo Vinícius e estão registradas na §1 abaixo.

---

## 0. O fluxo — duas sessões, três pontos de parada

**O que decide isto não é quanto tempo o Claude aguenta.** São dois critérios do próprio projeto:
*"código integralmente gerado sem compreensão"* é **eliminatório** (`plano.md` §2), e **medir não é
promover** (D-078) — promover é ato do Vinícius. E um de método: o **bloco 4 é a régua que julga a
saída do bloco 2**; construir os dois na mesma sessão é *sessão que se audita*, o erro que a §5 do
`achados-04-09.md` evitou ao exigir sessão nova para este plano.

| quando | quem | o quê |
|---|---|---|
| **04/09, agora** — sessão 1, ~2-3 h | Claude | blocos **1 e 2**. **Para antes de commitar**: o briefing vai para a tela com o checklist da §6 |
| ↳ ponto de parada 1 | **Vinícius** | lê as seis linhas do checklist e diz se passou |
| ↳ | Claude | escreve **D-098 a D-101**, commita, fecha a sessão ✅ **FEITO** |
| **04/09, tarde** | **Vinícius** | ✅ arguição feita · `/code-review` disparado, achados em mãos para a noite |
| **04/09, NOITE** — sessão 2, nova, ~4 h | Claude | portão de revisão (30 min) → blocos **3, 4 e 5** |
| ↳ ponto de parada 2 | **Vinícius** | o número da P-21 decide a **parte 2** do critério do bloco 2 |
| ↳ ponto de parada 3 | **Vinícius** | o número do `PROFUNDOS` — promover ou só registrar |
| ↳ | Claude | **D-103, D-104, D-105**, commit |

**Sessão nova se abre quando há commit e portão limpo — nunca no meio de um bloco.**

> **O FLUXO MUDOU EM 04/09 À TARDE, e a mudança é do Vinícius.** O plano original punha a
> interface na tarde de 04/09 e os blocos 3-5 na tarde de 05/09. **Passou a ser: blocos 3-5 na
> NOITE de 04/09, interface em 05/09 inteiro + a manhã de 06/09.** A razão é boa e vale escrita:
> o sistema de IA fecha com o material fresco, e o portão do eliminatório — a interface — ganha
> **dois dias limpos** em vez de um e meio disputado. A exigência de *sessão nova* continua
> valendo e continua atendida: o bloco 4 é a régua que julga a saída do bloco 2, e quem a
> constrói não pode ser quem decidiu o bloco 2.

**A REGRA DE CORTE MUDOU DE OBJETO JUNTO.** Antes ela protegia a interface contra os blocos 3-5.
Agora quem compete com os blocos 3-5 é **o relógio e o cansaço**, não a interface. A nova regra:

- **Corta-se 5, depois 4, depois 3** — inalterado, e o que cair vira ACEITAR escrito.
- **A sessão MEDE e REGISTRA; a promoção é ato do Vinícius** — e a razão não é a hora, é D-078:
  *medir não é promover* são dois atos, e o segundo é dele em qualquer horário. Vale para os dois
  números que os blocos 4 e 5 produzem: a parte 2 do critério de D-101, e promover-ou-não o
  `PROFUNDOS` alternativo. **O bloco 3 a sessão fecha sozinha** — é correção com teste, e não tem
  número para promover.

**O HARNESS DO BLOCO 4 RODA O GRAFO UMA VEZ E MEDE DA SAÍDA**, não uma vez por iteração — e a
razão é velocidade de iteração, não cota: um run sobre a base leva **~20 minutos** (medido em
04/09: 28 empresas, rerank ligado). Um harness que re-roda a cada ajuste é inutilizável como
instrumento. O briefing das 28 de 04/09 serve de entrada se ainda existir.

---

## 1. As cinco decisões, e a razão de cada uma

| § | decisão | escolhida |
|---|---|---|
| 4.5 | orçamento | **hoje (04/09) + a tarde de 05/09** — ~12 h. A interface tem prioridade sobre tudo aqui |
| 4.1 | empresa NÃO ELEGÍVEL recebe recomendação? | **(B) mantém e rotula** |
| 4.2 | `pontos == 0` | **(B) o rótulo fica, muda a consequência** |
| 4.3 | hipótese 2 de D-060 (`PROFUNDOS`) | **entra**, com protocolo anti-contaminação |
| 4.4 | P-21 (régua das 7 regras do TAPI) | **entra**, como instrumento — não promove nada |
| — | `justificativa_negocio` por dor (P-22) | **entra** |

**As duas decisões (B) são a mesma decisão**, e isso é o que torna a defesa curta: são D-010
aplicada a dois componentes que ainda não a obedeciam. O Validator *anota e rebaixa, nunca deleta*;
`Elegibilidade` já separa `x` (provado) de `?` (não provado). O Classifier deleta a empresa do
funil quando não acha sinal, e o Recommendation deleta a recomendação quando a empresa é recusada.
**Nos dois casos a correção é a mesma: anotar, rebaixar, e deixar o humano decidir.**

**O fato que decidiu a §4.1:** a **JetBov** é a única `AI-native` das 30 e o único `sweet-spot` da
base — e é NÃO ELEGÍVEL por idade (2015, 11 anos). Sob "recusada não recebe nada", o melhor
prospect que o sistema encontrou sai da tela em branco. E **4 das 7 recusas são por idade**, que
diz respeito ao programa, não à empresa.

**O fato que decidiu a §4.2:** `varrer_classes.py --custo-desenhos` mede que o desenho B custa
`3/7 → 3/7` — zero. E B **não introduz nenhum grau de liberdade**: é a mesma regra `pontos == 0`,
com outro destino. A razão do ACEITAR da P-24 em `plano.md` §3.2 — *"consertar exige gabarito;
calibrar detectores é calibrar contra o próprio julgamento"* — vale para o desenho A e para mexer
nos detectores. **Não vale para B, e ela foi escrita antes da medição que separa os dois.**

---

## 2. O que esta sessão reproduziu, e as duas divergências

Roda antes de qualquer edição, com `__pycache__` limpo. **Tudo reproduz**:
`varrer_classes` (`1 · 20 · 9`, as 9 com `---`) · `--custo-desenhos` (A `3/7→2/7`, B `3/7→3/7`) ·
`medir_confianca` (A=0 · B=2 · **C=2** · D=3 · trivial=3) · `varrer_elegibilidade` (7/30) ·
`avaliar_agentes` (`3/7 · 6/7 · 0/6 · 6/6 · 49%/100%`) · `--baseline` (`4/7 · 6/7 · 3/8 · 32%`) ·
`PROFUNDOS` (7 de 8 com zero; só Maritaca com 3) · datas (**86/93 ausentes**).

**Divergência 1 — 1.2(c), os 10,6%.** Medição direta dá 11,0% (49.637 chars). Somando **trechos
únicos** dá 47.818 = **10,6%** exato. O documento está certo; trecho repetido não amplia cobertura.

**Divergência 2 — 1.2(c), "de 7 para 11 recusas". Não reproduz: dá 13.** As seis novas conferem
(BemAgro, Ecotrace, Iniciador, Produzindo Certo, TideWise, iRancho), mas 7 + 6 = 13.
Investigando, achei o argumento **melhor** contra o conserto óbvio, e ele não é contagem de corpo:

> Varrer o documento inteiro **quebra `_fala_de_terceiro` por construção**. O veto exige que
> **toda** ocorrência do termo caia em frase com marcador. Medido na Iniciador: no trecho de
> evidência há 1 ocorrência de `stablecoin`, coberta por `mercado de stablecoin`; no documento
> inteiro há 2, e a segunda (*"pagamentos agênticos com cripto e stablecoins"*) não tem marcador
> nenhum → o `all()` colapsa. **Cada caractere a mais é outra chance de o veto falhar.**

---

## 3. Quatro achados novos, vistos na tela

1. **O briefing informa uma causa falsa.** `briefing.py:326` imprime *"nenhuma — sem evidência
   validada que sustente uma recomendação"* sempre que a lista está vazia. Conta Simples, Core AI e
   Iniciador têm 3, 5 e 7 dores **validadas** (a régua confirma que o filtro `if d.validada` não
   barra nada — D-074). A causa real é `recommendation.py:131`.
2. **A linha `Base` contradiz o rótulo na mesma tela:** as três dizem `posicionamento de copilot:
   vende a ferramenta` — constatação sobre o modelo de entrega — logo abaixo de
   `Classificação: non-AI`, que a rubrica define como *"sem IA no caminho crítico"*.
3. **1.2(e) aparece três vezes num só briefing**, não duas: NIM `latencia` → *"custo por token"*;
   TensorRT-LLM `escalabilidade` → *"Latência menor…"*; **NeMo `custo` → *"Sem processo de
   avaliação…"***. E `justificativa_tecnica` carrega quebra de linha crua, que quebra o alinhamento.
4. **O conserto amplo de 1.2(c) revela um falso NEGATIVO de hoje:** Produzindo Certo —
   *"oferece serviços de **consultoria**, gestão e verificação"*, a própria empresa. Hoje passa
   porque a frase não caiu em trecho de evidência. **P-23 tem os dois lados.**

**Deriva de documentação** (correção de uma linha cada): `plano.md` §1 diz `ano_fundacao` em 12 de
30 e `localizacao` em 5 — são **18** e **9** · `sessao-atual.md:77` diz `> 10 anos → Agrotools e
Solinftec` e a linha 46 do mesmo arquivo diz que a Solinftec sai ELEGÍVEL · `CLAUDE.md` diz
*"> 10 anos (Agrotools, e só ela)"* — hoje são **4** · `plano.md` §4.2 agenda P-13 e P-20 para a
tarde de 05/09 e ambas estão ✅ em §3.1, o que **libera exatamente o slot** que este plano ocupa.

---

## 4. Blocos, em ordem de execução

**Regra de corte, fixada agora:** os blocos 1 e 2 mudam o que o gerente vê e **não são cortáveis**.
Os blocos 3, 4 e 5 são instrumentos e profundidade. Se a interface escorregar em 05/09, corta-se
**5, depois 4, depois 3** — e o que for cortado vira ACEITAR escrito, não silêncio.

### Bloco 1 — os quatro defeitos de tela · 04/09, ~2 h · não cortável

Nenhum é medição; são correções com teste. Nenhum move régua.

| # | onde | o quê |
|---|---|---|
| 1a | `src/graph.py:102-108` | mover `elegibilidade` para **depois de `evidence_validator` e antes de `nvidia_rag`**. `briefing.node_analise` só lê `state["startup"]` e `state["perfil"]` — não depende de `nvidia_rag` nem de `recommendation`. Está no fim por acidente de construção |
| 1b | `src/agents/recommendation.py` | passa a ler `state["elegibilidade"]`. Empresa recusada **mantém** as recomendações, com `prioridade` forçada a `baixa` e `proxima_acao` prefixada com o motivo. Novo campo `fora_do_inception: str \| None` em `Recomendacao` |
| 1c | `src/agents/briefing.py:~318` | seção de empresa recusada ganha o cabeçalho `fora do Inception — abordagem comercial direta: <motivo>` antes das recomendações |
| 1d | `evidence_validator.py:210-215` | `ver D-059 para por que…` **sai do texto do usuário**. O motivo continua existindo e continua sendo impresso — sem o ponteiro interno. A informação de D-059 vai para o docstring do módulo, que é onde ela sempre pertenceu |
| 1e | `briefing.py:335-336` | `_resumir(texto, 150)` — corta em fronteira de palavra, colapsa `\s+` e acrescenta `…`. Aplicar aos dois campos e aos dois `[:130]` de evidência |
| 1f | `recommendation.py` + `state.py` | `AnaliseStartup.motivo_sem_recomendacao: str \| None` e o campo correspondente em `EstadoAnalise`. `recommendation.node` devolve a causa real; `briefing.py:326` imprime ela em vez da frase fixa |

**Testes:** um novo em `tests/test_grafo.py` para 1a/1b (*empresa recusada recebe recomendação
rotulada, e o rótulo cita o motivo da recusa*) e um em `tests/test_elegibilidade.py` para 1f
(*briefing não afirma "sem evidência validada" quando existe dor validada*). 1e pega um teste de
unidade sobre `_resumir` — nunca corta no meio de palavra, nunca devolve `\n`.

### Bloco 2 — o desenho B do Classifier · 04/09, ~2,5 h · não cortável

**O critério de aceitação, FIXADO AGORA, antes de qualquer medição:**

- **Parte 1 — não regressão. Decide sozinha, e qualquer piora reprova B:**
  `classe 3/7` · `maturidade_stack 6/7` · `confianca 0/6` · `elegivel 6/6` · precisão ≥ 49% ·
  recall 100% · `varrer_elegibilidade` com **as mesmas 7 recusas** · `pytest -q` verde.
- **Parte 2 — o ruído, medido pela régua do bloco 4:** a taxa de acerto das 9 sob as 7 regras do
  TAPI não pode ser pior que a das 21 que já estavam no funil. **Se for pior, B não sai** — B já
  carrega o rebaixamento (`prioridade baixa` + `?`), e a resposta é apertar isso, não voltar ao
  estado que viola o princípio. Está declarado assim para que o resultado não decida depois.

**O que muda:**

| onde | o quê |
|---|---|
| `src/state.py:262` | `Diagnostico.sinal_verificado: bool = True` — o par que `Elegibilidade` já tem, aplicado ao rótulo |
| `src/state.py:239` | `derivar_quadrante(classe, maturidade, sinal_verificado=True)`. `non-AI` **verificado** continua `fora-do-funil` — `tests/test_grafo.py:111-113` segue verde sem edição, e isso é o sinal de que a mudança é aditiva. `non-AI` **não verificado** vai para `prospect-de-evolucao` |
| `src/agents/classifier.py:203-204` | `pontos == 0` continua emitindo `non-AI` (o TAPI nomeia três classes), e passa a marcar `sinal_verificado=False`. Zero parâmetro novo |
| `src/agents/briefing.py:_secao` | quando `sinal_verificado` é falso, imprime `? sinal de IA não verificado — nenhum dos 3 detectores disparou; N dor(es) de IA extraída(s) com evidência`. É o mesmo idioma do `?` da elegibilidade |
| `src/agents/recommendation.py:178` | empresa com sinal não verificado recebe `prioridade` forçada a `baixa`. O sistema não deixa de recomendar; deixa de afirmar urgência sem evidência |

**Alternativa descartada e por quê (vai para D-101):** o desenho A — `indeterminado` como quarta
classe — é semanticamente mais limpo e custa duas coisas, não uma. A medida: `classe 3/7 → 2/7`,
porque a SunnyHUB também tem zero detector e passaria a divergir de um gabarito que diz `non-AI`.
A não medida, e maior: **o TAPI nomeia três classes**; uma quarta no output é desvio de
especificação — defensável, mas é uma defesa a mais que não compra nada além do que B compra.

**O preço declarado de B:** as 9 entram no funil, incluindo a SunnyHUB, que é energia solar e
`non-AI` de verdade. É o mesmo preço que o repositório já paga e reporta em `Elegibilidade` — a
Solinftec sai ELEGÍVEL com *"requisito não verificado"* porque o documento diz "há 18 anos" e não
um ano. **Troca um falso negativo silencioso por um falso positivo anotado**, que é a direção que
D-052 e D-057 já escolheram por escrito.

### Bloco 3 — `justificativa_negocio` por dor (P-22) · 05/09 tarde, ~2 h

O defeito é de índice, não de texto: `recommendation.py:63` indexa `NEGOCIO` por **tecnologia**, e
a dor vem de `citacao.dor_origem`. Os textos curados **sempre foram por (tecnologia, dor)** — o do
NeMo fala de avaliação e sai sob `custo`; o do NIM fala de custo e sai sob `latencia`. O código
perdeu o índice da dor.

- `NEGOCIO: dict[tuple[str, Dor], str]` — os 5 textos atuais reatribuídos ao seu par real
  (NIM → `custo`, `dependencia_fornecedor` · TensorRT-LLM → `latencia`, `escalabilidade` ·
  Triton → `custo`, `escalabilidade` · NeMo Guardrails → `governanca`, `privacidade` ·
  NVIDIA NeMo → `avaliacao`).
- `NEGOCIO_POR_DOR: dict[Dor, str]` — **8 textos**, um por dor, nomeando a tecnologia recebida.
  Cobre o espaço 16 × 8 com 8 frases curadas em vez de uma fórmula, e mata o fallback formulaico
  que hoje atende 11 das 16 tecnologias.
- **A fonte é `contexto/03` §4** — a tabela *dor observável → tecnologia*, escrita em 22/08 a
  partir das fontes do próprio TAPI, **antes de qualquer medição deste projeto**. Não é calibração.
- **Teste novo:** `test_justificativa_negocio_fala_da_dor_declarada` — irmão do
  `test_justificativa_negocio_fala_da_tecnologia_recomendada` que D-063 já criou pelo mesmo motivo.
- Não é medição: é correção com teste. Nenhuma régua se move.

### Bloco 4 — a régua das 7 regras do TAPI (P-21) · 05/09 tarde, ~3 h

`plano.md` §3.2 ACEITA P-21 com a razão *"só 1-2 das 7 regras têm startup na base"*. **Com 30
empresas são 5 de 7 por setor** (voz 3 · saúde 3 · robótica 4 · tabulares 1 · atendimento ~3), e as
outras 2 (`latência de inferência`, `governança em agentes`) são chaveadas por **dor**, que o
sistema também tem. **A justificativa não vale mais como está.**

- `data/avaliacao/regras-tapi.yaml` — as 7 regras de `contexto/01-tapi.md:143`, cada uma com
  `chave` (`setor` ou `dor`), `tecnologias_esperadas` e `origem` (a linha do TAPI). `origem` é
  obrigatória, pela mesma razão que em `exclusoes.yaml`.
- `scripts/avaliar_agentes.py --regras-tapi` — para cada empresa coberta por uma regra, o conjunto
  recomendado intersecta o esperado?
- **A linha trivial é obrigatória (D-051):** o recomendador constante — as 3 tecnologias mais
  recomendadas na base inteira, para todo mundo. Sem ela, um acerto de 60% não significa nada.
- **Não promove nada.** É instrumento: o passo 9 do TAPI (*avaliação de qualidade*) e o material do
  critério 2. **Medir não é promover** (D-078). O que ele decide hoje é só a parte 2 do bloco 2.

### Bloco 5 — hipótese 2 de D-060, com protocolo anti-contaminação · 05/09 tarde, ~1,5 h

A tentativa de 04/09 escreveu a lista alternativa **conhecendo o gabarito** e é imprestável. O
protocolo, **nesta ordem, sem exceção**:

1. Derivar a lista **só** de `contexto/02` §4 (*"self-hosting, quantização, avaliação, guardrails,
   MLOps real"*) e da coluna de justificativa técnica de `contexto/03` §4 — **ambos escritos em
   22/08, antes de qualquer medição**.
2. Gravar em `data/avaliacao/profundos-candidato.yaml`, com `origem` por termo (documento e linha),
   **e commitar antes de rodar qualquer coisa**. O commit é o carimbo de data.
3. Só então medir.
4. **Constante separada atrás de flag**, nunca editar `PROFUNDOS`: `MARCADORES_PARA_PROFUNDIDADE`
   é compartilhado pelos dois eixos, e mexer na lista de produção moveria a `maturidade_stack`, que
   é a guarda de D-060 (6/7).
5. **Critério fixado agora:** promove só se `classe ≥ 5/7` (a barra de D-058) **sem** derrubar
   `maturidade_stack` abaixo de 6/7. Abaixo disso: **mede, registra e não promove.**

---

## 5. As decisões a registrar em `projeto/decisoes.md`

Uma por bloco, na hora em que for tomada, com a alternativa descartada. **As CINCO de 04/09 estão
escritas** (D-098 a D-102 — D-102 salvou como script as medições que a sessão fez em
heredoc e não guardou); as três de 05/09 são **D-103 a D-105**.

| # | assunto | alternativa descartada |
|---|---|---|
| ~~D-099~~ ✅ | `elegibilidade` antes de `nvidia_rag`; recusada mantém recomendação rotulada | suprimir as recomendações — silenciaria a JetBov, única `AI-native` e único `sweet-spot` da base, e 3 outras recusadas por idade. Também: a variante por motivo de recusa (idade × regra do programa), mais correta e uma regra a mais para defender |
| ~~D-101~~ ✅ | desenho B: `non-AI` não verificado deixa de cortar o funil | desenho A (`indeterminado` como 4ª classe): custa 1 ponto de `classe` **e** desvia das três classes que o TAPI nomeia |
| ~~D-098~~ ✅ | os dois instrumentos de varredura ganham a decisão que já citavam | pô-los como flags de `avaliar_agentes.py`: menos arquivo, e a tabela das 30 passaria a ser lida como placar sobre um gabarito de 8 (D-062) |
| ~~D-100~~ ✅ | os três defeitos do texto que chega ao gerente (causa falsa · ponteiro `D-059` · truncagem) | o briefing INFERIR a causa a partir do quadrante: reconstruiria no consumidor uma decisão que o produtor já tomou |
| **D-103** | `NEGOCIO` reindexado por `(tecnologia, dor)` + 8 textos por dor | curar as 11 tecnologias restantes por tecnologia — 16 × 8 células, e mantém o defeito de índice |
| **D-104** | a régua das 7 regras do TAPI, com linha trivial | seguir com o ACEITAR da P-21 — a razão escrita (*"1-2 das 7 regras têm startup"*) está desatualizada: são 5 de 7 |
| **D-105** | `PROFUNDOS` alternativo, medido sob protocolo | usar a lista de 22 termos de 04/09 — escrita conhecendo o gabarito, é o erro que D-091 já custou uma sessão |

**Correções de documentação, no mesmo commit dos blocos:** a razão do ACEITAR da P-24 em
`plano.md` §3.2 (hoje diz *"consertar exige gabarito"*, o que só vale para o desenho A) · a razão
do ACEITAR da P-21 · os quatro itens de deriva da §3 acima · `projeto/achados-04-09.md` **sai**.

---

## 6. Verificação — o portão de fim de sessão

Nesta ordem, e **com `__pycache__` limpo antes** (D-060):

```bash
rm -rf **/__pycache__
python scripts/smoke_nvidia.py                      # 3/3 — LENTO não é EOL (D-080)
pytest -q                                           # 81 passed + os novos
python scripts/avaliar_agentes.py                   # parte 1 do critério do bloco 2
python scripts/avaliar_agentes.py --baseline        # a linha trivial, obrigatória (D-051)
python scripts/varrer_elegibilidade.py              # as mesmas 7 recusas
python scripts/varrer_classes.py                    # as 9 agora com `?`, não fora do funil
python scripts/avaliar_agentes.py --regras-tapi     # bloco 4, com trivial
python -m src.graph "startups de fintech AI-native" # RERANK_PROVEDOR=cohere (D-097)
```

**O portão não é o `pytest` — é a leitura do briefing inteiro.** D-083 e D-094: duas sessões de
auditoria estática não acharam nenhum dos três defeitos que uma execução achou em uma hora, e ler
um briefing inteiro achou dois que nenhum `grep` achou. O que tem de estar na tela ao fim:

- [ ] a Liqi sai `NÃO ELEGÍVEL` **e** as recomendações dela vêm sob `fora do Inception —
      abordagem comercial direta: exclusão por 'cripto'`, com prioridade `baixa`
- [ ] nenhuma ocorrência de `ver D-059` em nenhuma linha do briefing
- [ ] nenhum campo cortado no meio da palavra, nenhuma quebra de linha crua
- [ ] Conta Simples, Core AI e Iniciador saem com `? sinal de IA não verificado — … N dor(es)`,
      **dentro** do funil, e nenhuma delas exibe *"sem evidência validada"*
- [ ] toda `justificativa_negocio` fala da dor que a própria linha `dores:` declara
- [ ] uma consulta que traga as 9 — ler as **nove** seções, não uma amostra (D-094)

**E rodar sobre as 30, não sobre 5:** `MAX_STARTUPS` alto numa passada, para que a leitura seja da
base inteira. É o corolário de D-083 que D-094 escreveu: *rode-o sobre TUDO*.

---

## 7. O que este plano NÃO faz, e por quê

- **Não mexe nos detectores do Extractor.** É o que a razão do ACEITAR da P-24 protege
  corretamente: ajustar detectores até a Core AI "sair certa" é calibrar contra o próprio
  julgamento sobre fixtures curadas pela mesma pessoa (D-062).
- **Não conserta a P-23** (`elegibilidade()` lê 10,6% do texto). A investigação desta sessão a
  reforça: o conserto óbvio dá 13 recusas, e **quebra `_fala_de_terceiro` por construção**. Segue
  ACEITO — mas o texto do ACEITAR ganha o argumento do quantificador e o falso negativo da
  Produzindo Certo, que são mais fortes que o que está escrito hoje.
- **Não coleta `data_publicacao`** (1.2(h), 86/93 ausentes, metade da regra 2/3 desligada). Exige
  re-coleta dos 93 documentos e re-medição da régua — é P-25, depois da entrega. Fica escrito que
  `alta` é inalcançável hoje **por falta de dado, não por regra**, o que a defesa precisa dizer.
- **Não promove o braço D de `medir_confianca`** (o que faz 3, empata com o trivial e discrimina).
  Ele depende de `data_publicacao`, acima. **Medir não é promover** (D-078).
- **Não toca na interface.** Ela é a porta do eliminatório do vídeo e tem prioridade sobre tudo
  aqui; a regra de corte da §4 existe para isso.
