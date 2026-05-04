# DNAT Identity Validator

O fluxo operacional suportado neste repositório é o stack via `docker compose`.

Use [RUN_COMPOSE.md](RUN_COMPOSE.md) como fonte principal de execução para:
- subir a `CVM1` com frontend/API/IPFS/contrato
- subir a `CVM3` com builder Firecracker e cache de `.whl`
- subir a `CVM2` com executor Firecracker
- configurar `BUILDER_URL` e `EXECUTOR_URL`
- consultar o fluxo de testes operacionais

## Estrutura

- `docker/`: arquivos Compose ativos
- `smart-contract/`: contrato, API e interface web da CVM1
- `build_vm_runtime/`: builder isolado da CVM3
- `vm_runtime/`: executor isolado da CVM2

## Observações

- A CVM1 recebe app e dataset, fala com IPFS/contrato e nunca instala dependências Python externas.
- O registro de aplicação agora passa pela CVM3, que cria um `worker` efêmero por build, sobe uma `microVM` de build, devolve `application.ext4` e persiste apenas `.whl`.
- O cache de dependências fica somente na CVM3 e guarda apenas arquivos `.whl`.
- A CVM2 executa a aplicação sem rede e devolve o resultado via disco persistente anexado ao guest.
- Resultados de execução, uploads, manifests e artefatos locais ficam fora do versionamento.
- A explicação detalhada da arquitetura atual implementada fica em [ARCHITECTURE.md](ARCHITECTURE.md).
