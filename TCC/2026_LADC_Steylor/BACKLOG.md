# Backlog & Orientações — Artigo LADC 2026 (DNAT generalizado)

> Documento-guia para a revisão completa do artigo após os comentários do
> Prof. Andrey (e-mail de 2026-06-22 + comentários no Overleaf) e a reunião
> presencial. **Nada deve ser implementado fora do que está priorizado aqui.**
> Atualizar o campo *Status* de cada item conforme andamos.
>
> Arquivo-fonte do artigo: `ladc.tex`. Subseções já redigidas estão em
> `evaluation_data/*.tex`. Dados medidos em `evaluation_data/results_raw.md` e
> `evaluation_data/results_ab_campaign.md` (campanha A/B de 2026-06-11).

---

## 0. Decisões fechadas (o norte do trabalho)

| Decisão | Valor | Origem |
|--------|-------|--------|
| Enquadramento | **Caminho 1.a — generalizar o problema do DNAT** (não só ajustar o DNAT prático) | e-mail Andrey 2026-06-22 |
| Escopo ("funções pequenas") | **Processamentos que cabem em 1 VM** (workloads single-VM) | Andrey 2026-06-22 |
| Modelo de ataque | Confia na AWS/SEV-SNP (em vez de SGX do DNAT original) | caminho 1.a |
| Divisão | Steylor → **Evaluation (4–5 págs)**; Eduardo → Related Work; Andrey → intro/abstract/conclusão | e-mail |
| Baselines da avaliação | **M0 (sem microVM) + A (centralizado+µVM) + B (compartimentado) + DNAT/SGX citado** | reunião |
| Métricas quantitativas novas | **Tempo de boot (breakdown) + Custo AWS/execução + Custo blockchain (gas)** | reunião |
| Metodologia de segurança | **Mapear os testes T1–T5 no STRIDE** | comentário Andrey na Evaluation |
| Modo de trabalho | Varredura completa do artigo, guiada por este backlog | reunião |

**Implicação central do caminho 1.a:** Andrey foi explícito que ele "precisa de um
trabalho bem forte na seção de design". Hoje o `\section{Proposal}` é um stub
`(...)`. **Esse é o maior buraco do artigo** e o item de maior risco.

**Tensão a gerenciar:** o rascunho e a avaliação ainda são muito *DNAT-específicos*
(IPFS, blockchain, 3 CVMs). O caminho 1.a pede generalizar a linguagem: planos
**control / build / execution** como *padrão de projeto*; storage distribuído e
ledger como *instâncias* (IPFS e blockchain como uma das opções, usadas de forma
simplificada).

---

## 1. Estrutura-alvo do artigo e estado atual

| Seção | Estado hoje | Alvo | Dono |
|-------|-------------|------|------|
| Abstract | rascunho ("1ª versão") | reescrever; incluir app realista + número de overhead | Andrey |
| Introdução | esqueleto + bullets | multi-stakeholder + contraste forte com DNAT/SGX | Andrey/Eduardo |
| Background | 3 subseções DNAT-específicas | generalizar comp. confidencial / storage / ledger; cortar o que não se usa | Steylor |
| Problem definition | bom, mas **lista de requisitos vazia** | fechar com lista de requisitos/desafios | Steylor |
| Proposal/**Design** | **stub `(...)`** | **seção de design forte** (exigência do 1.a) | Steylor/Andrey |
| Implementation | texto pronto (`section_implementation.tex`) | integrar + resolver duplicação estrutural | Steylor |
| Evaluation | madura (texto+tabelas+A/B) | reorganizar via STRIDE + matriz comparativa + métricas novas | **Steylor** |
| Related Work | **vazia** | DNAT + limitações + trabalhos recentes | Eduardo |
| Conclusion | texto pronto (`section_conclusion.tex`) | integrar; repetir motivação + número | Andrey |

---

## 2. Backlog por seção (itens acionáveis)

> Legenda de esforço: 🟢 baixo (texto) · 🟡 médio (texto+dados existentes) ·
> 🔴 alto (precisa de código/medição nova). Status: `TODO` / `WIP` / `DONE`.

### B1 — Abstract  ·  dono Andrey · 🟢 · TODO
- Reescrever (Andrey já marcou que é provisório).
- **Incluir uma aplicação realista** (comentário do prof) — ver B7.6.
- Preencher o overhead real no lugar de `$X\%$`.

### B2 — Introdução  ·  dono Andrey/Eduardo · 🟡 · TODO
- Reforçar o ângulo **multi-stakeholder** (controladores de dados, devs, infra que desconfiam entre si).
- **Contrastar melhor com o DNAT** e expor suas limitações: execução em **SGX dificulta o reuso** de aplicações (recompilação/adaptação) e tem **problema de dependências**. Aqui usamos Firecracker → permite dependências e reuso sem recompilar.
- Declarar explicitamente o **escopo "single-VM" ("funções pequenas")** como premissa.
- Fechar com organização do artigo.

### B3 — Background  ·  dono Steylor · 🟡 · TODO
- (i) Trocar o foco da subseção *Confidential computing*: a ênfase do paper **não é** comp. confidencial. Dizer o mínimo e enfatizar a **oportunidade** que ela traz: não precisa copiar a infra e **simplifica o papel de validação da aplicação**.
- (ii) *Blockchain*: manter, mas conectar a **rastreabilidade/traceability** (palavra-chave do título).
- (iii) **Generalizar o storage**: falar em "armazenamento distribuído compatível com os objetivos" e apresentar **IPFS como uma opção, usada de forma simplificada** — não como requisito.
- Cortar tudo que não será de fato usado na implementação.

### B4 — Problem definition  ·  dono Steylor · 🟢 · TODO
- O texto anuncia "A secure solution must satisfy the following requirements:" e **não lista nada**. Escrever a lista (sugestão de requisitos a confirmar):
  - R1 Separação de privilégios entre fases (control/build/execution).
  - R2 Build com rede isolado de estado sensível e do runtime.
  - R3 Execução **sem rede** (sem canal de exfiltração) e efêmera.
  - R4 Confidencialidade de dados e de aplicação entre partes mutuamente desconfiadas.
  - R5 Rastreabilidade/controle de acesso verificável (ledger + content hash).
  - R6 Reuso de aplicações com dependências, sem recompilação (contraste com SGX).
- Considerar enquadrar como "multi-stakeholder ML" (comentário solto do prof) — confirmar se cabe.

### B5 — Proposal / Design  ·  dono Steylor/Andrey · 🔴 · TODO  **(PRIORIDADE)**
- Escrever a seção que hoje é `(...)`. Para o caminho 1.a, generalizar:
  - O **padrão de três planos** (control/build/execution) como solução genérica para processamento não-interativo single-VM entre stakeholders desconfiados — não amarrado ao marketplace DNAT.
  - Mapear **cada requisito (R1–R6) → mecanismo de design**.
  - Modelo de ameaça generalizado (confiança na AWS/SEV-SNP; o que é TCB).
  - Storage e ledger como **instâncias plugáveis**.
- Resolver a **duplicação estrutural** (ver B10).

### B6 — Implementation  ·  dono Steylor · 🟢 · TODO
- O texto já existe (`section_implementation.tex`) e já é `\input` na linha ~213. Apenas:
  - Resolver o conflito de hierarquia (Proposal tem subseção *Implementation* + `\input` traz um `\section{Implementation}`). Ver B10.
  - Alinhar a linguagem à generalização do B5 (não só "DNAT marketplace").

### B7 — Evaluation  ·  dono Steylor · 🔴 · WIP  **(SUA PARTE PRINCIPAL)**
Detalhado na Seção 3 deste backlog. Sub-itens:
- B7.1 Definir e construir o **M0** (variante sem microVM). 🔴 · **DONE — medido 2026-06-23**: M0 executa em **0,07 s** vs A/B **25,2 s** (mesmo host); microVM custa **~25,1 s**. M0 falha exfiltração (eth0) e contenção (6 segredos achados). Dados em `results_m0_campaign.md`.
- B7.2 Montar a **matriz comparativa "métrica × arquitetura"** (M0/A/B/SGX). 🟢 · **DONE** — `tab:comparison` em `results_tables.tex`; M0/A/B totalmente medidos (latência, overhead, gas); resta só a coluna **SGX** (citar do DNAT original).
- B7.3 Instrumentar **boot breakdown**. 🔴 · **PARCIAL** — o overhead agregado do microVM já é conhecido (~25,1 s = A − M0); falta só a **decomposição por fase** (boot kernel / discovery / sync / shutdown).
- B7.4 ~~Calcular **custo AWS/execução**~~. **REMOVIDO da matriz** (decisão 2026-06-23): não rodamos em VM realmente confidencial, então não há base realista p/ custo AWS SEV-SNP; coerente com a ressalva de substrato adicionada à evaluation/implementation.
- B7.5 Medir **custo de blockchain (gas)**. 🟢 · **DONE — medido 2026-06-23** (`smart-contract/scripts/measure-gas.js`): registerAsset dataset **388,7k** (bloom `0x`; +185k/256 B) / application **326,6k**; purchaseAccess **96,5k**. Idêntico p/ M0/A/B (contrato = control plane compartilhado). Dados em `results_gas.md`.
- B7.8 ✅ **DONE** — ressalva de substrato confidencial: adicionada em *Threats to Validity* (`section_evaluation.tex`) e na abertura de `section_implementation.tex` (container é stand-in da CVM; muda só a implementação, não a arquitetura/análise).
- B7.6 Reorganizar a segurança via **STRIDE** (mapear T1–T5). 🟢 · **DONE** — `tab:stride` + subseção "Security Evaluation with STRIDE" em `section_evaluation.tex`.
- B7.7 (opcional) Adotar uma **aplicação realista** como workload (pedido do Abstract). · TODO
- Manter o limite de **4–5 páginas**.

### B8 — Related Work  ·  dono Eduardo · 🟡 · TODO
- Recuperar o related work do DNAT e suas limitações (tecnologias limitadas, SGX).
- Acrescentar trabalhos recentes e semelhantes (ver quem citou o DNAT / quem ele citou).

### B9 — Conclusion  ·  dono Andrey · 🟢 · TODO
- Texto já existe (`section_conclusion.tex`, já `\input`). Ajustar:
  - Repetir pontos-chave da motivação + **um número de desempenho** (viabilidade).
  - Trabalhos futuros: blockchain (custo/escala/atraso), IPFS, outras linguagens, atestação remota, mTLS/segmentação.

### B10 — Limpeza estrutural / build LaTeX  ·  dono Steylor · 🟢 · WIP
- ✅ **DONE:** `tab:blast-radius` duplicado resolvido (mantida a versão EN em `section_results_ab.tex`; removida a PT de `results_tables.tex`). Labels únicos verificados.
- ✅ **DONE:** adicionados ao preâmbulo `\usepackage{booktabs}` e `\usepackage{tabularx}` (as tabelas não compilavam sem eles).
- ✅ **DONE:** tabelas de `results_tables.tex` padronizadas em **inglês**.
- ✅ **DONE:** citações ausentes adicionadas ao `sample.bib` (`shostack2014threat` para STRIDE, `agache2020firecracker` citada na Implementation).
- ✅ **DONE:** removidos os stubs vazios `\subsection{Security evaluation}` e `\subsection{Resource Consumption...}` no `ladc.tex` (cobertos pelo STRIDE + Operational Cost).
- ⬜ TODO (Sprint Design): duplicação `\section{Proposal}` → subseções *Architecture*/*Implementation* (stubs) **vs** `\input{section_implementation}` (outro `\section{Implementation}`).
- ⬜ TODO (dono Andrey, área do abstract): keywords herdadas de outro artigo (VPN/SPIRE/MFA) — trocar pelas do tema atual.

---

## 3. Plano de Avaliação (o coração da sua parte)

### 3.1 Conjunto de baselines

| Var. | Nome | O que é | Para que serve |
|------|------|---------|----------------|
| **M0** | Sem isolamento | App roda direto (processo/container), planos colocalizados, **sem microVM** | Quantifica o **custo real do microVM** e mostra que **não há contenção** |
| **A** | Centralizado + µVM | Container único, ativos colocalizados, mas **com** Firecracker | Isola a variável "compartimentação" (mesma sandbox de B) |
| **B** | Compartimentado | Três planos (control/build/execution) + Firecracker | A proposta |
| **SGX** | DNAT original | Números **citados** de `nascimento2020dnat` | Contraste de reuso/recompilação/dependências |

> M0 é o item novo de código: uma variante que executa a app **sem** lançar a
> microVM (mesmo namespace de A). Esperado: latência ≈ tempo de cômputo da app
> (ms–s), boot ≈ 0, e **falha** nos testes de segurança (rede alcançável,
> segredos presentes, estado persiste) — é justamente isso que dá a medida do
> que o isolamento compra.

### 3.2 Matriz comparativa "métrica × arquitetura" (esqueleto a preencher)

| Métrica | M0 | A | B | DNAT/SGX (cit.) |
|---------|----|----|----|------------------|
| Latência de execução (s) | _medir_ | 26,8 | 26,8 | citar |
| Tempo de boot — breakdown (s) | ~0 | _medir_ | _medir_ | citar |
| Latência de build, cache quente (s) | _medir_ | ~114 | ~114 | — |
| Custo AWS / 1k execuções (US$) | _calc_ | _calc_ | _calc_ | — |
| Custo blockchain por registro+compra (gas / US$) | _medir_ | _medir_ | _medir_ | — |
| Tamanho do artefato (MiB) | — | 16 / 19,6 | 16 / 19,6 | — |
| **Blast radius** (ativos alcançáveis) | todos | todos | **nenhum** | parcial |
| Exfiltração bloqueada | não | 7/7 | 7/7 | citar |
| Persistência entre runs | não | não | não | não |
| **Reuso de app c/ deps, sem recompilar** | sim | sim | sim | **não** |

### 3.3 Métricas novas — como medir

**(a) Tempo de boot (breakdown)** 🔴
Instrumentar o ciclo da microVM de execução (`run-vm.sh`) com timestamps,
emitindo marcadores no **console serial** (já usado para `EXECUTION_COMPLETE`):
1. Host: preparo (copiar overlay + criar discos input/output [+ anexar artefato]).
2. Boot do kernel Firecracker até o guest pronto.
3. Descoberta de discos (scan de block devices + mount).
4. Execução da app (`run.sh`) — hoje em ms.
5. Sync do disco de saída + marcador de conclusão.
6. Shutdown gracioso (+ janela de graça) + `cleanup`.
Reportar a fração que é *lifecycle* vs *cômputo* (a tese: ~30 s é boot, não app).

**(b) Custo AWS / execução** 🟡 (sem código; confirmar premissas)
Dois modelos — apresentar o (i) e usar (ii) como sanity check:
- (i) **Proporcional a recurso** (estilo Fargate, casa com "funções pequenas"):
  `custo = vCPU·s × preço_vCPU·s + GiB·s × preço_GiB·s`, usando exec = 1 vCPU /
  0,5 GiB por ~27 s e build = 2 vCPU / 1,5 GiB por ~114 s.
- (ii) **Instância dedicada confidencial** (SEV-SNP, ex. família `m6a`/`c6a`):
  `custo = (US$/h da instância ÷ 3600) × duração`.
- **Confirmar com o orientador:** tipo de instância confidencial e preço de
  referência (região, on-demand). Declarar a premissa no texto.

**(c) Custo de blockchain (gas)** 🟡
Capturar `gasUsed` dos recibos das txs de `registerAsset`/`register` e
`purchaseAccess` (já há tx no `results_raw.md`). Converter para US$ com um
preço de gás + câmbio de referência. **Premissa honesta:** a cadeia local é
Hardhat → reportar como *projeção* sobre uma cadeia pública, não custo real.

### 3.4 Segurança via STRIDE (mapeamento dos testes existentes)

| STRIDE | Como a arquitetura trata | Evidência (teste atual) |
|--------|--------------------------|--------------------------|
| **S**poofing | Acesso mediado por contrato; identidade on-chain (`purchaseAccess`) | T5 (`hasAccessByIds`) |
| **T**ampering | Integridade por content hash SHA-256 on-chain; artefato/cache read-only | T5 (binding), T2b (cache RO) |
| **R**epudiation | Ledger registra registro/compra (rastreabilidade) | T5 (registro on-chain) |
| **I**nformation disclosure | Execução **sem rede** + sem segredos + blast radius isolado | T1, T1b, T4 |
| **D**enial of service | microVM efêmera com caps (1 vCPU/512 MiB) + teardown limita vazamento de recurso | T3 *(área mais fraca — ser honesto: não é foco)* |
| **E**levation of privilege | Separação de planos; código de build/dep contido no plano isolado | T4, T2a (import-time), T2b (build-time) |

> Apresentar a Evaluation por estas seis letras, com cada uma apontando para o
> teste e o número. DoS é o ponto fraco — declarar como limitação/trabalho futuro.

### 3.5 O que já está medido (reaproveitar) × o que falta

| Item | Já temos | Falta |
|------|----------|-------|
| Exec latency A/B | ✅ 26,8 s (n=3) e 31,4 s (n=6) | M0 |
| Build latency A/B + cache | ✅ 30–137 s | M0 |
| Tamanho de artefato | ✅ 16 / 19,6 MiB | — |
| Blast radius B vs A | ✅ medido ao vivo | coluna M0 + SGX |
| T1/T1b/T2/T3/T4/T5 | ✅ medidos | rodar em M0 (devem falhar) |
| Boot breakdown | ❌ | instrumentar |
| Custo AWS | ❌ | calcular + confirmar premissas |
| Custo gas | ❌ | capturar `gasUsed` |
| App realista | ❌ | escolher workload |

---

## 4. Riscos e decisões em aberto (confirmar com Andrey/Eduardo)

1. **M0 precisa ser construído** (variante sem microVM). Esforço de código pequeno, mas é pré-requisito de várias linhas da matriz.
2. **Números do SGX**: quais valores citar de `nascimento2020dnat`? (boot/latência/overhead — verificar o que o paper reporta).
3. **Custo AWS**: confirmar tipo de instância confidencial (SEV-SNP) e preço de referência; decidir entre modelo proporcional vs instância dedicada.
4. **Custo gas**: assumir projeção sobre cadeia pública — confirmar se reportamos ou deixamos como qualitativo.
5. **Generalização vs evaluation DNAT-específica**: a linguagem genérica do B5/B3 não pode brigar com tabelas cheias de "IPFS/Hardhat/CVM". Padronizar termos.
6. **Aplicação realista**: precisa de uma para o Abstract/Evaluation — definir qual (ex.: um modelo de ML pequeno / estatística sobre dataset sintético maior).
7. **Idioma das tabelas**: padronizar para inglês (hoje há tabelas em PT).

---

## 5. Ordem de execução sugerida

- **Sprint 1 (entrega o pedido presencial):** B7.2 matriz + B7.6 STRIDE + B10 limpeza → consolida o que já está medido numa narrativa comparativa. (Texto, baixo risco.)
- **Sprint 2 (mede o que falta):** B7.1 M0 + B7.3 boot breakdown + B7.5 gas + B7.4 custo AWS → preenche as células `_medir_/_calc_` da matriz.
- **Sprint 3 (a parte estruturalmente cara):** B5 Design forte + B3 Background generalizado + B4 requisitos.
- **Paralelo (outros donos):** B2/B1/B9 (Andrey), B8 (Eduardo).

---

## 6. Mapa de arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `ladc.tex` | Artigo principal (com os comentários `% [AB]`) |
| `evaluation_data/section_implementation.tex` | Implementation (pronto) |
| `evaluation_data/section_evaluation.tex` | Metodologia + resultados de segurança/custo |
| `evaluation_data/results_tables.tex` | Tabelas EN — `tab:stride` (STRIDE) + `tab:comparison` (matriz M0/A/B/SGX) |
| `evaluation_data/section_results_ab.tex` | Comparação A/B ao vivo (EN) — `tab:ab-performance` + `tab:blast-radius` |
| `evaluation_data/section_conclusion.tex` | Conclusão (pronto) |
| `evaluation_data/results_raw.md` | Dados brutos campanha 1 (2026-06-11) |
| `evaluation_data/results_ab_campaign.md` | Dados brutos campanha A/B (2026-06-11) |
| `evaluation_data/results_m0_campaign.md` | Dados brutos campanha M0 vs A vs B, mesmo host (2026-06-23) |
| `evaluation_data/results_gas.md` | Dados brutos de gas register/purchase (2026-06-23) |
| `sample.bib` | Referências |

**Código do M0 (no repo, fora de `TCC/`):**

| Arquivo | Conteúdo |
|---------|----------|
| `vm_runtime/executor.py` | Toggle `DNAT_NO_MICROVM` → escolhe `run-direct.sh` vs `run-vm.sh`; `/health` reporta `mode` |
| `vm_runtime/vm/run-direct.sh` | Runner de execução **direta** (sem microVM); mesmo contrato `workspace/run.sh`, mesma saída JSON |
| `docker/m0-vm.compose.yaml` | Sobe o M0 (= imagem do baseline + `DNAT_NO_MICROVM=1`, portas 6xxx) |

---

## 7. M0 — desenho e implementação (Sprint 2)

**O que é.** M0 = o baseline centralizado (Ambiente A) **sem a microVM de
execução**. É o ponto "sem isolamento" do espectro M0→A→B: isola o **custo do
microVM** (boot ≈ 0, latência ≈ tempo de cômputo da app) e **expõe a contenção**
que o microVM provê (rede alcançável, segredos/env do host visíveis, filesystem
persistente). A vs M0 mede o microVM; B vs A mede a compartimentação.

**Como funciona.** O `executor.py` lê `DNAT_NO_MICROVM`; quando ligado, o
`POST /execute` chama `vm/run-direct.sh` em vez de `vm/run-vm.sh`. O runner direto
extrai o bundle em `/tmp/exec` (mesmo layout que o guest usa, porque o `run.sh`
gerado faz `cd /tmp/exec/workspace`) e roda **o mesmo** `run.sh`, sem Firecracker,
sem discos isolados e sem remover a rede — herdando rede, variáveis de ambiente e
filesystem do container. A saída é o mesmo JSON `{returncode, stdout, stderr}`, de
modo que o resto do pipeline e o harness não mudam. Como roda dentro da imagem do
baseline, os segredos (`ASSET_ENCRYPTION_KEY`, `PRIVATE_KEY`) e os stores
(IPFS, wheel cache, executions) estão colocalizados — é o que faz os testes de
contenção **falharem** em M0, de propósito.

**Como rodar (Sprint 2).**
```bash
# subir o M0 (porta do executor: host 6000 -> container 5000)
docker compose -f docker/m0-vm.compose.yaml up --build -d
# medir latência de execução com o mesmo harness de A/B
EXECUTOR_PORT=6000 bash assets/tests/run_execution_plane_tests.sh
# (opcional) evidência de segurança de M0: rede/segredos/persistência devem PASSAR p/ o atacante
#   T1 deve mostrar EXFILTRATION SUCCEEDED; T1b deve achar segredos.
```

**Resultado esperado / o que preenche na matriz.**
- `tab:comparison` → linha *Execution latency, mean (s)*, coluna **M0** (esperado: ordens de grandeza menor que os 26,8 s de A/B).
- `tab:comparison` → linha *microVM boot/life-cycle overhead*: confirma M0 ≈ 0 e dá o numerador do custo do microVM em A/B (ver B7.3).

**Escopo / caveats.**
- M0 cobre a **execução**. O *build* em M0 ainda usa o builder microVM; uma
  variante de build direto (pip no namespace) é **opcional** e não é necessária
  para o argumento de custo do microVM de execução.
- O **gas** (B7.5) é do control plane e independe do substrato → mesmo valor em
  M0/A/B; mede-se uma vez.
- M0 não roda em VM confidencial (coerente com a ressalva de substrato já no
  artigo); serve como ponto de comparação de custo/contenção, não de CC.
