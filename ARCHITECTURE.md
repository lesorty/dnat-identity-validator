# DNAT Architecture

Este documento descreve a arquitetura atualmente implementada no repositório.

## 1. Componentes

### 1.1 CVM1

A CVM1 agora tem dois serviços:

- `dnat-client`: web/API, Hardhat e IPFS
- `dnat-builder`: builder isolado de aplicações com Firecracker

Responsabilidades da CVM1:

- receber uploads de dataset e aplicação
- manter o IPFS e o marketplace local
- manter um cache persistente e separado de wheels Python em `dnat_wheel_cache`
- nunca instalar nem importar dependências Python no `dnat-client`
- disparar a `microVM` de build via `dnat-builder`
- criptografar o `application.ext4` retornado pelo builder e salvar no IPFS
- na execução, buscar dataset + artefato criptografado no IPFS, descriptografar localmente e enviar para a CVM2

Arquivos principais:

- `docker/frontend-vm.compose.yaml`
- `Dockerfile`
- `docker/root-entrypoint.sh`
- `smart-contract/scripts/api-server.js`
- `smart-contract/scripts/run_from_cids.py`
- `build_vm_runtime/`

### 1.2 CVM2

A CVM2 continua sendo o executor isolado da aplicação.

Responsabilidades da CVM2:

- receber da CVM1 apenas o bundle de execução
- instanciar a `microVM` executora sem rede
- montar `application.ext4` read-only e o dataset efêmero
- coletar o resultado do disco persistente de saída
- apagar todo o estado efêmero após a execução

Arquivos principais:

- `docker/executor-vm.compose.yaml`
- `vm_runtime/`

## 2. Fluxo de Registro da Aplicação

1. A aplicação chega à CVM1 com metadados e dependências.
2. A CVM1 materializa o upload localmente.
3. A CVM1 verifica o cache de wheels, que contém apenas arquivos `.whl`.
4. A CVM1 chama `dnat-builder`.
5. O `dnat-builder` instancia uma `microVM` de build temporária.
6. A `microVM` de build recebe:
   - o código da aplicação
   - o manifesto com dependências
   - um disco read-only com o cache de wheels da CVM1, quando existir
7. A `microVM` de build tem acesso à internet pública, mas não recebe canal de comunicação de volta com a CVM1.
8. A `microVM` resolve dependências, instala tudo dentro do ambiente dela e gera:
   - `application.ext4`
   - novas wheels reaproveitáveis, quando houver
9. A `microVM` grava esses artefatos em um disco persistente de saída e morre.
10. O `dnat-builder` coleta o `application.ext4` e as novas wheels.
11. A CVM1 salva no cache apenas as wheels validadas:
   - somente `.whl`
   - tamanho individual limitado
   - total do cache limitado
   - nunca instala nem importa esses arquivos
12. A CVM1 criptografa `application.ext4` e publica o blob no IPFS.

## 3. Fluxo de Execução

1. A CVM1 verifica acesso no marketplace.
2. A CVM1 busca no IPFS:
   - o dataset
   - o `application.ext4` criptografado
3. A CVM1 descriptografa o artefato da aplicação localmente.
4. A CVM1 monta um bundle temporário e envia para a CVM2.
5. A CVM2 instancia a `microVM` executora com:
   - `rootfs` base imutável
   - disco de entrada com `workspace`
   - disco read-only com `application.ext4`
   - disco persistente de saída
6. O guest executa a aplicação sem rede.
7. O resultado é gravado no disco de saída.
8. A CVM2 coleta `result.json`, `stdout.txt` e `stderr.txt`.
9. A CVM2 limpa overlay, discos temporários, mounts e socket do Firecracker.

## 4. Propriedades de Segurança

- A CVM1 não executa `pip install` nem importa wheels do cache.
- O cache de dependências fica em volume separado: `dnat_wheel_cache`.
- Apenas `.whl` entram no cache.
- Wheels maiores que o limite configurado são descartadas.
- O cache total é podado por tamanho.
- A `microVM` de build usa internet pública para resolver dependências, mas o acesso a redes privadas e ao host da CVM1 é bloqueado por regras no host do builder.
- A `microVM` de build devolve resultados apenas via disco persistente de saída.
- A `microVM` executora continua sem stack de rede no kernel.
- A CVM2 não acessa IPFS.
- A aplicação sensível não fica persistida na CVM2 após a limpeza.

## 5. Persistência por Camada

### 5.1 Persistente na CVM1

- estado do IPFS
- dados do marketplace local
- artefatos e execuções exibidos na interface
- cache de wheels `.whl`
- blobs criptografados de aplicação publicados no IPFS

### 5.2 Persistente na CVM2

- runtime base do executor
- kernel e rootfs base do guest

### 5.3 Efêmero na CVM1

- uploads temporários
- bundles temporários do builder
- artefatos temporários retornados pelo builder antes da criptografia/IPFS

### 5.4 Efêmero na CVM2

- overlay do rootfs
- discos de entrada/saída
- mounts temporários
- socket do Firecracker

## 6. Comandos de Teste

### 6.1 Subir os serviços

```bash
export ASSET_ENCRYPTION_KEY="dnat-dev-asset-key"

docker compose -f docker/executor-vm.compose.yaml build --no-cache
docker compose -f docker/executor-vm.compose.yaml up -d

docker compose -f docker/frontend-vm.compose.yaml build --no-cache
docker compose -f docker/frontend-vm.compose.yaml up -d
```

### 6.2 Health checks

```bash
curl http://127.0.0.1:3001/api/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-executor:5000/health
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client curl http://dnat-builder:5100/health
```

### 6.3 Teste funcional

1. Abrir `http://127.0.0.1:3001`
2. Registrar dataset
3. Registrar aplicação com dependências, por exemplo `requests` ou `numpy,pandas`
4. Comprar acesso
5. Executar `Run From CIDs`

### 6.4 Verificar o cache de wheels

```bash
docker compose -f docker/frontend-vm.compose.yaml exec dnat-client sh -lc 'find /app/smart-contract/wheel-cache -maxdepth 1 -type f -name "*.whl" | sort'
```

### 6.5 Verificar limpeza do executor

```bash
docker exec dnat-executor sh -lc 'find /tmp -maxdepth 2 \( -name firecracker.socket -o -name rootfs-overlay.ext4 -o -name input.ext4 -o -name output.ext4 -o -name serial.log \) -print | sort'
docker exec dnat-executor sh -lc 'mount | grep -E "result-mount|input-mount|output-mount" || true'
```
