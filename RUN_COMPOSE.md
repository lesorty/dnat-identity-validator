## Modo local no mesmo host Docker
# Nao precisa definir EXECUTOR_URL. O frontend usa http://dnat-executor:5000
# pela rede Docker compartilhada `dnat-runtime`.
# Em desenvolvimento existe um default, mas para testar explicitamente voce pode
# fixar a mesma chave na CVM1 antes de subir o frontend:
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"
docker compose -f docker/executor-vm.compose.yaml build
docker compose -f docker/executor-vm.compose.yaml up -d
docker compose -f docker/frontend-vm.compose.yaml up -d --build

## Verificacao rapida do executor no modo local
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health

## Verificacao rapida da API web
curl http://127.0.0.1:3001/api/health

## Verificacao de limpeza do executor apos execucao
docker exec dnat-executor sh -lc 'ps -ef | grep firecracker | grep -v grep || true'
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'

## Modo distribuido em VMs separadas
# Na CVM1, sobrescreva com o IP real da CVM2.
export EXECUTOR_URL="http://10.0.0.20:5000"
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"
docker compose -f docker/frontend-vm.compose.yaml up -d --build

## Verificacao rapida a partir da CVM1 no modo distribuido
curl "$EXECUTOR_URL/health"

## Documentacao detalhada
# Consulte ARCHITECTURE.md para o estado implementado hoje e para a arquitetura
# alvo aprovada, onde a CVM1 builda e entrega o artefato read-only da aplicacao
# para a CVM2 sem que a CVM2 fale com o IPFS.
