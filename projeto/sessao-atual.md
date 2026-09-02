# Pauta corrente — fecha a sessão 09, abre a revisão do plano final

> Este é o único arquivo de sessão do repositório. Ele guarda **o que está aberto**, não o que já
> aconteceu — o que aconteceu está em `decisoes.md` e no git.
>
> **A próxima sessão é uma REVISÃO DO PLANO em plan mode.** A seção "o que eu considero frágil"
> lista o que quem fez o plano acha que não se sustenta — é por ali que a revisão rende mais.

**Documento de estudo:** [Anatomia do Radar](https://claude.ai/code/artifact/dc527bde-f149-49f8-87a5-3105197cc2e2)
**Mapa e plano:** [O que falta no Radar](https://claude.ai/code/artifact/7e6e13e8-e7b5-4f5a-a2ae-85ff247eb007)

## A BIFURCAÇÃO que a próxima sessão precisa resolver

Tudo o mais no plano depende disto, e ainda não está escrito em decisão nenhuma:

> **Este projeto é um pipeline determinístico, ou um sistema multi-agente com julgamento por LLM?**

Hoje ele é **determinístico** — nenhum dos 8 agentes chama LLM em produção. Isso não foi preguiça:
foi medido quatro vezes (D-056 empatou; D-059, D-060 e D-075 reprovaram). **Mas as quatro medições
foram feitas em modelos que não existem mais** — três no 8B, três no `nemotron-3-nano` que morreu em
01/09. E D-072 é o precedente que assusta: **o mesmo juiz que empatou no 8B PASSOU no modelo
seguinte.**

Os dois desfechos são bons, e são bons de formas diferentes:

- **Se o LLM ganhar no modelo novo:** o Entregável 1 ("sistema multi-agente") deixa de ser topologia
  e passa a ser julgamento; `classe` pode se resolver por flag em vez de por curadoria de base; e o
  juiz do Extractor sai da gaveta.
- **Se perder de novo:** o projeto ganha uma afirmação rara e forte — *"julgamento por LLM foi
  testado em três gerações de modelo, contra linha de base trivial e com critério fixado antes, e
  perdeu nas três"*. Isso é mais defensável que qualquer arquitetura.

**O que não é aceitável é não saber** — e hoje não se sabe, porque o instrumento que produziu a
resposta morreu. Custo estimado: ~200 chamadas. Risco: o modelo novo **emite raciocínio dentro do
`content`**, o que pode exigir ajuste de prompt antes de qualquer número valer.

## Estado verificado em 01/09, no fim da sessão

| verificação | resultado |
|---|---|
| `smoke_nvidia.py` | **3/3** — chat (modelo novo), embedding 676 ms, rerank Cohere 1177 ms |
| `pytest -q` | **53 passed**, 168 s |
| `avaliar_agentes.py` | `precisão 49% · recall 100% · discriminação 8/8 · proibidas 10` — bate com D-074 |
| `avaliar_agentes.py --exclusoes` | `7/7` falso negativo · `2/7` falso positivo — bate com D-071 |
| ponteiros `D-NNN` | zero quebrados |

## O que mudou nesta sessão

- **D-078** — o barema saiu do lugar de função objetivo. O que ordena o trabalho passou a ser o
  defeito do sistema para quem vai usá-lo. Documentação, método e 11 docstrings reescritos; log
  comprimido em três entradas; **zero mudança de comportamento**.
- **D-079** — **quarto EOL**: `nemotron-3-nano-30b-a3b` morreu às 09:00 UTC de 01/09, com aviso
  formal do fornecedor no corpo do 410. Trocado por `nemotron-3.5-lightning-30b-a3b`. E o achado de
  D-070 foi **corrigido**: "listado mas morto" eram três coisas somadas — 1 morte real contra 7
  entitlement, o que inflava o risco de EOL do projeto por um fator de 7.

## A auditoria contra a spec — feita em 01/09

**Completo e conferido item a item:** schema mínimo (9 campos em `startups`, 7 em `documentos`) ·
os **7 campos obrigatórios** do output, anotados um a um em `state.py:316` · as **16 tecnologias** ·
os **9 passos** do RAG, incluindo o passo 9 · os **8 agentes** registrados no grafo · diversidade de
perfis (4/3/1) · rastreabilidade com `url_fonte` verificada.

**Conformidade com as tecnologias recomendadas do TAPI: 4 de 4** (verificado em 01/09 no documento
original, §5.3). pgvector — alternativa explicitamente permitida a Qdrant · PostgreSQL · `bm25s` ·
**Cohere `rerank-v3.5`**. **O TAPI não recomenda LLM nenhum**, então a escolha do modelo dos agentes
não desobedece nada — não há recomendação a seguir ali.

**As três lacunas, todas dentro do escopo:**

1. **Volume: 24 documentos contra os 90-240 que o TAPI pede.** 8 startups de 30-80, cada uma com
   exatamente o mínimo de 3 documentos. É 27% do piso.
2. **`query_planner` é o único agente sem teste E sem régua.** 63 linhas de casamento de substring,
   e `estrategia_analise` é uma **string literal constante** que nada lê — enquanto o TAPI nomeia
   *"…e define a estratégia de análise"* como responsabilidade dele.
3. **Nenhum dos 8 agentes chama LLM em produção.** `USAR_JUIZ_LLM = False`,
   `JULGAR_SUSTENTACAO = False`, e `nvidia_rag` faz só recuperação. Cada escolha é *medida*
   (D-056 empatou; D-059, D-060 e D-075 reprovaram) — **mas todas as medições estão em dois modelos
   mortos**, e D-072 é o precedente de que a conclusão vira no modelo seguinte.

## A fila, em ordem de quanto o defeito custa a quem usa

1. **Re-medir o que foi medido em modelo morto.** `--juiz` (D-072), `--rubrica` (D-060),
   `--confianca-diagnostico` (D-059), `--geracao` (P-15). Decide se o sistema é determinístico por
   medição ou multi-agente com julgamento. **Os dois são defensáveis; não saber não é.**
2. **Régua do motor de recomendação (P-10)** + a régua passar a chamar `recommendation.node()` em vez
   de espelhar o filtro por fora. As **sete regras de exemplo do TAPI** são gabarito pronto.
3. **P-17, o eixo de admissão** — com as duas colunas novas e critério fixado antes. Ver a conta em
   D-077: admitir tudo dá 100%/49%, e o recall só se move se a régua contar em outro lugar.
4. **`justificativa_negocio` sai do LLM** — hoje vem de tabela cobrindo 5 de 16 tecnologias.
5. **O `min()` da `confianca`** — 0/6 constante: um campo no briefing carregando zero informação.
6. **`query_planner` + P-14.**
7. **A base.** Ver a tensão não resolvida abaixo.
8. **`classe` 3/7** — depende da base, ou de a re-medição do item 1 virar D-060.

## O que eu considero FRÁGIL no plano — é aqui que a revisão rende

**Escrito por quem fez o plano, para ser contestado.**

- **O maior risco estrutural: interface e vídeo em sessões consecutivas, sem folga entre elas.** Se a
  interface escorregar, não há demo — e o vídeo é o único prazo imóvel. **É ponto único de falha
  colado no prazo**, e nenhuma outra parte do plano tem essa forma.
- **A tensão do volume não está resolvida, está escondida.** D-062 fixou timebox de 3h com piso em
  20. Eu "corrigi" para 30 startups / 90 documentos por argumento de spec. Mas 22 novas × 3
  documentos com `url_fonte` real e verificada em 3h é otimista. **Se render 20, a correção só trocou
  "abaixo do alvo" por "estouro de timebox".** Precisa ser decidido de verdade, não herdado.
- **A sessão de re-medição pode comer a sessão inteira.** São ~200 chamadas, e o modelo novo **emite
  raciocínio dentro do `content`** — pode exigir ajuste de prompt antes de qualquer medição valer.
  A alternativa é aceitar o pipeline determinístico e gastar o tempo na base e na interface.
- **`query_planner`: vale uma sessão?** A alternativa de 10 minutos é tirar a promessa do diagrama.
  Fazer o agente de verdade é melhor — mas é a única peça do plano cujo custo eu não estimei sobre
  nada.
- **P-06 não está decidida** e a interface tem uma sessão. Escopo não decidido mais prazo curto é a
  combinação que estoura.
- **Só existe UM fornecedor de LLM, e o Grok está parado há quatro dias.** D-067 registrou, em 28/08,
  que o Grok *"foi sugerido pela liga e está pré-autorizado"* e que **não foi descartado por mérito —
  não foi testado, porque a chave não existia**. Desde então o modelo escolhido morreu e a conta se
  provou sem acesso a **nenhum** modelo de terceiros (0 vivos em 12).
  **Isto tem a mesma forma do episódio do Cohere:** lá, a lição não foi "obedeça o TAPI" — foi que a
  opção recomendada também era a mais robusta, e depender de um fornecedor só custou uma migração sob
  pressão. Uma cadeia de fallback **entre modelos da NVIDIA** não resolve: não protege contra
  entitlement nem contra o tier inteiro. **A cadeia certa é entre PROVEDORES**, `src/config.py` já
  isola o provedor, e o segundo provedor já está pré-autorizado. **O bloqueio é a chave, não o
  código.**

## Dívidas declaradas

- **`README.md` afirma coisas falsas hoje** — diz *"a definir"* para LLM, embeddings, busca vetorial
  e reranking, todos decididos (D-016, D-046, D-068, D-079), e *"Em breve"* para como rodar. A árvore
  não lista `src/`, `scripts/`, `data/` nem `tests/`. Conserto na M6; critério de pronto é
  **verdadeiro e suficiente para alguém rodar sozinho**.
- **Interface web (P-06)** — não começada, e é a única superfície pela qual quem não lê código julga
  o sistema.
- **Os números de D-072, D-074 e D-075 não valem** até serem refeitos no modelo vivo.

## Perguntas para a liga — a primeira virou BLOQUEANTE

1. **A chave do Grok.** É a única pergunta que desbloqueia trabalho: o Grok foi sugerido pela própria
   liga e está pré-autorizado, e é o **único caminho fora do `build.nvidia.com`** — o catálogo que já
   matou quatro modelos e não avisa. Pedir agora; se sair, é uma sessão curta.
2. Vocês vão **executar** o projeto na avaliação, e com chave de quem? O catálogo aposentou o LLM em
   01/09 sem aviso prévio de nenhum tipo, e a conta gratuita não alcança nenhum modelo de terceiros.
3. O reranker hospedado da NVIDIA saiu do ar e o projeto migrou para o Cohere, que o próprio TAPI
   recomenda — confirmam que é aceitável?
4. Aviso de que o catálogo lista modelos que a conta não pode chamar, e que o EOL só é descoberto por
   chamada real, depois do fato.
