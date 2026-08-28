# Sessão 08 — a stack voltou, e o juiz passou no critério que o reprovou há três dias

## Sessão 08 — FECHADA em 28/08/2026

Pauta: o Bloco 0 que escorregou duas vezes. **6 decisões novas (D-067 a D-072).** A stack saiu de
"não roda" para rodando ponta a ponta, e uma medição reabriu uma decisão que estava fechada.

### O que ficou de pé no fim do dia

| verificação | 27/08 | **28/08** |
|---|---|---|
| `smoke_nvidia.py` | 1/3 | **3/3** |
| `python -m src.graph` | 404 no reranker | **roda — briefing completo, 2 startups, 3 recomendações** |
| LLM dos agentes | 410 Gone | **`nvidia/nemotron-3-nano-30b-a3b`** |
| passo 7 | 404, sem substituto | **Cohere `rerank-v3.5`** |
| `avaliar_agentes.py` (produção) | 3/7 · 49% · 8/8 | **idêntica** — a troca de stack não moveu agente |
| `avaliar_agentes.py --exclusoes` | 6/7 · 3/7 | **7/7** · 2/7 |

---

## 1. O substituto que D-064 recomendou POR NOME estava morto (D-067, D-070)

D-064 indicou `nvidia/mistral-nemo-minitron-8b-8k-instruct` porque ele aparecia em
`GET /v1/models`. **Ele devolve 404.** É o mesmo erro de método que D-065 nomeou dois dias antes —
premissa não verificada — cometido dentro da própria correção.

Sondados 10 candidatos, um a um, com chamada real:

| resultado | quantos |
|---|---|
| HTTP 404 | **7** |
| inutilizável (400 + timeout de 300 s · 35 s e 500 no structured output) | 2 |
| **utilizável** | **1** |

**Todos os 10 estavam listados.** O catálogo é vitrine, não inventário — e **encolhe entre
execuções**: 84 modelos em 27/08, 83 em 28/08, com dois que respondiam parando de responder.
`scripts/sondar_catalogo.py` entra versionado, separado do smoke de propósito: o smoke precisa
**falhar alto** sobre a config vigente, a sondagem varre alternativas. Misturar faz o smoke nunca
falhar — o argumento que o próprio docstring dele já usava para paths de rerank.

---

## 2. O Cohere volta, e o teto da trial é pior que a documentação (D-068)

**Nunca houve argumento medido contra o Cohere.** Ele jamais foi testado. As duas razões que o
eliminaram em D-015 eram um fato falso ("é pago") e uma narrativa — e o TAPI o recomenda
**nominalmente** na seção 5.3.

`ConfigRerank` ganhou `provedor`: `cohere` (produção), `nvidia` (registro do que rodou até 27/08),
`nenhum` (degradação graciosa). **A variável que faltava não era o nome do modelo, era o nome de
quem o hospeda** — trocar de modelo só resolve se existir outro modelo, e em 27/08 não existia.

**Medido, e é pior que o documentado:** o 429 chega na **4ª** chamada sequencial (a doc promete 10
req/min), `retry-after` vem **ausente**, e a janela de recuperação é de **~26 s**. Sem controle de
taxa o Cohere serve para 3 chamadas, e um run do grafo faz 20-30. Limitador proativo
(`COHERE_REQ_POR_MIN`, default 10) mais retry exponencial: **12 chamadas em 72,0 s = 10,0 req/min,
zero 429**. Janela: não recusou até ~32.000 tokens, contra 446 do maior chunk.

**Consequência para o vídeo:** ~2-3 min só de rerank num run completo, com teto de 7. O TAPI pede a
demo *pela interface* — a cena é uma consulta com `MAX_STARTUPS` baixo, não o run inteiro.

### A troca de fornecedor custou duas perguntas, e isso está escrito

| | NVIDIA (25/08) | **Cohere (28/08)** |
|---|---|---|
| e@1 | 84% | **79%** |
| e@5 sobre híbrida | 100% | **95%** |
| ganho do braço lexical | e@5 95% → 100% | **nenhum — os dois braços empatam** |

**O braço lexical voltou a não pagar nada.** O achado de D-037 Atualização 2 (a q17, âncora
`Evaluator`) era **específico do reranker**, não uma propriedade da fusão. O reranking continua
pagando o que sempre pagou: **e@3 de 79% → 95%**.

Não virou mudança de produção, e a omissão é decisão: trocar o motor exige critério fixado antes
(D-055, D-058), e agora o híbrido custa mais chamadas — o que importa a 10 req/min.

**Limitação do instrumento, registrada:** `--por-pergunta` mede posição do DOCUMENTO e as perdas
são no critério ESTRITO (o chunk conter a âncora). Ele não localiza as duas perguntas perdidas.

---

## 3. A diferença que D-047 mediu DESAPARECEU (D-069)

Mesmo protocolo, schema e prompt reais do passo 8, em `scripts/medir_saida_estruturada.py`:

| método | 24/08 · `llama-3.1-8b` † | 28/08 · `nemotron-3-nano-30b` |
|---|---|---|
| `json_schema` | 4/5 | **14/15** |
| `function_calling` | 0/5 | **15/15** |
| `json_mode` | 0/5 | **0/5** — segue sem parsear |

**A decisão fica, o argumento morre.** Uma execução de diferença não troca a convenção do
repositório. A propriedade era do **modelo**, não do método.

**O colateral vale mais:** na primeira sonda, com um schema de brinquedo, este mesmo modelo
**alucinou**; com `SaidaGerador` e a `INSTRUCAO` reais faz 10/10. É D-045 confirmado por um caminho
que não foi desenhado para testá-lo — **o docstring do schema é prompt**, e medir com schema de
brinquedo mede o brinquedo.

---

## 4. O juiz do Extractor PASSOU, e é o achado da sessão (D-072)

**Mesmo código, mesmo prompt de 25/08. Só o modelo mudou.**

| | alvo D-055 | 25/08 · 8b † | **28/08 · 30B (n=3)** |
|---|---|---|---|
| dor — precisão | **≥ 64%** | 50-62% → **empate** | **83 · 96 · 96** |
| discriminação | ≥ 6/8 | 8/8 | 6 · 8 · 6 |
| dor proibida | — | 6-9 | **1-2** |
| elegível / motivo | — | 5-6 / 7 | **6/7 nas três** |
| dor — recall | *sem guarda* | 79-96% | **71-79%** |
| classe | *sem guarda* | 2-3 / 7 | 2-3 / 7 |

**O critério fixado antes do código foi atendido nas três execuções, com o pior caso 19 pontos
acima do alvo.** E o modo de falha que D-056 nomeou — *o 8b recitando as regras do prompt como
justificativa* — não reapareceu. Era falha de modelo pequeno.

**A tese que isto abre, e que vale mais que o placar:** várias conclusões deste projeto sobre *"o
LLM não dá conta"* eram sobre um modelo de **8B**, não sobre a abordagem. Vale re-testar onde o LLM
foi descartado.

**A lacuna, pela segunda vez:** D-055 nunca fixou guarda de **recall**, que cai 25 pontos. É a mesma
classe de buraco que a sessão 07 achou em `classe` — *fixar a margem sem calcular todos os lados é
fixar um número, não um critério*.

**A promoção está PENDENTE de decisão do Vinícius.** `USAR_JUIZ_LLM` segue `False`. **Medir não é
promover**, e esta linha existe para a diferença ficar explícita.

---

## 5. Bloco 1: `revenda` → `revend` (D-071)

Falso negativo **6/7 → 7/7**, falso positivo 3/7 → **2/7**. **É um TRADE-OFF, não melhora dos dois
lados** — o plano da sessão afirmou errado e foi corrigido. O que autoriza é a assimetria de D-057:
o falso positivo aparece no briefing; o falso negativo não aparece em lugar nenhum.

O helper duplicado (achado nº 13) **não** foi unificado: o gatilho registrado era *"quando
`elegibilidade()` mudar de corpus"*, e o corpus não mudou.

---

## 6. O diagnóstico do núcleo, levantado a pedido do Vinícius

Três causas concretas, e duas são a mesma classe de erro:

1. **`confianca` 0/6 é constante, não impreciso.** `evidence_validator.py:122` faz
   `min()` sobre as confianças das afirmações: **uma afirmação fraca derruba o diagnóstico
   inteiro**, e quanto mais evidência o sistema junta, pior fica. O agente piora quanto melhor
   trabalha.
2. **Os gatilhos de dor casam o domínio do PRODUTO, não o da IA.** `observabilidade` é 5 das 10
   dores proibidas, e o que dispara é *"monitoramento do **sistema fotovoltaico**"* (SunnyHUB),
   *"**dashboards** que mensuram a qualidade do atendimento"* (Doutor-AI), *"as **métricas** da
   Laura, taxa de mortalidade 25% menor"*. Nenhum fala de instrumentação de IA.
3. **`classe` erra 4 vezes, todas na mesma direção** — `AI-native` → `AI-enabled`. Gargalo de
   vocabulário: 7 das 8 fixtures têm profundidade técnica zero.

**O padrão que liga 2, 3 e a exclusão da Axenya por `consultoria`:** todos casam palavra sem checar
**de que a frase fala**. É a mesma classe de D-048 e o achado aberto de D-052 — detector léxico
onde é preciso julgamento de sujeito e domínio. **É exatamente o que o juiz faz**, e é por isso que
D-072 move a agulha.

### E o buraco maior não é nenhum dos três

**O critério 3 (Motor de recomendação, 20 pontos) NÃO TEM RÉGUA.** O gabarito das 8 fixtures tem 9
campos e nenhum é sobre recomendação — a recomendação esperada existe só em prosa livre, em
`perfil_alvo_nota`. Nada quebra se ela vier errada.

É o mesmo estado que os agentes tinham antes da sessão 06: *3 startups, as 3 AI-native, e um
classificador constante passava em 3 de 3.* A saída real de hoje mostra o efeito — para dor de
**custo**, a justificativa técnica é *"Join our ecosystem of startups, partners, and developers"*.

**Cobertura por agente:** `query_planner` (stub, sem LLM, **zero testes, zero régua**) ·
`retriever` (sem gabarito) · `recommendation` (**sem régua**). Quatro dos nove agentes sem
instrumento.

---

## Orçamento de API — gasto ~700

LLM ~250 (sondagem 25 · D-047 45 · juiz n=3 ~156) · embedding ~120 · **Cohere ~300 de 1.000/mês**.
O limitador de taxa fez a avaliação levar ~10 min por tabela — previsto e orçado.

---

## Pauta da sessão 09 — o Vinícius escreve depois de estudar

**Documento de estudo:** `Anatomia do Radar` — https://claude.ai/code/artifact/dc527bde-f149-49f8-87a5-3105197cc2e2

**As quatro decisões abertas, em ordem de quanto movem a nota:**

1. **Ligar o juiz?** (D-072) — dor 49% → 83-96%, custo recall 100% → 71-79%. Critério atendido;
   falta a decisão sobre a lacuna de recall.
2. **Dar régua ao motor de recomendação** — 20 pontos sem instrumento. Trabalho de curadoria:
   quais tecnologias são esperadas e quais são proibidas, por fixture.
3. **Consertar o `min()` da confiança** — 0/6 constante. Barato, mas exige critério fixado antes
   (uma tentativa já foi reprovada em D-059).
4. **`classe`** — o mais caro: curadoria de documentos ou reescrita da rubrica.

**Não feito nesta sessão, e é corte declarado:** a M3 (22 empresas) · `pytest` completo (rodei só
`test_elegibilidade`, 9/9 — os 53 exigem uma passada com Cohere, ~7 min de throttle) · a
**re-medição da abstenção do passo 8**, cujos números (20-22/24) ainda são do modelo morto (D-069
previu n=3 e não foi executado) · interface · README.

**Perguntas para a liga, se houver contato:** (1) o reranker hospedado da NVIDIA saiu do ar e o
projeto migrou para o Cohere, que o próprio TAPI recomenda — confirmam que é aceitável? (2) vocês
vão **executar** o projeto na avaliação, e com chave de quem? (3) aviso de que o catálogo de
preview aposentou modelos em 18/05, 25/08 e 27/08, e que ele lista modelos que devolvem 404.
