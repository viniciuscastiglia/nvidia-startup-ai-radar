# Pauta corrente — sessão 09

> Este é o único arquivo de sessão do repositório. Ele guarda **o que está aberto**, não o que já
> aconteceu — o que aconteceu está em `decisoes.md` e no git. Fechamento de sessão anterior não
> entra aqui: vira decisão no log, ou não vale registro.

**Documento de estudo:** [Anatomia do Radar](https://claude.ai/code/artifact/dc527bde-f149-49f8-87a5-3105197cc2e2)

## O diagnóstico do núcleo (levantado em 28/08)

Três causas concretas, e duas são a mesma classe de erro:

1. **`confianca` 0/6 é constante, não impreciso.** `evidence_validator.py:122` faz `min()` sobre as
   confianças das afirmações: uma afirmação fraca derruba o diagnóstico inteiro, e quanto mais
   evidência o sistema junta, pior fica. **O agente piora quanto melhor trabalha.**
2. **Os gatilhos de dor casam o domínio do PRODUTO, não o da IA.** `observabilidade` responde por 5
   das 10 dores proibidas, e o que dispara é *"monitoramento do **sistema fotovoltaico**"*
   (SunnyHUB), *"**dashboards** que mensuram a qualidade do atendimento"* (Doutor-AI). Nenhum fala
   de instrumentação de IA.
3. **`classe` erra 4 vezes, todas na mesma direção** — `AI-native` → `AI-enabled`. Gargalo de
   vocabulário: 7 das 8 fixtures têm profundidade técnica zero.

**O padrão que liga 2, 3 e a exclusão da Axenya por `consultoria`:** todos casam palavra sem checar
de que a frase fala. É a mesma classe de D-048 e do achado aberto de D-052 — detector léxico onde é
preciso julgamento de sujeito e domínio. É exatamente o que o juiz do Extractor faz, e é por isso
que D-072 move a agulha.

**E o buraco maior não é nenhum dos três: o motor de recomendação não tem régua.** O gabarito das 8
fixtures tem 9 campos e nenhum é sobre recomendação — a esperada existe só em prosa livre, em
`perfil_alvo_nota`. Nada quebra se ela vier errada. É o mesmo estado que os agentes tinham antes de
D-050. A saída real mostra o efeito: para dor de **custo**, a justificativa técnica sai como
*"Join our ecosystem of startups, partners, and developers"* — e a recomendação é justamente o
texto que o gerente lê primeiro e sobre o qual ele decide se aborda a startup.

**Quatro dos nove agentes sem instrumento:** `query_planner` (stub, zero testes, zero régua),
`retriever` (sem gabarito), `recommendation` (sem régua), `briefing` (só o teste de elegibilidade).

## As decisões abertas, em ordem de quanto o defeito custa a quem usa

1. **Dar régua ao motor de recomendação.** É a saída que o gerente lê e sobre a qual ele age, e hoje
   nada quebra quando ela vem errada. Curadoria: quais tecnologias são esperadas e quais são
   proibidas, por fixture. Sem isso, todo item abaixo é medido no meio do pipeline e ninguém sabe se
   a ponta melhorou.
2. **Ligar o juiz do Extractor?** (D-072) — precisão de dor 49% → 83-96%, custo de recall 100% →
   71-79%. Está aqui porque a dor é o que alimenta a recomendação: dor falsa vira tecnologia
   recomendada sem motivo, na frente do usuário. O critério de D-055 foi atendido; falta decidir a
   lacuna de recall, que D-055 nunca fixou — e decidi-la sem a régua do item 1 é decidir no escuro.
3. **`classe`** — erra 4 vezes, sempre `AI-native` → `AI-enabled`. É o rótulo de manchete do
   briefing: errar aqui faz o gerente despriorizar exatamente a startup que ele deveria abordar.
   O mais caro dos itens, e depende da base ampliada (D-060 mostrou que o gargalo não é a regra de
   decisão).
4. **Consertar o `min()` da confiança** — 0/6 constante. O campo aparece no briefing carregando
   zero informação, o que é pior que não aparecer: o leitor supõe que significa algo. Barato de
   mexer, mas exige critério fixado antes — uma tentativa já foi reprovada em D-059.
5. **`estrategia_analise`** — o campo é calculado em `query_planner.py:58` e **nada o lê**, mas a
   arquitetura publicada anuncia *"critérios de busca + estratégia de análise"*. O diagrama promete
   uma capacidade que o sistema não tem. Ou o subgrafo passa a ler, ou o diagrama para de prometer.
6. **A tese aberta por D-072:** conclusões deste projeto sobre *"o LLM não dá conta"* foram medidas
   num modelo de **8B que morreu**. D-059 e D-060 reprovaram mudanças no Classifier e no Evidence
   Validator naquele mesmo modelo. São candidatas diretas a re-medição.

## Dívidas declaradas, com o achado escrito

- **`README.md` afirma coisas falsas hoje.** Não é "está incompleto": ele diz *"Busca vetorial: a
  definir"*, *"Embeddings e reranking: a definir"*, *"LLM: a definir"* para coisas decididas há uma
  semana (D-016, D-046, D-067, D-068), diz *"Como rodar: Em breve"* num repositório que roda, e a
  árvore não lista `src/`, `scripts/`, `data/` nem `tests/`. Quem abrir para entender o sistema é
  ativamente enganado. **A data de conserto continua na M6** — o README não é o sistema, e
  antecipá-lo não melhora nada; o que muda é o critério de pronto: verdadeiro e suficiente para
  alguém rodar sozinho.
- **A abstenção do passo 8 não foi re-medida no modelo novo.** Os 20-22/24 são do modelo morto;
  D-069 previu n=3 e não foi executado.
- **A M3 está em 8 das 30 empresas** (D-062).
- **Interface web (P-06)** — não começada, e é a única superfície pela qual alguém que não lê código
  consegue julgar o sistema. O escopo é decisão de produto em aberto.

## Estado verificado em 31/08, depois da faxina

`pytest -q` → **53 passed, 0 failed** em 179 s. É a primeira vez que a suíte inteira passa desde o
EOL de 27/08. `smoke_nvidia.py` → **3/3**: chat 1808 ms, embedding 592 ms, rerank Cohere 1193 ms.
A régua dos agentes bate linha por linha com D-072 e o filtro do Inception com D-071 — nenhuma
remoção da faxina mexeu em placar.

## Perguntas para a liga, se houver contato

1. O reranker hospedado da NVIDIA saiu do ar e o projeto migrou para o Cohere, que o próprio TAPI
   recomenda — confirmam que é aceitável?
2. Vocês vão **executar** o projeto na avaliação, e com chave de quem?
3. Aviso de que o catálogo de preview aposentou modelos em 18/05, 25/08 e 27/08, e que ele **lista**
   modelos que devolvem 404.
