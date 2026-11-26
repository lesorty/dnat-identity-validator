# Arquitetura compartimentada DNAT

### Modo local no mesmo host Docker

Suba os 3 papéis separadamente:
- `CVM1`: `dnat-client`
- `CVM2`: `dnat-builder`
- `CVM3`: `dnat-executor`

```bash
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"

docker compose -f docker/builder-vm.compose.yaml build --no-cache
docker compose -f docker/builder-vm.compose.yaml up -d

docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d

unset EXECUTOR_URL
unset BUILDER_URL
docker compose -f docker/frontend-vm.compose.yaml up -d --build
```

Os defaults locais sao:
- `EXECUTOR_URL=http://dnat-executor:5000`
- `BUILDER_URL=http://dnat-builder:5100`

pela rede Docker compartilhada `dnat-runtime`.

## Verificacao rapida no modo local

```bash
curl http://127.0.0.1:3001/api/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-builder:5100/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health
```

### Modo distribuido em VMs separadas

Na CVM2:

```bash
docker compose -f docker/builder-vm.compose.yaml build --no-cache
docker compose -f docker/builder-vm.compose.yaml up -d
```

Na CVM3:

```bash
docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d
```

Na CVM1, sobrescreva com os IPs reais da CVM2 e da CVM3:

```bash
export BUILDER_URL="http://10.0.0.30:5100"
export EXECUTOR_URL="http://10.0.0.20:5000"
docker compose -f docker/frontend-vm.compose.yaml up -d --build
```

## Verificacao rapida a partir da CVM1 no modo distribuido

```bash
curl "$BUILDER_URL/health"
curl "$EXECUTOR_URL/health"
curl http://127.0.0.1:3001/api/health
```

## Teste funcional

1. Abrir `http://127.0.0.1:3001`
2. Registrar dataset
3. Registrar aplicacao com dependencias, por exemplo `requests` ou `numpy,pandas`
4. Comprar acesso
5. Executar `Run From CIDs`

## Inspecionar cache de wheels da CVM2

```bash
docker exec dnat-builder sh -lc 'find /var/dnat/wheel-cache -maxdepth 1 -type f -name "*.whl" | sort'
```

## Verificar limpeza do executor na CVM3

```bash
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'
```

## Modo direto (arquitetura atual, T-815)

Na arquitetura atual (D4, T-102) não há microVM: cada job roda direto numa CVM de uso único,
isolada pela rede dela (T-801). Localmente, as três CVMs viram containers leves, sem KVM nem
Firecracker:

```bash
docker compose -f docker/direct.compose.yaml up -d --build
```

- **CVM1** (`dnat-client`): IPFS, hardhat, API e o Juiz (`model_gate` com `uv`, Python 3.12 e torch de
  CPU do `uv.lock`). Os dados locais do model_gate (`$MODEL_GATE_DATA`, padrão `~/model_gate_data`)
  entram só leitura em `/data/model_gate_data`.
- **CVM2** (`dnat-builder`): `build_vm_runtime/Dockerfile.direct`, ext4 por `mkfs.ext4 -d`.
- **CVM de job** (`dnat-executor`): `vm_runtime/Dockerfile.direct`. `start-direct.sh` deixa a rede
  entra-só (a CVM1 conecta no agente; nenhuma conexão nova sai, nem para a CVM1) e troca para um
  usuário sem privilégio antes de subir o agente.

Liberação do Juiz pelo operador, dentro da CVM1 (exemplo com o pacote e a referência locais):

```bash
docker exec dnat-client node smart-contract/scripts/judge_cli.js battery --dir /data/model_gate_data/battery/local_t807
docker exec dnat-client node smart-contract/scripts/judge_cli.js allow --battery-commitment <64 hex> \
  --prereg model_gate/experiments/judge_local_prereg.yaml --evaluator-kind detector
docker exec dnat-client node smart-contract/scripts/judge_cli.js reference --parent <id do base> \
  --dir /data/model_gate_data/references/<referência medida>
```

Testes de segurança contra esta pilha (T1 rede, T3 limpeza, T4 alcance a partir da CVM de job,
T5 controle de acesso):

```bash
bash assets/tests/run_all_tests.sh
```

### Cache de wheels do builder

O cache compartilhado (`/var/dnat/wheel-cache`, volume `dnat_direct_wheels`) só recebe o que o operador põe;
as wheels geradas no build de um usuário servem só a esse build (uma wheel plantada pelo `setup.py` de um
usuário não entra no build de outro). Para pré-carregar, por exemplo, as dependências do LoRA da T-806:

```bash
docker exec dnat-builder pip download --only-binary=:all: -d /var/dnat/wheel-cache \
  --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
  torch==2.15.0+cpu transformers==5.22.1 peft==0.21.2 accelerate==1.15.0 safetensors==0.8.0
```

`DNAT_WHEEL_CACHE_INGEST=1` no builder religa a ingestão automática (só para desenvolvimento com um usuário).

### Rotas do operador

`/api/revoke-asset`, `/api/update-asset` e `/api/executions[/:id]` só respondem com o token do operador
(`DNAT_OPERATOR_TOKEN` na CVM1, enviado no cabeçalho `X-Operator-Token`). Sem a variável, ficam fechadas
(403). A interface em `http://localhost:3001` não usa essas rotas: o usuário vê os próprios jobs por
`/api/my/jobs`, assinado pela identidade.

### CVM de job de uso único (T-801)

Cada job roda numa CVM nunca usada, destruída depois dele (`smart-contract/scripts/job_vm.js`). A CVM1
escolhe o provedor por `DNAT_JOB_VM_PROVIDER`:

- `static` (padrão): o `EXECUTOR_URL` fixo, reaproveitado entre jobs; só para desenvolvimento.
- `docker`: um container novo da imagem do executor por job, pela API do Docker no socket:

  ```bash
  docker compose -f docker/direct.compose.yaml -f docker/direct.single-use.compose.yaml up -d --build
  ```

- `command`: a nuvem. `DNAT_JOB_VM_CREATE_CMD` cria a CVM (imagem do executor com
  `DNAT_SINGLE_USE=1`, grupo de segurança entra-só) e imprime na última linha
  `{"id": "...", "url": "http://IP:5000"}`; `DNAT_JOB_VM_DESTROY_CMD` a destrói pelo id em
  `DNAT_JOB_VM_ID`.

`DNAT_JOB_VM_POOL` (padrão 0) é o tamanho do warm pool e `DNAT_JOB_VM_MEMORY` (docker) o limite
de memória. Duas travas contra reuso: o pool nunca entrega o mesmo id duas vezes, e o agente com
`DNAT_SINGLE_USE=1` recusa o segundo `/execute` com `used`. Antes de destruir, a CVM1 lê
`GET /stats` do agente (pico do cgroup e RSS do job) e grava em `jobVm` no `metadata.json` da execução.
Roteiro: `node e2e/run_direct.js --single-use [--base-dir DIR]` (precisa da imagem e da rede da pilha).

Sem Docker, o mesmo fluxo roda como processos locais: `npm run e2e:direct` e `npm run e2e:teste8` em
`smart-contract/` (T-811, T-814).

