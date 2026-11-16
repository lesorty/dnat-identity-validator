# Rotinas do DNAT num lugar só. `make` (ou `make help`) lista tudo.
# Tudo aqui é verificação local: pela regra de 12/11, todo dado do artigo sai da nuvem.

SHELL := /bin/bash
SC := smart-contract
MG := model_gate
COMPOSE := docker compose -f docker/direct.compose.yaml -f docker/direct.single-use.compose.yaml
CPUS ?= 0-3

.DEFAULT_GOAL := help
.PHONY: help setup doctor check test test-contract test-judge test-identity e2e teste8 lora demo-cota \
        dev dev-tiny ui-check stack-up stack-seed stack-down stack-tests clean clean-executions board

help: ## lista as rotinas
	@awk 'BEGIN{FS=":.*## "} /^[a-z0-9-]+:.*## /{printf "  \033[1m%-17s\033[0m %s\n", $$1, $$2} /^## /{printf "\n%s\n", substr($$0,4)}' $(MAKEFILE_LIST)

## Ambiente
setup: ## instala tudo: dependências do smart-contract, contrato compilado e ambiente do model_gate
	cd $(SC) && npm ci && npx hardhat compile
	cd $(MG) && ./setup.sh

doctor: ## confere ferramentas, dados, pilha Docker e higiene, e diz o comando que resolve cada pendência
	@python3 -I tools/doctor.py

## Testes rápidos (cerca de 1,5 min, sem rede nem nuvem)
check: doctor test ## doctor e os testes rápidos

test: test-contract test-judge ## contrato, CVM1 e Juiz

test-contract: ## contrato, CVM1, identidade, cota, CVM de job (hardhat test; não use npx mocha, que trava)
	cd $(SC) && npx hardhat test

test-judge: ## Juiz (model_gate, pytest)
	cd $(MG) && uv run --frozen pytest -q

test-identity: ## só identidade e cota (Teste 9 local)
	cd $(SC) && npm run --silent test:identity

## Roteiros de ponta a ponta (pilha descartável; o estado fica em /tmp e sai no fim)
e2e: ## fluxo inteiro com base minúsculo, Juiz real (falha sem prereg) e simulado; ~2 min
	cd $(SC) && node e2e/run_direct.js

teste8: ## Teste 8 local com o Qwen e o Juiz real de fumaça; ~15 min
	cd $(SC) && node e2e/teste8.js

lora: ## LoRA real numa CVM de uso único (precisa da pilha Docker no ar); ~25 min
	cd $(SC) && node e2e/t806_lora.js

demo-cota: ## demonstração da identidade e da cota (o 5º job recusado)
	cd $(SC) && node e2e/demo_cota.js

## Usar a interface
dev: ## pilha semeada com o Qwen e o Juiz real de fumaça na porta 3002 (Ctrl+C encerra); depósito em ~2 min
	cd $(SC) && node e2e/dev_stack.js

dev-tiny: ## pilha semeada com o base minúsculo, em segundos (sem referência: jobs sem veredito)
	cd $(SC) && node e2e/dev_stack.js --tiny

ui-check: ## confere a interface no Chrome headless (todas as abas, 1280 e 390 px) contra a pilha no ar
	node tools/ui_check.js

## Pilha Docker (testes de segurança T1–T5 e CVM de job de uso único)
stack-up: ## reconstrói e sobe a pilha Docker (a cadeia em memória recomeça vazia)
	$(COMPOSE) up -d --build

stack-seed: ## libera o Juiz atual e deposita a bateria na pilha Docker (make stack-seed REF=<id do base>)
	tools/stack_seed.sh $(if $(REF),--reference $(REF))

stack-down: ## derruba a pilha Docker
	$(COMPOSE) down

stack-tests: ## testes de segurança T1–T5 contra a pilha Docker
	bash assets/tests/run_all_tests.sh

## Manutenção
clean: ## apaga temporários antigos, CVMs de job órfãs e processos de pilhas e2e esquecidos
	tools/clean.sh

clean-executions: ## apaga os arquivos em claro que execuções antigas guardaram (metadata e result ficam)
	tools/clean.sh --executions

board: ## regenera a fila (FILA.md, fila.json) e confere a ordem contra o backlog.json
	python3 -I DSN2027/backlog/fila.py
