# DNAT Architecture

Este documento separa claramente:

- a arquitetura atualmente implementada no repositorio
- a arquitetura alvo aprovada para a proxima fase
- os comandos para testar o sistema atual

## 1. Arquitetura Atual Implementada

### 1.1 Papéis das VMs

#### CVM1

A CVM1 e a maquina de aplicacao. Ela:

- executa a API web e a interface
- mantem o no local de IPFS
- faz upload de datasets e aplicacoes para o IPFS
- consulta o contrato/local marketplace
- resgata do IPFS os bytes da aplicacao e do dataset no momento da execucao
- empacota esses bytes em um bundle temporario
- envia esse bundle para a CVM2 pela rota HTTP do executor

Na implementacao atual, a CVM1 e representada pelo servico `dnat-client` e pelo codigo em:

- `docker/frontend-vm.compose.yaml`
- `docker/root-entrypoint.sh`
- `smart-contract/scripts/api-server.js`
- `smart-contract/scripts/run_from_cids.py`

#### CVM2

A CVM2 e a maquina executora. Ela:

- recebe da CVM1 apenas o bundle da execucao
- cria uma `microVM` Firecracker temporaria
- injeta o bundle como disco de entrada read-only
- injeta um disco de saida temporario para persistencia do resultado
- coleta o resultado apos a execucao
- remove o estado temporario da `microVM`

Na implementacao atual, a CVM2 e representada pelo servico `dnat-executor` e pelo codigo em:

- `docker/executor-vm.compose.yaml`
- `vm_runtime/executor.py`
- `vm_runtime/vm/run-vm.sh`
- `vm_runtime/rootfs/init`
- `vm_runtime/rootfs/runner`

### 1.2 Fluxo Atual de Cadastro de Aplicacao

1. O usuario registra a aplicacao via CVM1.
2. A CVM1 materializa o upload localmente.
3. A CVM1 gera um artefato `ext4` read-only da aplicacao.
4. A CVM1 criptografa esse artefato.
5. A CVM1 envia o blob criptografado para o IPFS.
6. O marketplace passa a apontar para o CID do artefato criptografado da aplicacao.

Observacao:

- na implementacao atual, esse build ainda nao nasce de uma imagem OCI/Docker completa
- a CVM1 gera diretamente um artefato `ext4` de execucao a partir do arquivo da aplicacao

### 1.3 Fluxo Atual de Execucao

1. O usuario registra uma aplicacao e um dataset via CVM1.
2. A CVM1 salva o dataset no IPFS e grava no marketplace os metadados/URIs.
3. Quando a execucao e solicitada, a CVM1 baixa do IPFS:
   - o dataset
   - o artefato criptografado da aplicacao
4. A CVM1 descriptografa o artefato da aplicacao localmente.
5. A CVM1 cria um `workspace/` temporario com:
   - `workspace/data/dataset.csv`
   - `workspace/run.sh`
   - `artifacts/application.ext4`
6. A CVM1 compacta esse workspace em `bundle.tar.gz`.
7. A CVM1 envia o bundle para `POST /execute` da CVM2.
8. A CVM2 cria uma `microVM` Firecracker com:
   - `rootfs` base imutavel do guest
   - overlay temporario do `rootfs`
   - disco de entrada com o `workspace`
   - disco read-only separado com `application.ext4`
   - disco de saida para o resultado
9. O guest monta os discos, extrai o bundle, monta a aplicacao em `/mnt/dnat-app` e executa `workspace/run.sh`.
10. O guest grava `result.json`, `stdout.txt` e `stderr.txt` no disco de saida.
11. O host da CVM2 remonta o disco de saida, le o resultado e devolve o JSON para a CVM1.
12. A CVM2 remove overlays, discos temporarios, mounts e socket do Firecracker.

### 1.3 Propriedades de Seguranca Implementadas Hoje

- A `microVM` nao recebe interface de rede.
- O kernel do guest foi compilado sem `NET`, `INET`, `IPV6` e `VIRTIO_NET`.
- O resultado volta pela persistencia em disco, nao como payload principal via serial.
- O dataset entra na `microVM` como dado efemero de execucao.
- A aplicacao entra na `microVM` como artefato `ext4` read-only descriptografado pela CVM1 antes do envio.
- A CVM2 limpa o estado temporario apos a coleta do resultado.

### 1.4 Limites da Implementacao Atual

Os pontos abaixo ainda nao estao implementados como politica forte do sistema:

- A CVM2 ainda nao esta restringida no nivel de rede para falar exclusivamente com a CVM1.
- O builder atual da aplicacao ainda nao usa uma imagem OCI/Docker completa como origem.
- A fase de build isolado forte da aplicacao na CVM1 ainda pode ser endurecida.

## 2. Arquitetura Alvo Aprovada

Esta e a arquitetura aprovada para a proxima fase.

### 2.1 Fluxo de Cadastro de Aplicacao

1. A aplicacao e cadastrada na CVM1.
2. A CVM1 builda a imagem da aplicacao em ambiente isolado.
3. A CVM1 converte a imagem buildada para um artefato read-only de execucao:
   - `squashfs`, ou
   - `ext4` read-only
4. A CVM1 criptografa esse artefato.
5. A CVM1 salva o artefato criptografado no IPFS.
6. O marketplace passa a referenciar esse artefato de execucao.

### 2.2 Fluxo de Execucao Aprovado

1. A execucao e solicitada pela CVM1.
2. A CVM1 resgata do IPFS:
   - o artefato read-only da aplicacao
   - o dataset
3. A CVM1 envia esses artefatos diretamente para a CVM2.
4. A CVM2 nao consulta IPFS e nao deve depender de internet para esse fluxo.
5. A CVM2 instancia a `microVM` com:
   - `rootfs` base do runtime
   - artefato read-only da aplicacao
   - artefato read-only do dataset
   - disco read-write temporario do resultado
6. A `microVM` executa.
7. O guest grava o resultado no disco de saida.
8. A CVM2 coleta o resultado, responde para a CVM1 e apaga o estado efemero.

### 2.3 Requisitos Operacionais da Arquitetura Alvo

- A CVM2 deve conversar apenas com a CVM1.
- A CVM2 nao deve buscar nada no IPFS.
- A aplicacao sensivel nao deve permanecer cacheada de forma persistente na CVM2.
- A aplicacao deve chegar pronta para execucao, evitando `pip install`, `apt-get` ou build dinamico na CVM2.

## 3. Dados Persistentes por Camada

### 3.1 Persistente na CVM1

- estado do IPFS
- uploads e manifests do marketplace
- artefatos locais da API/web
- metadados de execucao exibidos ao usuario
- artefatos criptografados de aplicacao publicados no IPFS

### 3.2 Persistente na CVM2

Hoje:

- binario do Firecracker
- kernel do guest
- `rootfs` base do guest

Na arquitetura alvo:

- runtime base imutavel da `microVM`
- nenhum cache persistente obrigatorio da aplicacao sensivel

### 3.3 Efemero na CVM2

- overlay do `rootfs`
- disco de entrada
- disco de saida
- mountpoints temporarios
- socket do Firecracker
- logs temporarios de execucao

## 4. Mapeamento de Arquivos no Repositorio

### 4.1 CVM1

- `docker/frontend-vm.compose.yaml`
- `docker/root-entrypoint.sh`
- `smart-contract/scripts/api-server.js`
- `smart-contract/scripts/build_application_artifact.py`
- `smart-contract/scripts/run_from_cids.py`
- `smart-contract/web/`

### 4.2 CVM2

- `docker/executor-vm.compose.yaml`
- `vm_runtime/Dockerfile.build`
- `vm_runtime/build/build-kernel.sh`
- `vm_runtime/build/build-rootfs.sh`
- `vm_runtime/executor.py`
- `vm_runtime/start-executor.sh`
- `vm_runtime/vm/run-vm.sh`
- `vm_runtime/rootfs/init`
- `vm_runtime/rootfs/runner`

## 5. Comandos de Teste do Sistema Atual

Os comandos abaixo validam a arquitetura hoje implementada.

### 5.1 Modo local no mesmo host Docker

Subir o executor:

```bash
docker compose -f docker/executor-vm.compose.yaml build
docker compose -f docker/executor-vm.compose.yaml up -d
```

Subir a CVM1 local:

```bash
unset EXECUTOR_URL
docker compose -f docker/frontend-vm.compose.yaml up -d --build
```

### 5.2 Verificacoes basicas

Saude do executor a partir da CVM1:

```bash
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health
```

Saude da API web:

```bash
curl http://127.0.0.1:3001/api/health
```

### 5.3 Teste funcional pela interface

1. Abrir `http://127.0.0.1:3001`
2. Registrar dataset
3. Registrar aplicacao
   A CVM1 deve gerar o artefato `ext4`, criptografar e publicar no IPFS.
4. Comprar acesso
5. Executar `Run From CIDs`

### 5.4 Teste funcional pela API

Listar assets:

```bash
curl http://127.0.0.1:3001/api/assets
```

Listar execucoes:

```bash
curl http://127.0.0.1:3001/api/executions
```

Ver detalhes de uma execucao:

```bash
curl http://127.0.0.1:3001/api/executions/EXECUTION_ID
```

### 5.5 Verificacao de limpeza da `microVM`

Verificar se nao restou processo Firecracker:

```bash
docker exec dnat-executor sh -lc 'ps -ef | grep firecracker | grep -v grep || true'
```

Verificar se nao restaram artefatos temporarios da `microVM` em `/tmp`:

```bash
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
```

Verificar se nao restaram mounts temporarios:

```bash
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'
```

### 5.6 Modo distribuido em duas VMs

Na CVM2:

```bash
docker compose -f docker/executor-vm.compose.yaml build
docker compose -f docker/executor-vm.compose.yaml up -d
```

Na CVM1:

```bash
export EXECUTOR_URL="http://IP_DA_CVM2:5000"
docker compose -f docker/frontend-vm.compose.yaml up -d --build
curl "$EXECUTOR_URL/health"
```

## 6. Proximo Passo de Endurecimento

O proximo passo natural e endurecer o builder da aplicacao na CVM1 para que a
geracao do artefato `ext4` passe a nascer de uma imagem OCI/Docker buildada em
ambiente mais isolado, mantendo o restante do fluxo atual:

- artefato read-only
- criptografia antes do IPFS
- resgate pela CVM1
- envio da CVM1 para a CVM2
- execucao da `microVM` sem que a CVM2 fale com o IPFS
