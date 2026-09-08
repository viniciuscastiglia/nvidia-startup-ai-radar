# Envelope lacrado — a avaliação de 08/09, para conferir DEPOIS

> **NÃO LEIA ISTO ANTES DE ESCREVER A SUA.**
>
> Este arquivo contém as notas que uma auditoria de 08/09/2026 atribuiu a cada critério do TAPI,
> com a justificativa de cada uma. **Lê-lo antes de avaliar transforma auditoria em confirmação** —
> é a mesma razão que faz `revisao-pontos-cegos.md` existir, e a mesma disciplina que faz este
> repositório fixar critério antes de medir.
>
> **Sequência correta:** rode o repositório como um avaliador externo rodaria · escreva a SUA nota
> por critério, com justificativa · **só então** abra este arquivo e compare. Onde divergir, a
> divergência é o achado — e ela pode ser contra o que está escrito aqui.
>
> **Quem escreveu isto tinha um conflito de interesse:** a mesma sessão que avaliou também
> consertou (D-113 a D-119). Ninguém checou os consertos de forma independente. Trate as notas
> abaixo como HIPÓTESE a derrubar, não como referência.

---

## Como esta avaliação foi produzida

Clone limpo em diretório separado · `pytest` · grafo ponta a ponta · as 4 réguas · os ~21 comandos
que o README e o `CLAUDE.md` anunciam · leitura do TAPI em `contexto/01-tapi.md`.

## As notas (escala do TAPI: 2 = cumpre · 3 = cumpre bem, com decisão consciente · 4 = supera)

| # | critério | peso | nota | a razão em uma linha |
|---|---|---|---|---|
| 1 | multiagente LangGraph | 20 | **3** | topologia é 4 (`Send`, `defer`, `retry_policy`, `error_handler` por nó); a SAÍDA dos agentes não é — `classe 3/7` perde da trivial e `confianca` é 0/6 |
| 2 | RAG com reranking | 20 | **4** | os 9 passos como módulos separados, gabarito com **5 perguntas sem resposta**, corpus versionado que reproduz offline. O passo 9 é o que quase ninguém entrega |
| 3 | motor de recomendação | 20 | **3** | os 7 campos são garantia de TIPO, o que é 4; o CONTEÚDO de dois deles não é (mobília de página na justificativa técnica, `prioridade` nunca `alta`) |
| 4 | interface web | 5 | **4** | SSE ao vivo, exportação, vitrine do passo 7 mostrando as duas ordens, porta do passo 8, guarda de concorrência com 409 |
| 5 | vídeo | 20 | — | fora do escopo desta avaliação |
| 6 | diferencial | 5 | **4** | a recusa fundamentada em três lugares independentes, medida dos dois lados e nomeada no README |
| 7 | repositório e documentação | 10 | **4** | clone limpo reproduz · 119 decisões com alternativa descartada · **cada número afirmado reproduz** |

**Sem o vídeo: ~72 dos 80 pontos disponíveis.**

## Os três eliminatórios que foram verificados por execução

- **executa:** `python -m src.graph` sai com exit 0 e briefing completo · `pytest` **134 passed**
- **compreensão:** 119 decisões com a alternativa descartada, incluindo hipóteses REPROVADAS
- **prazo e autoria:** ok

## O que segura os critérios 1 e 3 em 3, e não sobe

Nenhum destes tem conserto disponível — todos exigem re-coleta da base ou redesenho:

| defeito | causa medida |
|---|---|
| `classe 3/7`, perdendo da trivial (4/7) | **D-119**: as 4 `AI-native` do gabarito saem `AI-enabled`; o teto do conserto é +1 (D-060) |
| `confianca` 0/6 → `prioridade` **nunca** `alta` (0 de 89) | `min()` → `data_publicacao` ausente em 86 de 93 (P-11, P-25) |
| `justificativa_tecnica` com mobília de página | a régua diz 71% e a produção discorda — contradição não resolvida (D-086, D-101) |
| relevância 38% contra 44% da trivial | dor a 49% de precisão alimenta a consulta (D-105) |
| filtro do Inception vê 10,6% do texto | varrer tudo quebra o veto de terceiro, medido em D-102 |

## Onde a auditoria de 08/09 pode ter errado — comece por aqui

1. **A nota 4 do critério 4 viu só a tela inicial.** Nenhuma consulta foi rodada PELA interface: a
   trilha do fan-out, o dossiê, a evidência clicável e a vitrine do passo 7 **não foram vistos
   funcionando**. Se algo ali quebra, a nota cai e ninguém percebeu.
2. **`run-recomendacoes.json` tem 30 empresas e a base tem 32** (D-118). `--regras-tapi` reporta
   38% × 44% sobre um run que não cobre mais a base inteira.
3. **Duas propostas desta sessão morreram na medição** — o filtro de proposta de valor (7% de
   cobertura) e a poda de gatilhos (zero casos nas 8 do gabarito). **Se algo mais que ela propôs
   entrou sem medição, é aqui que está.**
4. **D-115 e D-117 mudaram comportamento no mesmo dia.** A Solinftec passou a ser recusada e o
   verificador de URL parou de reprovar 403/429. As duas foram medidas, mas pela mesma sessão.
5. **A latência do fornecedor é de HOJE:** mediana 216,9 s (D-116). Se mudou, `LLM_TIMEOUT=300`
   pode estar errado nos dois sentidos.
