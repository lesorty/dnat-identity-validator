# DNAT — Suíte de testes de segurança (T1–T5)

Protocolo reprodutível dos testes de isolamento do DNAT na arquitetura compartimentada atual
(Firecracker). Será reexecutado contra o executor OCI (ver `DSN2027/etapas/E2_isolamento_confidencial.md`,
propriedades P1–P8).

> Papéis (ver `RUN_COMPOSE.md`): CVM1 = `dnat-client` (controle), CVM2 = `dnat-builder` (build),
> CVM3 = `dnat-executor` (execução).

## 0. Pré-requisitos

- Host Linux com `/dev/kvm`; o Firecracker **não** roda sem virtualização.
- Docker + Docker Compose; portas `3001/5001/8080/8545/5100/5000` livres.

```bash
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"
docker compose -f docker/builder-vm.compose.yaml up -d --build
docker compose -f docker/executor-vm.compose.yaml up -d --build
docker compose -f docker/frontend-vm.compose.yaml up -d --build
curl http://127.0.0.1:3001/api/health   # ok:true quando builder e executor respondem
```

## 1. Plano de execução: T1, T1b, benigno

Enviam o bundle direto ao executor (sem builder, IPFS ou contrato):
```bash
bash assets/tests/run_execution_plane_tests.sh
```
Evidências em `assets/test-results/exec-plane-<timestamp>/`.

| Teste | Esperado |
|---|---|
| T1 exfiltração por rede | `OVERALL: EXFILTRATION FAILED`; interfaces `['lo','sit0']`; `blocked=7 succeeded=0` |
| T1b filesystem | `NO-SECRETS`; discos vizinhos ausentes |
| Benigno | `processed 60 rows, 8 columns` |

## 2. T3 — Limpeza efêmera

Após pelo menos uma execução:
```bash
bash assets/tests/t3_cleanup_check.sh
```
**Esperado:** nenhum socket, disco, mount ou dataset remanescente.

## 3. T4 — Movimento lateral

```bash
bash assets/tests/t4_cross_cvm_isolation.sh
```
Presença de segredos sem imprimir valores:
```bash
docker exec dnat-executor sh -lc '
  for v in ASSET_ENCRYPTION_KEY PRIVATE_KEY; do
    eval x=\$$v; [ -n "$x" ] && echo "$v: SET" || echo "$v: NOT SET"; done'
docker exec dnat-executor sh -lc 'for d in /data/ipfs /var/dnat/wheel-cache /app/smart-contract/executions; do printf "%s -> " "$d"; [ -e "$d" ] && echo EXISTS || echo absent; done'
```
**Esperado:** segredos `NOT SET`, stores `absent`.

## 4. T5 — Controle de acesso

```bash
DS=$(curl -s -X POST http://127.0.0.1:3001/api/register-dataset \
  -F "file=@assets/data/dataset_synthetic.csv" -F "manifest.name=ds-eval")
DS_ID=$(echo "$DS" | python3 -c "import sys,json;print(json.load(sys.stdin)['assetId'])")
curl -s -X POST http://127.0.0.1:3001/api/run-from-cids \
  -H "Content-Type: application/json" \
  -d "{\"datasetId\":\"$DS_ID\",\"applicationId\":\"$DS_ID\"}"
```
**Esperado:** `{"error":"Access denied. ..."}`.

## 5. T2 — Dependência maliciosa no build

```bash
bash assets/malicious_wheel/build_dist.sh          # gera o pacote (sdist roda setup.py no build)
bash assets/malicious_wheel/seed_cache.sh          # semeia o cache de wheels da CVM2
RUN_T2=1 bash assets/tests/run_build_plane_tests.sh
docker logs dnat-builder 2>&1 | grep -i "T2-MALICIOUS-PKG" | tail -40
```
**Esperado:** o payload fica contido na microVM de build (que só persiste wheels) e, na
execução, roda sem segredos e sem rede.

## 6. Todos de uma vez

```bash
bash assets/tests/run_all_tests.sh
```

## Mapa: teste → propriedade

| Teste | Propriedade (E2, P1–P8) |
|---|---|
| T1 | P1 sem caminho de rede |
| T1b, T2, T4 | P2 contenção de escape / raio de dano; P6 build isolado |
| T3 | P3 nenhum estado entre jobs |
| T5 | Controle de acesso pelo contrato |
