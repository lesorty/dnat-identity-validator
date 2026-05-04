# DNAT Architecture

Este documento descreve a arquitetura atualmente implementada no repositório, agora separada em 3 camadas:

- `CVM1`: cliente, frontend, IPFS, contrato e criptografia
- `CVM2`: builder isolado e cache de `.whl`
- `CVM3`: executor isolado da aplicação

## 1. Componentes

### 1.1 CVM1

A CVM1 executa apenas o serviço `dnat-client`.

Responsabilidades da CVM1:

- receber uploads de dataset e aplicação
- manter o IPFS e o marketplace local
- falar com a CVM2 para buildar `application.ext4`
- nunca instalar nem importar dependências Python externas
- criptografar `application.ext4` recebido da CVM2 e salvar no IPFS
- na execução, buscar dataset + artefato criptografado no IPFS, descriptografar localmente e enviar para a CVM3

Arquivos principais:

- `docker/frontend-vm.compose.yaml`
- `Dockerfile`
- `docker/root-entrypoint.sh`
- `smart-contract/scripts/api-server.js`
- `smart-contract/scripts/run_from_cids.py`

### 1.2 CVM2

A CVM2 executa apenas o serviço `dnat-builder`.

Responsabilidades da CVM2:

- manter somente cache persistente de `.whl`
- expor uma API mínima de build para a CVM1
- criar um `worker` efêmero por requisição de build
- o `worker` sobe a `microVM` de build do Firecracker
- receber de volta `application.ext4` e novas wheels
- persistir apenas as novas `.whl` válidas
- apagar estado temporário da aplicação após cada build

Arquivos principais:

- `docker/builder-vm.compose.yaml`
- `build_vm_runtime/builder.py`
- `build_vm_runtime/worker.py`
- `build_vm_runtime/vm/build-vm.sh`
- `build_vm_runtime/rootfs/runner`

### 1.3 CVM3

A CVM3 continua sendo o executor isolado da aplicação.

Responsabilidades da CVM3:

- receber da CVM1 apenas o bundle de execução
- instanciar a `microVM` executora sem rede
- montar `application.ext4` read-only e o dataset efêmero
- coletar o resultado do disco persistente de saída
- apagar todo o estado efêmero após a execução

Arquivos principais:

- `docker/executor-vm.compose.yaml`
- `vm_runtime/`

## 1.4 Diagramas Visuais

Os diagramas abaixo foram movidos para `PlantUML`, pensando em exportacao para figuras de TCC e apresentacoes.

Arquivos:

- `docs/diagrams/architecture-overview.puml`
- `docs/diagrams/application-registration-sequence.puml`
- `docs/diagrams/execution-sequence.puml`

Eles cobrem:

- visao geral da arquitetura com `CVM1`, `CVM2`, `CVM3` e as `microVMs`
- sequencia de registro da aplicacao
- sequencia de execucao

Para renderizar localmente, voce pode usar uma extensao PlantUML no VS Code ou o CLI oficial, por exemplo:

```bash
plantuml docs/diagrams/architecture-overview.puml
plantuml docs/diagrams/application-registration-sequence.puml
plantuml docs/diagrams/execution-sequence.puml
```

## 2. Fluxo de Registro da Aplicação

1. A aplicação chega à CVM1 com metadados e dependências.
2. A CVM1 materializa o upload localmente.
3. A CVM1 monta um bundle de build com:
   - `application.py`
   - `manifest.json`
4. A CVM1 envia esse bundle para a API da CVM2.
5. A CVM2 cria um `worker` efêmero para aquela build.
6. O `worker` cria os artefatos temporários da build e chama `build-vm.sh`.
7. `build-vm.sh` instancia a `microVM` de build temporária.
8. A `microVM` de build recebe:
   - o código da aplicação
   - o manifesto com dependências
   - um disco com o cache atual de `.whl` da CVM2
9. A `microVM` resolve dependências, instala em `site-packages` e gera:
   - `application.ext4`
   - `wheelhouse` com wheels reaproveitáveis
10. A `microVM` grava esses artefatos no disco persistente de saída e morre.
11. O `worker` coleta a saída, ingere apenas arquivos `.whl` válidos no cache da CVM2, reempacota a resposta e termina.
12. A CVM2 devolve à CVM1 apenas:
   - `application.ext4`
   - `build-result.json`
13. A CVM1 criptografa `application.ext4` e publica o blob no IPFS.

## 3. Fluxo de Execução

1. A CVM1 verifica acesso no marketplace.
2. A CVM1 busca no IPFS:
   - o dataset
   - o `application.ext4` criptografado
3. A CVM1 descriptografa o artefato da aplicação localmente.
4. A CVM1 monta um bundle temporário e envia para a CVM3.
5. A CVM3 instancia a `microVM` executora com:
   - `rootfs` base imutável
   - disco de entrada com `workspace`
   - disco read-only com `application.ext4`
   - disco persistente de saída
6. O guest executa a aplicação sem rede.
7. O resultado é gravado no disco de saída.
8. A CVM3 coleta `result.json`, `stdout.txt` e `stderr.txt`.
9. A CVM3 limpa overlay, discos temporários, mounts e socket do Firecracker.

## 4. Worker da CVM2

O `worker` é um processo efêmero criado por build.

Ele existe para:

- dar um escopo limpo de processo por requisição
- concentrar diretórios temporários, subprocessos, mounts e artefatos daquela build
- ingerir wheels novas no cache da CVM2 sem deixar a aplicação persistida
- morrer completamente ao final, evitando contaminação entre builds

Então a cadeia real fica:

- `builder.py`: serviço HTTP persistente da CVM2
- `worker.py`: processo temporário por build
- `build-vm.sh`: orquestrador host-side da `microVM`
- `microVM` de build: ambiente que instala dependências e monta o `application.ext4`

## 5. Propriedades de Segurança

- A CVM1 não executa `pip install` nem importa wheels.
- A CVM1 não mantém cache de dependências Python.
- A CVM2 persiste apenas `.whl`, nunca a aplicação.
- Apenas `.whl` entram no cache da CVM2.
- Wheels maiores que o limite configurado são descartadas.
- O cache total da CVM2 é podado por tamanho.
- A CVM2 não tem IPFS, wallet privada nem frontend.
- A comunicação CVM1 -> CVM2 é feita apenas pela API de build.
- A `microVM` de build devolve resultados apenas via disco persistente de saída.
- A `microVM` executora continua sem stack de rede no kernel.
- A CVM3 não acessa IPFS.
- O dataset nunca é enviado para a CVM2.
- A aplicação sensível não fica persistida na CVM3 após a limpeza.

Observação:
- `mTLS` ainda não está implementado no repositório.
- Em ambiente distribuído real, a restrição de rede entre CVM1, CVM2 e CVM3 deve ser reforçada via firewall/security groups/ACLs do host.

## 6. Persistência por Camada

### 6.1 Persistente na CVM1

- estado do IPFS
- dados do marketplace local
- artefatos e execuções exibidos na interface
- blobs criptografados de aplicação publicados no IPFS

### 6.2 Persistente na CVM2

- runtime base do builder
- kernel e rootfs base do guest de build
- cache de `.whl`

### 6.3 Persistente na CVM3

- runtime base do executor
- kernel e rootfs base do guest

### 6.4 Efêmero na CVM1

- uploads temporários
- bundles temporários antes do envio à CVM2
- artefatos temporários descriptografados antes do envio à CVM3

### 6.5 Efêmero na CVM2

- diretórios temporários do `worker`
- bundles de entrada e saída do build
- overlays e discos temporários da `microVM` de build
- cópia temporária da aplicação durante o build

### 6.6 Efêmero na CVM3

- overlay do rootfs
- discos de entrada/saída
- mounts temporários
- socket do Firecracker

## 7. Comandos de Teste

### 7.1 Subir os serviços

```bash
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"

docker compose -f docker/builder-vm.compose.yaml build --no-cache
docker compose -f docker/builder-vm.compose.yaml up -d

docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d

docker compose -f docker/frontend-vm.compose.yaml build --no-cache
docker compose -f docker/frontend-vm.compose.yaml up -d
```

### 7.2 Health checks

```bash
curl http://127.0.0.1:3001/api/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-builder:5100/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health
```

### 7.3 Teste funcional

1. Abrir `http://127.0.0.1:3001`
2. Registrar dataset
3. Registrar aplicação com dependências, por exemplo `requests` ou `numpy,pandas`
4. Comprar acesso
5. Executar `Run From CIDs`

### 7.4 Verificar o cache de wheels da CVM2

```bash
docker exec dnat-builder sh -lc 'find /var/dnat/wheel-cache -maxdepth 1 -type f -name "*.whl" | sort'
```

### 7.5 Verificar limpeza do executor

```bash
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'
```
