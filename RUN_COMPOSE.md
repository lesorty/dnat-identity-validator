## Ambiente A (baseline centralizado) - usado pelo TCC para comparacao

Sobe um unico container `dnat-baseline` que hospeda control plane, builder e executor no mesmo trust domain (mesmo usuario, mesmo namespace de mount/rede). Firecracker continua isolando os microVMs de build e execucao para manter a comparacao com o Ambiente B justa (a unica variavel e a separacao em planos).

```bash
docker compose -f docker/baseline-vm.compose.yaml build --no-cache
docker compose -f docker/baseline-vm.compose.yaml up -d
```

As portas externas do Ambiente A ficam no range 4xxx para coexistir com o B:

| Servico         | Ambiente B | Ambiente A |
|-----------------|-----------:|-----------:|
| frontend/API    | 3001       | 4001       |
| IPFS API        | 5001       | 4501       |
| IPFS gateway    | 8080       | 4480       |
| Hardhat RPC     | 8545       | 4545       |
| Builder API     | 5100       | 4100       |
| Executor API    | 5000       | 4000       |

Verificacao rapida:

```bash
curl http://127.0.0.1:4001/api/health
curl http://127.0.0.1:4100/health
curl http://127.0.0.1:4000/health
```

Para encerrar:

```bash
docker compose -f docker/baseline-vm.compose.yaml down
```

## Ambiente B (arquitetura compartimentada DNAT)

### Modo local no mesmo host Docker

Suba os 3 papéis separadamente:
- `CVM1`: `dnat-client`
- `CVM3`: `dnat-builder`
- `CVM2`: `dnat-executor`

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

Na CVM3:

```bash
docker compose -f docker/builder-vm.compose.yaml build --no-cache
docker compose -f docker/builder-vm.compose.yaml up -d
```

Na CVM2:

```bash
docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d
```

Na CVM1, sobrescreva com os IPs reais da CVM3 e da CVM2:

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

## Inspecionar cache de wheels da CVM3

```bash
docker exec dnat-builder sh -lc 'find /var/dnat/wheel-cache -maxdepth 1 -type f -name "*.whl" | sort'
```

## Verificar limpeza do executor na CVM2

```bash
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'
```
