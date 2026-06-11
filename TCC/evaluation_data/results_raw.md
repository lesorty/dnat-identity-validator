# DNAT — Dados Brutos da Avaliação de Segurança e Desempenho

> Evidências coletadas em execução real do protótipo. Cada número aqui foi
> medido na máquina de testes; nada é estimado. Use estes dados para preencher
> as tabelas do artigo (`results_tables.tex`) e o texto da Seção de Evaluation.

## Ambiente de medição

| Item | Valor |
|------|-------|
| Host | Windows 11 + Docker (backend Linux), kernel guest Firecracker `6.6.0` |
| Plano de execução (CVM3) | container `dnat-executor`, Firecracker microVM, 1 vCPU / 512 MiB |
| Plano de build (CVM2) | container `dnat-builder`, Firecracker microVM, 2 vCPU / 1536 MiB |
| Control plane (CVM1) | container `dnat-client-local` (frontend/API + IPFS + Hardhat) |
| Dataset de teste | `assets/data/dataset_synthetic.csv`, 60 linhas, 3202 bytes, sintético (sem PII) |
| sha256 do dataset | `5881e7514713ee87f6746e6f6329abd7de1d355c4eb4ffe04d9e143cd4944596` |
| Data da coleta | 2026-06-11 |

> Observação metodológica: o **plano de execução** foi exercitado enviando
> bundles diretamente ao executor (`POST :5000/execute`), reproduzindo
> exatamente o `workspace/run.sh` que o `run_from_cids.py` gera. Isso isola a
> variável sob teste (a microVM de execução) sem depender de IPFS/builder/contrato.

---

## T1 — Resistência a exfiltração de rede (execution plane)

Aplicação: `assets/apps/t1_network_exfil.py`. Tenta 7 canais de saída.

- Interfaces de rede visíveis ao guest: **`['lo', 'sit0']`** (nenhuma `eth0`).
- Resultado global: **EXFILTRATION FAILED** — `blocked=7 succeeded=0`.

| Canal | Resultado | Detalhe do erro |
|-------|-----------|-----------------|
| DNS resolution (`gethostbyname`) | bloqueado | `gaierror [Errno -3] Temporary failure in name resolution` |
| DNS UDP 8.8.8.8:53 | bloqueado | `OSError [Errno 101] Network is unreachable` |
| DNS TCP 8.8.8.8:53 | bloqueado | `OSError [Errno 101] Network is unreachable` |
| HTTPS 1.1.1.1:443 | bloqueado | `OSError [Errno 101] Network is unreachable` |
| HTTP 93.184.216.34:80 | bloqueado | `OSError [Errno 101] Network is unreachable` |
| SMTP 142.250.0.0:25 | bloqueado | `OSError [Errno 101] Network is unreachable` |
| HTTP urllib example.com:80 | bloqueado | `URLError Temporary failure in name resolution` |

**Interpretação:** a microVM de execução é iniciada sem interface de rede
(`run-vm.sh` não configura `network-interfaces`), então não há rota de saída.
A exfiltração é bloqueada *por construção*, não por uma regra de firewall que
poderia ser desabilitada. Evidência direta da claim (ii) "exfiltration resistance".

---

## T1b — Contenção no sistema de arquivos (execution plane)

Aplicação: `assets/apps/t1b_fs_escape.py`. Guest roda como `uid=0` (root), mas o
guest é descartável.

- **`env_secrets = {}`** — nenhum segredo do control plane no ambiente de execução
  (ASSET_ENCRYPTION_KEY, PRIVATE_KEY, AWS_*, RPC_URL, etc. todos ausentes).
- Discos visíveis ao guest:
  - `/dev/vdb` → montável, contém apenas `bundle.tar.gz` + `lost+found` (o próprio input).
  - `/dev/vdc` → já montado (disco de output da própria execução).
  - `/dev/vdd`, `/dev/vde` → **ausentes** (nenhum disco de outra execução/tenant).
- Leituras de arquivo: `/etc/passwd`, `/etc/shadow`, `/proc/version` são legíveis,
  **mas pertencem ao rootfs efêmero mínimo do guest** (apenas `root`/`daemon`,
  shadow com `root:*` sem hash), não ao host. `/run/secrets/key` e
  `/root/.ssh/id_rsa` → `FileNotFoundError`.
- Escritas fora do workspace: 4 caminhos retornaram `WRITE-OK`, porém **todos em
  disco efêmero destruído no teardown** (validado por T3). Em modo artefato real,
  `/mnt/dnat-app` é montado read-only e a escrita lá falha.

**Interpretação:** o código de execução não encontra segredos do control plane
nem discos de outras execuções; o que ele escreve não sobrevive. Evidência da
contenção no nível da microVM efêmera.

---

## T3 — Resistência a persistência (ephemeral cleanup)

Verificado no `dnat-executor` após 9+ execuções consecutivas:

| Artefato procurado | Encontrado? |
|--------------------|-------------|
| `firecracker.socket` | **nenhum** |
| `rootfs-overlay.ext4`, `input.ext4`, `output.ext4`, `application.ext4` | **nenhum** |
| mounts residuais (`result-mount`/`input-mount`/`output-mount`) | **nenhum** |
| datasets residuais (`*.csv` em `/tmp`) | **nenhum** |
| workdirs temporários (`/tmp/tmp.*`) | **nenhum** |

**Interpretação:** o `cleanup()`/`trap EXIT` do `run-vm.sh` remove o `WORKDIR`
inteiro após cada run. Nenhum estado efêmero contamina execuções futuras.
Evidência direta da claim (iii) "persistence resistance".

---

## T4 — Movimento lateral / blast radius (cross-CVM)

Inspeção do container `dnat-executor` (CVM3 comprometido hipoteticamente).
**Valores de segredos nunca impressos — apenas presença/ausência.**

| Ativo do control plane | Alcançável a partir da CVM3 (Ambiente B / DNAT) |
|------------------------|--------------------------------------------------|
| `ASSET_ENCRYPTION_KEY` (env) | **NOT SET** (ausente) |
| `PRIVATE_KEY` (env) | **NOT SET** |
| `RPC_URL`, `IPFS_API_URL`, `BUILDER_URL`, `EXECUTOR_URL` (env) | **NOT SET** |
| nº de variáveis com nome de segredo | **0** |
| repositório IPFS `/data/ipfs` (FS) | **ausente** |
| cache de wheels `/var/dnat/wheel-cache` (FS) | **ausente** |
| store de execuções `/app/smart-contract/executions` (FS) | **ausente** |
| API de controle `dnat-client:3001` (rede) | **alcançável (HTTP 200)** ⚠ |
| IPFS API `dnat-client:5001` (rede) | **bloqueado (000 / conn-fail)** |
| Hardhat RPC `dnat-client:8545` (rede) | **alcançável (HTTP 200)** ⚠ |

**Interpretação (honesta):** a contenção de **segredos** e **armazenamento** é
forte — a CVM3 não possui nenhuma credencial do control plane nem enxerga os
stores sensíveis no seu filesystem. Porém, no deployment **local de host único**
(rede Docker compartilhada `dnat-runtime`), a CVM3 ainda alcança a API de
controle (3001) e o RPC (8545) pela rede; a API do IPFS (5001), que daria acesso
direto aos blobs cifrados, fica inacessível por escutar em loopback dentro da
CVM1. Esse resultado substancia exatamente a limitação já declarada no artigo
("mutual TLS / segmentação de rede interna ainda pendente") e deve ser citado na
subseção de risco residual. No modo distribuído (VMs separadas), 3001/8545 ficam
sujeitos à política de rede entre hosts.

### Comparação arquitetural com o baseline (Ambiente A)

Derivado de `docker/baseline-vm.compose.yaml`: no baseline, control plane,
builder e executor compartilham o **mesmo container/namespace**. Portanto, um
executor comprometido no baseline compartilha o ambiente com:
`ASSET_ENCRYPTION_KEY` e `PRIVATE_KEY` (env **SET**), `/data/ipfs`,
`/var/dnat/wheel-cache` e `/app/smart-contract/executions` (mesmo filesystem),
e todos os serviços em `127.0.0.1` (5001 inclusive). Ou seja, todos os ativos
que estão **isolados** na CVM3 do Ambiente B estão **colocalizados** no Ambiente A.

---

## T5 — Controle de acesso (smart contract)

- Dataset sintético registrado on-chain: `assetId=1`, tx
  `0x96eaf1b74f654ad9871a93764e76431e837150335048b0b468b9999c09ad8c1b`,
  `contentHash` on-chain = `0x5881e7…944596` (igual ao sha256 do arquivo → integridade).
- `POST /api/run-from-cids` **sem** `purchaseAccess` →
  `{"error": "Access denied. Purchase access to the selected dataset and application before executing."}`

**Interpretação:** a execução é barrada pelo gate `hasAccessByIds` do contrato
antes de qualquer preparação de bundle. Evidência do enforcement de acesso.

---

## Desempenho — Latência de execução (execution plane)

Aplicação benigna (`benign_stats.py`), 6 execuções consecutivas, mesmo dataset.

| Run | Latência de parede (ms) | returncode |
|-----|------------------------:|-----------:|
| 1 | 32150 | 0 |
| 2 | 31492 | 0 |
| 3 | 32936 | 0 |
| 4 | 28465 | 0 |
| 5 | 32372 | 0 |
| 6 | 31064 | 0 |

**Resumo:** n=6, min=28465 ms, max=32936 ms, **média=31413 ms (≈31,4 s)**,
mediana=31821 ms, desvio-padrão=1449 ms.

Amostra adicional (primeira rodada do harness, apps distintos):
T1=30064 ms, T1b=33658 ms, benign=28931 ms, bundle trivial=30760 ms.

**Interpretação:** a latência é dominada pelo ciclo de vida da microVM
(boot do kernel + descoberta de discos + sincronização do disco de saída +
shutdown com janela de graça), não pelo processamento da aplicação (o cômputo
sobre 60 linhas leva milissegundos). Esse é o "custo operacional" da claim (iv):
o isolamento por microVM efêmera adiciona ~30 s de overhead fixo por execução.

---

## Pendências (requerem o builder/baseline construídos — ver MANUAL_TESTS.md)

- **T2 (supply chain no build plane):** requer imagem `dnat-builder` construída e
  o pacote malicioso semeado no cache (`assets/malicious_wheel/seed_cache.sh`).
- **Latência de build** (com e sem dependências) e **tamanho do artefato**.
- **Comparação A/B end-to-end** com o container `dnat-baseline` no ar.
- **Ferramentas estáticas/supply-chain** (Bandit, Semgrep, pip-audit, Trivy, Grype).
