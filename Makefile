# Rotinas do DNAT num lugar só. `make` (ou `make help`) lista tudo.
# Tudo aqui é verificação local: pela regra de 12/11, todo dado do artigo sai da nuvem.

SHELL := /bin/bash
SC := smart-contract
MG := model_gate
COMPOSE := docker compose -f docker/direct.compose.yaml -f docker/direct.single-use.compose.yaml
CPUS ?= 0-3

.DEFAULT_GOAL := help
.PHONY: help setup doctor check test test-contract test-judge test-identity e2e teste8 lora demo-cota t10 t11 \
        testes testes-verificar teste testes-status testes-pacote testes-executor \
        dev dev-tiny ui-check stack-up stack-seed stack-down stack-tests clean clean-executions board \
        nuvem-enviar nuvem-preparar nuvem-bootstrap dados ficha congelar campanha-status campanha pacote importar numeros

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

t10: ## Teste 10, o preço da identidade (d de 16 a 22 aqui; ARGS="--max 27 --reps 3" na nuvem); ~3 min
	cd $(SC) && node e2e/t10_preco_identidade.js $(ARGS)

t11: ## Teste 11, o atacante com muitas identidades (usa o resultado do t10, se houver); ~10 s
	cd $(SC) && node e2e/t11_atacante_sybil.js $(ARGS)

## Testes T1 a T11 (tools/testes; PERFIL=mini no notebook; na VM: PERFIL=ensaio, PERFIL=piloto, PERFIL=nuvem com FASE=1 ou 2)
PERFIL ?= mini
FASE ?= todas
testes-verificar: ## pré-voo de todos os testes, sem rodar nada (antes de ligar a VM cara)
	python3 -I tools/testes/todos.py verificar --perfil $(PERFIL) --fase $(FASE) $(ARGS)

testes: ## roda os testes na ordem, retomando (mini: ~20 min; ensaio: na GPU da VM; nuvem: FASE=1, depois FASE=2)
	python3 -I tools/testes/todos.py rodar --perfil $(PERFIL) --fase $(FASE) $(ARGS)

teste: ## um teste só: make teste T=3 [PERFIL=nuvem] [ARGS="--refazer vereditos"]
	python3 -I tools/testes/$$(ls tools/testes | grep -E "^t0?$(T)_" | head -1) --perfil $(PERFIL) $(ARGS)

testes-status: ## situação de cada teste da campanha (passos e conferências)
	python3 -I tools/testes/todos.py status --perfil $(PERFIL)

testes-pacote: ## .tar.gz da campanha (sem textos gerados); ARGS=--completo: com textos, referências e adaptadores (fora do git)
	python3 -I tools/testes/todos.py pacote --perfil $(PERFIL) $(ARGS)

testes-executor: ## testes do próprio executor (retomada, falha, tempo esgotado, pré-voo)
	python3 -I tools/testes/test_executor.py

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

## Nuvem (fase de testes; o passo a passo está em tools/cloud/README.md)
nuvem-enviar: ## no notebook: código (git bundle) e os 2 arquivos locais para a VM (make nuvem-enviar VM=usuario@host)
	tools/cloud/enviar.sh $(VM) $(ARGS)

nuvem-preparar: ## na VM: tudo o que os testes precisam, GPU inclusive (ARGS="--docker" ou "--sem-gpu"), e o pré-voo
	tools/cloud/preparar_testes.sh $(ARGS)

nuvem-bootstrap: ## prepara uma VM Ubuntu nova: ferramentas fixas, make setup, dados, ficha e doctor
	tools/cloud/bootstrap.sh $(ARGS)

dados: ## baixa e confere os dados do model_gate pelos manifestos (ARGS="--judges --population")
	tools/cloud/fetch_data.sh $(ARGS)

ficha: ## ficha da máquina (CPU, BF16/AMX, confidencial, tipo de VM), para o artigo e o pacote
	python3 -I tools/cloud/machine_card.py

congelar: ## fecha o sistema (T-1611): tag congelado-* com os hashes do Juiz e do prereg (ARGS=--ensaio)
	tools/congelar.sh $(ARGS)

campanha-status: ## o que a campanha vai rodar, o que já rodou e o que está bloqueado ou sem script
	uv run --project $(MG) --frozen --quiet python tools/cloud/campanha.py status

campanha: ## roda os passos pendentes da campanha (PASSOS="ficha vazao", ARGS="--forcar --sem-congelamento")
	uv run --project $(MG) --frozen --quiet python tools/cloud/campanha.py run $(PASSOS) $(ARGS)

pacote: ## empacota resultados, registro, fichas e logs da campanha para trazer de volta
	uv run --project $(MG) --frozen --quiet python tools/cloud/campanha.py pacote

importar: ## no notebook: importa um pacote da nuvem para resultados_nuvem/ (PACOTE=arquivo.tar.gz)
	tools/cloud/importar.sh $(PACOTE)

## Manutenção
clean: ## apaga temporários antigos, CVMs de job órfãs e processos de pilhas e2e esquecidos
	tools/clean.sh

clean-executions: ## apaga os arquivos em claro que execuções antigas guardaram (metadata e result ficam)
	tools/clean.sh --executions

numeros: ## gera DSN2027/artigo/numeros.tex: os números do artigo tirados dos resultados (nuvem congelada antes de local)
	python3 -I tools/numeros.py

board: ## regenera a fila (FILA.md, fila.json) e confere a ordem contra o backlog.json
	python3 -I DSN2027/backlog/fila.py
