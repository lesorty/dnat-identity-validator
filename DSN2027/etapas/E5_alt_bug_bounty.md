# E5 — Alternativa A: DNAT como mercado anônimo de bug bounty sobre a cadeia de suprimentos

**Status:** RASCUNHO de exploração (2026-10-26). Nada decidido; nada medido. Este documento
estrutura **uma das duas alternativas** ao rumo vigente (Juiz de IA como avaliador geral de
vazamento), julgado amplo demais. A alternativa B será escrita por outra pessoa no mesmo molde
(11 seções) e as duas serão comparadas.
**Decisões vigentes que isto tensiona:** D1 (contribuição = Juiz de IA), D2, D3, D4
([DECISOES.md](../DECISOES.md)). **Convenções do repo:** toda afirmação sobre literatura leva
link; o que não foi conferido na fonte primária leva **(a verificar)**; ✔ marca referência
conferida na fonte; afirmações sobre o código do DNAT citam `arquivo:linha`.

---

## 1. Tese em uma frase

O DNAT vira um **mercado anônimo de bug bounty sobre a cadeia de suprimentos de computação
confidencial**: qualquer um deposita (e qualquer outro soma) recompensa sobre um componente
atacável — imagem-base, dependência ou aplicação —, quem **prova** a vulnerabilidade **mecanicamente
dentro da CVM de uso único** (estendendo a verdade de referência estilo CTF, D2) reivindica a
recompensa, e toda aplicação que lista o componente no SBOM é marcada comprometida na hora e
notificada — com os dependentes **ocultos** dos caçadores, para que reivindicar no DNAT seja mais
atraente do que atacar aplicações reais por fora.

---

## 2. Atores e fluxo

| Ator | Papel |
|---|---|
| **Dono de componente** | Registra imagem-base/dependência/app como ativo (hoje `registerAsset`, `DnatMarketplace.sol:126`). Pode ser alvo de recompensa sem consentir |
| **Dono de app** | Dono de ativo `Application` cujo SBOM referencia o componente; é quem recebe a notificação e corrige |
| **Patrocinador de recompensa** | Qualquer endereço que deposita ETH num *vault* ligado ao componente; vários somam (recompensa cumulativa) |
| **Caçador** | Prova a vulnerabilidade e reivindica o *vault*; anônimo (endereço pseudônimo) |
| **DNAT** | Executa a prova na CVM, confere o canário, paga o caçador, propaga pelo SBOM, notifica donos, controla embargo/divulgação |

**Fluxo (ciclo de vida):**

```
registro do componente ──▶ patrocínio (depósitos somam no vault) ──▶ submissão da prova
   (exploit + alvo) ──▶ verificação mecânica na CVM (canário/flag gerado na execução)
   ──┬─ válida ─▶ pagamento ao caçador ─▶ propagação no SBOM (marca dependentes)
     │                                   ─▶ notificação aos donos (dependentes ocultos do caçador)
     │                                   ─▶ embargo (janela de correção) ─▶ divulgação
     └─ inválida ─▶ vault intacto; registra tentativa (anti-spam)
```

**Visibilidade (o ponto central da alternativa):** o livro público mostra **componentes atacáveis +
recompensa acumulada**; **esconde a lista de aplicações dependentes**. A hipótese de incentivo é que,
sem saber *quais* apps caem, o caçador maximiza ganho reivindicando no DNAT (recompensa certa) em vez
de atacar apps específicas por fora (ganho incerto e ilegal). É o mesmo princípio de "tornar a
divulgação a jogada dominante" do Hydra Framework ([Breidenbach et al., USENIX Security 2018 ✔](https://www.usenix.org/conference/usenixsecurity18/presentation/breindenbach)),
aqui movido do nível de um contrato para o nível da cadeia de suprimentos.

---

## 3. Modelo de ameaça

**Confiável:** a plataforma DNAT (operador) para executar a prova e custodiar o *vault* — é o
mesmo ponto único de confiança já assumido em D3 (sem distribuição; operador é ponto único de
disponibilidade e censura). A CVM de uso único e sua atestação (implícita, D3).

**Parcialmente confiável / adversário:** donos de componente (podem patrocinar a si mesmos),
caçadores (podem ser Sybils ou conluiados), patrocinadores (podem inflar recompensa para sinalizar
alvo), operador (pode censurar ou espiar; conluio é limitação declarada, D4).

**O que o atacante sabe:** o catálogo público de componentes atacáveis e o valor de cada *vault*;
o SBOM/proveniência de cada componente (gerado no build, [E2c](E2c_ameacas_oci.md) §7 B4, `syft`
sugerido); **não** sabe quais apps dependem de quê (inferência pelo tamanho da recompensa é um risco
de uso dual, §9). Fora da plataforma, conhece a literatura e pode rodar agentes de exploração
([CyberGym ✔](http://arxiv.org/abs/2506.02548), [CVE-Bench ✔](https://arxiv.org/abs/2503.17332)).

**O que o DNAT garante:**
1. **Verificação sem juiz humano nem LLM generalista:** a prova vale se, e só se, o exploit roda na
   CVM e o canário/flag plantado na execução sai pelo canal observado (estende D2 §9.2).
2. **Propagação correta e imediata:** todo dependente no SBOM é marcado assim que a prova passa.
3. **Fair exchange:** o caçador só revela o exploit dentro da CVM; o pagamento é atômico com a
   verificação (contrato), evitando o "reporto e não me pagam" (motivação de
   [zkPoEX](https://www.risczero.com/blog/zkpoex) e de [Green et al., PoPETs 2023 ✔](https://doi.org/10.56553/popets-2023-0036)).
4. **Confidencialidade do exploit frente a terceiros** até a divulgação coordenada (embargo).

**Fora do escopo / limitação:** conluio operador+caçador; canais laterais da CVM; vazamento do
próprio exploit pelo operador que roda a CVM (ao contrário de uma prova em ZK, aqui o operador **vê**
o exploit — ver §8 e §9).

---

## 4. O que reaproveita do DNAT (D2–D4, com arquivo:linha)

| Peça existente | Reuso na alternativa | Fonte |
|---|---|---|
| **Marketplace em contrato** (`registerAsset`, `purchaseAccess`, eventos, guarda de reentrância) | Base do *vault* de recompensa: `registerAsset` já modela Dataset/Application; falta um tipo de recompensa e depósito cumulativo | `smart-contract/contracts/DnatMarketplace.sol:33-64,126-159,214-265` |
| **`contentHash` no ativo e na compra** | Vincula a prova ao digest exato julgado (como o veredito do Juiz é vinculado ao digest, JUIZ_IA §1) | `DnatMarketplace.sol:47,147`; E2b.4 passo 5 |
| **CVM de uso único, container sem rede** (D4) | Sandbox onde a prova roda; "a app roda sem rede, a CVM só fala com o DNAT" é exatamente o ambiente para medir um exploit sem vazá-lo para fora | `DECISOES.md:37-59`; [E2c](E2c_ameacas_oci.md) §2 (R1–R9) |
| **Verdade de referência estilo CTF com canário** (D2) | É o coração da prova mecânica: já decidido que "vale se a tarefa é cumprida e o canário sai da saída" — aqui vira "vale se o exploit dispara a condição e a flag sai" | `DECISOES.md:18-20`; [JUIZ_IA.md](../JUIZ_IA.md) §9.2, §9.4 |
| **Build atestado em duas CVMs + proxy de registro que anota cada download** (D4) | Fonte natural do **SBOM**: o proxy já registra cada dependência baixada como `materials` da proveniência; é o grafo componente→app que a propagação precisa | `DECISOES.md:43-51`; [E2b](E2b_build_oci.md) §3, §4.1; [E2c](E2c_ameacas_oci.md) §7 B4 (`syft`/`osv-scanner`) |
| **Executor mínimo** (seccomp, gVisor, rootfs RO, saída como dado) | Roda o exploit não confiável com as mesmas defesas X1–X6 | `vm_runtime/executor.py:11-16,52-57`; [E2c](E2c_ameacas_oci.md) §3 |
| **Apps de ataque semente** (`t1_network_exfil`, `t1b_fs_escape`, `t2_malicious_dep`) | Casos-teste prontos de exploit reproduzível na CVM | `assets/apps/`; [E2c](E2c_ameacas_oci.md) §8 |
| **`manifestUri` / proveniência** | Onde o SBOM por ativo é ancorado | `DnatMarketplace.sol:44,151` |

**Observação de encaixe (D3):** a alternativa **mantém** "sem distribuição" e "atestação implícita"
e **não precisa** da parte mais cara do Juiz (o LLM generalista). Em troca, pede um subsistema novo
(abaixo).

---

## 5. O que falta construir

1. **Vault de recompensa cumulativo no contrato:** novo tipo/estrutura ligando um componente a um
   saldo somável por N patrocinadores, com reivindicação atômica à verificação. Hoje o contrato só
   tem preço fixo por ativo e pagamento na compra (`DnatMarketplace.sol:214-265`); não há depósito
   cumulativo nem *escrow* condicionado a uma prova. Precedente de desenho: *vaults* públicos do
   [Hats Finance](https://research.lido.fi/t/bug-bounty-vault-proposal-by-hats-finance/5404) (qualquer
   um deposita) e split finder/projeto do [Internet Bug Bounty 80/20](https://www.hackerone.com/press-release/hackerone-expands-internet-bug-bounty-improve-collective-security-software-supply).
2. **Harness de prova dentro da CVM:** contrato de submissão `(exploit, alvo, digest)` → execução →
   predicado de sucesso. Estende o harness CTF do Juiz (JUIZ_IA §9.4) de "canário na saída" para
   famílias de exploit (§6/§7).
3. **Gerador de canário/flag em tempo de execução por classe de vulnerabilidade** (o que distingue
   RCE de leitura arbitrária de DoS — ver §7, crítica).
4. **Grafo de SBOM e motor de propagação:** ingerir os `materials` do proxy de fetch (E2b.3) num
   grafo componente→app e, dada uma prova válida, marcar o fecho transitivo dos dependentes. Base de
   dados e consultas no estilo [GUAC](https://guac.sh/) / [OSV](https://ossf.github.io/osv-schema/)
   (casar pacote↔vulnerabilidade por `purl`/ranges).
5. **Camada de ocultação dos dependentes:** o livro público mostra componente+recompensa e esconde
   a lista de apps; exige separar o que é on-chain (público por construção) do que fica off-chain no
   DNAT. **Tensão real:** eventos do contrato são públicos (`AccessPurchased` já expõe IDs,
   `DnatMarketplace.sol:91-97`); ocultar dependentes exige que o vínculo app↔componente **não** esteja
   on-chain, ou esteja cego (compromissos/ZK — ver §8 zkSBOM).
6. **Fluxo de notificação + embargo + divulgação coordenada** (janela de correção antes de tornar
   público; estado estilo VEX `affected`/`fixed`, [CISA VEX](https://www.cisa.gov/sites/default/files/2023-09/Vulnerability%20Exploitability%20eXchange%20%28VEX%29_508c.pdf)).
7. **Anti-abuso:** anti-Sybil, anti-autopatrocínio, custo de submissão para conter spam de prova
   (lição do [curl encerrando o bounty por "AI slop"](https://www.theregister.com/2026/01/21/curl_ends_bug_bounty/)).

---

## 6. Contribuições candidatas

- **C1 — Mercado de bug bounty com verificação mecânica em TEE sobre a cadeia de suprimentos.**
  Primeiro desenho em que a recompensa é liberada por uma **prova executável conferida numa CVM de
  uso único** (não por juiz humano, vídeo ou LLM), e em que a validação **propaga** automaticamente
  para todos os dependentes via SBOM. Novidade frente a Sealed-Glass Proofs (verifica um exploit,
  não propaga) e ao Hydra (um contrato, não uma cadeia).
- **C2 — Ocultação de dependentes como mecanismo de incentivo.** Formalizar e avaliar a hipótese de
  que esconder a lista de apps dependentes (revelando só componente+recompensa) torna a reivindicação
  no DNAT a estratégia dominante frente ao ataque ilegal externo. Contribuição de **segurança
  econômica/teoria dos jogos** com um artefato que a testa.
- **C3 — Recompensa cumulativa e aberta sobre componentes de terceiros.** Qualquer um pode pôr preço
  na cabeça de uma dependência que não controla, e a propagação transforma uma prova única em
  marcação de N apps. Modelo e implementação em contrato.
- **C4 — Artefato: harness de verificação de exploit por classe + benchmark de propagação** sobre
  CVEs reproduzíveis (ARVO/CyberGym/Vulhub), com métricas de corretude da propagação pelo SBOM.
- **C5 (pré-requisito, herdado):** execução de imagens OCI em CVM, container sem rede (= C4 do rumo
  atual, D4) — reaproveitado, não refeito.

---

## 7. Avaliação possível até 02/dez

**Pergunta de pesquisa:** (i) que fração de vulnerabilidades reais é **mecanicamente verificável**
por canário/flag numa CVM? (ii) a propagação pelo SBOM marca os dependentes **corretos** e **rápido**?
(iii) qual o **custo** da verificação em CVM? (iv) o incentivo de ocultação se sustenta num modelo?

### 7.1 Experimento A — verificabilidade mecânica por classe (crítica central da "ideia a explorar")

Rodar exploits reais numa CVM e medir se um predicado mecânico decide sucesso **sem juiz**. Fontes de
exploit reproduzível já empacotadas em container:

| Dataset | O que traz | Uso |
|---|---|---|
| [ARVO ✔](http://arxiv.org/abs/2408.02153) | >5.000 (depois >6.000) vulns de memória OSS-Fuzz, cada uma com *input* gatilho e patch, em imagens Docker | Alvo pré/pós-patch; predicado = crash de sanitizador |
| [CyberGym ✔](http://arxiv.org/abs/2506.02548) | 1.507 instâncias, 188 projetos; tarefa = PoC que quebra pré-patch e não pós-patch | Mesmo predicado diferencial que a verdade CTF do DNAT |
| [CVE-Bench ✔](https://arxiv.org/abs/2503.17332) | 40 CVEs web críticos; **8 metas de ataque** com *grader* por meta | Mapa direto de "classe → como a flag é conferida" |
| [Vulhub](https://github.com/vulhub/vulhub) | Ambientes vulneráveis por CVE em docker-compose | Casos extra de RCE/leitura |
| [SEC-bench ✔](http://arxiv.org/abs/2506.11791) | 200 CVEs reais, tarefas de PoC e patch | Benchmark de PoC já automatizado |

**Crítica honesta — que classes cabem numa flag?** (ponto que o experimento A deve resolver, não
assumir):

| Classe | Cabe em flag/canário mecânico? | Como |
|---|---|---|
| **RCE / execução arbitrária** | **Sim, limpo** | Flag secreta gerada na execução; exploit só sai com execução; conferir presença da flag na saída/arquivo/conexão (as metas *file creation*, *outbound service* do CVE-Bench) |
| **Leitura arbitrária / exfiltração** | **Sim** | Plantar segredo (canário) fora do que o componente deveria ler; sucesso = segredo recuperado. É a verdade CTF já decidida (D2), aplicada ao exploit |
| **Escape de sandbox/container** | **Sim** | Flag acessível só fora do sandbox; é o `t1b_fs_escape` generalizado (`assets/apps/t1b_fs_escape.py`) |
| **Corrupção de memória** | **Sim (via ARVO/CyberGym)** | Crash de AddressSanitizer no binário pré-patch e não no pós — predicado diferencial objetivo |
| **DoS** | **Parcial/frágil** | Precisa de um limiar (tempo, memória, indisponibilidade). CVE-Bench checa "índice ficou irresponsivo", mas limiar é arbitrário e ruidoso na CVM compartilhada (canais de tempo, [E2c](E2c_ameacas_oci.md) §4 S3) |
| **Erro de lógica / autorização** | **Difícil** | "Admin sem credencial" exige modelar o estado esperado (CVE-Bench tem *unauthorized admin login*, mas é específico por app); não há flag genérica |
| **Falha criptográfica** | **Em geral não** | "A chave é fraca" raramente vira um gatilho binário reproduzível; é propriedade, não evento |

**Conclusão provável a medir:** a prova mecânica cobre bem **RCE, leitura/exfiltração, escape e
corrupção de memória** (as classes que também dominam o SBOM de imagens OCI), e **mal** cobre DoS,
lógica e cripto. Isso **reduz o escopo** do rumo vigente de forma defensável — que é o objetivo
declarado — mas precisa ser dito como limitação, não escondido. Métrica: % de CVEs de cada classe
com predicado mecânico que **falha quando deve** (um predicado que nunca falha não prova nada).

### 7.2 Experimento B — propagação pelo SBOM

Montar um grafo componente→app a partir de imagens OCI reais (reusando o proxy de fetch, E2b.3, ou
SBOMs públicos) e, dada uma vuln num componente, medir **corretude** (dependentes marcados vs. reais)
e **tempo até marcar**. Casos de estudo de propagação profunda:
[Log4Shell (Google OSV: milhares de pacotes Maven afetados, ~8% do ecossistema)](https://security.googleblog.com/2021/12/understanding-impact-of-apache-log4j.html) **(números a conferir na fonte primária)**;
[npm "small world" ✔](https://arxiv.org/pdf/1902.09217); [propagação em árvores de dependência npm, ICSE'22 ✔](https://doi.org/10.1145/3510003.3510142).
**Risco medido aqui:** SBOMs são incompletos e atacáveis — [geração de SBOM é inconsistente e
sujeita a *parser confusion*, DSN'24 ✔](https://doi.org/10.1109/dsn58291.2024.00018). Métrica:
precisão/recall da propagação sob SBOM imperfeito.

### 7.3 Experimento C — custo da verificação em CVM
Reaproveitar as campanhas de overhead de CVM já no repo (`assets/apps/cvm_overhead_probe.py`,
`assets/tests/run_cvm_overhead_campaign.sh`) para medir US$/prova e latência. Referência externa de
ordem de grandeza: AIxCC relatou **~US$ 152 por tarefa** de análise/patch
([DARPA AIxCC results ✔](https://www.darpa.mil/news/2025/aixcc-results)); SEC-bench, **US$ 0,87 por
instância** só para montar o ambiente ([SEC-bench ✔](http://arxiv.org/abs/2506.11791)).

### 7.4 Experimento D — incentivos (teoria dos jogos / simulação)
Modelo: caçador escolhe entre (reivindicar no DNAT: recompensa R certa) e (atacar app externa:
ganho V incerto, risco legal). Variar R, a opacidade dos dependentes e o preço de mercado negro.
Ancorar em dados reais: [exploits no mercado negro custam igual ou mais que bounties legítimos, CCS'17 ✔](https://doi.org/10.1145/3133956.3133960);
[cada caçador acha um número limitado de bugs, Journal of Cybersecurity 2017 ✔](https://doi.org/10.1093/cybsec/tyx008);
[incentivo monetário correlaciona com nº de reports, CCS'15 ✔](https://doi.org/10.1145/2810103.2813704).
Resultado-alvo: região de R em que reivindicar domina.

### 7.5 Esforço estimado (semanas, com o prazo de 02/dez e S2–S5 em [PLANO.md](../PLANO.md))

| Item | Esforço | Viável até 02/dez? |
|---|---|---|
| A (verificabilidade por classe, 3–4 datasets) | 2–3 sem | Sim, se cortar a 2 classes + 2 datasets |
| B (propagação SBOM) | 2 sem | Sim (SBOMs públicos; grafo simples) |
| C (custo em CVM) | 0,5 sem | Sim (campanhas já existem) |
| D (modelo de incentivo) | 1–1,5 sem | Sim (modelo analítico + simulação pequena) |
| Vault no contrato + harness (mínimo demonstrável) | 2 sem | Apertado; demonstração, não produção |

**Realista para 11 páginas:** A + B + C fortes, D como modelo analítico, contrato como protótipo
demonstrado. A ocultação de dependentes (§5.5) é o item de maior risco de prazo.

---

## 8. Trabalhos relacionados e lacuna

**Provar/vender conhecimento de exploit em TEE.** [Sealed-Glass Proofs, EuroS&P 2017 ✔](https://doi.org/10.1109/eurosp.2017.28):
enclave SGX + contrato inteligente formam uma plataforma de bug bounty / solicitação de zero-day com
*fair exchange* e proteção contra retirada injusta da recompensa — **é o parente mais próximo**.
Diferença: eles verificam/vendem **um** exploit; não há cadeia de suprimentos nem propagação a
dependentes, e assumem SGX com vazamento ilimitado (o nosso modelo é CVM plana, D4).

**Bounties principiados em contrato.** [Hydra, USENIX Security 2018 ✔](https://www.usenix.org/conference/usenixsecurity18/presentation/breindenbach):
"exploit gap" + N-of-N-version programming tornam a recompensa alta o bastante para a divulgação ser
a jogada racional, com *Submarine Commitments* contra *bug withholding*. Reusamos o **princípio de
incentivo**, não o mecanismo (eles transformam o programa; nós rodamos o exploit numa CVM).

**Provas de exploit em zero-knowledge.** [Cheesecloth, USENIX Security 2023 ✔](http://arxiv.org/abs/2301.01321)
(prova ZK de Heartbleed/FFmpeg); [Green et al., PoPETs 2023 ✔](https://doi.org/10.56553/popets-2023-0036)
(MSP430, desafios Microcorruption); [DARPA SIEVE](https://www.darpa.mil/news/2021/zero-knowledge-proofs);
[zkPoEX](https://www.risczero.com/blog/zkpoex) (PoC de reentrância, hackathon). ZK **esconde o exploit
do verificador**; o nosso desenho **não** (o operador vê). Trade-off a declarar: TEE é muito mais
barato e genérico, mas confia no operador — exatamente a fronteira de D3/D4.

**SBOM, proveniência, propagação.** [SLSA](https://slsa.dev/spec/v1.0/levels),
[in-toto, USENIX Security 2019 ✔](https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias),
[Sigstore, CCS 2022 ✔](https://doi.org/10.1145/3548606.3560596),
[OSV](https://ossf.github.io/osv-schema/), [GUAC](https://guac.sh/),
[VEX/CISA](https://www.cisa.gov/sites/default/files/2023-09/Vulnerability%20Exploitability%20eXchange%20%28VEX%29_508c.pdf).
SBOM privado em ZK: [zkSBOM ✔](http://arxiv.org/abs/2605.00076) e
[VeriSBOM ✔](http://arxiv.org/abs/2602.13682) (consultar vuln sem revelar o resto do SBOM) — relevante
para a **ocultação de dependentes** (§5.5). Propagação empírica:
[Docker Hub, CODASPY'17 ✔](https://doi.org/10.1145/3029806.3029832) (>180 vulns/imagem em média),
[contêineres desatualizados, SANER'19 ✔](https://doi.org/10.1109/saner.2019.8668013),
[dependências que importam, ESEM'18](https://arxiv.org/abs/1808.09753),
[npm USENIX'19 ✔](https://arxiv.org/pdf/1902.09217).

**Economia de bounty / mercados de vulnerabilidade.**
[Böhme, ETRICS 2006 ✔](https://doi.org/10.1007/11766155_21) (taxonomia de mercados);
[Kannan & Telang, Management Science 2005 ✔](https://doi.org/10.1287/mnsc.1040.0357) (mercado não
regulado em geral perde para CERT); [Finifter et al., USENIX Security 2013 ✔](https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/finifter)
(VRPs são custo-efetivas); [Maillart et al., 2017 ✔](https://doi.org/10.1093/cybsec/tyx008);
[Zhao et al., CCS 2015 ✔](https://doi.org/10.1145/2810103.2813704);
[Allodi, CCS 2017 ✔](https://doi.org/10.1145/3133956.3133960) (preço de mercado negro ≥ bounty);
[Akgul et al., USENIX Security 2023 ✔](https://www.usenix.org/conference/usenixsecurity23/presentation/akgul)
(perspectiva dos caçadores); [Wachs 2022](https://arxiv.org/pdf/2204.06905). Plataformas:
[HackerOne IBB 80/20](https://www.hackerone.com/press-release/hackerone-expands-internet-bug-bounty-improve-collective-security-software-supply),
[Immunefi](https://immunefi.com/bug-bounty/immunefi/information/) (% dos fundos em risco até um teto),
[Hats Finance](https://research.lido.fi/t/bug-bounty-vault-proposal-by-hats-finance/5404) (vault
aberto a depósitos), [huntr (IA/ML)](https://protectai.com/threat-research/november-vulnerability-report),
[Code4rena/Sherlock](https://docs.code4rena.com/awarding) (audit contest).

**Benchmarks de exploit reproduzível / agentes.** [Cybench, ICLR'25 ✔](https://arxiv.org/abs/2408.08926),
[CVE-Bench ✔](https://arxiv.org/abs/2503.17332), [CyberGym ✔](http://arxiv.org/abs/2506.02548),
[SEC-bench ✔](http://arxiv.org/abs/2506.11791),
[BountyBench ✔](http://arxiv.org/abs/2505.15216) (impacto em US$ de agentes atacantes/defensores),
[AIxCC ✔](https://www.darpa.mil/news/2025/aixcc-results), [OSS-Fuzz](https://github.com/google/oss-fuzz).

**Lacuna (o que é novo de fato).** Há (a) provas de exploit em TEE/ZK, (b) bounties em contrato, (c)
grafos de SBOM/propagação, (d) economia de bounty — mas **ninguém une os quatro**: um mercado em que
a recompensa é liberada por **verificação mecânica executável** e a validação **propaga pela cadeia
de suprimentos** marcando dependentes, com **ocultação dos dependentes como alavanca de incentivo**.
Busca por "bounty + notificação automática a dependentes + marketplace SBOM" não achou trabalho que
combine os três (busca de 2026-10-26; ausência de achado não prova novidade). É uma lacuna
real; o risco é a parte **nova** (ocultação + propagação) ser fina demais se a verificação mecânica
(a parte mais forte) for herdada de C4/D2.

**Âncoras no próprio DSN** (detalhes em [GUIA_DSN.md](../referencias/GUIA_DSN.md); conferidas na
consolidação de 2026-10-26):
- **[9] OCTOPOCS, DSN'21 ✔** ([10.1109/DSN48987.2021.00032](https://doi.org/10.1109/DSN48987.2021.00032)):
  reforma a PoC original para **verificar mecanicamente** a vulnerabilidade no software que herdou o
  código. É o vizinho mais próximo de C1 dentro do DSN; diferença: nós marcamos pela presença no
  SBOM e verificamos na CVM, com dependentes ocultos. **Precisa entrar no related work.**
- **[2] SBOM por metadados, DSN'24 ✔** ([10.1109/dsn58291.2024.00018](https://doi.org/10.1109/dsn58291.2024.00018)):
  SBOM gerado por metadados erra e pode ser manipulado; motiva o SBOM do build atestado (E2b).
- **[1] PDGraph, DSN'21**: 42 mil projetos ainda dependem de versões vulneráveis divulgadas;
  motiva a marcação imediata dos dependentes.
- **[10] Silent fixes, DSN'25**: quase 50% das vulnerabilidades ficam > 30 dias expostas após a
  correção silenciosa; motiva divulgação com prova e marcação.
- **[3] Pacotes maliciosos, DSN'25** e **[5] VCAligner, DSN'26**: cadeia de suprimentos é tema
  recorrente no DSN, embora o CFP não o nomeie.
- **[21] Reentrancy Redux, DSN'25** e **[26] Iniva, DSN'24**: exploits reais em contratos e
  compatibilidade de incentivos aceitos no DSN (apoio a C2/C3).

---

## 9. Riscos

**Técnicos.**
- A prova mecânica só cobre algumas classes (§7.1): DoS, lógica e cripto ficam de fora. Se o catálogo
  real for dominado por essas, o mercado cobre pouco.
- SBOM incompleto/atacável ⇒ propagação com falsos negativos ([DSN'24 ✔](https://doi.org/10.1109/dsn58291.2024.00018)).
  Um componente fora do SBOM não propaga.
- Rodar exploit não confiável na CVM é o caso para o qual o executor já foi endurecido (X1–X6,
  [E2c](E2c_ameacas_oci.md) §3), mas aqui o exploit **quer** escapar — é o pior caso do design.
- Flag/canário mal gerado = prova trivial de forjar (predicado que não falha quando deveria).

**Éticos (uso dual — o mais sério).**
- O catálogo público de componentes atacáveis + recompensa é, literalmente, **uma lista de alvos com
  preço**. Mesmo ocultando dependentes, a existência de recompensa sinaliza "aqui vale a pena atacar".
- **Inferência dos dependentes:** o tamanho da recompensa e a popularidade do componente permitem
  adivinhar quem depende dele (recompensa alta ⇒ muitos/valiosos dependentes). A ocultação (§5.5) é
  frágil; mitigação parcial com SBOM cego em ZK ([zkSBOM ✔](http://arxiv.org/abs/2605.00076)) tem custo
  e vazamento residual medido pelos próprios autores.
- CFP do DSN exige tratar vulns de alto impacto (contato com fabricantes) e passar por comitê de
  ética (§10). Publicar o desenho de um "mercado de alvos" precisa de justificativa forte.

**Econômicos.**
- **Dono pagando a si mesmo / conluio:** dono do componente patrocina, um caçador cúmplice reivindica,
  a recompensa volta — com propagação punindo apps de concorrentes. Precisa de anti-conluio.
- **Sybil:** vários pseudônimos para dominar reivindicações/patrocínios (o split do Code4rena é
  desenhado contra isso; o nosso não, ainda).
- **Recompensa < mercado negro:** [Allodi, CCS'17 ✔](https://doi.org/10.1145/3133956.3133960) mostra
  que exploits valem igual ou mais no submundo; se R não bater o preço negro **e** o ganho de atacar
  apps reais, o incentivo falha — é o cerne do Experimento D.
- **Spam de prova / "AI slop":** agentes geram submissões em massa; sem custo por submissão o
  verificador afoga (lição do [curl](https://www.theregister.com/2026/01/21/curl_ends_bug_bounty/)).

**Legais.**
- *Safe harbor*: [política do DOJ de 2022 (CFAA) protege pesquisa de boa-fé](https://www.mofo.com/pdf/resources/insights/220525-cyber-crime-charging-policy),
  mas é política, não lei, e não cobre extorsão — um mercado que "paga para não atacar" beira a linha.
- **Divulgação coordenada e CRA:** a [EU Cyber Resilience Act passa a exigir reporte em 24h de vuln
  ativamente explorada a partir de 11/set/2026](https://www.jonesday.com/en/insights/2026/07/eu-cyber-resilience-act-24hour-reporting-duties-start-september-11-2026) **(detalhes a conferir no
  texto da regulação)** — o embargo do DNAT tem de conviver com prazos legais.

**Prazo.** O vault+harness+ocultação é mais engenharia nova do que o rumo vigente reaproveita; o item
de ocultação (§5.5) pode não fechar até 02/dez e virar "trabalho futuro", enfraquecendo C2.

---

## 10. Encaixe no CFP do DSN 2027

CFP: [dsn2027-berlin.github.io/call-for-contributions](https://dsn2027-berlin.github.io/call-for-contributions/).
Regular paper 11 páginas (D1/[PLANO.md](../PLANO.md)); DSN funde **dependabilidade e segurança**.

| Tópico do CFP | Encaixe |
|---|---|
| **Distributed ledgers/blockchains** (inclui *zero-knowledge proofs*, contratos via "cryptocurrencies") | Vault/escrow em contrato; ocultação por compromisso/ZK |
| **Hardware → TEEs** | Verificação na CVM confidencial é o núcleo |
| **Software → software security, dependable software** | Cadeia de suprimentos, SBOM, propagação |
| **AI/ML e Agentic AI (prompt injection, ataques)** | Atacantes/defensores como agentes (BountyBench, CVE-Bench) na avaliação |
| **Models and methodologies (benchmarking, field data)** | C4: benchmark de verificação+propagação |

**Observação:** "software supply chain" e "security economics" **não** são rubricas nomeadas no CFP
(confirmado na fonte); entram via "software security", "distributed ledgers" e "models/methodologies".
Isso é levemente menos central do que o rumo vigente, que casa direto com "AI/ML for security". O CFP
também **exige** seção de ética para vulns de alto impacto e disclosure — aqui é mandatório, não
opcional (§9).

---

## 11. Perguntas em aberto

1. **Qual a fração real de CVEs verificável por flag mecânica?** (Experimento A decide se a tese se
   sustenta.) Se for baixa fora de RCE/memória, o mercado cobre pouco — melhor ou pior que o Juiz amplo?
2. **A ocultação de dependentes resiste à inferência** por recompensa/popularidade? Precisa de ZK
   (zkSBOM/VeriSBOM) e, se precisar, o custo cabe no prazo?
3. **On-chain vs. off-chain:** o que fica público no contrato sem vazar dependentes? Os eventos atuais
   (`DnatMarketplace.sol:91-97`) já expõem IDs; o vínculo app↔componente pode sair do on-chain?
4. **Quem define que um componente é "atacável"?** Qualquer um pode abrir vault sobre qualquer ativo
   sem o dono consentir — isso é feature (pressão) ou abuso (difamação)?
5. **Prova de exploit sem revelar ao operador:** vale o custo de ZK, ou TEE+confiança no operador
   (coerente com D3) é suficiente e honesto como limitação?
6. **Interação com o Juiz de IA:** a alternativa **substitui** C1/C2 do rumo atual ou **coexiste**
   (o harness de prova é o mesmo mecanismo CTF)? Se coexiste, qual é a contribuição principal do
   artigo?
7. **Desarmar o uso dual:** é publicável sem virar manual de criação de um mercado de alvos? Que
   salvaguardas o comitê de ética exigiria?
8. **Preço de equilíbrio:** existe R que bate o mercado negro **e** fecha economicamente para a
   plataforma? (Experimento D.)
```
