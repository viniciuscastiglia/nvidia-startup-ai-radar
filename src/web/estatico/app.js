/* NVIDIA Startup AI Radar — cliente.
 *
 * Três coisas que este arquivo faz e que valem ser lidas antes do resto:
 *
 * 1. O SSE É FECHADO À MÃO NO FIM. `EventSource` RECONECTA sozinho quando o servidor encerra
 *    o stream — e como o stream é o run, uma reconexão dispararia o grafo DE NOVO, gastando
 *    3m30 e cota do Cohere sem ninguém pedir. `es.close()` nos eventos `fim` e `erro` é o que
 *    impede isso.
 * 2. NADA É CALCULADO AQUI. Rótulo de quadrante, ordem das empresas e texto do briefing vêm
 *    prontos do servidor, que os pega de `src/agents/briefing.py`. A tela não pode discordar
 *    do .txt que ela mesma exporta.
 * 3. TODO TEXTO VINDO DO RUN PASSA POR `esc`. O conteúdo é trecho literal de página pública:
 *    ele contém HTML, e interpolá-lo cru injetaria a página de origem dentro do Radar.
 */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const NOS_PAI = ["query_planner", "retriever", "analisar_startup", "briefing"];
const NOS_ANALISE = ["extractor", "classifier", "evidence_validator", "elegibilidade",
                     "nvidia_rag", "recommendation"];

let runAtual = null;
let fonteAtual = null;

/* ── consulta ─────────────────────────────────────────────────────────────── */

$("form-busca").addEventListener("submit", (ev) => {
  ev.preventDefault();
  iniciar($("consulta").value.trim(), Number($("max-startups").value) || 5);
});

document.querySelectorAll(".sugestao").forEach((b) =>
  b.addEventListener("click", () => {
    $("consulta").value = b.textContent;
    iniciar(b.textContent, Number($("max-startups").value) || 5);
  }));

function iniciar(consulta, maxStartups) {
  if (!consulta) return;
  if (fonteAtual) fonteAtual.close();

  $("vazio").hidden = true;
  $("resultado").hidden = true;
  $("avisos").innerHTML = "";
  $("btn-analisar").disabled = true;
  montarProgresso();

  const url = `/api/consulta?q=${encodeURIComponent(consulta)}&max_startups=${maxStartups}`;
  const es = new EventSource(url);
  fonteAtual = es;

  es.onmessage = (ev) => {
    const e = JSON.parse(ev.data);
    if (e.tipo === "startups") desenharBranches(e.nomes);
    else if (e.tipo === "no") marcarNo(e);
    else if (e.tipo === "fim") { es.close(); fonteAtual = null; concluir(e.run); }
    else if (e.tipo === "erro") { es.close(); fonteAtual = null; falhar(e.mensagem); }
  };
  // Uma queda de conexão não pode deixar o botão desabilitado para sempre.
  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED) {
      fonteAtual = null;
      falhar("a conexão com o servidor caiu no meio do run. O servidor ainda está de pé? " +
             "Se o run terminou, ele está em “Runs salvos”.");
    }
  };
}

function concluir(run) {
  $("btn-analisar").disabled = false;
  $("progresso").hidden = true;
  desenharRun(run);
}

function falhar(mensagem) {
  $("btn-analisar").disabled = false;
  $("progresso").hidden = true;
  $("vazio").hidden = false;
  $("avisos").innerHTML =
    `<div class="aviso aviso-alerta"><strong>O run não terminou.</strong> ${esc(mensagem)}</div>`;
}

/* ── progresso: a topologia do grafo, não uma barra ───────────────────────── */

function montarProgresso() {
  $("progresso").hidden = false;
  $("trilha-pai").innerHTML = NOS_PAI
    .map((n) => `<li data-no="${n}">${esc(n)}</li>`).join("");
  $("trilha-pai").firstElementChild.classList.add("ativo");
  $("fanout").innerHTML = "";
}

function desenharBranches(nomes) {
  $("fanout").innerHTML = nomes.map((nome) => `
    <div class="branch" data-empresa="${esc(nome)}">
      <span class="branch-nome">${esc(nome)}</span>
      <span class="branch-nos">${NOS_ANALISE
        .map((n) => `<span class="no-chip" data-no="${n}">${esc(n)}</span>`).join("")}</span>
    </div>`).join("");
}

function marcarNo(e) {
  if (e.escopo === "pai") {
    const li = $("trilha-pai").querySelector(`[data-no="${e.no}"]`);
    if (li) {
      li.classList.remove("ativo");
      li.classList.add("pronto");
      li.nextElementSibling?.classList.add("ativo");
    }
    return;
  }
  if (!e.empresa) return;
  const branch = $("fanout").querySelector(`[data-empresa="${CSS.escape(e.empresa)}"]`);
  branch?.querySelector(`[data-no="${e.no}"]`)?.classList.add("pronto");
}

/* ── resultado ────────────────────────────────────────────────────────────── */

function desenharRun(run) {
  runAtual = run;
  $("progresso").hidden = true;
  $("vazio").hidden = true;
  $("resultado").hidden = false;
  desenharAvisos(run);

  const n = run.analises.length;
  $("rail-contagem").textContent = n === 1 ? "1 empresa analisada" : `${n} empresas analisadas`;
  $("rail-consulta").textContent = run.consulta;
  $("link-briefing").href = `/api/runs/${run.thread_id}/briefing.txt`;
  $("link-json").href = `/api/runs/${run.thread_id}/run.json`;

  $("lista-empresas").innerHTML = run.analises.map((a, i) => {
    const d = a.diagnostico;
    const eleg = a.elegibilidade;
    const selo = !eleg ? ""
      : eleg.elegivel
        ? '<span class="selo selo-sim">Inception</span>'
        : '<span class="selo selo-nao">fora</span>';
    const classe = d ? (d.sinal_verificado ? esc(d.classe) : "a verificar") : "—";
    const n = a.recomendacoes.length;
    const recs = n === 0 ? "sem recomendação" : n === 1 ? "1 recomendação" : `${n} recomendações`;
    return `<li data-i="${i}" ${i === 0 ? 'class="aberta"' : ""}>
      <button type="button">
        <span class="emp-nome">${esc(a.nome)}</span>
        <span class="emp-linha">${classe} · ${recs} ${selo}</span>
      </button></li>`;
  }).join("");

  $("lista-empresas").querySelectorAll("li").forEach((li) =>
    li.querySelector("button").addEventListener("click", () => {
      $("lista-empresas").querySelectorAll("li").forEach((o) => o.classList.remove("aberta"));
      li.classList.add("aberta");
      desenharDossie(run.analises[Number(li.dataset.i)]);
    }));

  if (n) desenharDossie(run.analises[0]);
  else $("dossie").innerHTML =
    `<h2>Nenhuma empresa casou os critérios</h2>
     <p class="meta">${esc(run.consulta)}</p>
     <p>Alargue o setor, remova o filtro de estágio, ou revise as palavras-chave.</p>`;
}

/* Os avisos são o sistema declarando o que ele NÃO garante. Cada um tem uma decisão atrás. */
function desenharAvisos(run) {
  const avisos = [];
  if (run.rerank_provedor === "nenhum") {
    avisos.push(["cautela",
      "Este run rodou sem o passo 7 (reranking).",
      "A ordem das citações é a da busca híbrida. Serve para desenvolver — não para julgar " +
      "qual tecnologia o sistema recomendaria de verdade."]);
  }
  if (run.discrimina === false) {
    avisos.push(["alerta",
      "Esta consulta não produziu nenhum critério de busca.",
      "As empresas abaixo são uma fatia arbitrária da base, não um resultado de recuperação. " +
      "Refaça a consulta nomeando setor, estágio ou tecnologia."]);
  }
  $("avisos").innerHTML = avisos
    .map(([t, forte, resto]) =>
      `<div class="aviso aviso-${t}"><strong>${esc(forte)}</strong> ${esc(resto)}</div>`)
    .join("");
}

/* ── dossiê da empresa ────────────────────────────────────────────────────── */

function desenharDossie(a) {
  const meta = (runAtual.startups || []).find((s) => s.startup_id === a.startup_id) || {};
  const d = a.diagnostico;
  const e = a.elegibilidade;
  const P = [];

  P.push(`<h2>${esc(a.nome)}</h2>`);
  // `score_recuperacao` GANHOU LEITOR — P-14, D-112. `db.py` o preenche com o score do
  // `tsvector` desde sempre e ninguém o mostrava. Ele responde à primeira pergunta de quem abre
  // um resultado e não reconhece o nome: POR QUE ESTA EMPRESA ESTÁ AQUI. Zero é omitido — é o
  // valor de quem entrou por filtro estrutural e não por casamento de texto, e imprimir "0.000"
  // afirmaria uma medição que não houve.
  P.push(`<p class="meta">${[meta.setor, meta.estagio, meta.localizacao,
    meta.ano_fundacao ? `fundada em ${meta.ano_fundacao}` : null,
    meta.score_recuperacao ? `recuperação ${Number(meta.score_recuperacao).toFixed(3)}` : null]
    .filter(Boolean).map(esc).join(" · ") || "sem metadados na base"}
    ${meta.site ? ` · <a href="${esc(meta.site)}" target="_blank" rel="noopener">site</a>` : ""}</p>`);

  if (a.erros?.length) {
    P.push(`<div class="aviso aviso-alerta">Análise incompleta: ${esc(a.erros.join("; "))}</div>`);
  }

  if (d) {
    P.push(`<h3>Diagnóstico</h3>
      <div class="diagnostico">
        <div><span class="diag-rotulo">classificação</span>
             <span class="diag-valor">${esc(d.classe)}</span></div>
        <div><span class="diag-rotulo">maturidade da stack</span>
             <span class="diag-valor">${esc(d.maturidade_stack)}</span></div>
        <div><span class="diag-rotulo">confiança</span>
             <span class="diag-valor">${esc(d.confianca)}</span></div>
      </div>
      <p class="quadrante${d.sinal_verificado ? "" : " incerto"}">${esc(a.rotulo_quadrante)}</p>
      <p class="base">${esc(d.justificativa)}</p>
      ${d.motivo_confianca ? `<p class="base">Confiança: ${esc(d.motivo_confianca)}</p>` : ""}`);
  }

  if (e) {
    P.push(`<h3>NVIDIA Inception</h3>
      <p class="veredito"><span class="titulo">${e.elegivel ? "ELEGÍVEL" : "NÃO ELEGÍVEL"}</span>
      <span class="selo ${e.elegivel ? "selo-sim" : "selo-nao"}">
        ${e.elegivel ? "entra no funil de captação" : "não entra no programa"}</span></p>`);
    const itens = [];
    e.motivos_exclusao.forEach((m, i) => {
      const ev = e.evidencias[i];
      itens.push(`<li class="excluiu">${esc(m)}${ev ? citacaoHTML(ev) : ""}</li>`);
    });
    e.requisitos_nao_verificados.forEach((p) => itens.push(`<li class="pendente">${esc(p)}</li>`));
    if (itens.length) P.push(`<ul class="motivos">${itens.join("")}</ul>`);
  }

  // AS DORES E O TRABALHO DO EVIDENCE VALIDATOR — `motivo_validacao`, P-14, D-112.
  // `avaliar()` preenchia este campo por afirmação e NADA o lia: o briefing imprimia o irmão
  // dele (`Diagnostico.motivo_confianca`) e descartava este. A tela promete no rodapé que toda
  // conclusão aponta para o documento que a sustenta — `motivo_validacao` é o que diz QUANTO
  // aquele documento sustenta, e é o único lugar do sistema onde o Evidence Validator aparece
  // com o raciocínio dele à mostra em vez de só com o rótulo.
  const dores = a.perfil?.dores_observadas || [];
  if (dores.length) {
    P.push(`<h3>Dores observadas (${dores.length})</h3>
      <ul class="dores">${dores.map((d) => `
        <li class="${d.validada ? "dor-validada" : "dor-fraca"}">
          <span class="dor-nome">${esc(d.dor)}</span>
          <span>
            <span class="dor-grau">confiança ${esc(d.confianca || "—")}${
              d.validada ? "" : " · não validada"}</span>
            ${d.motivo_validacao ? `<br><span class="salvo-meta">${esc(d.motivo_validacao)}</span>` : ""}
            ${(d.evidencias || []).slice(0, 1).map(citacaoHTML).join("")}
          </span>
        </li>`).join("")}</ul>`);
  }

  P.push(`<h3>Recomendações (${a.recomendacoes.length})</h3>`);
  if (!a.recomendacoes.length) {
    P.push(`<p class="sem-nada">Nenhuma — ${esc(a.motivo_sem_recomendacao
      || "a análise não chegou ao motor de recomendação")}.</p>`);
  }
  // D-099: a recusa do Inception ROTULA as recomendações em vez de suprimi-las. A JetBov é o
  // caso que decidiu isso — única AI-native da base e não elegível por idade.
  if (a.recomendacoes.length && e && !e.elegivel) {
    P.push(`<div class="aviso aviso-cautela"><strong>Fora do Inception.</strong>
      Abordagem comercial direta, não captação para o programa. O motivo está acima.</div>`);
  }
  a.recomendacoes.forEach((r) => P.push(recomendacaoHTML(r, a)));

  $("dossie").innerHTML = P.join("");
  $("dossie").scrollTop = 0;
  $("dossie").querySelectorAll(".btn-vitrine").forEach((b) =>
    b.addEventListener("click", () => abrirVitrine(b.dataset.consulta, b.dataset.dor, a.nome)));
}

function citacaoHTML(ev) {
  return `<blockquote class="citacao">${esc(ev.trecho)}
    <span class="fonte">[${esc(ev.tipo_documento)}]
      <a href="${esc(ev.url_fonte)}" target="_blank" rel="noopener">${esc(ev.url_fonte)}</a>
    </span></blockquote>`;
}

function recomendacaoHTML(r, a) {
  const num = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(3));
  const consultaDaDor = (dor) =>
    (a.consultas_rag || []).find((c) => c.dor === dor)?.consulta || "";

  const rag = r.citacoes_rag.map((c) => {
    const consulta = consultaDaDor(c.dor_origem);
    return `<div class="rag-item">
      <span class="rag-tec"><a href="${esc(c.url_fonte)}" target="_blank" rel="noopener">${esc(c.tecnologia)}</a></span>
      <span>
        <span class="scores">denso ${num(c.score_denso)} · lexical ${num(c.score_lexical)} · rerank ${num(c.score_rerank)}</span>
        ${consulta ? `<button type="button" class="btn-vitrine"
            data-consulta="${esc(consulta)}" data-dor="${esc(c.dor_origem || "")}">por quê?</button>` : ""}
      </span></div>`;
  }).join("");

  return `<div class="rec">
    <div class="rec-cabeca">
      <span class="rec-tec">${r.tecnologias.map(esc).join(", ")}</span>
      <span class="rec-grau">prioridade ${esc(r.prioridade)} · complexidade ${esc(r.complexidade)}</span>
    </div>
    <div class="rec-corpo">
      <div class="campo"><span>dores</span><span>${
        r.dores_enderecadas.length ? r.dores_enderecadas.map(esc).join(", ")
        : '<span class="sem-nada">a citação não veio de uma dor</span>'}</span></div>
      <div class="campo"><span>técnica</span><span>${esc(r.justificativa_tecnica)}</span></div>
      <div class="campo"><span>negócio</span><span>${esc(r.justificativa_negocio)}</span></div>
      <div class="campo acao"><span>próxima ação</span><span>${esc(r.proxima_acao)}</span></div>
      <div class="campo"><span>evidência</span><span>${
        r.evidencias.length ? r.evidencias.map(citacaoHTML).join("")
        : '<span class="sem-nada">sem trecho de evidência</span>'}</span></div>
    </div>
    ${rag ? `<div class="rag">${rag}</div>` : ""}
  </div>`;
}

/* ── vitrine do passo 7 ───────────────────────────────────────────────────── */

async function abrirVitrine(consulta, dor, empresa) {
  const dlg = $("dialogo-vitrine");
  $("conteudo-vitrine").innerHTML = "<h2>Consultando a base NVIDIA…</h2>";
  dlg.showModal();
  let dados;
  try {
    const r = await fetch("/api/vitrine", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consulta }),
    });
    dados = await r.json();
    if (!r.ok) throw new Error(dados.detail || r.statusText);
  } catch (err) {
    $("conteudo-vitrine").innerHTML =
      `<h2>A vitrine não carregou</h2><p>${esc(err.message)}</p>`;
    return;
  }

  if (dados.aviso) {
    $("conteudo-vitrine").innerHTML =
      `<h2>O passo 7 está fora do caminho</h2><p>${esc(dados.aviso)}</p>`;
    return;
  }

  // O deslocamento vem calculado do servidor, sobre a UNIÃO INTEIRA — a tela só recebe o topo,
  // então uma passagem promovida da 15ª posição seria invisível se a conta fosse feita aqui.
  const linha = (p, mostrarDelta) => {
    const d = p.delta;
    return `<li class="${mostrarDelta && d > 0 ? "subiu" : mostrarDelta && d < 0 ? "desceu" : ""}">
      <span class="pos">${p.posicao}</span>
      <span>${esc(p.tecnologia)}
        <br><span class="salvo-meta">${esc(p.trecho || p.caminho_secao || "")}…</span></span>
      <span class="delta ${d > 0 ? "mais" : d < 0 ? "menos" : ""}">${
        !mostrarDelta ? "" : d > 0 ? `▲ ${d}  (era ${p.posicao_fusao}ª)`
        : d < 0 ? `▼ ${-d}` : "="}</span>
    </li>`;
  };

  $("conteudo-vitrine").innerHTML = `
    <h2>Por que esta tecnologia</h2>
    <p class="salvo-meta">${esc(empresa)} · dor <strong>${esc(dor)}</strong> · a consulta abaixo é
      exatamente a que o agente NVIDIA RAG mandou à base, montada com a fala literal da empresa.</p>
    <blockquote class="citacao">${esc(dados.consulta)}</blockquote>
    <div class="vitrine-colunas">
      <div><h3>Ordem da busca híbrida — passo 6</h3>
        <ol class="ranking">${dados.fusao.map((p) => linha(p, false)).join("")}</ol></div>
      <div><h3>Ordem do reranking — passo 7</h3>
        <ol class="ranking">${dados.rerank.map((p) => linha(p, true)).join("")}</ol></div>
    </div>
    <p class="salvo-meta">${esc(dados.nota || "")}</p>`;
}

/* ── o passo 8: perguntar à base NVIDIA ───────────────────────────────────── */
/*
 * A ABSTENÇÃO É A MANCHETE, NÃO A NOTA DE RODAPÉ. Quando o sistema recusa responder, é isso
 * que ocupa o topo do diálogo — com o motivo e com as passagens que ele LEU E DESCARTOU. Um
 * "não sei" escondido embaixo de um parágrafo de desculpas seria o mesmo que não tê-lo: a
 * capacidade só existe para quem a vê acontecer.
 *
 * A cor do estado é `--sem-prova`, a mesma de `requisito não verificado` e `sinal de IA não
 * verificado`. Não é escolha estética — a paleta desta tela tem três cores de veredito porque
 * o sistema distingue "prova que sim", "prova que não" e "não prova", e a abstenção do RAG é
 * o terceiro caso, no terceiro componente.
 */

const $dlgPergunta = () => $("dialogo-pergunta");

$("btn-perguntar").addEventListener("click", () => {
  $("resposta-rag").innerHTML = "";
  $dlgPergunta().showModal();
  $("pergunta").focus();
});

$("form-pergunta").addEventListener("submit", (ev) => {
  ev.preventDefault();
  perguntar($("pergunta").value.trim());
});

document.querySelectorAll(".sugestao-rag").forEach((b) =>
  b.addEventListener("click", () => {
    $("pergunta").value = b.textContent.trim();
    perguntar(b.textContent.trim());
  }));

async function perguntar(consulta) {
  if (!consulta) return;
  const botao = $("btn-enviar-pergunta");
  // Um segundo envio enquanto o primeiro corre gastaria outra chamada de LLM e outra rodada
  // de rerank — e o servidor devolveria 409, porque o cadeado é o mesmo do run.
  botao.disabled = true;
  $("resposta-rag").innerHTML =
    `<p class="rag-pensando">Buscando na base, reordenando com o cross-encoder e lendo as
     passagens… A leitura é uma chamada de LLM e leva alguns segundos.</p>`;
  let d;
  try {
    const r = await fetch("/api/perguntar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consulta }),
    });
    d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);
  } catch (err) {
    $("resposta-rag").innerHTML =
      `<div class="aviso aviso-alerta"><strong>A pergunta não foi respondida.</strong>
       ${esc(err.message)}</div>`;
    return;
  } finally {
    botao.disabled = false;
  }

  const passagens = d.citacoes.map((c) => `
    <li class="${c.citada ? "passagem-citada" : "passagem-lida"}">
      <span class="passagem-marca">${c.citada ? "citada" : "lida"}</span>
      <span>
        <a href="${esc(c.url_fonte)}" target="_blank" rel="noopener">${esc(c.tecnologia)}</a>
        <br><span class="salvo-meta">${esc(c.trecho)}</span>
      </span>
    </li>`).join("");

  const cabeca = d.abstencao
    ? `<div class="rag-abstencao">
         <h3>O Radar não respondeu.</h3>
         <p>${esc(d.motivo_abstencao || "os trechos recuperados não contêm o fato pedido.")}</p>
         <p class="salvo-meta">Os trechos abaixo foram recuperados e LIDOS. Todos falam do
           assunto — é justamente por isso que nenhum limiar de score os separa: nem a cosseno
           densa (margem −0,2810) nem o logit do cross-encoder (−17,6328). Quem distingue
           “fala do assunto” de “contém o fato” é o componente que lê.</p>
       </div>`
    : `<div class="rag-resposta"><p>${esc(d.texto)}</p></div>`;

  $("resposta-rag").innerHTML = `
    ${cabeca}
    <h3 class="rag-passagens-titulo">As ${d.citacoes.length} passagens que ele leu</h3>
    <ul class="rag-passagens">${passagens}</ul>
    <p class="salvo-meta">modelo: <code>${esc(d.modelo)}</code> ·
      rerank: <code>${esc(d.rerank_provedor)}</code>${
      d.rerank_provedor === "nenhum"
        ? " — o passo 7 está fora do caminho, então a ordem acima é a da busca híbrida"
        : ""}</p>`;
}

/* ── runs salvos ──────────────────────────────────────────────────────────── */

$("btn-salvos").addEventListener("click", async () => {
  const dlg = $("dialogo-salvos");
  const runs = await (await fetch("/api/runs")).json();
  $("lista-salvos").innerHTML = runs.length
    ? runs.map((r) => `<li><button type="button" data-id="${esc(r.thread_id)}">
        ${esc(r.consulta)}
        <span class="salvo-meta">${esc(r.gerado_em.replace("T", " ").slice(0, 16))} ·
        ${r.empresas === 1 ? "1 empresa" : `${r.empresas} empresas`} ·
        rerank: ${esc(r.rerank_provedor)}</span></button></li>`).join("")
    : "<li class='salvo-meta'>Nenhum run salvo ainda. Faça uma consulta.</li>";
  $("lista-salvos").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", async () => {
      dlg.close();
      desenharRun(await (await fetch(`/api/runs/${b.dataset.id}`)).json());
    }));
  dlg.showModal();
});

/* Estado do servidor no carregamento: se algo está degradado, quem abre a tela precisa saber
   ANTES de gastar 3m30 num run. */
fetch("/api/estado").then((r) => r.json()).then((s) => {
  $("max-startups").value = s.max_startups_padrao;
  if (!s.tem_credencial) {
    $("avisos").innerHTML = `<div class="aviso aviso-alerta"><strong>Sem credencial de API.</strong>
      Preencha <code>NVIDIA_API_KEY</code> no <code>.env</code>. Sem ela o embedder não responde e
      o run falha no agente NVIDIA RAG.</div>`;
  }
});
