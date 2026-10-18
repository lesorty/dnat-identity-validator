# DNAT Identity Validator

Marketplace confidencial de dados e aplicações: o dono do dataset e o dono da aplicação negociam
o direito de executar uma sobre o outro, e a execução acontece isolada, sem rede.

**Trabalho em andamento:** artigo para o **DSN 2027** — aplicações em imagem OCI e um **Juiz de
IA** que verifica se uma aplicação vaza dados. Plano, decisões e LaTeX em [DSN2027/](DSN2027/).

## Estrutura

| Caminho | O que é |
|---|---|
| `smart-contract/` | Contrato, API, CLI e interface web (CVM1, plano de controle) |
| `build_vm_runtime/` | Builder: worker efêmero e microVM de build, cache de `.whl` (CVM2) |
| `vm_runtime/` | Executor: microVM sem rede que roda a aplicação (CVM3) |
| `docker/` | Composes de cada plano e entrypoint da CVM1 |
| `assets/` | Apps de exemplo e de ataque, datasets sintéticos, suíte de testes T1–T5 |
| `DSN2027/` | Página de trabalho do artigo |

## Como rodar

- Subir os planos e testar o fluxo: [RUN_COMPOSE.md](RUN_COMPOSE.md).
- Arquitetura implementada hoje: [ARCHITECTURE.md](ARCHITECTURE.md).
- Testes de segurança: [assets/tests/EVALUATION_PROTOCOL.md](assets/tests/EVALUATION_PROTOCOL.md).

## Observações

- A CVM1 recebe app e dataset, fala com IPFS e contrato e nunca instala dependências externas.
- O build roda numa microVM efêmera na CVM2, que devolve `application.ext4` e persiste só `.whl`.
- A CVM3 executa a aplicação sem rede e devolve o resultado por um disco de saída.
- Dataset e aplicação ficam cifrados (AES-256-GCM) no IPFS; teste: `cd smart-contract && npm run test:envelope`.
- Dentro de uma CVM o Firecracker não roda (sem virtualização aninhada): existe um **modo direto**
  sem microVM (`build_vm_runtime/vm/build-direct.sh`, `vm_runtime/vm/run-direct.sh`), e a migração
  para OCI está em andamento (`DSN2027/`).
