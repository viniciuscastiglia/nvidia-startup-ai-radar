# 04 — Ecossistema brasileiro: de onde vêm os dados

Estado de cada fonte listada nas §7.1 e §7.2 do TAPI, **verificado um a um em 22/08/2026**
(inclusive com `dig` para checar resolução de DNS).

> Contexto importante: o TAPI foi escrito em junho/2026 e **5 dos 23 links já estão mortos ou
> degradados**. Isso muda a estratégia de montar a base de startups.

---

## 1. Fontes de dados de startups (§7.1)

### Funcionam e servem

| Fonte | URL | Estado | O que dá para extrair |
|---|---|---|---|
| **Cubo Itaú** | https://cubo.itau (antes `cubo.network`, 302) | ✅ vivo | **Melhor fonte viva.** Portfólio público em `/startups-portfolio`. 1.000+ startups no ecossistema, base de 30.000+ na LatAm. **14 hubs, incluindo AI** — além de Agro, Construliving, Consumer, Education, Energy, ESG, Fintech, Health, Legal, Logistics, Maritime & Port, Media & Entertainment, Smart Mobility. Sem fins lucrativos, fundado em 2015 |
| **100 Open Startups** | https://www.openstartups.net/ | ✅ vivo | Ranking público em `/site/ranking/`. 40.000 startups, 10.000 corporações, 270.000 profissionais, R$ 20 bi em negócios, 165.000 contratos. O Ranking 100 Open Startups premia corporações e startups em inovação aberta |
| **Darwin Startups** | https://www.darwinstartups.com/ | ✅ vivo | Portfólio público em `/portfolio`. 100 startups investidas, 14 turmas de aceleração, 11 exits, +R$ 150M captados pelo portfólio |
| **WOW Aceleradora** | https://www.wow.ac/ | ✅ vivo | Portfólio público em `/portfolio`. 195 startups aceleradas, R$ 36M investidos, 17 exits, 500+ investidores anjo. Opera do Cubo Itaú (SP) e do Instituto Caldeira (POA) |
| **Latitud** | https://www.latitud.com/ | ✅ vivo | Portfólio público de investidas. VC early-stage focado em LatAm, com Fellowship |
| **Endeavor Brasil** | https://brasil.endeavor.org/ (antes `endeavor.org.br`, 301) | ⚠️ parcial | 450+ empreendedores no Brasil, 300+ mentores. Showcase parcial: VTEX, Ebanx, OneSkin, Livance, Insider, Delend. Não há diretório completo público |
| **Abstartups** | https://abstartups.com.br/ | ⚠️ parcial | Associação viva. **Mapeamento de Startups 2025** (8ª edição): 3.650 startups em 424 cidades. Relatórios públicos, mas o diretório caiu (ver abaixo) |

### Gated — o dado existe mas não é público

| Fonte | URL | Situação |
|---|---|---|
| **Distrito** | https://distrito.me/ | Pivotou para consultoria de IA enterprise ("Enterprise AI & Transformation"). Opera a plataforma **ÍON** com +38.000 startups mapeadas e o **GenAI Lab** com +80 startups de IA brasileiras. Relatórios de mercado públicos; a base é gated |
| **Liga Ventures** | https://liga.ventures/ | Virou "consultech". Afirma ter mapeado **62,7 mil startups** e ter "a maior base de startups da LatAm". Base gated, via **Startup Scanner** (startupscanner.com) |
| **Anjos do Brasil** | https://www.anjosdobrasil.net/ | Rede de investidores anjo sem fins lucrativos, desde 2011. Sem lista pública de investidas — exige login |
| **StartSe** | https://www.startse.com/ | **Não é base de dados.** É escola internacional de negócios (SP, Palo Alto, Xangai): formações, MBAs, imersões, eventos. Tem seção de artigos que serve como fonte de notícia, não de dado estruturado |

### Mortas ou comprometidas — não usar

| Fonte | URL do TAPI | Problema |
|---|---|---|
| **StartupBase** | `startupbase.com.br` | **Domínio sem registro DNS** — confirmado com `dig`, não resolve. Era o melhor recurso público: 12.800 startups mapeadas, 9.000 empreendedores, 30 comunidades, 560 cidades, consulta livre sem login, com badges de unicórnio / acelerada / Cubo / 100 Open Startups. Perda relevante para este projeto |
| **ACE Startups** | https://acestartups.com.br/ | Domínio resolve (Cloudflare) mas **serve conteúdo de aposta** — "Jogo do Tigrinho" / PG Soft. O domínio foi perdido |
| **InovAtiva Brasil** | `inovativabrasil.com.br` → `inovativa.online` | **Fora do ar até 25/10/2026** por conformidade com a legislação eleitoral |
| **Bossa Invest** | https://bossainvest.com/ | Site com **injeção de spam SEO** (links de cassino no topo da página). O conteúdo institucional existe — VC mais ativo da LatAm, 1.500+ startups investidas, 100+ exits — mas o site está comprometido. Citar com cautela |

### Fontes genéricas que o TAPI também lista
Sites oficiais das startups · blogs oficiais · páginas de carreiras · perfis públicos de founders.

> **As páginas de carreiras são o recurso mais subestimado da lista.** Ver a tabela de sinal por
> tipo de documento em `02-rubrica-ai-native.md`: a vaga é o documento mais honesto sobre a stack
> real de uma empresa. Vale priorizar coletar vagas.

---

## 2. Notícias e sinais públicos (§7.2)

| Veículo | URL | Estado | Nota |
|---|---|---|---|
| **Brazil Journal** | https://braziljournal.com/ | ✅ grátis | De Geraldo Samor. *"Quem faz o PIB lê"*. **Tem seção AI Journal**, além de Startups, VC, Private Equity, Tech. URLs em slug descritivo: `/slug-do-artigo/`. Melhor veículo para este projeto |
| **NeoFeed** | https://neofeed.com.br/ | ✅ grátis | Seções `/startups/` e `/inovacao/`. Cobre rodadas e VC. Também opera o AgFeed (agro) |
| **Startups.com.br** | https://startups.com.br/ | ✅ grátis | Seção dedicada em `/negocios/inteligencia-artificial/`. URLs: `/[categoria]/[slug]/`. 30 mil assinantes de newsletter. Cobre rodadas com valores |
| **Mobile Time** | https://www.mobiletime.com.br/ | ✅ grátis | Indústria mobile e **robôs conversacionais / chatbots** — nicho útil para startups de IA conversacional. URLs: `/noticias/DD/MM/AAAA/slug/` |
| **Exame Startups** | `exame.com/bussola/startups/` | ❌ **404** | O caminho da §7.2 não existe mais. A Exame continua publicando sobre startups, mas em outra estrutura |
| **PEGN** | https://revistapegn.globo.com/ | ✅ grátis | Pequenas Empresas & Grandes Negócios, da Globo. Foco em PME e empreendedorismo |
| **Valor Econômico** | https://valor.globo.com/ | ⚠️ paywall | Jornalismo econômico de referência, mas majoritariamente pago — atrito para gerar `url_fonte` verificável |
| **Meio & Mensagem** | https://www.meioemensagem.com.br/ | ✅ grátis | Imprensa de marketing e publicidade. Útil para startups de martech e adtech |

---

## 3. Estratégia sugerida para popular a base

O TAPI pede **30 a 80 startups com pelo menos 3 documentos cada** (90 a 240 documentos), com
diversidade entre AI-native, AI-enabled e non-AI. Sem scraping. Com StartupBase fora do ar:

1. **Eixo de descoberta: Cubo Itaú.** O hub de AI dá o recorte que o projeto precisa, e os outros
   13 hubs dão os casos AI-enabled e non-AI necessários para exercitar o classificador.
   Complementar com 100 Open Startups, WOW e Darwin para variar estágio e região.
2. **Por startup, buscar 3 tipos de documento diferentes** — a diversidade de tipo vale mais que
   o volume, porque cada tipo carrega um sinal distinto:
   - **site institucional** (posicionamento: copilot ou autopilot)
   - **vaga** (stack técnica real — maior densidade de sinal)
   - **notícia** de Brazil Journal / NeoFeed / Startups.com.br (estágio, rodada, tamanho, data)
   - opcionalmente **blog de engenharia** (maturidade técnica) ou **perfil de founder**
3. **`url_fonte` tem que ser real e resolver.** É o requisito de rastreabilidade do TAPI, e é
   verificável por qualquer leitor em segundos. Uma `url_fonte` inventada destrói a única coisa que
   o sistema promete: que toda conclusão aponta para o documento que a sustenta.
4. **Incluir de propósito casos difíceis**, para que o classificador e o validator tenham o que
   fazer: pelo menos uma empresa **inelegível ao Inception** (consultoria de IA, cripto, ou
   empresa de capital aberto — ver as exclusões em `03-stack-nvidia.md`), pelo menos uma com
   evidência fraca ou desatualizada, e pelo menos uma que parece AI-native no marketing mas é
   wrapper na vaga.
5. **Registrar a proveniência de cada documento** — quando foi coletado e de onde. Isso vira
   seção de metodologia no README e conta no critério 7.

---

## 4. A persona é uma pessoa real

O TAPI descreve o usuário como *"o gerente de Startups & VCs da NVIDIA no Brasil"*. Não é uma
persona hipotética.

| Pessoa | Papel |
|---|---|
| **Jomar Silva** | Diretor do NVIDIA Inception para a América Latina |
| **Andrei Golfeto** | **Community Manager do NVIDIA Inception para a América Latina.** Apoia +1.300 startups de IA e conecta a +140 fundos de investimento. Mestrado em Empreendedorismo e Inovação pela USP. Antes: **Head of Startups do Cubo Itaú**, inovação aberta na aceleradora ACE, e time de New Ventures do iFood |

**Andrei Golfeto é o palestrante do vídeo *"Panorama I.A com: Andrei Golfeto (NVIDIA)"***,
que o próprio TAPI linka na §8.1 como material de apoio sobre benefícios do Inception.
O outro vídeo linkado é *"NVIDIA Inception: Construindo o futuro da AI com uma comunidade de startups"*.

### Números do Inception na América Latina
- ~300 startups inscritas em 2021
- 633 em 2024
- **1.200 a 1.600 em 2025/2026 — crescimento de 74% em 2025**
- **Mais da metade são brasileiras**
- No Brasil, o programa faz ponte com Cubo, Antler, Distrito, Instituto Caldeira e outros hubs

> **Uso no vídeo:** abrir falando da persona com nome, papel e números reais, e do problema
> concreto dela — qualificar 1.600 startups na LatAm sem time para isso — enquadra o projeto como
> ferramenta de trabalho, não exercício acadêmico. É também o que mantém o escopo honesto: cada
> decisão de produto pode ser checada contra o que essa pessoa realmente precisa.
> A trajetória do Andrei (Cubo → ACE → NVIDIA) também explica por que o Cubo é a melhor fonte
> de dados para o recorte deste projeto.

Fontes: https://blog.nvidia.com.br/blog/nvidia-enterprise-tem-vagas-para-programa-gratuito-de-aceleracao-de-startups/ ·
https://www.nvidia.com/en-us/startups/venture-capital/ · perfis públicos
