docker compose -f docker/frontend.compose.yaml build --no-cache
docker compose -f docker/frontend-vm.compose.yaml up -d


docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d
