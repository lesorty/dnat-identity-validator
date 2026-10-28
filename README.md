# DNAT Identity Validator

Marketplace confidencial de dados e aplicações: o dono do dataset e o dono da aplicação negociam
o direito de executar uma sobre o outro, e a execução acontece isolada, sem rede.

**Trabalho em andamento:** artigo para o **DSN 2027** — **proteção de modelos abertos**: pesos e
derivados sob custódia numa CVM e um portão de liberação contra obliteração. Plano, decisões e
LaTeX em [DSN2027/](DSN2027/). O material do Juiz de código e do bug bounty, descartados, está na
tag git `archive/juiz-bounty-2026-10`.

## Estrutura

| Caminho | O que é |
|---|---|
| `smart-contract/` | Contrato, API, CLI e interface web (CVM1, plano de controle) |
| `build_vm_runtime/` | Builder (CVM2): monta a app com as dependências, cache de `.whl`; numa CVM, em modo direto |
| `vm_runtime/` | Executor: roda o job; numa CVM, em modo direto (vira a CVM de job de uso único da D4) |
| `docker/` | Composes de cada plano e entrypoint da CVM1 |
| `assets/` | Apps de exemplo e de ataque, datasets sintéticos, suíte de testes T1–T5 |
| `DSN2027/` | Página de trabalho do artigo |
| `pesquisa/` | Levantamentos de literatura (transparência e confiabilidade de LLMs; proteção de modelos) |

## Como rodar

- Subir os planos e testar o fluxo: [RUN_COMPOSE.md](RUN_COMPOSE.md).
- Arquitetura: a definida é a D4 em [DSN2027/DECISOES.md](DSN2027/DECISOES.md) (CVM1 plano de controle,
  builder numa CVM, uma CVM de uso único por job, sem microVM). [ARCHITECTURE.md](ARCHITECTURE.md)
  descreve o código legado.
- Testes de segurança: [assets/tests/EVALUATION_PROTOCOL.md](assets/tests/EVALUATION_PROTOCOL.md).

## Observações

- A CVM1 recebe app e dataset, fala com IPFS e contrato e nunca instala dependências externas.
- A CVM2 monta a app com as dependências e persiste só `.whl`.
- O executor roda o job; na arquitetura (D4), cada job ganha uma CVM de uso único, sem rede para o
  script, descartada no fim.
- Dataset e aplicação ficam cifrados (AES-256-GCM) no IPFS; teste: `cd smart-contract && npm run test:envelope`.
- **Não há microVM na arquitetura.** O Firecracker não roda numa CVM (sem virtualização aninhada);
  numa CVM o código usa o **modo direto** (`build_vm_runtime/vm/build-direct.sh`,
  `vm_runtime/vm/run-direct.sh`), e o caminho com Firecracker (`run-vm.sh`, `build-vm.sh`) é
  legado. A troca pela CVM de uso único está planejada em `DSN2027/` (D4, E13 W7).
