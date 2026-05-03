# DNAT Identity Validator

O fluxo operacional suportado neste repositorio e o stack via `docker compose`.

Use [RUN_COMPOSE.md](RUN_COMPOSE.md) como fonte unica de execucao para:
- subir o executor `vm_runtime`
- subir o frontend/API com Hardhat e IPFS
- configurar `EXECUTOR_URL`

## Estrutura

- `docker/`: arquivos Compose ativos
- `vm_runtime/`: executor baseado em microVM
- `smart-contract/`: contrato, API e interface web

## Observacoes

- O runner usado pela API para baixar assets do IPFS e enviar bundles ao `vm_runtime` agora fica em `smart-contract/scripts/run_from_cids.py`.
- A `microVM` do executor roda sem interface de rede e devolve o resultado via disco persistente anexado ao guest, que a VM hospedeira coleta apos o shutdown.
- Resultados de execucao, uploads, manifests e artefatos locais ficam fora do versionamento.
