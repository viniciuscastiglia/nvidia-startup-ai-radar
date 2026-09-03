# Pauta corrente — 03/09, manhã livre, base pela frente

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.

## O que hoje pede

**Um item de código: a base 8 → 30.** Ordem `fintech → agro → demais`, **timebox de 3 h**, parar em
20 com fintech e agro dentro já é sucesso. D-062 dá a estrutura: as 8 atuais mantêm gabarito, as 22
novas entram **como dado, sem gabarito**, com `url_fonte` real. `scripts/coletar.py` puxa o texto,
`seed.py --verificar-urls` confere.

> **A ordem de "demais setores" ganhou critério em 03/09 (D-088):** das 7 regras de exemplo do TAPI,
> só `Saúde` e `governança em agentes` têm startup na base. Faltam **voz/call center**, **dados
> tabulares** e **robotics/simulação** — e cada uma que entrar viabiliza a régua da P-21, que é a
> única medição de relevância de recomendação que este projeto pode ter.

**Opcional, para a manhã livre:** cachear as 16 fontes do RAG (~1 h, hoje é item de 06/09). O único
argumento para puxar: hoje o corpus está **validado 24/24**, e cachear depois obriga a revalidar.

**PORTÃO 03/09:** o grafo roda · `"fintechs AI-native"` devolve resultado · nenhuma justificativa
técnica cita empresa alheia. *A 1ª e a 3ª já estão satisfeitas em 03/09; a 2ª depende da base.*

## Estado verificado em 03/09, antes de qualquer edição

| verificação | resultado |
|---|---|
| `pytest -q` | **81 passed** |
| `smoke_nvidia.py` | **3/3** — o chat respondeu em **7,9 s** (a faixa de D-080 é mais larga por baixo) |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1amb · 49%/100%` |
| `--exclusoes` · `--justificativas` | `7/7 · 7/7` · trivial `12/21`, seletor `15/21` |
| **clone limpo do GitHub** | **roda ponta a ponta, exit 0** — corpus com a contagem medida, gabarito **24/24** (D-089) |

**Todos reproduzem o que 02/09 documentou.** Nenhum número do log é falso.

## O que 03/09 abriu, e não é de hoje

- **P-22** — `justificativa_negocio` é stub em **11 de 16** tecnologias. Campo 3 dos 7 obrigatórios,
  irmão do que D-086 consertou. **FAZER em 05/09** (D-088).
- **O briefing imprime `ver D-059`** — `evidence_validator.py:210` monta, `briefing.py:258` imprime.
  O gerente lê, o vídeo mostra. Entrou na **P-11**, e tirar o ponteiro **custa uma linha** e não
  depende da decisão maior (D-089).
- **O seletor de D-086 é atraído por barra de badges** — `Python | PyTorch | NumPy` é a linha mais
  densa da página, e densidade é a heurística. Não é regressão; é o mecanismo da falha restante.
  Munição para a decisão de **(b)** em 04/09 (D-089).
- **A deriva do corpus é diária, medida** — o clone baixou hoje e o hash difere do de ontem. O
  gabarito sobreviveu porque a deriva bateu em ruído, não em âncora (D-089).

## Decisões do Vinícius

- ✅ **A entrega é INDIVIDUAL**, e o formato é **o repositório + o vídeo** (03/09).
- **O canal de submissão** segue aberto, com prazo **06/09**. É o único item que ninguém conserta
  em 09/09.
- **04/09: escopo da interface (P-06) e se (b) entra** — as duas se decidem com o briefing real na
  frente, não antes.
- **Novo:** o repositório é **público**, então `projeto/` faz parte do entregável. É ativo — mas só
  se o README apontar para o log. Item 7 do §3.3, junto com o README de 06/09.

## As duas regras que não se negociam

- **RODE O SISTEMA antes de fechar a sessão** (D-083). Duas auditorias estáticas não acharam o que
  uma execução achou em uma hora — três vezes.
- **20 minutos de arguição, todo dia** (§4.1). Sem abrir o arquivo: *o que mudei, por quê, e qual
  alternativa descartei.* São **89 decisões**, e as duas últimas nasceram numa sessão com IA.
