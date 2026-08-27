# Sessão 06 — a régua dos agentes, e o Extractor que empatou

## Sessão 06 — FECHADA em 25/08/2026

A pauta era construir o instrumento antes do agente, e foi o que aconteceu. **9 decisões novas
(D-048 a D-056)**, 5 fixtures curadas, um harness novo, 46 testes.

### O que ficou de pé no fim do dia

| verificação | resultado |
|---|---|
| `pytest -q` | **49 passed** (40 + 9 do filtro de elegibilidade) |
| `seed.py --verificar-urls` | **24/24** URLs resolvem |
| `avaliar_agentes.py --validar` | coerência ok · evidência literal ok · teto do casador **12/12** |
| `avaliar_rag.py --validar` | 24/24, intocado |
| `python -m src.graph "..."` | ponta a ponta, sem `erros` |

---

## O que a sessão entregou, em ordem de importância

### 1. A régua existe, e no primeiro dia já disse algo que ninguém sabia

**O stub é PIOR que o classificador trivial no rótulo do TAPI: 3/7 contra 4/7.** Esse número não
era observável com 3 startups todas `AI-native` — era literalmente a situação que a régua existia
para tornar visível. Ver D-050 (as 8 fixtures), D-051 (o que se conta) e D-052 (os achados).

**A linha de base trivial é obrigatória na tabela.** É o `denso puro` deste critério, e sem ela o
49% de precisão do stub pareceria bom em vez de "17 pontos acima de emitir tudo".

### 2. Um diagnóstico do próprio projeto foi refutado pela medição

O `CLAUDE.md` e a sessão 04 afirmavam que *"o Extractor produz o mesmo conjunto de dores para toda
startup"*. Sobre 8 fixtures diversas ele produz **8 conjuntos distintos**. A afirmação era
verdadeira sobre a base que existia — 3 startups, todas de saúde — e generalizava um artefato da
amostra. É a segunda vez que ampliar o n derruba uma conclusão do projeto; a primeira foi D-039.

O que sobrevive da dívida nº 6 é o outro lado, e ele está medido: **precisão de 49%**. São as
dores ERRADAS que poluem a consulta, não a falta de variação.

### 3. O Extractor com LLM foi medido, empatou, e não entrou

D-055 fixou a margem **antes** de medir: precisão ≥ 64% (os 49% do casador + 0,15). A faixa em
**três execuções** é **50–62%** — nem o melhor caso alcança. `USAR_JUIZ_LLM = False` é resultado de
medição, não esquecimento. Ver D-056.

**A primeira redação desta conclusão foi publicada com n=1**, num projeto que já tinha escrito
que *"número de geração se reporta em três execuções ou não se reporta"*. As três execuções foram
rodadas depois do code review; a conclusão sobreviveu e ficou mais forte, mas a régua tinha sido
aplicada a mim mesmo pela metade.

**O achado que vale mais que o número:** a primeira versão do prompt listava os modos de falha da
busca por palavra-chave e terminava com *"na dúvida, reprove"*. Precisão **22%**, recall **20%**,
cinco das oito startups viraram `non-AI`. O diagnóstico com duas amostras mostrou o modelo
devolvendo **a regra nº 2 do próprio prompt** como justificativa, e escrevendo que uma frase
*"pode ser interpretado como preocupação com otimização de inferência"* para concluir, na mesma
resposta, que nenhuma frase sustentava. **Num 8b, uma lista de erros a evitar vira um menu de
desculpas prontas.** Um ajuste — critério positivo primeiro — levou a 58% e 89%.

**Um ajuste só, e declarado como único antes de rodar.** Ajustar até passar de 64% não seria
medir, seria ajustar ao gabarito, e destruiria a régua no dia em que ela nasceu.

### 4. Os dois achados de code review da sessão 05 que produziam saída errada foram pagos

- **D-048** — `"token"` fora da lista de cripto, e a exclusão passa a casar por **fronteira de
  palavra**. O gatilho já estava no repositório: `tests/test_grafo.py:102` monta um documento com
  "custo por token", e aquela startup era reprovada em toda execução do `pytest` sem que nenhuma
  asserção olhasse. Escrito em red-green, e **em par** com o teste que impede que a correção seja
  apagar a regra.
- **D-049** — `Elegibilidade.evidencias` deixa de nascer vazia. Era a única conclusão do sistema
  sem `list[Evidencia]`, sob o rodapé que promete o contrário.

---

## O que a régua achou e a sessão NÃO pagou

**O filtro do Inception exclui por MENÇÃO, não por identidade.** Foi a evidência que D-049 passou
a anexar que tornou isso legível:

- **Axenya** — o prospect de prioridade máxima — recusada por *"Integramos **consultoria**, dados e
  operação clínica"*. Ela usa consultoria; não é uma consultoria.
- **Freedom AI** recusada porque um **parceiro** (Grant Thornton) é *"auditoria, **consultoria** e
  tributos"*. A palavra não se refere à startup.
- **Deal** recusada corretamente: *"A Deal **é a consultoria** de IA"*.

**Fronteira de palavra não resolve** — é isso que separa este caso de D-048. O termo é o certo; o
**sujeito** é outro. A decisão de não consertar com heurística está em D-052, achado 3, e o motivo
é assimetria de risco: um padrão de identidade introduz **falso negativo silencioso** (se a frase
que afirma a identidade não estiver entre as evidências recortadas, a Deal deixa de ser excluída e
o Diferencial para de funcionar sem ninguém notar). Falso positivo aparece no briefing; falso
negativo não aparece em lugar nenhum.

**Também não pago:** o filtro tautológico de `recommendation.py:135` — `dores_enderecadas` ainda
lista as 7 dores validadas em toda recomendação, e isso está visível na saída do grafo.

---

## O code review derrubou três afirmações desta sessão (D-057)

`/code-review high` devolveu 8 achados; **6 foram pagos**. Três merecem estar aqui porque não são
polimento — são afirmações desta sessão que estavam erradas:

1. **A fronteira de palavra de D-048 estava ancorada dos dois lados e desligou o plural.**
   `\bconsultoria\b` não casa "consultorias". D-048 tinha trocado um falso positivo visível por um
   **falso negativo silencioso**, que é a troca ruim — e o comentário da própria decisão afirmava o
   contrário. Corrigido para âncora só no início, com teste dos dois lados.
2. **A justificativa do desempate copilot/autopilot citava uma medição inexistente.** Eu escrevi
   que a RD Station "empatava 1×1"; ela é **3×1** e sai autopilot com os dois operadores. Li a
   lista de TERMOS que casaram como se fosse a contagem de EVIDÊNCIAS. Medido depois: `>=` e `>`
   dão o mesmo placar. A mudança fica por argumento conceitual, declarado como tal.
3. **A régua estava medindo `motivo_exclusao` errado, e publicava 1/1.** `null` era lido como "não
   medido" mesmo com `elegivel: true`, quando significa "nenhum motivo esperado". Axenya e Freedom
   AI, excluídas pelo rótulo errado, apareciam numa coluna limpa. Corrigido: **5/7**.

**E a correção nº 3 mudou a leitura da sessão.** Com a régua auditada, o casador perde do
classificador trivial em **quatro dos cinco campos** — classe 3/7×4/7, confiança 0/6×3/8,
elegível 5/7×6/7, motivo 5/7×6/7 — e só ganha em dor. A afirmação certa não é "o stub é pior que o
trivial": é **"o valor do casador está inteiro na extração de dores, e a camada de classificação
em cima dele é pior que constante"**. É mais forte e mais acionável, e só apareceu porque a régua
foi auditada em vez de ser confiada.

Achados **não pagos**, com o motivo: a exclusão por menção (assimetria de risco, D-052 achado 3) e
o `min()` do Evidence Validator — a este o review acrescentou o diagnóstico que faltava: `alta` é
**estruturalmente inalcançável**, porque o mínimo é tomado sobre TODAS as afirmações, incluindo
toda `DorObservada`. Consequência perversa: **um extrator que acha mais dores reais BAIXA a
confiança do diagnóstico**. O 0/6 da régua está medindo isso, não a qualidade do classificador.

---

## Observação sobre a dívida nº 6, com a ressalva de atribuição

`python -m src.graph "startups brasileiras de saúde usando IA"` **não recomenda mais Morpheus nem
CUDA Toolkit**. A Laura Networks recebe Inception, TensorRT-LLM e NVIDIA Healthcare; a Axenya
recebe NVIDIA Healthcare em primeiro lugar.

**A atribuição não é limpa e não deve ser vendida como se fosse:** entre a observação da sessão 04
e esta, a stack de recuperação inteira foi trocada (D-046, o EOL de 25/08). A melhora é real e
observável; *de quem* ela é, esta sessão não mediu.

---

## Orçamento de API — orçado ~406, teto 450, **gasto ~516. Estourou.**

| bloco | orçado | gasto |
|---|---|---|
| 0 aquecimento · 1 curadoria · 2 `--validar` · 3 `--baseline` | 0 | **0** |
| 4 Extractor com LLM, 1ª medição | ~64 | 52 |
| 4b diagnóstico das 2 amostras (não orçado) | 0 | 2 |
| 5 Extractor com LLM, 2ª medição | ~64 | 52 |
| **5b re-medição × 3 depois do code review (NÃO ORÇADA)** | 0 | **156** |
| 6 `--motor ponta-a-ponta` | ~50 | **0 — não rodado** |
| 7 `pytest -q` | ~195 (×3) | ~128 (×2) |
| 8 `python -m src.graph` | ~30 (×2) | ~126 (×3) |
| **total** | **~406** | **~516** |

**O estouro tem duas causas e as duas são minhas:**

1. **O bloco 5b não estava no plano: 156 chamadas, 30% do orçamento.** Ele existiu porque o code
   review mostrou que a régua media `motivo_exclusao` errado — e publicar a coluna do juiz medida
   com a régua velha ao lado das colunas medidas com a régua nova seria repetir exatamente o erro
   que a revisão da sessão 03 puniu (*"três documentos com números diferentes na mesma régua"*).
   Re-medir foi certo; **não ter orçado uma contingência para re-medição pós-review foi o erro**,
   e é a segunda sessão seguida em que o bloco não orçado é o que estoura.
2. **`python -m src.graph` foi rodado 3 vezes e orçado como 2**, a ~42 chamadas cada — mais caro
   por execução do que a estimativa, porque o fan-out roda 3 startups com ~7 dores cada.

**O que funcionou:** a contagem seca do custo ANTES de gastar (52 previstas, 52 gastas, erro zero),
e os blocos 0 a 3 custarem zero e entregarem a régua inteira.

**Lição para o próximo orçamento, somada à da 05:** reservar um bloco de contingência para
**re-medição depois do code review**. Achado de review que invalida uma medição não é exceção —
aconteceu nas duas últimas sessões.

## Pauta da próxima sessão

**A régua diz onde mexer, e não é mais no Extractor.** Depois do juiz com LLM, `classe` continua
3/7 e `confianca` continua 0/6 — os dois são insensíveis a melhorar a evidência de entrada:

**Bloco 1 — o Classifier e o Evidence Validator, que agora são os gargalos nomeados.**
- `classe` sai de aritmética de pontos (`>= 4` é AI-native) sobre três sinais booleanos. Com a
  Maritaca — quantização QAT, MoE, prefill/decode, MFU em B200 — saindo `AI-enabled`, o problema é
  o limiar, não a evidência.
- `confianca` é `min()` sobre TODAS as afirmações do perfil. Como sempre existe uma afirmação
  fraca, o diagnóstico é `baixa` para todo mundo — 0/6 na régua. Um mínimo sobre um conjunto que
  cresce converge para "baixa" por construção, e isso é defeito de desenho, não de dado.
- `maturidade_stack` é 6/7 e não precisa de ninguém.

**Bloco 2 — o filtro de identidade do Inception**, com a régua para medir falso negativo, que é o
risco que impediu a correção hoje.

**Bloco 3 — a M3.** 30 a 50 empresas, vencida em 02/09. As 8 fixtures contam, e a sessão provou
que 5 empresas com 3 documentos cada custam cerca de uma hora de coleta — o que torna a estimativa
de "sumidouro do projeto" mensurável pela primeira vez.

**CORTADO, e o corte é decisão:** ajustar o prompt do juiz até ele passar da margem. Ver D-056.
