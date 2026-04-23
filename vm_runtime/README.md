# DNAT VM Runtime - Puro Executor

Minimal executor para microVMs: recebe bundle → executa → retorna resultado → deleta.

## Setup Rápido (Local - Recomendado)

**Para evitar demora do Docker, execute localmente no Linux:**

```bash
# Setup de uma vez (~30-40 min: Linux kernel 6.6 + Ubuntu rootfs)
bash setup-local.sh

# Testa se está tudo ok
firecracker --version
ls -lh artifacts/vmlinux artifacts/rootfs.ext4

# Start servidor executor
python3 executor.py 5000 &

# Demo
curl -X POST --data-binary @seu-bundle.tar.gz http://localhost:5000/execute | jq .
```

**O que setup-local.sh faz:**

- ✅ Instala: build-essential, python3, debootstrap, qemu-utils, Firecracker v1.7.0
- ✅ Compila Linux 6.6 otimizado (KVM, Virtio drivers)
- ✅ Cria Ubuntu Jammy rootfs mínimo (~512MB)
- ✅ Verifica todas as dependências

> **Nota:** Primeira execução compila kernel (20-30 min com paralelização). Próximas são instantâneas.

## Setup com Docker (Alternativa)

Se preferir containerizado, o Dockerfile agora faz o build completo automaticamente:

```bash
# Build completo (kernel + rootfs) - ~40-50 min primeira vez
docker build -f Dockerfile.build -t dnat-executor .

# Executar servidor automaticamente
docker run -p 5000:5000 dnat-executor

# Ou executar shell para debug
docker run -it dnat-executor /bin/bash
```

**Nota Importante:** O build completo do Docker pode falhar devido a limitações de privilégios para montar filesystems. Para uso completo, recomendamos usar o setup local (`bash setup-local.sh`) que funciona perfeitamente no Linux nativo.

Se quiser usar Docker mesmo assim, você pode:

1. Buildar localmente primeiro: `bash setup-local.sh`
2. Depois usar Docker apenas para runtime: `docker build -f Dockerfile.build -t dnat-executor .`

**O que o Dockerfile faz:**

- ✅ Instala todas as dependências (build-essential, python3, debootstrap, etc.)
- ✅ Compila Linux 6.6 otimizado (~20-30 min)
- ✅ Cria Ubuntu rootfs (~5-10 min)
- ✅ Inicia executor HTTP automaticamente na porta 5000

## Rápido

```bash
# Build (uma vez, ~15-30 min)
bash build/ensure-image.sh
bash setup-runtime.sh

# Criar bundle
tar -czf bundle.tar.gz workspace/

# Executar (opção 1 - script)
bash execute-bundle.sh bundle.tar.gz | jq .

# Executar (opção 2 - HTTP)
python3 executor.py 5000 &
curl -X POST --data-binary @bundle.tar.gz http://localhost:5000/execute | jq .
```

## Estrutura

```
vm_runtime/
├── executor.py              # HTTP POST /execute (~60 linhas)
├── execute-bundle.sh        # Script direto (~2 linhas)
├── quickstart.sh            # Setup automático
│
├── vm/
│   └── run-vm.sh           # Executa VM (~55 linhas)
│
├── rootfs/
│   ├── init                # Boot VM (~4 linhas)
│   └── runner              # Executa bundle (~45 linhas)
│
├── build/
│   ├── ensure-image.sh     # Checa/constrói imagens
│   ├── build-kernel.sh     # Compila Linux 6.6
│   ├── build-rootfs.sh     # Cria rootfs via debootstrap
│   └── build-image.sh      # (deprecated)
│
├── artifacts/              # Saída do build
│   ├── vmlinux             # Kernel compilado
│   └── rootfs.ext4         # Base filesystem
│
├── input/                  # Bundles temporários
└── output/                 # Resultados (se salvo)
```

## Como Funciona

### 1. Client envia bundle

```bash
curl -X POST --data-binary @my-bundle.tar.gz \
  http://localhost:5000/execute
```

### 2. Host setup

- Cria workdir epêmero: `mktemp -d`
- Cria overlay CoW: `qemu-img -b rootfs.ext4`
- Cria output disk: novo ext4 (64MB)
- Inicia HTTP server: porta 8888
- Inicia Firecracker

### 3. VM executa

```
init
├─ Mount /proc, /sys
├─ Redireciona output → /dev/ttyS0
└─ Exec /runner

runner (Python3)
├─ Aguarda output disk
├─ Download bundle via curl
├─ Extract tar -xzf
├─ Execute workspace/run.sh
├─ Escreve result.json
├─ Sinaliza "EXECUTION_COMPLETE"
└─ poweroff -f

Dentro da VM (seu código):
├─ python3 -m venv venv
├─ pip install -r env/requirements.txt
└─ python code/script.py data/dataset.parquet
```

### 4. Host retorna

- Verifica serial: "EXECUTION_COMPLETE"
- Monta output disk
- Lê result.json
- **Cleanup automático** (trap):
  - Kill HTTP server
  - Kill Firecracker
  - Delete overlay
  - Delete output disk
  - Delete workdir

### 5. Client recebe

```json
{
  "returncode": 0,
  "stdout": "...",
  "stderr": ""
}
```

## Bundle Format

```
bundle.tar.gz
└── workspace/
    ├── run.sh              # Entry point (obrigatório)
    ├── code/
    │   └── script.py       # Seu código
    ├── data/
    │   └── dataset.parquet # Seus dados
    └── env/
        └── requirements.txt  # pip deps
```

### Exemplo run.sh

```bash
#!/bin/bash
set -e

# Setup environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r env/requirements.txt

# Run application
python code/script.py data/dataset.parquet
```

## Performance

| Etapa                    | Tempo                           |
| ------------------------ | ------------------------------- |
| Kernel compile           | 5-10 min (uma vez)              |
| Rootfs create            | 30-60 seg (uma vez)             |
| VM startup               | ~2 seg                          |
| Bundle download          | ~100ms                          |
| Execution                | ~1-30 seg (depende do workload) |
| Cleanup                  | ~2 seg                          |
| **Total (por execução)** | **~5-40 seg**                   |

## Security

- ✅ CoW overlay: mudanças isoladas, nunca modifica base image
- ✅ Ephemeral output disk: novo ext4 para cada execução
- ✅ Trap cleanup: garante limpeza mesmo com erro
- ✅ Amnesia: zero persistência entre execuções

## Integração

### Teste Local

```bash
bash quickstart.sh
bash execute-bundle.sh test-bundle/bundle.tar.gz | jq .
```

### Smart Contract Integration

```python
import requests

bundle = open('my-bundle.tar.gz', 'rb')
response = requests.post('http://executor:5000/execute', data=bundle)
result = response.json()

print(f"Exit: {result['returncode']}")
print(f"Output: {result['stdout']}")
```

### Docker

```bash
docker build -f Dockerfile.build -t dnat-executor .
docker run -it dnat-executor bash quickstart.sh
```

## Troubleshooting

### "Kernel or rootfs not found"

```bash
bash build/ensure-image.sh
```

### "VM execution timeout"

- Aumentar TIMEOUT em `vm/run-vm.sh`
- Verificar se bundle é válido
- Verificar se run.sh tem execute permission

### Sem resultado JSON

- Verificar serial log: `vm_runtime/build/`
- VM talvez não terminou (timeout ou erro)

## Minimalism Philosophy

**Linhas de Código** (total ~250):

- executor.py: ~60 (HTTP server)
- vm/run-vm.sh: ~55 (VM orchestration)
- rootfs/runner: ~45 (bundle execution)
- rootfs/init: ~4 (boot)
- Buildchain: ~60 (kernel + rootfs)

**Cada linha deve justificar sua existência.**

## Licença

Open source - Use como quiser.

---

Veja também:

- [PURE_EXECUTOR.md](PURE_EXECUTOR.md) - Filosofia de simplicidade
- [AMNESIA_GUARANTEE.md](AMNESIA_GUARANTEE.md) - Como amnesia funciona
- [SYNC_ANALYSIS.md](SYNC_ANALYSIS.md) - Sincronização VM↔Host
