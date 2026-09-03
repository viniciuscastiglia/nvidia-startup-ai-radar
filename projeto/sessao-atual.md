# Pauta corrente — fim de 03/09, base em 16, interface pela frente

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

## O que 03/09 fechou

**A base foi de 8 para 16** (D-090), no timebox de 3 h. **`"fintechs AI-native"` devolve 4
empresas, `"agro"` devolve 2, `"call center e voz"` devolve 2** — as duas primeiras devolviam zero.
**48/48 `url_fonte` resolvem** e a régua reproduz exatamente.

| verificação, ao fim do dia | resultado |
|---|---|
| `seed.py --verificar-urls` | **16 startups · 48 documentos · 48/48 URLs** |
| `avaliar_agentes.py --validar` | exit 0 · **evidência literal ok nas 16** |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1amb · 49%/100%` — **idêntico ao de antes da base** |
| `pytest -q` | **81 passed** |
| `python -m src.graph` | roda nas três consultas novas |

**As 8 novas entram como DADO, sem `gabarito:` nem `perfil_alvo`** (D-062) — e isso agora está
**no código**, não só na prosa: a régua filtra por `gabarito`. Sem esse filtro, a precisão cairia
de **49% para 24%** com `classe` e `recall` idênticos — corrupção silenciosa, medida (D-090).

## O que 03/09 abriu, e é para amanhã

- **A base parou em 16, e o gargalo tem nome: o 3º documento.** Achar a empresa é barato; achar
  três documentos públicos com **2 tipos distintos** é o que mata. Quatro empresas boas caíram já
  coletadas — **Aro** (o `aro.com.br` é de uma fabricante de embalagens de 1943), **Creditas**
  (3 matérias, um tipo só), **alt.bank** (SPA: `/sobre` e `/guard` servem a home), e **ESGreen**,
  que **já é membro do NVIDIA Inception** e só tem 2 documentos públicos.
- **`dados tabulares` continua sem startup.** A P-21 destrava **3 das 7** regras do TAPI, não 4.
- **P-12 virou cena, não número.** A **Core AI** — cujo produto É modelo de crédito com IA — sai
  `non-AI` no briefing. Segue **ACEITA** (D-060: o gargalo é vocabulário), mas o custo dela agora
  é visível para quem assistir ao vídeo.
- **O seletor de D-086 segue atraído por mobília de página**, agora em dado novo: na NeMo saiu
  *"More Customer Stories / View All Blogs / View All Sessions"*. **Munição para (b) em 04/09.**
- **P-22 ganhou exemplo concreto:** `NEGOCIO` é indexado por TECNOLOGIA, não por dor — NeMo
  recomendada para `custo` traz o texto de `avaliação`. **FAZER em 05/09.**
- **O briefing ainda imprime `ver D-059`** — P-11, uma linha, 05/09.

## Decisões do Vinícius

- ✅ **A entrega é INDIVIDUAL**, e o formato é **o repositório + o vídeo** (03/09).
- **O canal de submissão** segue aberto, com prazo **06/09**. É o único item que ninguém conserta
  em 09/09.
- **04/09: escopo da interface (P-06) e se (b) entra** — as duas se decidem com o briefing real na
  frente, e ele existe agora, com 16 empresas.
- O repositório é **público**, então `projeto/` faz parte do entregável — mas só se o README
  apontar para o log. Item 7 do §3.3, junto com o README de 06/09.

## As duas regras que não se negociam

- **RODE O SISTEMA antes de fechar a sessão** (D-083). Em 03/09 ela pagou de novo: a execução
  mostrou a Core AI saindo `non-AI` e o `NEGOCIO` falando de outra dor — nenhum dos dois aparece
  em leitura de código. E o `--verificar-urls` achou um **falso negativo de rastreabilidade** numa
  fixture de 22/08.
- **20 minutos de arguição, todo dia** (§4.1). Sem abrir o arquivo: *o que mudei, por quê, e qual
  alternativa descartei.* São **90 decisões**, e a de hoje tem três alternativas registradas.
