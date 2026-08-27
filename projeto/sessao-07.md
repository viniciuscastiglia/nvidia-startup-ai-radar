# Sessão 07 — as duas mudanças foram reprovadas pelo próprio critério, e a stack caiu no meio

## Sessão 07 — FECHADA em 27/08/2026

Pauta: Classifier e Evidence Validator, os gargalos que a régua da 06 nomeou. **8 decisões novas
(D-058 a D-065).** Duas mudanças de agente implementadas, medidas e **as duas reprovadas** pelo
critério fixado antes do código. E, no meio da sessão, o **terceiro EOL da stack NVIDIA**.

### O que ficou de pé no fim do dia

| verificação | resultado |
|---|---|
| `avaliar_agentes.py --validar` | coerência ok · evidência literal ok · teto do casador 12/12 · **teto do degrau 2a 1/4** |
| `avaliar_agentes.py` (produção) | **idêntica à linha de base** — nenhuma mudança promovida |
| `avaliar_agentes.py --exclusoes` | **6/7 excluídas · 3/7 passaram** (régua nova) |
| `pytest -q` | **52 passed, 1 failed** (53 testes) — a falha é o 404 do reranker, não o código |
| `python -m src.graph` | **não rodado** — falharia no mesmo 404 |

---

## 1. As duas mudanças do Bloco 1 foram medidas e reprovadas

O critério foi escrito **antes da primeira linha de código** (D-058), com alvo, guardas e regra de
empate. É a disciplina de D-055.

| campo | trivial | controle (`>= 3`) | produção | **medido** | alvo | veredito |
|---|---|---|---|---|---|---|
| `classe` | 4/7 | **4/7** | 3/7 | **4/7** | ≥ 5/7 | **empata — não entra** |
| `confianca` | 3/8 (37,5%) | — | 0/6 | **2/6 (33%)** | ≥4 abs. e ≥50% | **perde — não entra** |

As duas ficaram atrás de flag (`--rubrica`, `--confianca-diagnostico`), medidas e documentadas — o
destino que D-058 já tinha citado por nome antes de existir número. **A produção voltou byte a byte
à linha de base.** Todas as guardas seguraram em todos os braços: maturidade 6/7, dor 49%, recall
100%, discriminação 8/8.

### O achado que vale mais que os dois números: o alvo era inalcançável

O harness tinha `teto_do_casador` para dores desde D-053 e **nenhum teto equivalente para `classe`**.
D-058 fixou 5/7 sem ele. Calculado depois e agora medido pelo `--validar`:

```
teto do degrau 2a da rubrica: 1/4 das AI-native decididas
```

**Sete das oito fixtures têm profundidade técnica ZERO.** O degrau `2a` nunca poderia mover mais que
a Maritaca; as outras três `AI-native` dependem do `2b`, idêntico à aritmética antiga. Máximo
alcançável: 3/7 + 1 = **4/7, o placar do trivial**.

> **D-055 ensinou a fixar a margem antes de medir. Esta sessão aprendeu que fixar a margem sem
> calcular o teto é fixar um número, não um critério.** `teto_do_degrau_2a` entrou no harness.

E o teto diz para onde ir: o gargalo de `classe` não está na regra de decisão, está no
**vocabulário** — ou os documentos não contêm o sinal (curadoria, M3), ou `PROFUNDOS` não cobre como
uma healthtech descreve a própria stack (rubrica). Nenhuma das duas se resolve mexendo em limiar.

### O gargalo de `confianca` mudou de lugar

Não é mais o validator. Doutor-AI recebe `baixa` porque o Classifier lhe anexou **uma** evidência,
de um `release` sem data; SunnyHUB porque não anexou **nenhuma**. O validator relata fielmente a
espessura da evidência que recebe. Melhorar isso é trabalho do Extractor, que recorta uma frase por
documento.

---

## 2. A régua de exclusão achou um falso negativo vivo em produção

`data/avaliacao/exclusoes.yaml` + `--exclusoes`: 14 pares mínimos (6 de documento real, 8 sintéticos
**declarados**), dois números que nunca são somados.

Na primeira execução:

> **`"Somos revendedores autorizados"` PASSA pelo filtro do Inception.** `"revenda"` não é prefixo
> de `"revendedores"` — o 7º caractere é `a` contra `e`.

E o comentário de `briefing.py:45` afirmava o contrário. **Sobreviveu à auditoria que D-057 fez de
D-048**, porque não havia régua que exercitasse `revenda`. Terceira vez que ampliar o instrumento
derruba uma afirmação escrita (D-039, D-052, esta).

**A correção de corpus foi medida e NÃO entrou**, apesar de fazer 7/7 nas fixtures: ela deixa a
regra de casamento em **6/7 · 3/7, idêntica à produção**. Não resolve sujeito — evita as frases onde
o problema aparece, comprando o 7/7 num campo de uma linha curado à mão, com 22 empresas prestes a
entrar cuja `descricao_curta` o próprio curador escreve. É a troca que D-057 puniu.

Medido e deixado para decidir: trocar `"revenda"` pelo prefixo `"revend"` leva o falso negativo de
6/7 para **7/7** e o falso positivo de 3/7 para **2/7**.

---

## 3. O TERCEIRO EOL, no meio da sessão (D-064)

Descoberto pelo `pytest`, confirmado por smoke e por 18 sondagens diretas:

| capacidade | modelo | resultado |
|---|---|---|
| chat | `meta/llama-3.1-8b-instruct` (D-012) | **410 Gone** |
| embedding | `llama-nemotron-embed-vl-1b-v2` | **PASSOU** |
| reranking | `rerank-qa-mistral-4b` (D-046) | **404** — e nenhum substituto no catálogo |

**O embedder sobreviveu** — era a única morte que invalidaria os 381 vetores.

**A assimetria que importa:** o LLM é usado em **dois** lugares (o passo 8 e o juiz do Extractor,
que está desligado) e **o grafo nunca o chama**. O reranker é chamado **dentro do grafo**, no
`nvidia_rag`. Então **o reranker é o que quebra a demo ponta a ponta; o LLM quebra o passo 8, que
mora na interface que ainda não existe.**

---

## 4. E a contingência para isto já estava escrita, e escorregou duas vezes (D-065)

D-046 escreveu em 25/08 que descartar o cross-encoder local por *"perde o argumento do Diferencial"*
era *"a única linha deste log onde uma história venceu uma propriedade técnica"*, e agendou o
fallback como **Bloco 0 da próxima sessão**. Não entrou na 06 nem na 07.

A pauta da 05 rebaixou-o com argumento explícito: o playbook de recuperação cabia em uma sessão.
**A premissa não escrita era que existiria um substituto.** Em 25/08 existia — *"sobrou um reranker
no catálogo"*. Hoje: zero.

**E o questionamento do Vinícius derrubou mais uma afirmação do log:** D-015 descartou o Cohere por
*"é pago"*, e **isso é falso** — há trial key gratuita cobrindo Command, Embed e Rerank (1.000
chamadas/mês, 10 req/min, vedada a uso comercial, o que não se aplica aqui). Com isso, a leitura
certa é que **as duas alternativas ao fornecedor único caíram por narrativa**, uma delas com um fato
falso por cima. D-015, D-046 e a linha do Diferencial no `CLAUDE.md` foram corrigidos.

O erro de método, nomeado em D-065: **o rigor foi aplicado à escolha técnica e não à premissa que
eliminou as alternativas** — e é a premissa que decide o espaço de opções.

---

## 5. Também entregue

- **`dores_enderecadas` deixou de ser tautológico** (D-063): "de quais dores tiro EVIDÊNCIA" e
  "quais dores DECLARO endereçadas" viraram duas listas. Nenhuma recomendação some.
- **M3 fechada em 30 empresas** (D-062), em duas camadas — 8 com gabarito, 22 como dado, 3-4
  adversariais para a régua de D-061. Coleta em sessão própria, timebox 3h, piso 20.
- **Nota de método:** uma medição foi contaminada por **bytecode obsoleto** — trocar `>= 4` por
  `>= 3` preserva o tamanho do arquivo, e o `.pyc` sobreviveu ao `git checkout`. Só foi pego porque
  `classe` se mexeu onde era estruturalmente impossível. Toda medição passou a limpar `__pycache__`.

---

## 6. O `/code-review` derrubou uma correção desta sessão (D-066)

15 achados, **11 pagos**. Três merecem estar aqui:

1. **D-063 quebrou a rastreabilidade que existe para proteger.** A correção estreitou a
   *declaração* (`dores_enderecadas`) e deixou o *lastro* largo — produzindo recomendação que
   declara `observabilidade` e cita trechos sobre **custo**, sob o rodapé que promete o contrário.
   Antes de D-063 as duas listas concordavam por construção. Corrigido com `lastro = dores or
   validadas`, e **quatro testes novos** fecham o buraco com zero API.
2. **`motivo_confianca` era código morto.** D-059 escreveu que ele *"fica em produção"*; ele só era
   preenchido dentro do braço da flag, que é `False`. A afirmação era falsa quando foi escrita.
3. **Instrução contaminada de novo, no `CLAUDE.md`.** A tabela de Stack ainda dizia
   *"(o único vivo)"* sobre o reranker morto, vinte linhas acima do aviso que a mesma sessão
   adicionou. `config.py` e `.env.example` idem.

**O padrão que atravessa os três:** D-063 foi a única mudança de comportamento da sessão que entrou
**sem flag, sem teste e sem braço de harness**, numa sessão cuja tese era que mudança sem critério
medido não entra. Foi exatamente ela que quebrou.

---

## Orçamento de API — orçado ~170, teto ~276, **gasto ~25**

O núcleo custou zero (a régua não chama LLM). O `pytest` abortou cedo e as chamadas caras falharam
rápido por causa do EOL. `python -m src.graph` **não foi rodado** — falharia no mesmo 404 sem
responder nada. **O bloco de contingência de re-medição pós-review não foi usado e continua
disponível.**

---

## Pauta da sessão 08 — o Bloco 0 que escorregou duas vezes vem primeiro

**Bloco 0 — a stack. Bloqueante: nada roda ponta a ponta sem isto.**

Duas decisões independentes, e a segunda é a que pesa:

1. **LLM** — substituto direto (`nvidia/mistral-nemo-minitron-8b-8k-instruct`), Grok (a liga
   sugeriu, e isso o pré-autoriza), ou os dois com fallback. **Não encosta no Diferencial.** Custo
   real não é código, é **re-medir** abstenção (20–22/24), `json_schema` (n=5) e o juiz (50–62%) —
   ou declará-los históricos com modelo e data, como D-046 fez.
2. **Reranking** — cross-encoder local, Cohere com trial key, os dois medidos, ou nenhum. A
   hipótese de D-065: **local como default** (roda sempre, sem chave, sem quota, sem EOL) **e**
   Cohere atrás de env var, **com as duas linhas na tabela de ablação** ao lado de "sem rerank".
   É `--truncar-pool` aplicado ao fornecedor.

**O argumento que deve decidir não é de pontos, é o eliminatório nº 3:** um avaliador que rodar este
repositório em outubro bate no mesmo 404. Componente hospedado em catálogo de preview é passivo do
entregável, independente do apagão de hoje.

**Verificar antes de o roteiro do vídeo depender:** a trial do Cohere limita Rerank a **10 req/min**,
e um run do grafo faz ~20 chamadas sequenciais — **~2 min de throttle** numa demo ao vivo com teto de
7 minutos.

**Bloco 1 — os achados do review NÃO pagos** (D-066): a sub-declaração de `dores_enderecadas`
causada pela dedup do `nvidia_rag` (exige `dor_origem` virar lista), o contador do eixo 1
contornando o juiz de D-053, e a duplicação do helper de perfil mínimo — esta última se resolve
junto com a decisão de corpus que D-061 deixou aberta.

**Bloco 2 — a M3**, 30 empresas, timebox 3h (D-062).

**Depois:** interface (5 pontos, uma sessão), README (hoje ainda diz "Como rodar: Em breve" e "a
definir" para LLM, embeddings e busca vetorial), vídeo até 07/09.

**Perguntas para a liga:** (1) o reranker hospedado da NVIDIA saiu do ar e o TAPI recomenda Cohere,
que também não é NVIDIA — cross-encoder local é aceitável no passo 7? (2) vocês vão **executar** o
projeto na avaliação, e com chave de quem? (3) aviso de que o catálogo de preview aposentou modelos
em 18/05, 25/08 e 27/08.
