# Pauta corrente — fim de 03/09, base fechada em 30, interface pela frente

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

## ⚠️ LEIA PRIMEIRO — a cota mensal do Cohere ACABOU (D-093)

`HTTP 429`: *"Trial key, limited to **1000 API calls / month**"*. **Não é o teto de 10 req/min,
que recupera em 26 s — é a cota do mês.** A causa foi esta sessão: ~15 runs do grafo e 5 de
`pytest`, e cada run do grafo faz 20-30 chamadas sequenciais de rerank.

**O que fazer, e já está medido — não é suposição:**
- **`RERANK_PROVEDOR=nenhum` roda tudo.** Grafo ponta a ponta com recomendação, evidência e
  fonte; **`pytest` 81 passed em 6,5 s** (contra 150-460 s com o Cohere ligado — o throttle era o
  gargalo do suite inteiro, e ninguém sabia porque ninguém tinha rodado sem ele).
- **O que se perde está medido:** denso puro faz **95% r@1 e 100% r@3** (D-064). O reranking
  comprava o critério estrito, não a capacidade de responder.
- **Assuma que a cota NÃO volta antes de 09/09.** Planejar contando com isso repete o erro de
  D-015 (assumir sem verificar).
- **Para o vídeo de 07/09 isso é vantagem narrativa, não desculpa:** o provedor está isolado em
  `src/config.py` desde o começo, e gravar com o passo 7 desligado **demonstra a arquitetura** que
  três EOLs compraram. O número honesto ao lado é o `95% r@1` do denso puro.
- **Decisão sua:** chave de produção paga, se quiser o caminho completo no vídeo. Abrir outra
  trial foi **descartado** — é contornar o teto do fornecedor por outra porta, num processo
  seletivo.
- **Regra nova:** `RERANK_PROVEDOR=nenhum` é o **default de desenvolvimento**. O Cohere entra
  quando se quer medir o passo 7, e aí a chamada é deliberada.

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
| `python -m src.graph` | roda em fintech, agro, voz, robótica, cripto e rastreabilidade |

**As 22 novas entram como DADO, sem `gabarito:` nem `perfil_alvo`** (D-062) — e isso agora está
**no código**, não só na prosa. Sem o filtro, a precisão cairia de **49% para 24%** com `classe` e
`recall` idênticos: corrupção silenciosa, medida.

**As 4 exclusões do Inception ganharam caso real:** consultoria (Deal) · **capital aberto →
Zenvia** · **cripto → Liqi** · **> 10 anos → Agrotools e Solinftec**. Antes só havia frase
sintética escrita por nós.

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
- **O canal de submissão** segue aberto, com prazo **06/09**. É o único item que ninguém conserta
  em 09/09.
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
