## Modo local no mesmo host Docker

# Nao precisa definir EXECUTOR_URL. O frontend usa http://dnat-executor:5000

# pela rede Docker compartilhada `dnat-runtime`.

docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d
docker compose -f docker/frontend-vm.compose.yaml up -d --build

## Verificacao rapida do executor no modo local

docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health

## Modo distribuido em VMs separadas

# Na CVM1, sobrescreva com o IP real da CVM2.

export EXECUTOR_URL="http://10.0.0.20:5000"
docker compose -f docker/frontend-vm.compose.yaml up -d --build

## Verificacao rapida a partir da CVM1 no modo distribuido

curl "$EXECUTOR_URL/health"
