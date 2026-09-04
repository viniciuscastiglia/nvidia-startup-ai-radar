# Achados medidos em 04/09 — material de entrada para a sessão de plano

> **ESTE ARQUIVO É EFÊMERO.** Ele existe para alimentar UMA sessão: a que escreve o plano de
> fechamento do sistema de IA. Quando esse plano existir, este arquivo **sai** — o que sobrevive
> vai para `decisoes.md` como decisão, e para `plano.md` como item com destino. Ver a regra de
> faxina em `guia-de-trabalho.md`.

> ## ⚠️ LEIA ANTES DE USAR QUALQUER NÚMERO DAQUI
>
> **Este documento foi escrito pela mesma sessão que fez as medições.** Sessão que audita a si
> mesma não é auditoria, e este projeto tem histórico caro disso: D-097 anunciou como achado
> a morte que D-013 registrou no dia 1; D-066 justificou uma correção com um exemplo que nunca
> aconteceu ("quarta ocorrência do mesmo padrão"); e **em 04/09 esta sessão repetiu como causa
> estabelecida uma hipótese de D-059 que a própria medição refutou** (§3).
>
> **Portanto: a primeira coisa da sessão de plano é RE-RODAR o §1.** Não é ritual — é o
> único jeito de saber se este material está contaminado antes de virar especificação.
> **Se algum número não reproduzir, PARE e investigue antes de escrever uma linha de plano.**

---

## 1. VERIFICADO por execução — cada linha com o comando que a derruba

Rode tudo isto antes de usar qualquer coisa deste arquivo. Limpe o `__pycache__` antes (D-060).

### 1.1 O sistema de IA — zero API, segundos

| afirmação | comando | saída esperada |
|---|---|---|
| **9 de 30 empresas saem `non-AI`, e as 9 têm ZERO detector** | `python scripts/varrer_classes.py` | `AI-native 1 · AI-enabled 20 · non-AI 9`, as 9 com `ADT` = `---` |
| **As 9 têm dores de IA extraídas pelo mesmo Extractor** | idem | Iniciador 7 · Lexter.AI 6 · Core AI 5 · Zenvia 5 · PhoneTrack 4 · Visio.AI 4 · Conta Simples 3 · TideWise 3 · SunnyHUB 2 |
| **Consertar P-24 custa 1 ponto de `classe` NO DESENHO A e ZERO no B** | `python scripts/varrer_classes.py --custo-desenhos` | `A: 3/7 -> 2/7` · `B: 3/7 -> 3/7` |
| **`confianca`: nenhum braço passa o alvo de 4** | `python scripts/medir_confianca.py` | `A=0 · B=2 · C=2 · D=3` |
| **A régua dos agentes** | `python scripts/avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6 · precisão 49% · recall 100% · discriminação 8/8` |
| **A linha trivial GANHA do sistema em 2 campos** | `python scripts/avaliar_agentes.py --baseline` | `classe **4/7** · confianca **3/8** · precisão 32% · discriminação 1/8` |
| **O filtro do Inception: 7 recusas, todas certas** | `python scripts/varrer_elegibilidade.py` | 4 idade · 1 consultoria · 1 cripto · 1 capital aberto |
| **O seletor de justificativa bate a linha trivial** | `python scripts/avaliar_agentes.py --justificativas` | trivial `12/21` · seletor `15/21` |

### 1.2 A cadeia da recência — a causa que não estava registrada

| afirmação | comando | saída esperada |
|---|---|---|
| **`avaliar()` exige recência para conceder `alta`** | `sed -n 96,112p src/agents/evidence_validator.py` | `if len(tipos) >= 2 and n_recentes >= 1: return "alta"` |
| **Sem data conta como NÃO recente** | `sed -n 88,92p src/agents/evidence_validator.py` | `_recente(None) -> False` |
| **86 dos 93 documentos têm `data_publicacao: null`** | `grep -h "data_publicacao:" data/seed/*.yaml \| sed 's/.*data_publicacao: *//' \| sort \| uniq -c` | `86 null`, 7 com data |
| **`coletar.py` não captura data nenhuma** | `grep -n "data\|date\|publish" scripts/coletar.py` | **vazio** |

### 1.3 Defeitos visíveis na tela do gerente

| afirmação | comando | o que aparece |
|---|---|---|
| **Recommendation roda ANTES de Elegibilidade** | `grep -n "add_edge" src/graph.py` | `g.add_edge("recommendation", "elegibilidade")` — o motor não tem como saber que a empresa foi recusada |
| **A Liqi sai `NÃO ELEGÍVEL` e recebe 3 recomendações com "agendar conversa"** | `python -m src.graph "startups de fintech AI-native"` | bloco `x exclusão por 'cripto'` seguido de `ação: Agendar conversa técnica ... com o time de engenharia da Liqi` |
| **Dois campos dos 7 obrigatórios são cortados no meio da palavra** | `sed -n 333,338p src/agents/briefing.py` | `[:150]` sem reticências → `"...NVIDIA NIM™ microse"`, `"...citada da documentaçã"` |
| **`ver D-059` é impresso ao usuário final** | `grep -n "D-059" src/agents/evidence_validator.py src/agents/briefing.py` | o ponteiro entrou em 27/08 (`git log -S "ver D-059"` → `6fae6c5`) |
| **`NEGOCIO` é indexado por TECNOLOGIA, não por dor** | `sed -n 55,70p src/agents/recommendation.py` | texto curado em 5 de 16; e nos 5, ele contradiz a dor ao lado: `dores: latencia` → *"reduz o custo por token"*; `dores: escalabilidade` → *"latência menor melhora a experiência"* |
| **P-21, três casos independentes** | os briefings de hoje | Morpheus (spear phishing) pela dor de **custo** na Liqi · Healthcare (genoma) para a **agtech** Produzindo Certo · Morpheus para **privacidade** de healthtech (D-086) |

### 1.4 O clone limpo — o eliminatório "projeto que não executa" está FECHADO

Percurso completo do avaliador, feito em 04/09: repo público → venv nova → banco novo.

| passo | resultado |
|---|---|
| `pip install -r requirements.txt` | 60 pacotes, zero erro |
| `scripts/init_db.sql` em banco vazio | 3 tabelas, exit 0 |
| `scripts/seed.py` | 30 startups · 93 documentos |
| `scripts/ingerir_nvidia.py` (baixa as 16 URLs ao vivo) | **377 chunks (175 + 202) — idêntico ao medido** |
| `scripts/avaliar_rag.py --validar` | **24/24 válidas** |
| `python -m src.graph "startups de fintech AI-native"` | exit 0, 5 empresas |
| `pytest -q` | **81 passed em 2m32** (com `RERANK_PROVEDOR=cohere`, o default do `.env.example`) |
| `scripts/smoke_nvidia.py` | 3/3 |

### 1.5 P-21 deixou de ser inmedível

As 7 regras de exemplo do TAPI (`contexto/01-tapi.md:143`) são pares setor/dor → tecnologia, e
**são da especificação, não nossas** — o que desarma a objeção de D-062. Com a base em 30:

| regra | empresas na base | comando |
|---|---|---|
| Voz / call center → Riva, NIM | **3** | `grep -h "^setor:" data/seed/*.yaml \| sort \| uniq -c` |
| Saúde → Clara, NIM, NeMo Guardrails | **3** | idem |
| Robótica / simulação → Isaac, Omniverse | **4** | idem |
| Dados tabulares → RAPIDS, cuDF, cuML | 1 explícita | idem |
| LLM em atendimento → NIM, Guardrails, Triton | ~3 | idem |

**5 das 7 têm caso real**, contra "1-2" que `plano.md` §3.2 registra. Aquela justificativa de
ACEITAR está desatualizada pela base nova.

---

## 2. NÃO VERIFICADO — e isto é parte do material, não uma nota de rodapé

Nada abaixo foi medido. Não use como premissa; meça, ou trate como pergunta em aberto.

- **Todas as estimativas de tempo** ("~1h", "~2h") que esta sessão produziu são chute. Nenhuma
  saiu de cronometragem.
- **Se o desenho B introduz ruído**: ele faz as 9 entrarem no funil, incluindo a **SunnyHUB**,
  que é energia solar e é `non-AI` de verdade. Recomendar NVIDIA para ela é ruído — e **isso
  não foi medido**. A régua de `classe` não vê, por construção.
- **O que as 4 empresas de robótica recebem hoje.** Foi afirmado que "deveriam receber
  Isaac/Omniverse" por leitura das regras do TAPI. **Ninguém rodou o grafo nelas.**
- **Se promover o braço D quebra algo a jusante.** `confianca` alimenta `_prioridade()` em
  `recommendation.py:178`. O efeito de a confiança deixar de ser constante **não foi medido**.
- **P-23** (`elegibilidade()` só lê os trechos citados) é de D-091 e **não foi re-verificado
  hoje**.
- **O caminho Docker** do `docker-compose.yml`: o daemon estava parado, então **não foi
  testado**. A `DATABASE_URL` do `.env.example` aponta `5432` e o compose expõe `5433` — isso
  é leitura de arquivo, não execução.
- **`classe 3/7`, o teto de 4/7 (D-060) e o placar do juiz (D-072)** foram medidos no
  `nemotron-3-nano-30b-a3b`, **morto em 01/09**. Só `--geracao` foi refeito no modelo vivo.

---

## 3. O que estas medições REFUTAM

Duas afirmações caíram hoje. Ambas estavam sendo tratadas como fato.

**3.1 — A hipótese que D-059 deixou escrita, e que ficou 8 dias sem teste.**
D-059 concluiu: *"Melhorar isso é fazer o Classifier anexar evidência mais larga, e isso é
trabalho do Extractor."* O braço **C** de `medir_confianca.py` mede exatamente isso — anexa
TODAS as afirmações de cada detector em vez de só a `[0]` — e dá **2, idêntico ao braço B**.
**Anexar evidência mais larga não move o campo.** O que move é a recência (braço D, +1), que
depende de `coletar.py` capturar data.

**3.2 — A afirmação desta sessão de que consertar P-24 custa 1 ponto de régua.**
Foi feita por inferência e apresentada como propriedade do problema. `--custo-desenhos` mostra
que **vale para o desenho A e não para o B**. O trade-off é de um desenho, não do defeito.

---

## 4. Decisões que são do Vinícius, e travam o plano

Nenhuma destas é técnica; todas são de produto. O plano não fecha sem elas.

1. **Empresa NÃO ELEGÍVEL ao Inception deve receber recomendação de tecnologia?**
   Pró: a NVIDIA vende fora do programa. Contra: o sistema existe para captar PARA o programa.
   Muda o conserto do §1.3 (ordem no grafo).

2. **`confianca`: promover o braço D, só trocar o rótulo pelo motivo, ou os dois + `coletar.py`?**
   Nenhum passa o alvo de 4. D discrimina e empata em acertos — a decisão é de produto.

3. **P-24: desenho A (rótulo honesto, −1 na régua) ou B (rótulo intocado, custo não medido)?**
   Ver §2: o custo de B não foi medido.

4. **P-21 entra agora que 5 das 7 regras do TAPI têm caso real?**

---

## 5. Como iniciar a sessão de plano

Sessão **nova**, para que o plano não seja escrito por quem fez a análise. Cole isto:

```
Leia projeto/achados-04-09.md.

Ele foi escrito pela mesma sessão que fez as medições, então trate tudo como SUSPEITO até
reproduzir. Antes de escrever qualquer plano:

1. Limpe o __pycache__ e re-rode TODOS os comandos da §1. Compare com a saída esperada.
2. Diga o que reproduziu e o que não reproduziu. Se algo divergir, PARE e investigue —
   material contaminado não vira especificação.
3. Leia a §2 (o não verificado) e a §3 (o que foi refutado). A §3 contém uma hipótese do
   próprio decisoes.md que caiu por medição: não assuma que o log está certo.

Só então escreva o plano de fechamento do sistema de IA, em docs/superpowers/plans/.
O objetivo é fechar a parte de IA para liberar interface e vídeo.

Regras deste projeto (CLAUDE.md):
- fixe o critério ANTES de medir; medir não é promover
- toda decisão vai para projeto/decisoes.md com a alternativa descartada
- não use subagentes
- RODE O SISTEMA antes de fechar a sessão
- não julgue recomendação com RERANK_PROVEDOR=nenhum (D-097)

As decisões da §4 são do Vinícius — pergunte, não assuma.
```

**Antes de rodar qualquer coisa:** `python scripts/smoke_nvidia.py`. São 4 segundos, e o passo 7
tem fornecedor único desde maio (D-097). Para desenvolver, `RERANK_PROVEDOR=nenhum`; para julgar
o que o gerente veria, o Cohere ligado.
