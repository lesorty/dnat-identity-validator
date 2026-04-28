
docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d

$env:EXECUTOR_URL="http://host.docker.internal:5000"
docker compose -f docker/frontend-vm.compose.yaml up -d --build

docker compose -f docker/frontend-vm.compose.yaml up -d