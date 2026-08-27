# Mensagem de abertura — sessão 07

> Copiar e colar num chat novo. Este arquivo guarda **só a próxima sessão**: prompt de abertura
> velho é armadilha, porque carrega diagnóstico que já mudou. Os anteriores estão no git.
>
> **Aperte `Shift+Tab` duas vezes ANTES de enviar**, para entrar em plan mode.

## Por que o alvo mudou de agente

O prompt da 06 pedia a régua antes do Extractor, e estava certo: a régua nasceu e no primeiro dia
derrubou um diagnóstico do próprio projeto. Mas ela também disse onde **não** mexer. Depois do
juiz com LLM medido em três execuções, `classe` continua 3/7 e `confianca` continua 0/6 — os dois
são **insensíveis a melhorar a evidência de entrada**. Não adianta extrair melhor para alimentar
uma camada que decide mal.

O achado que reorganiza a pauta: **o casador perde do classificador trivial em quatro dos cinco
campos.** O valor dele está inteiro na extração; a camada de classificação em cima é pior que
constante (D-052, D-057).

---

```
Sessão 07. Estou em plan mode de propósito — não escreva código de agente nesta
conversa.

Leia, nesta ordem: projeto/sessao-06.md (a pauta que ela deixou e os achados NÃO
pagos), contexto/02-rubrica-ai-native.md (a rubrica que o TAPI não fornece) e
scripts/avaliar_agentes.py (o que se conta e por que a linha trivial existe).

ANTES DE PROPOR QUALQUER COISA, rode a régua — ela custa ZERO chamada de API:

    python scripts/avaliar_agentes.py --baseline
    python scripts/avaliar_agentes.py

Quero os números na sua frente, não os do CLAUDE.md. Eles batem, conferi em 27/08,
mas um plano sobre agente medido por tabela lida é o erro que a revisão da sessão
03 puniu.

O CRITÉRIO DE SUCESSO É FIXADO AGORA, ANTES DO CÓDIGO — é a disciplina de D-055,
que é a única razão pela qual a conclusão sobre o juiz é defensável hoje. E ele
NÃO é "melhorou": nos dois campos que vamos mexer, o sistema atual PERDE do
classificador trivial.

    classe:     casador 3/7  x  trivial 4/7
    confianca:  casador 0/6  x  trivial 3/8

Passar do trivial é o piso. Me diga qual é o alvo e o que fazer se empatar,
escrito antes de medir.

BLOCO 1 — Classifier e Evidence Validator, os gargalos nomeados.

  · confianca: evidence_validator.py:76 toma min() sobre perfil.afirmacoes, e
    essa property (state.py:200) inclui TODAS as dores_observadas. Com ~7 dores
    por startup, "alta" é estruturalmente inalcançável e um extrator que acha
    MAIS dores reais BAIXA a confiança do diagnóstico. É defeito de desenho, não
    de dado — o 0/6 mede isso, não o classificador.

  · classe: classifier.py:52 decide com pontos >= 4 sobre três booleanos, onde
    otimização técnica vale 1. Por isso a Maritaca — quantização QAT, MoE,
    prefill/decode, MFU em B200 — sai AI-enabled: profundidade de infraestrutura
    sozinha não alcança o limiar.

  · maturidade_stack é 6/7. Não encoste.

  Quero as opções de desenho de cada um, com recomendação, e para cada uma a
  alternativa descartada e o motivo — é isso que vira resposta pronta quando
  perguntarem "por que não X?".

BLOCO 2 — o filtro de identidade do Inception. Ele exclui por MENÇÃO, não por
identidade: a Axenya (prospect de prioridade máxima) é recusada por "Integramos
consultoria, dados e operação clínica" e a Freedom porque um PARCEIRO é
"auditoria, consultoria e tributos". Fronteira de palavra não resolve — o termo é
o certo, o sujeito é outro. D-052 achado 3 não pagou isto por assimetria de
risco: um padrão de identidade introduz falso negativo SILENCIOSO. Então o
entregável aqui é a régua que mede falso negativo, antes da correção.

BLOCO 3 — a M3, que vence em 02/09 e hoje tem 8 de 30-50. A sessão 06 mediu o
custo pela primeira vez: ~1h para 5 empresas com 3 documentos. O plano.md
autoriza o corte ("corte o número de empresas, não o rigor"). Preciso decidir o
NÚMERO nesta sessão, com o argumento.

BARATO E VISÍVEL NA SAÍDA: recommendation.py:135 filtra dores com
any(c.tecnologia == citacao.tecnologia for c in citacoes) — como citacao já
pertence a citacoes, a condição é sempre verdadeira, e dores_enderecadas lista
as 7 dores validadas em TODA recomendação.

Antes de eu aprovar, o plano precisa dizer: quantas chamadas de API custa no
total — contando o pytest, que roda o grafo de verdade, e o python -m src.graph,
que custa ~42 por execução e não ~15 —, o que ele NÃO faz, e um BLOCO DE
CONTINGÊNCIA para re-medição depois do /code-review. As sessões 05 e 06 estouraram
o orçamento pelo mesmo motivo: o bloco não orçado foi o de re-medir depois da
revisão.

CORTADO, e o corte é decisão: ajustar o prompt do juiz do Extractor até ele passar
da margem de D-055. Ver D-056 — ajustar até passar não é medir.

Regras: português. Toda decisão vai para decisoes.md no momento em que é tomada.
/code-review high antes de considerar pronto.
```

---

## O que aconteceu em 27/08, entre a 06 e a 07

Sessão curta de higiene, sem código de agente:

- **A sessão 06 inteira foi commitada e empurrada.** Estava fora do git desde 25/08 — 827 inserções
  e 8 arquivos novos. `origin/main` estava no commit de docs de 22/08; hoje tem os 42.
- **Cinco instruções contaminadas corrigidas.** `contexto/05` §4.3 recomendava um reranker morto
  desde 18/05; `.env.example` documentava o embedder morto em 25/08 (os valores já estavam certos);
  `sessao-04.md` guardava a dívida nº 6 sem a anotação de refutação; `CLAUDE.md` dizia 46 testes e
  são 49. E, fora do repo, `~/.claude/settings.json` carregava um bloco `autoMode.environment` que
  descrevia OUTRO projeto — GitLab da faculdade, branch `develop` protegida via merge request —
  em escopo global, portanto lido aqui. Movido para o projeto dono.
- **Duas correções de número dentro do código**, ambas da mesma classe que a sessão 06 diagnosticou:
  o comentário de `USAR_JUIZ_LLM` publicava 58% (n=1) depois de D-056 ter corrigido para a faixa
  50–62% (n=3), e o docstring de `avaliar_agentes.py` ainda afirmava, em presente, que o extrator
  emite o mesmo conjunto de dores para toda startup — a hipótese que o próprio harness refutou
  com discriminação 8/8.

**Contexto de prazo:** a entrega é 09/09 e o vídeo é 07/09, eliminatório e com teto de 7 minutos.
Tudo que ele precisa MOSTRAR tem que existir em 06/09. Os critérios 1 e 3 valem 40 pontos e estão
em nível de stub; o critério 2 vale 20 e está no teto. A sessão marginal rende aqui.

**Depois da 07:** a M3 completa, a interface (5 pontos, uma sessão e não mais), e o README —
que o `plano.md` agenda para 06–07/09 e que hoje ainda diz "Como rodar: *Em breve*" e "*a definir*"
para LLM, embeddings e busca vetorial, todos decididos desde a sessão 01.
