# E1 — Auditoria do código frente às direções de evolução

> **Nota (2026-10-18):** os achados A1–A15 continuam valendo como retrato do código. As colunas e
> seções sobre "direções" (1: cadeia verificável; 2: distribuição; 3: build reproduzido) são de
> uma fase anterior e estão **fora do foco** do DSN (D-031, D-032). A10 e A14 seguem relevantes
> (build com rede e código presentes; sem isolamento por job na CVM). A16 (dataset em claro) foi
> achado depois e já está corrigido na `main` (D-018).

**Data:** 2026-10-12 · **Base auditada:** `main` @ `1dfd94a` e `origin/feat/cvm-direct-mode-deploy` @ `a668d0b`
**Pergunta:** o que o código garante hoje, e o que falta para as direções 1–3
(cadeia verificável, distribuição de confiança, build reproduzido)?

## Resumo

1. **Não existe atestação remota em lugar nenhum.** Nenhuma ocorrência de SEV-SNP, TDX,
   relatório de atestação, medição, assinatura ou TLS no código (busca em todo o repositório).
   A segurança entre planos depende só da topologia de rede.
2. **O operador do plano de controle (CVM1) é um ponto único de confiança total.** Ele guarda a
   única chave simétrica de todos os ativos, assina todas as transações com uma carteira única,
   decifra dataset e aplicação e os envia em claro ao executor, e recebe o resultado em claro.
3. **O ledger hoje registra compras, não execuções**, e não amarra a compra a nenhuma prova do
   que foi executado.
4. **Os pontos que a direção 1 precisa ancorar ainda não existem:** hash da aplicação
   verificável por terceiros, proveniência do build, verificação de integridade na execução e
   resultado assinado.
5. Há um **risco novo que o artigo não discute**: a microVM de build tem acesso à internet
   *enquanto o código-fonte da aplicação está dentro dela* (achado A9).
6. A dúvida sobre modo direto × Firecracker aninhado na CVM tem resposta no histórico: **dentro da CVM o
   sistema roda em modo direto, sem Firecracker** (leitura **(a)**).

## Achados

Severidade frente ao modelo de ameaça do artigo: 🔴 contradiz ou enfraquece uma afirmação central ·
🟡 lacuna conhecida ou de protótipo · ⚪ observação.

### Confiança e chaves

| # | Achado | Evidência | Sev. | Direção afetada |
|---|---|---|---|---|
| A1 | Nenhuma atestação remota; nenhum plano verifica a identidade ou a medição de outro plano | busca por `attest\|snp\|tdx\|measurement\|sign\|tls` sem ocorrências em código | 🔴 | 1, 2 |
| A2 | **Chave simétrica única e global** para todos os ativos de todos os donos: `SHA-256(ASSET_ENCRYPTION_KEY)`, com padrão `"dnat-dev-asset-key"`; sem KDF e sem chave por ativo | `smart-contract/scripts/api-server.js:23`, `:179-181`; `docker/*.compose.yaml` | 🔴 | 1, 2 |
| A3 | **Carteira custodial única** (padrão: conta #0 do Hardhat). Registro e compra são assinados pelo servidor, então o `owner` on-chain de todo ativo é o operador e os pagamentos vão para ele. A separação de stakeholders no ledger é só nominal | `api-server.js:13-15`, `:41`; `DnatMarketplace.sol:148` | 🔴 | 2 |
| A4 | `/api/run-from-cids` aceita o campo `user` do corpo da requisição **sem assinatura**; qualquer cliente que alcance a API executa em nome de qualquer comprador | `api-server.js:833-841`, `:1096-1101`, `:769` | 🔴 | 1, 2 |

### Ledger e rastreabilidade

| # | Achado | Evidência | Sev. | Direção afetada |
|---|---|---|---|---|
| A5 | A compra grava só um booleano; **não há registro de execução on-chain** nem limite de execuções por compra (o T3 do plano). O histórico de execuções fica local na CVM1 | `DnatMarketplace.sol:234-237`; `api-server.js:1128-1140` | 🟡 | 1 |
| A6 | O `contentHash` da aplicação é o SHA-256 do `application.ext4` **construído**, que não é reproduzível (`mkfs.ext4 -d` gera UUID e timestamps novos). Nenhum terceiro consegue recalcular esse hash a partir do código-fonte | `api-server.js:698`, `:716`; `build_application_artifact.py:307-311` | 🟡 | 1, 3 |
| A7 | **A execução não verifica integridade contra o ledger:** nada compara o artefato decifrado com o `contentHash` on-chain. O tag GCM só prova que o artefato foi cifrado por quem tem a chave global, que é o próprio operador | sem ocorrência de `contentHash`/`sha256` em `run_from_cids.py` e `vm_runtime/rootfs/runner` | 🟡 | 1 |

### Canais entre planos

| # | Achado | Evidência | Sev. | Direção afetada |
|---|---|---|---|---|
| A8 | Dataset e aplicação são decifrados na CVM1 e enviados **em claro por HTTP** ao executor. O resultado volta em claro, não é cifrado para o comprador e não é assinado por ninguém | `api-server.js:860-865`; `vm_runtime/executor.py:36-73` | 🔴 | 1 |
| A9 | Executor e builder **sem autenticação**, escutando em `0.0.0.0`; mTLS não implementado (já conhecido, T1 do plano) | `executor.py:94`; `builder.py:102`; `ARCHITECTURE.md:188` | 🟡 | 1, 2 |

### Build (supply chain)

| # | Achado | Evidência | Sev. | Direção afetada |
|---|---|---|---|---|
| A10 | **A microVM de build tem egress para a internet pública com o código-fonte da aplicação presente.** Uma dependência maliciosa (sdist com `setup.py`) pode **exfiltrar o código do desenvolvedor** durante o build. As faixas privadas e `169.254/16` são bloqueadas (bom), mas a internet pública não | `build_vm_runtime/vm/build-vm.sh:174-186`, `:275`; `build_vm_runtime/rootfs/runner:44-50`, `:123` | 🔴 | 1, 3 |
| A11 | `pip` sem `--require-hashes` e sem `--only-binary`: a resolução não é fixada e sdists executam código arbitrário | `smart-contract/scripts/build_application_artifact.py:131-179` | 🟡 | 3 |
| A12 | O cache de wheels valida nome, tamanho e SHA-256 de conflito, mas não a origem: uma wheel produzida por um build envenenado entra no cache compartilhado (T6 do plano) | `build_vm_runtime/worker.py:26-92` | 🟡 | 3 |

### Isolamento local

| # | Achado | Evidência | Sev. | Direção afetada |
|---|---|---|---|---|
| A13 | Builder e executor rodam em containers `privileged: true` com `/dev/kvm`, e o Firecracker é chamado **sem o `jailer`** (sem chroot, cgroups ou seccomp dedicados). Um escape do VMM vira root na CVM inteira | `docker/builder-vm.compose.yaml:9-11`; `docker/executor-vm.compose.yaml:9-11`; sem ocorrência de `jailer` | 🟡 | E2 |
| A14 | No modo direto (branch `feat`), build e execução rodam no namespace do container privilegiado: **não há isolamento entre jobs dentro da CVM**. O `pip` do build direto roda ao lado do cache de wheels | `build_vm_runtime/vm/build-direct.sh`; `vm_runtime/vm/run-direct.sh`; commit `4a38e86` | 🔴 | E2 |
| A15 | Desligamento lento confirmado: o host envia `SendCtrlAltDel`, espera até 20 s e faz polling de 1 s; o guest tenta `poweroff -f` antes de `reboot -f` | `vm_runtime/vm/run-vm.sh:20-21`, `:192-224`; `vm_runtime/rootfs/init:16-18` | ⚪ | (E1 do plano) |

### Resposta à questão aberta do plano (§2: modo direto ou Firecracker aninhado?)

A mensagem do commit `4a38e86` registra que o Firecracker "não roda em VM confidencial por
falta de virtualização aninhada", e a campanha `run_cvm_overhead_campaign.sh` grava o `mode` do
executor como evidência. Portanto, **na CVM o sistema roda em modo direto**: a
confidencialidade frente ao operador vale na granularidade da CVM, e **não há isolamento por
job dentro dela** (A14). Os dados brutos dessa campanha não estão no repositório **(a verificar
onde estão)**.

## O que isso muda nas direções

| Direção | Pré-requisitos que faltam no código |
|---|---|
| **1. Cadeia verificável** | Atestação de cada plano (A1); chave por ativo liberada só para medição atestada (A2); hash da aplicação verificável por terceiros (A6); verificação de integridade na execução (A7); resultado assinado pelo executor e cifrado para o comprador (A8); registro de execução on-chain (A5); pedido de execução assinado pelo comprador (A4) |
| **2. Distribuição de confiança** | Carteiras dos donos fora do servidor (A3); fim da chave global (A2); planos que se autenticam mutuamente (A9). Sem isso, separar operadores não muda nada, porque a CVM1 continua vendo tudo |
| **3. Build reproduzido** | Build determinístico: hashes fixados, wheels, ext4 reproduzível (A6, A11); build sem rede depois da fase de download, para fechar A10; cache com proveniência (A12) |

## Consequências para o artigo atual (SAC)

- O texto não deve afirmar proteção frente ao operador da CVM1: hoje ele tem acesso a tudo (A2, A3, A8).
- **A10** é um risco residual novo e deveria entrar na análise STRIDE (I@build): a confidencialidade do
  código do desenvolvedor frente a uma dependência maliciosa. A correção é barata: separar o build
  em duas fases, `pip download` com rede **sem** o código da aplicação, depois instalação **sem** rede
  e com o código. Candidato a entrar no SAC junto com o mTLS.
- A4 e A3 são esperados num protótipo, mas convém citá-los como limitação de implementação.

## Próximo passo

E2: escolher como ter isolamento por job **com** confidencialidade frente ao operador (A13, A14),
porque a resposta define onde a atestação da direção 1 é ancorada.
