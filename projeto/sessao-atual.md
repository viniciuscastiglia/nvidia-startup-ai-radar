# Pauta corrente — fim de 03/09, base fechada em 30, interface pela frente

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

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
| `--exclusoes` | **9/9** falso negativo · **8/8** falso positivo (era 7/7 · 7/7, com 2 casos reais novos) |
| `--justificativas` | trivial `12/21` · seletor `15/21` — sem regressão |
| `pytest -q` | **81 passed** |
| `python -m src.graph` | roda em fintech, agro, voz, robótica, cripto e rastreabilidade |

**As 22 novas entram como DADO, sem `gabarito:` nem `perfil_alvo`** (D-062) — e isso agora está
**no código**, não só na prosa. Sem o filtro, a precisão cairia de **49% para 24%** com `classe` e
`recall` idênticos: corrupção silenciosa, medida.

**As 4 exclusões do Inception ganharam caso real:** consultoria (Deal) · **capital aberto →
Zenvia** · **cripto → Liqi** · **> 10 anos → Agrotools e Solinftec**. Antes só havia frase
sintética escrita por nós.

## O que 03/09 abriu, e é para amanhã

- **P-23, nova e a mais séria (D-091):** `elegibilidade()` varre **os trechos de evidência**, não
  o documento. A Liqi diz *"oferecer criptomoedas, stablecoins e tokens"* no site, `criptomoeda`
  **já estava na lista de exclusão**, e ela passava — porque a frase não caiu em nenhum trecho
  citado pelo Extractor. **O Diferencial declarado do projeto tem a cobertura do casador de
  dores.** Consertar reintroduz o falso positivo por MENÇÃO que D-085 matou. **Está escrito; não
  se conserta a 4 dias do vídeo.**
- **P-12 virou cena, não número.** A **Core AI** — cujo produto É modelo de crédito com IA — sai
  `non-AI` no briefing. Segue **ACEITA** (D-060: o gargalo é vocabulário), mas o custo agora é
  visível para quem assistir ao vídeo.
- **O seletor de D-086 segue atraído por mobília de página**, agora em dado novo: na NeMo saiu
  *"More Customer Stories / View All Blogs / View All Sessions"*. **Munição para (b) em 04/09.**
- **P-22 ganhou exemplo concreto:** `NEGOCIO` é indexado por TECNOLOGIA, não por dor — NeMo
  recomendada para `custo` traz o texto de `avaliação`. **FAZER em 05/09.**
- **O briefing ainda imprime `ver D-059`** — P-11, uma linha, 05/09.
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

- **RODE O SISTEMA antes de fechar a sessão** (D-083). Em 03/09 ela pagou quatro vezes: a execução
  achou a Core AI saindo `non-AI`, o `NEGOCIO` falando de outra dor, a **Ecotrace recusada por
  usar blockchain para rastrear boi**, e um **falso negativo de rastreabilidade** numa fixture de
  22/08. Nenhum dos quatro aparece em leitura de código.
- **20 minutos de arguição, todo dia** (§4.1). Sem abrir o arquivo: *o que mudei, por quê, e qual
  alternativa descartei.* São **92 decisões**, e as duas de hoje têm alternativa registrada.

> **A lição de método mais cara do dia está em D-091, e é sobre mim:** escrevi na régua um caso
> "rede" com uma frase **que eu mesmo redigi** já contendo o termo que queria testar. Ela deu 8/8
> enquanto a empresa real passava no grafo. **Rede tricotada em volta da resposta não é rede** —
> é o motivo de `origem` ser campo obrigatório em `exclusoes.yaml`, e eu passei por cima da regra
> do próprio arquivo.
