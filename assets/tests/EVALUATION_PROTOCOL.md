# DNAT — Protocolo de Avaliação (Seção de Evaluation do artigo)

Protocolo reprodutível para a avaliação de segurança e desempenho do DNAT.
Cobre cinco testes de segurança (T1–T5) e medições de custo operacional,
comparando o **Ambiente B** (arquitetura compartimentada) com o **Ambiente A**
(baseline centralizado). Onde já há dados reais coletados, eles estão em
[`TCC/evaluation_data/results_raw.md`](../../TCC/evaluation_data/results_raw.md).
Onde o passo depende de infraestrutura ainda não construída na máquina de teste,
há um **template para preencher**.

> Convenção de papéis (ver `RUN_COMPOSE.md`): CVM1 = `dnat-client` (control
> plane), CVM2 = `dnat-builder` (build plane), CVM3 = `dnat-executor` (execution
> plane).

---

## 0. Pré-requisitos

- Host Linux com `/dev/kvm` (ou Docker com backend que exponha KVM). O Firecracker
  **não** roda sem virtualização aninhada.
- Docker + Docker Compose.
- Portas livres: B usa `3001/5001/8080/8545/5100/5000`; A usa `4001/4501/4480/4545/4100/4000`.

Subir o Ambiente B (compartimentado):
```bash
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"
docker compose -f docker/builder-vm.compose.yaml up -d --build
docker compose -f docker/executor-vm.compose.yaml up -d --build
docker compose -f docker/frontend-vm.compose.yaml up -d --build
curl http://127.0.0.1:3001/api/health   # ok:true quando builder+executor respondem
```

Subir o Ambiente A (baseline), para a comparação:
```bash
docker compose -f docker/baseline-vm.compose.yaml up -d --build
curl http://127.0.0.1:4001/api/health
```

---

## 1. Testes do plano de execução — T1, T1b, benigno (AUTOMATIZADO)

Não dependem de builder/IPFS/contrato: enviam o bundle direto ao executor.

```bash
# Ambiente B (executor :5000)
bash assets/tests/run_execution_plane_tests.sh
# Ambiente A (executor do baseline :4000)
EXECUTOR_PORT=4000 bash assets/tests/run_execution_plane_tests.sh
```

Evidências salvas em `assets/test-results/exec-plane-<timestamp>/`.

**T1 (exfiltração) — esperado:** `OVERALL: EXFILTRATION FAILED`, interfaces
`['lo','sit0']`, `blocked=7 succeeded=0`. ✔ Coletado (Ambiente B).
**T1b (filesystem) — esperado:** `NO-SECRETS`; discos vizinhos ausentes. ✔ Coletado.
**Benigno — esperado:** `processed 60 rows, 8 columns`. ✔ Coletado.

Template A vs B:

| Teste | Ambiente B | Ambiente A |
|-------|-----------|-----------|
| T1 interfaces | `['lo','sit0']` | _________ |
| T1 blocked/succeeded | 7 / 0 | ___ / ___ |
| T1b segredos no env | nenhum | _________ |

---

## 2. T3 — Limpeza efêmera (AUTOMATIZADO)

Após pelo menos uma execução:
```bash
bash assets/tests/t3_cleanup_check.sh                              # Ambiente B
docker exec dnat-baseline bash -lc 'find /tmp -maxdepth 3 \( -name firecracker.socket -o -name "*.ext4" \)'  # Ambiente A
```
**Esperado:** nenhum socket/disco/mount/dataset remanescente. ✔ Coletado (B).

---

## 3. T4 — Movimento lateral / blast radius (AUTOMATIZADO, sem expor segredos)

```bash
bash assets/tests/t4_cross_cvm_isolation.sh    # checa rede + presença de segredos
```
Para presença de segredos sem imprimir valores (recomendado):
```bash
docker exec dnat-executor sh -lc '
  for v in ASSET_ENCRYPTION_KEY PRIVATE_KEY; do
    eval x=\$$v; [ -n "$x" ] && echo "$v: SET" || echo "$v: NOT SET"; done'
docker exec dnat-executor sh -lc 'for d in /data/ipfs /var/dnat/wheel-cache /app/smart-contract/executions; do printf "%s -> " "$d"; [ -e "$d" ] && echo EXISTS || echo absent; done'
```
**Esperado (B):** segredos `NOT SET`, stores `absent`. **Esperado (A):** segredos
`SET`, stores `EXISTS` (mesmo container). ✔ Coletado (B); preencher A:

| Ativo acessível pela CVM3 | B | A |
|---------------------------|---|---|
| ASSET_ENCRYPTION_KEY (env) | NOT SET | _____ |
| PRIVATE_KEY (env) | NOT SET | _____ |
| /data/ipfs (FS) | absent | _____ |
| wheel-cache (FS) | absent | _____ |
| executions (FS) | absent | _____ |
| dnat-client:3001 (rede) | 200 | _____ |
| dnat-client:5001 (rede) | conn-fail | _____ |
| dnat-client:8545 (rede) | 200 | _____ |

---

## 4. T5 — Controle de acesso (AUTOMATIZADO)

```bash
# Registra um dataset e tenta executar sem comprar acesso
DS=$(curl -s -X POST http://127.0.0.1:3001/api/register-dataset \
  -F "file=@assets/data/dataset_synthetic.csv" -F "manifest.name=ds-eval")
DS_ID=$(echo "$DS" | python3 -c "import sys,json;print(json.load(sys.stdin)['assetId'])")
curl -s -X POST http://127.0.0.1:3001/api/run-from-cids \
  -H "Content-Type: application/json" \
  -d "{\"datasetId\":\"$DS_ID\",\"applicationId\":\"$DS_ID\"}"
```
**Esperado:** `{"error":"Access denied. ..."}`. ✔ Coletado.

---

## 5. T2 — Supply chain no plano de build (AUTOMATIZADO — requer builder)

> Harness: `RUN_T2=1 bash assets/tests/run_build_plane_tests.sh` (após semear o
> cache). ✔ Coletado: o pacote é resolvido do cache e empacotado; o payload de
> import-time roda na execução **sem segredos e sem rede**; o de build-time
> inicia no build microVM. Ver `results_raw.md` (seção T2).

Reprodução passo a passo de uma dependência comprometida cujo código roda na CVM2/CVM3.

```bash
# 1. Gera o pacote malicioso (sdist dispara setup.py no build microVM)
bash assets/malicious_wheel/build_dist.sh

# 2. Semeia o pacote no cache de wheels da CVM2 (build-time)
bash assets/malicious_wheel/seed_cache.sh             # Ambiente B
BUILDER_CONTAINER=dnat-baseline bash assets/malicious_wheel/seed_cache.sh   # Ambiente A

# 3. Registra a aplicação T2 declarando a dependência maliciosa
curl -s -X POST http://127.0.0.1:3001/api/register-application \
  -F "file=@assets/apps/t2_malicious_dep.py" \
  -F "manifest.name=t2-supply-chain" \
  -F "manifest.dependencies=malicious-pkg"
# (o build dispara setup.py dentro do build microVM; observe os logs)

# 4. Inspecione o que o payload conseguiu alcançar no build plane
docker logs dnat-builder 2>&1 | grep -i "T2-MALICIOUS-PKG" | tail -40
```

**O que medir (preencher):**

| Pergunta | Ambiente B | Ambiente A |
|----------|-----------|-----------|
| setup.py executou no build? | sim/não | sim/não |
| Segredos lidos do env (`ASSET_ENCRYPTION_KEY`, `PRIVATE_KEY`)? | _____ | _____ |
| Faixas privadas alcançáveis (8.8.8.8 ok, 10/172.16/192.168 REJECT)? | _____ | _____ |
| Escrita em `/var/dnat/`, `/data/ipfs` possível? | _____ | _____ |
| Após o build, o payload alcançou ativos do control plane? | _____ | _____ |

**Hipótese:** no B, o payload está contido na microVM de build da CVM2 (que só
persiste wheels); no A, o mesmo namespace contém IPFS, chaves e estado do
marketplace, ampliando o alcance.

---

## 6. Custo operacional — latência e tamanho de artefato

### 6.1 Latência de execução (AUTOMATIZADO) — ✔ coletado
Média **31,4 s** (n=6; ver `results_raw.md`). Repita no Ambiente A:
```bash
EXECUTOR_PORT=4000 bash assets/tests/run_execution_plane_tests.sh
```

### 6.2 Latência de build e tamanho de artefato (AUTOMATIZADO — requer builder)

> Harness: `bash assets/tests/run_build_plane_tests.sh`. ✔ Coletado: sem deps
> 103 s / 16 MiB; `requests` (rede) 131 s / 19,6 MiB; `requests` (cache quente)
> 114 s. Comandos manuais equivalentes abaixo.
```bash
# Build SEM dependências
time curl -s -X POST http://127.0.0.1:3001/api/register-application \
  -F "file=@assets/apps/benign_stats.py" -F "manifest.name=bench-nodeps"
# Build COM dependências
time curl -s -X POST http://127.0.0.1:3001/api/register-application \
  -F "file=@assets/apps/benign_stats.py" -F "manifest.name=bench-deps" \
  -F "manifest.dependencies=numpy,pandas"
# Tamanho do artefato application.ext4 (no executor, durante um run)
docker exec dnat-executor sh -lc 'ls -l /tmp/tmp.*/application.ext4 2>/dev/null'
```

| Métrica | Ambiente B | Ambiente A |
|---------|-----------|-----------|
| Build sem deps (s) | _____ | _____ |
| Build com deps (s) | _____ | _____ |
| Build com deps + cache quente (s) | _____ | _____ |
| Tamanho `application.ext4` sem deps (MB) | _____ | _____ |
| Tamanho `application.ext4` com deps (MB) | _____ | _____ |

---

## 7. Ferramentas estáticas e de supply chain (MANUAL — opcional, fortalece o artigo)

Conforme sugerido na metodologia. Rode na raiz do repositório:
```bash
# Análise estática do código de orquestração
pip install bandit semgrep
bandit -r smart-contract/scripts vm_runtime build_vm_runtime -f txt -o bandit.txt
semgrep --config auto smart-contract/scripts vm_runtime build_vm_runtime

# Risco de dependências / artefatos
pip install pip-audit
pip-audit -r <(echo "numpy
pandas") || true

# Scanners de imagem/container (precisa das imagens construídas)
trivy image dnat-executor:latest
syft dnat-builder:latest -o table
grype dnat-builder:latest
```

| Ferramenta | Alvo | Achados (resumo) |
|-----------|------|------------------|
| Bandit | scripts de orquestração | _____ |
| Semgrep | scripts de orquestração | _____ |
| pip-audit | dependências de exemplo | _____ |
| Trivy | imagem do executor | _____ |
| Grype/Syft | imagem do builder | _____ |

---

## Mapa: teste → claim do artigo

| Teste | Claim sustentada |
|-------|------------------|
| T1, (T2 rede) | (ii) exfiltration resistance |
| T1b, T2, T4 | (i) compromise containment / blast radius |
| T3 | (iii) persistence resistance |
| Latência, tamanho | (iv) operational cost |
| T5 | enforcement de acesso (smart contract) |
