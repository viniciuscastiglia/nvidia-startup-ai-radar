# Pauta corrente — fim de 03/09, base fechada em 30, interface pela frente

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

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

## O que fica para 05/09 à tarde — blocos 3 a 5 do plano

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
