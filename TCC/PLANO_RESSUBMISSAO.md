# Plano de Ressubmissão — pós-LADC 2026 (submissão #33941)

> Decisões fechadas em 2026-10-08:
> - **Estratégia:** SAC 2027 (16/out) → se rejeitar, DSN 2027 (02/dez) → se rejeitar cedo, SBRC 2027.
> - **Fio condutor:** *separação de privilégios com o build tratado como ameaça de supply chain*.
>   Ledger e storage viram componentes plugáveis (um parágrafo cada), não protagonistas.
> - **Hardware:** só CVMs de nuvem (sem bare metal SEV-SNP) → nada de microVM confidencial
>   própria; o caminho A1 usa os mecanismos gerenciados descritos na Fase 2.
> - **Peso do Andrey:** ele concordou com o SAC e conhece o DSN → ele precisa receber o
>   rascunho do SAC até **13/out** para dar tempo de revisar.

## 0. Calendário

| Evento | Prazo | Resultado | Formato |
|---|---|---|---|
| SAC 2027 (trilha **DADS**; alternativa: SEC) | **16/out/2026** | 13–20/nov | ACM sigconf, double-blind (confirmar o limite de páginas no CFP da trilha; historicamente 8 + 2 pagas) |
| DSN 2027 | resumo 25/nov, artigo **02/dez** | rejeição antecipada 26/jan, final 18/mar | 11 págs (regular) ou 7 págs (*Practical Experience Report*), double-blind, com rebuttal e revisão |
| SBRC 2027 | a confirmar (costuma ser dez/jan) | — | SBC |

Não pode haver submissão simultânea: a versão do DSN só é enviada depois do resultado do SAC
(que sai antes de 25/nov). O trabalho da Fase 2 roda **durante** a revisão do SAC.

---

## 1. Mapa das críticas → ação

Legenda: **R1/R2/R3** = revisor · 🟢 texto · 🟡 dados/código pequeno · 🔴 engenharia nova ·
**S** = entra no SAC · **D** = fica para o DSN.

### 1.1 Problemas de avaliação (a maior fraqueza)

| # | Crítica | Ação | Custo | Alvo |
|---|---|---|---|---|
| E1 | ~25 s "artificial wait", ~20 s de graceful shutdown (R1, R2) | **Bug de engenharia**: `run-vm.sh` espera `SHUTDOWN_GRACE_SECONDS=20` porque o guest faz `poweroff -f` primeiro, e no Firecracker x86 isso não encerra o VMM. Trocar por `reboot -f` (com `reboot=k` o Firecracker encerra) e/ou matar a VM logo após `EXECUTION_COMPLETE` + sync. Polling de 1 s → 50 ms. | 🟡 0,5 dia | S |
| E2 | Separar boot / execução / teardown (R2) | Timestamps no host + marcadores na serial (BACKLOG B7.3): preparo de discos, boot do kernel, descoberta de discos, app, sync, shutdown, cleanup | 🟡 0,5 dia | S |
| E3 | Rodadas únicas, n=1 (R3) | Campanha nova: **n≥30 por célula**, média ± IC95%, mesmo host, ordem aleatorizada | 🟡 1 dia de máquina | S |
| E4 | Workload sintético de 60 linhas; falta caso real (R2, R3, Andrey) | (a) ML real: treino com scikit-learn em dataset público (ex.: UCI Adult ~48k linhas ou detecção de fraude); (b) escala do dataset 1k → 100k → 1M linhas para mostrar a **amortização** do custo fixo; (c) reaproveitar o raytracer e o I/O stress da branch `feat/cvm-direct-mode-deploy`, apresentando-os antes de usar | 🟡 1 dia | S |
| E5 | Ambiente mal descrito: quantas VMs, versões, recursos (R1); `n2d-standard-2` sem explicação | Tabela de ambiente: host/CVM, CPU, RAM, kernel do host e do guest, versões de Firecracker, Docker, Python, Hardhat e IPFS; o que roda em cada máquina. Nota de rodapé sobre o tipo de instância | 🟢 | S |
| E6 | Justificar 1 vCPU / 512 MiB (R2) | Uma frase + mostrar na escala de E4 onde o limite passa a pesar (ou torná-lo configurável por job) | 🟢 | S |
| E7 | Medição da CVM confusa: protótipo sem CVM, mas mede SEV-SNP (R2, R3) | Ver §2: deixar explícito o que rodou dentro da CVM e o que essa medição prova | 🟢/🟡 | S |
| E8 | Gas pouco claro para quem não é da área (R2) | Duas frases (o que é gas, quem paga, por que importa) ou reduzir para uma frase — o ledger deixa de ser protagonista | 🟢 | S |
| E9 | A avaliação mistura perguntas diferentes (R2) | Organizar por perguntas de pesquisa: **RQ1** contenção (STRIDE + blast radius), **RQ2** custo do isolamento (breakdown + escala), **RQ3** custo do substrato confidencial | 🟢 | S |

### 1.2 Contribuição e posicionamento

| # | Crítica | Ação | Custo | Alvo |
|---|---|---|---|---|
| P1 | Objetivo e contribuição pouco explícitos; (ii) e (iii) são atividades, não contribuições (R1) | Parágrafo "Problema no DNAT → o que é novo". Contribuições: **C1** a reformulação como separação de privilégios entre fases, com o build como superfície de ataque de supply chain; **C2** uma arquitetura independente de TEE que remove a dependência do SGX (reuso sem recompilação); **C3** uma avaliação de segurança verificável (STRIDE por interação → testes reproduzíveis) e de custo | 🟢 | S |
| P2 | Comparar com o DNAT: o que já existia e o que é novo (R1) | **Tabela DNAT × este trabalho** (substrato, modelo de ameaça, dependências, build, rede na execução, rastreabilidade, TCB) | 🟢 | S |
| P3 | Tabela R1–R6 × trabalhos relacionados (R3) | Linhas R1–R6 × colunas DNAT, PrivacyGuard, VDDPI, SGXPy, Confidential Containers, este trabalho | 🟢 | S |
| P4 | Escopo difuso, "colcha de retalhos" (R2) | Narrativa única (§0). Cortar detalhes de IPFS e gas; storage e ledger cabem em um parágrafo de "instanciação" | 🟢 | S |
| P5 | Falta um cenário concreto (R2) | Parágrafo de motivação: ex. um hospital (provedor) e uma startup de ML (comprador); job em lote; latência aceitável na ordem de minutos → justifica a ausência de rede e o custo fixo | 🟢 | S |
| P6 | Por que ledger e não assinaturas/CA? (R2) | Argumentar: não há um operador confiável por todos para ser a raiz (a CA seria de quem?), e é preciso uma ordem global e não-repudiável de compras/execuções. Admitir que um *transparency log* (estilo Sigstore/Rekor) é uma instanciação válida → reforça que o componente é plugável | 🟢 | S |
| P7 | Título/abstract prometem "confidential" (R3) | Abstract com a ressalva logo na 1ª frase; avaliar trocar o título (ex.: "Containing Build- and Run-Time Compromise in Multi-Stakeholder Confidential Data Processing") | 🟢 | S |
| P8 | Related work: in-toto, SLSA, SGXPy, Confidential Containers (R2); anais do LADC (R1) | Adicionar ao bib e posicionar; buscar 2–3 artigos do LADC/SBSeg sobre TEE e supply chain | 🟢 | S |

### 1.3 Ameaças e limitações

| # | Crítica | Ação | Custo | Alvo |
|---|---|---|---|---|
| T1 | Canais internos sem autenticação; por que não usar mTLS se é barato? (R1, R3) | **Implementar mTLS interno** (CA interna gerada no deploy, certificados por plano; o executor deixa de alcançar a control API) + rodar de novo o T4 → o resíduo do *confused deputy* fecha | 🟡 1 dia | S se der tempo, senão D |
| T2 | Explicar o impacto prático do *confused deputy* (R3) | Se T1 entrar: vira "fechado, antes/depois". Se não: cenário concreto do que vaza (saídas anteriores, enumeração) | 🟢 | S |
| T3 | DoS por execuções ilimitadas (R2) | Cota por comprador no contrato (execuções por compra) + fila com concorrência máxima no executor | 🟡 0,5 dia | S (cota) / D (fila) |
| T4 | Confiança total no operador de infraestrutura (R1, R2, R3) | Mitigação real na Fase 2 (§2). No SAC: discutir as mitigações possíveis (CVM por plano + atestação ancorada no ledger) | 🟢 → 🔴 | S texto / D código |
| T5 | Só Python e wheels (R1, R2) | Generalizar o contrato do build ("resolvedor de dependências do ecossistema X"); demo em Node/npm ou R | 🔴 2–3 dias | D |
| T6 | Cache de wheels: sdist malicioso persiste (R2) | Particionar o cache por comprador + hash fixo das wheels | 🟡 | D |

### 1.4 Redação

| # | Ação | Alvo |
|---|---|---|
| W1 | Background mínimo de CVM (SEV-SNP, atestação) e de ledger (transação, contrato, quem paga) | S |
| W2 | Definir sdist/wheel na 1ª menção; apresentar o raytracer; trocar "per-run state hygiene" por "per-run state cleanup (no residual sockets, disks or mounts)" | S |
| W3 | Corrigir as frases apontadas pelo R1; nota de rodapé antes do ponto (`(I3).\footnote{}` → `(I3)\footnote{}.`); "malicious sdist" definido | S |
| W4 | Revisão de inglês da Implementação em diante (R2: a qualidade cai depois da Arquitetura) | S |

---

## 2. Confidencialidade — o que dizer agora e o que fazer depois

**Situação atual:** o sistema rodou dentro de uma CVM confidencial grande; o Firecracker
**não tem confidencialidade aninhada** (não existe hoje em CVMs de nuvem).
⚠️ *Confirmar qual leitura vale*: (a) os três planos rodaram em **modo direto** (sem
Firecracker) dentro da CVM, ou (b) o Firecracker rodou aninhado dentro da CVM, sem SNP próprio.

- **Se (b):** é um argumento forte e precisa ser dito com todas as letras. A memória da
  microVM (L2) é memória da CVM (L1), portanto cifrada contra o operador. A confidencialidade
  frente ao operador vem da CVM e o isolamento entre planos/jobs vem da microVM. Isso
  responde diretamente ao R2 ("rodar microVM dentro de TEE"). Medir o custo real do
  Firecracker aninhado na CVM.
- **Se (a):** dizer que a confidencialidade frente ao operador vale na granularidade da CVM,
  e que o isolamento por job dentro da CVM ainda depende de um mecanismo sem virtualização
  (ver D-A abaixo).

**Fase 2 (DSN) — confidencialidade de verdade usando só nuvem:**

| Opção | O que é | Prós | Contras |
|---|---|---|---|
| **D-A gVisor dentro da CVM** | Sandbox com kernel em espaço de usuário (`runsc --network=none`), dispensa virtualização aninhada | leve, efêmero, sem rede, roda em qualquer CVM | fronteira mais fraca que uma VM; TCB maior |
| **D-B Azure Confidential Containers (ACI / AKS CoCo)** | Cada container group roda numa *utility VM* SEV-SNP própria com política de atestação | **é uma microVM confidencial gerenciada**: microVM + TEE sem bare metal; o hash da política vai para o ledger (análogo do MRENCLAVE) | depende do Azure; custo e tempo de boot a medir |
| **D-C Uma CVM efêmera por execução** | O execution plane sobe uma CVM nova por job, sem IP público e com egress negado | simples de argumentar, confidencialidade total | boot na casa de dezenas de segundos; custo |

**Recomendação:** D-B como instanciação principal (atende a crítica central do R2), D-A
como alternativa leve. Em qualquer caso: **atestação remota ancorada no ledger** — o
contrato só libera a chave do dataset para uma medição/política registrada — e **mTLS
atestado** entre os planos.

---

## 3. Cronograma do SAC (8 dias)

| Dia | Tarefa | Itens |
|---|---|---|
| **qui 08 – sex 09** | Puxar a versão submetida do Overleaf para o repo; integrar a branch `feat/cvm-direct-mode-deploy`; corrigir o shutdown + instrumentar as fases; validar | E1, E2 |
| **sex 09 – sáb 10** | Campanhas: M0/A/B n≥30; workloads ML e escala; CVM (conforme §2) | E3, E4, E7 |
| **sáb 10 – dom 11** | mTLS interno + rodar o T4 de novo; cota por comprador | T1, T3 |
| **sáb 10 – seg 13** | Reescrita no template ACM (anonimizado): intro/contribuições, cenário, tabelas DNAT e R1–R6, background, avaliação por RQs, related work | P1–P8, W1–W3, E5, E6, E8, E9 |
| **seg 13** | **Rascunho para o Andrey e o Eduardo** | — |
| **ter 14 – qua 15** | Incorporar a revisão; cortar para o limite de páginas; revisão de inglês | W4 |
| **qui 16** | Anonimizar o link do artefato (anonymous.4open.science); submeter na trilha DADS | — |

**Se o tempo apertar, cortar nesta ordem:** mTLS → cota → escala de dataset (mantendo o
workload de ML). **Inegociáveis:** E1–E4, P1–P5, P7.

## 4. Fase 2 — rumo ao DSN (17/out → 25/nov)

1. Execução confidencial real (D-B e/ou D-A) + medição de custo.
2. Atestação ancorada no ledger + mTLS atestado.
3. Proveniência do build (in-toto/SLSA) assinada pelo build plane e verificada pelo
   executor; cache particionado por comprador → fortalece a tese do build.
4. Workload não-Python (npm ou R).
5. Concorrência/throughput; pool de microVMs a partir de snapshot limpo (warm start sem
   quebrar a efemeridade).
6. (opcional) ProVerif: sigilo do dataset e correspondência compra → execução.

**Plano B para o DSN:** se 1–2 não ficarem prontos, submeter como *Practical Experience
Report* (7 págs), focado nas lições sobre isolar o build e no custo do isolamento.
