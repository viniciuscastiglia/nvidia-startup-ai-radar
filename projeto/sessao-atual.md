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

**E o buraco maior não é nenhum dos três: o critério 3 (motor de recomendação, 20 pontos) não tem
régua.** O gabarito das 8 fixtures tem 9 campos e nenhum é sobre recomendação — a esperada existe só
em prosa livre, em `perfil_alvo_nota`. Nada quebra se ela vier errada. É o mesmo estado que os
agentes tinham antes de D-050. A saída real mostra o efeito: para dor de **custo**, a justificativa
técnica sai como *"Join our ecosystem of startups, partners, and developers"*.

**Quatro dos nove agentes sem instrumento:** `query_planner` (stub, zero testes, zero régua),
`retriever` (sem gabarito), `recommendation` (sem régua), `briefing` (só o teste de elegibilidade).

## As decisões abertas, em ordem de quanto movem a nota

1. **Ligar o juiz do Extractor?** (D-072) — precisão de dor 49% → 83-96%, custo de recall 100% →
   71-79%. O critério de D-055 foi atendido; falta decidir a lacuna de recall, que D-055 nunca fixou.
2. **Dar régua ao motor de recomendação** — 20 pontos sem instrumento. Curadoria: quais tecnologias
   são esperadas e quais são proibidas, por fixture.
3. **Consertar o `min()` da confiança** — 0/6 constante. Barato, mas exige critério fixado antes:
   uma tentativa já foi reprovada em D-059.
4. **`classe`** — o mais caro: curadoria de documentos ou reescrita da rubrica.
5. **`estrategia_analise`** — o campo é calculado em `query_planner.py:58` e **nada o lê**, mas a
   arquitetura publicada anuncia *"critérios de busca + estratégia de análise"*. Ou o subgrafo passa
   a ler, ou o diagrama para de prometer. Exposição direta ao eliminatório nº 4.
6. **A tese aberta por D-072:** conclusões deste projeto sobre *"o LLM não dá conta"* foram medidas
   num modelo de **8B que morreu**. D-059 e D-060 reprovaram mudanças no Classifier e no Evidence
   Validator naquele mesmo modelo. São candidatas diretas a re-medição.

## Dívidas declaradas, com o achado escrito

- **`README.md` está desatualizado e vale 10 pontos.** Diz *"Busca vetorial: a definir"*,
  *"Embeddings e reranking: a definir"*, *"LLM: a definir"*, *"Como rodar: Em breve"*, e a árvore do
  repositório não lista `src/`, `scripts/`, `data/` nem `tests/`. É o primeiro arquivo que o
  avaliador abre. Decisão: fica para a M6, junto com o vídeo.
- **A abstenção do passo 8 não foi re-medida no modelo novo.** Os 20-22/24 são do modelo morto;
  D-069 previu n=3 e não foi executado.
- **A M3 está em 8 das 30 empresas** (D-062).
- **`pytest` completo não roda desde a troca de reranker** — exige uma passada com Cohere, ~7 min de
  throttle.
- **Interface web (P-06)** — 5 pontos, ainda não começada.

## Perguntas para a liga, se houver contato

1. O reranker hospedado da NVIDIA saiu do ar e o projeto migrou para o Cohere, que o próprio TAPI
   recomenda — confirmam que é aceitável?
2. Vocês vão **executar** o projeto na avaliação, e com chave de quem?
3. Aviso de que o catálogo de preview aposentou modelos em 18/05, 25/08 e 27/08, e que ele **lista**
   modelos que devolvem 404.
