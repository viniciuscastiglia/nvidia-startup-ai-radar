# Achados de 04/09 — material de entrada para a sessão de plano

> **EFÊMERO.** Existe para alimentar UMA sessão: a que escreve o plano de fechamento do sistema
> de IA. Quando esse plano existir, este arquivo **sai**. O que sobreviver vira decisão em
> `decisoes.md` e item com destino em `plano.md`.

## ⚠️ Procedência deste documento — leia antes de usar qualquer linha

**Foi escrito pela mesma sessão que fez as medições.** Sessão que audita a si mesma não é
auditoria. Este projeto tem histórico caro disso: D-097 anunciou como achado a morte que D-013
registrou no dia 1; D-066 justificou uma correção com um exemplo que nunca aconteceu ("quarta
ocorrência do mesmo padrão").

**E aconteceu de novo em 04/09, três vezes, dentro da própria sessão que escreve isto.** As três
estão na §2, com o que as derrubou. Duas eram afirmações desta sessão; uma estava no `decisoes.md`
há oito dias.

**Portanto:** a primeira coisa da sessão de plano é **reproduzir a §1**. Se algo divergir, PARE.

## §0 — O que este documento NÃO é

- **Não é plano.** Não há ordem de execução, nem prioridade, nem estimativa de esforço. Ordenar é
  juízo, e o juízo é da sessão de plano com o Vinícius.
- **Não está ordenado por gravidade.** A ordem abaixo é arbitrária, de propósito.
- **Não usa placar como índice.** Os números de régua aparecem como *verificação* de cada item,
  nunca como o motivo de ele estar na lista. O que põe um item aqui é ele contrariar algo que o
  próprio repositório declara, ou aparecer errado na tela do gerente.
- **Não é régua.** As réguas do projeto são `avaliar_agentes.py` e `avaliar_rag.py`.

---

# §1 — O que foi encontrado, por natureza

## 1.1 Uma violação de princípio declarado

Este é o único item da lista onde o repositório **contradiz a si mesmo**. Os outros são defeitos
de desenho; este é uma regra escrita sendo desobedecida.

**O princípio, escrito em dois lugares desde o dia 2 do projeto:**

- `src/agents/evidence_validator.py:11` — *"4. Ausência de sinal != sinal negativo → nada é
  DELETADO, só rebaixado"*
- **D-010** (22/08) — *"o Validator preenche `confianca` e `validada` e **nunca deleta**…
  `Elegibilidade` segue a mesma disciplina, separando `motivos_exclusao` (a base **prova** que é
  consultoria) de `requisitos_nao_verificados` (a base **não prova** que tem developer)…
  **Deletar destrói informação que o humano precisa.**"*

**Onde é obedecido:** `briefing.py:elegibilidade()` — o `x` versus `?` que aparece no briefing.

**Onde é desobedecido:** `src/agents/classifier.py:204` (e :195 no braço da flag).

A rubrica define a classe por uma propriedade **positiva** (`contexto/02` §4):

> *"**`non-AI`** — O produto não depende de IA… **Sem IA no caminho crítico** da entrega de valor."*

Isso é constatação sobre a empresa, e constatação exige evidência. O código emite esse rótulo
quando `pontos == 0` — quando **não encontrou sinal**.

**A rubrica pede "constatamos que não há IA no caminho crítico". O código entrega "não achei
sinal de IA".**

**Comando:** `python scripts/varrer_classes.py`
**Saída:** `AI-native 1 · AI-enabled 20 · non-AI 9`; as 9 com `ADT` = `---` (nenhum detector) e
**todas com 2 a 7 dores de IA extraídas pelo mesmo Extractor**.

**O que NÃO é defeito, e foi verificado nesta sessão:** os componentes a jusante estão corretos.
`contexto/02` §4 diz literalmente `non-AI: fora do funil, não é prospect`, então
`derivar_quadrante` e `recommendation.py:131` implementam a rubrica fielmente. **Eles fazem a
coisa certa com uma entrada errada.** O raio de mudança é o Classifier.

## 1.2 Defeitos de desenho — independentes entre si

Cada um contraria um requisito, um diagrama ou a própria saída. Nenhum é manifestação de outro.

### (a) Ordem no grafo: recomenda para quem o sistema recusou
`src/graph.py` — `g.add_edge("recommendation", "elegibilidade")`. O motor de recomendação roda
**antes** do filtro do Inception, então não tem como saber que a empresa foi recusada.
**Comando:** `python -m src.graph "startups de fintech AI-native"`
**Na tela:** a Liqi sai `x exclusão por 'cripto'` e três linhas abaixo recebe
`ação: Agendar conversa técnica ... com o time de engenharia da Liqi`.
**Não consta em `decisoes.md`, `plano.md` nem `sessao-atual.md`** — achado desta execução.

### (b) Acoplamento invertido entre dois agentes
`evidence_validator.py:204` — `diagnostico.confianca` é `min()` sobre `perfil.afirmacoes`, e essa
property inclui todas as `dores_observadas`. **Quanto mais dores o Extractor acha, menor a
confiança que o Classifier recebe.** A métrica de um agente se move contra a melhoria de outro.
D-059 nomeia isso como "monotonicidade perversa".
**Comando:** `python scripts/medir_confianca.py` → braço A = 0.
**Nota:** isto **não** é violação da regra 4 — o `min()` rebaixa, não deleta. É defeito distinto.

### (c) Dependência entre agentes que não está no diagrama
`briefing.py:210` — `elegibilidade()` varre `perfil.afirmacoes[*].evidencias[*].trecho`, não o
documento. **Medido: 47.818 de 452.822 caracteres — 10,6%.** Os outros 89,4% o filtro nunca lê.
O filtro do Inception é o **Diferencial declarado** do projeto e tem a cobertura do recorte do
Extractor; a arquitetura publicada não mostra essa dependência.
**Comando:** ver §5 (o script de cobertura está no scratchpad desta sessão e precisa ser
reescrito — **não foi salvo no repositório**).
**O conserto óbvio foi medido e é pior:** varrer o documento inteiro leva de 7 para 11 recusas
em 30, e pelo menos 3 das 6 novas são falsos positivos claros — a **TideWise** seria recusada por
*"Dados da **consultoria** Fortune Business Insights"* (uma consultoria citada como fonte de
estatística) e a **BemAgro** por *"a **revenda** goiana MM Agro"* (outra empresa). Hoje o filtro
erra por omissão; varrendo tudo, erraria por exclusão — e exclusão errada some do briefing sem
deixar rastro.

### (d) A rubrica de profundidade cobre um tipo de empresa só
`classifier.py:101` — `PROFUNDOS` são 13 termos, todos de infraestrutura de serving de LLM:
`cuda, gpu, tensorrt, triton, vllm, quantiz, self-hosted, on-premise, inferência, latência,
throughput, mlops, observabilidade`. Uma healthtech que treina modelo preditivo não usa nenhum
deles.
**Comando:** ver a Parte 1 do script em §5 — **também não salvo no repositório.**
**Medido:** 7 das 8 fixtures de gabarito têm **zero** desses termos nos documentos inteiros. Só a
Maritaca tem 3.
> **⚠️ A CONTINUAÇÃO DESTE ITEM ESTÁ CONTAMINADA E NÃO DEVE SER USADA COMO EVIDÊNCIA.**
> Esta sessão testou a hipótese 2 de D-060 ("a lista não cobre como uma healthtech descreve a
> própria stack") com uma lista alternativa de 22 termos — e **escreveu essa lista conhecendo o
> gabarito**. É exatamente o erro que D-091 custou uma sessão. O resultado (as 4 `AI-native`
> marcam, as 3 outras não; 46% de marcação nas 30) é **sugestivo e imprestável como medição.**
> Para valer, a lista tem de sair de `contexto/02` **antes** de olhar o gabarito, ser congelada,
> e só então medida. Trate como pergunta em aberto, não como achado.

### (e) Dois eixos que deveriam casar e não casam
`recommendation.py:63` — `NEGOCIO` é indexado por **tecnologia**; a dor vem de
`citacao.dor_origem`. Nada garante que combinem, e na saída eles se contradizem:
`dores: latencia` → texto *"Reduz o **custo** por token"*; `dores: escalabilidade` → texto
*"**Latência** menor melhora a experiência"*. Além disso o dicionário cobre **5 de 16**
tecnologias; as outras 11 caem em fallback formulaico. É o **campo 3 dos 7 obrigatórios**.

### (f) Referência interna de decisão no texto do usuário final
`evidence_validator.py:210` monta e `briefing.py:258` imprime *"— ver D-059 para por que este
agregado é o defeito que a régua mede em 0/6"*, uma vez por empresa, no relatório executivo.
Entrou em 27/08 (`git log -S "ver D-059"` → `6fae6c5`), deliberadamente, para tornar o defeito
visível — a intenção era boa e a superfície escolhida foi a errada.

### (g) Dois dos sete campos obrigatórios são cortados no meio da palavra
`briefing.py:335-336` — `[:150]` sem reticências. Na tela: `"...NVIDIA NIM™ microse"`,
`"...é a passagem citada da documentaçã"`.

### (h) Uma regra que nunca roda porque o dado não é coletado
`evidence_validator.py:96` exige `>= 1 documento recente` para conceder `alta`, e `_recente(None)`
devolve `False`. **86 dos 93 documentos têm `data_publicacao: null`**, porque `coletar.py` não
captura data nenhuma (`grep -n "data\|date\|publish" scripts/coletar.py` → vazio). Metade da
regra 2/3 está desligada desde sempre.

## 1.3 O que foi verificado e está CORRETO

Registrado para que a sessão de plano não "conserte" o que funciona:

- **`recommendation.py:131` e `derivar_quadrante`** implementam `contexto/02` §4 fielmente.
- **O filtro do Inception acerta as 7 recusas** (`python scripts/varrer_elegibilidade.py`).
- **O eliminatório "projeto que não executa" está fechado**, por clone limpo real do repositório
  público em 04/09: venv nova (60 pacotes, zero erro), banco novo, `seed` 30/93,
  `ingerir_nvidia` **377 chunks (175+202), idêntico ao medido**, `avaliar_rag --validar`
  **24/24**, `python -m src.graph` exit 0, `pytest -q` **81 passed em 2m32**, `smoke` 3/3.

---

# §2 — O que foi REFUTADO em 04/09

Três afirmações caíram. Todas estavam sendo tratadas como fato.

**(1) A hipótese que D-059 deixou escrita, 8 dias sem teste.**
D-059 concluiu: *"Melhorar isso é fazer o Classifier anexar evidência mais larga."* O braço C de
`medir_confianca.py` mede exatamente isso e dá **2, idêntico ao braço B**. Anexar evidência mais
larga não move o campo. **O `decisoes.md` contém afirmação não testada — não o trate como
verificado.**

**(2) "Consertar o Classifier custa 1 ponto de `classe`."** — afirmação desta sessão, por
inferência. `python scripts/varrer_classes.py --custo-desenhos`: vale para o desenho A
(`3/7 → 2/7`) e **não** para o B (`3/7 → 3/7`). O trade-off era de um desenho, não do defeito.

**(3) "É um defeito de arquitetura com cinco manifestações."** — afirmação desta sessão, e a mais
perigosa, porque era a mais elegante. `contexto/02` §4 **autoriza** o corte de `non-AI` do funil,
então `recommendation.py` não viola nada; e o `min()` rebaixa sem deletar, então também não viola
a regra 4. **Há uma violação, não cinco.** Se este documento tivesse sido escrito sem a
verificação, teria mandado consertar dois componentes corretos.

**Além disso:** `plano.md` §3.2 justifica ACEITAR P-21 dizendo que "só 1-2 das 7 regras do TAPI
têm startup na base". Com a base em 30, são **5 de 7** (voz 3 · saúde 3 · robótica 4 · tabulares 1
· atendimento ~3). **Aquela justificativa está desatualizada** — o que não decide nada, só
significa que a razão escrita não vale mais como está.

---

# §3 — O que NÃO foi verificado

Não use como premissa.

- **Todas as estimativas de tempo desta sessão são chute.** Nenhuma saiu de cronometragem.
- **Se o "desenho B" introduz ruído.** Ele faz as 9 entrarem no funil, incluindo a SunnyHUB, que
  é energia solar e `non-AI` de verdade. **Não medido.**
- **O que as 4 empresas de robótica recebem hoje.** Afirmou-se que "deveriam receber
  Isaac/Omniverse" por leitura das regras do TAPI. Ninguém rodou o grafo nelas.
- **Se mexer em `confianca` quebra algo a jusante.** Ela alimenta `_prioridade()`
  (`recommendation.py:178`). Efeito não medido.
- **A lista de vocabulário alternativo do item 1.2(d)** — contaminada, ver o aviso lá.
- **P-23** (`elegibilidade()` e o recorte) é de D-091 e não foi re-verificado hoje; o que foi
  medido hoje é a **cobertura de 10,6%** e o **efeito do conserto óbvio**.
- **O caminho Docker** — daemon parado na máquina; não testado. A divergência
  `.env.example` 5432 × `docker-compose` 5433 é leitura de arquivo, não execução.
- **`classe 3/7`, o teto de 4/7 (D-060) e o placar do juiz (D-072)** foram medidos no
  `nemotron-3-nano-30b-a3b`, morto em 01/09. Só `--geracao` foi refeito no modelo vivo.

---

# §4 — Decisões que são do Vinícius

Nenhuma é técnica. O plano não fecha sem elas, e a sessão de plano deve **perguntar, não assumir**.

1. **Empresa NÃO ELEGÍVEL ao Inception deve receber recomendação de tecnologia?**
   Pró: a NVIDIA vende fora do programa. Contra: o sistema existe para captar PARA o programa.
   Decide o conserto de 1.2(a).
2. **O Classifier deve emitir um rótulo próprio para "não achei sinal", ou manter `non-AI` e
   mudar só o que acontece depois?** Ver §2(2) — os dois custos são diferentes e um não foi medido.
3. **A hipótese 2 de D-060 (`PROFUNDOS` enviesada) entra no plano com o protocolo anti-contaminação
   da §1.2(d), ou fica de fora?**
4. **P-21 entra**, agora que a justificativa de ACEITAR está desatualizada (§2)?
5. **Quanto tempo o fechamento da IA pode ocupar?** A interface tem zero byte e é a porta do
   eliminatório do vídeo. Sem orçamento declarado, um plano bem escrito entrega mais trabalho do
   que cabe nos dias restantes.

---

# §5 — Como iniciar a sessão de plano

Sessão **nova**, para que o plano não seja escrito por quem fez a análise.

**Dois scripts foram salvos no repositório** e reproduzem parte da §1:
`scripts/varrer_classes.py` (com `--custo-desenhos`) e `scripts/medir_confianca.py`.

**Dois NÃO foram salvos** e precisam ser reescritos pela sessão de plano se ela quiser confirmar
1.2(c) e 1.2(d): a cobertura de `elegibilidade()` sobre o texto (10,6%) e a contagem de marcadores
`PROFUNDOS` por fixture. Ambos são ~20 linhas sobre `avaliar_agentes.carregar()`.

Cole isto:

```
Leia projeto/achados-04-09.md inteiro, incluindo §0 e §2.

Ele foi escrito pela sessão que fez as medições, e essa sessão errou três vezes em 04/09 — as
três estão na §2. Trate tudo como suspeito até reproduzir.

Antes de escrever qualquer plano:
1. Limpe o __pycache__ e rode: varrer_classes.py, varrer_classes.py --custo-desenhos,
   medir_confianca.py, varrer_elegibilidade.py, avaliar_agentes.py, avaliar_agentes.py --baseline.
   Compare com o que a §1 afirma.
2. Rode `python -m src.graph "startups de fintech AI-native"` e LEIA o briefing inteiro.
   1.2(a), (e), (f) e (g) aparecem na tela. Diga o que viu, não o que o documento diz que você veria.
3. Diga o que reproduziu e o que não reproduziu. Se algo divergir, PARE e investigue.
4. Leia §3 (não verificado) e trate cada linha como pergunta, não como premissa.

Só então escreva o plano, em docs/superpowers/plans/.

O que o plano precisa endereçar, e a razão é arquitetural, não de placar: o TAPI avalia "a
capacidade de tomar e defender decisões técnicas", então o que importa é o desenho estar
coerente e defensável. As réguas VERIFICAM que o conserto não quebrou nada; elas não escolhem
o que consertar.

Regras deste projeto (CLAUDE.md):
- fixe o critério ANTES de medir; medir não é promover
- toda decisão vai para projeto/decisoes.md com a alternativa descartada
- não use subagentes
- RODE O SISTEMA antes de fechar a sessão
- não julgue recomendação com RERANK_PROVEDOR=nenhum (D-097)

As cinco decisões da §4 são do Vinícius. Pergunte antes de dimensionar o plano — a §4.5
(orçamento de tempo) muda o tamanho de tudo.
```

**Antes de rodar qualquer coisa:** `python scripts/smoke_nvidia.py`. São 4 segundos, e o passo 7
tem fornecedor único desde maio (D-097).
