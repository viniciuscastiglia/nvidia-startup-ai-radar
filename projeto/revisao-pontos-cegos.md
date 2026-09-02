# Envelope lacrado — a lista de quem fez o plano

> **NÃO ABRA ESTE ARQUIVO ANTES DE TER ESCRITO A SUA PRÓPRIA LISTA.**
>
> Este arquivo existe separado do `sessao-atual.md` por um motivo específico: uma lista de pontos
> fracos entregue *antes* da análise não informa a revisão — ela a **substitui**. O revisor confere
> os itens que recebeu, não encontra nada além, e conclui que o plano está sólido. O nome disso é
> ancoragem, e o custo dela é exatamente a sessão que este arquivo deveria ajudar.

## O protocolo

1. **Fase independente.** Leia `sessao-atual.md` (sem esta lista), `plano.md`, D-078 e D-079, e o
   código que precisar. **Rode o que precisar rodar** — a lição de 01/09 é que uma sessão inteira de
   análise estática não achou o que 4 segundos de `smoke_nvidia.py` acharam. Escreva **a sua** lista
   do que não se sustenta no plano.
2. **Só então abra a lista abaixo.**
3. **Compare, e a leitura da comparação é o que vale:**
   - **nos dois** → confirmado, prioridade alta
   - **só na minha** → ou eu estava errado, ou você não olhou ali. Decida qual
   - **só na sua** → **estes são os mais valiosos da sessão**, porque são exatamente os que a minha
     lista teria suprimido se você a tivesse lido primeiro

---

## O que eu NÃO verifiquei — os limites da minha própria auditoria

Antes da lista, o mais útil: **o que sustenta as minhas conclusões, e o que não sustenta.** Isto
não é modéstia, é o mapa de onde procurar o que passou.

- **Nunca rodei o grafo ponta a ponta.** Não executei `python -m src.graph "..."` uma única vez.
  **Tudo o que eu afirmei sobre a qualidade da saída veio de documento, não de execução** — incluindo
  o exemplo do *"Join our ecosystem"*, que eu li em `sessao-atual.md` e nunca vi sair. **Rodar isso é
  provavelmente a primeira coisa a fazer.**
- **Não rodei `avaliar_rag.py`.** O `e@1 = 79%` que eu cito é de D-068, medido em 28/08. E o passo 8
  depende do LLM, que **mudou hoje** — esses números estão garantidamente velhos.
- **Não li a maior parte do código.** Li fragmentos por `grep`. `briefing.py` (243 linhas),
  `classifier.py` (228) e `extractor.py` (249) eu **nunca abri inteiros**.
- **Não auditei a qualidade dos testes.** Verifiquei que 53 passam e quais agentes aparecem em quais
  arquivos. **Não verifiquei se testam a coisa certa** — cobertura por menção não é cobertura.
- **Não olhei a interface concretamente.** Nenhum esboço, nenhum escopo, nenhuma decisão de P-06.
  Falo dela no plano com uma sessão alocada e zero evidência de que cabe.
- **Eu escrevi o plano**, então não enxergo as suposições de enquadramento dele — por exemplo, que o
  trabalho se divide em ~6 sessões de um tema cada. Isso pode simplesmente estar errado.

---

## A minha lista

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
