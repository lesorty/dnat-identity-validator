# DNAT VM Runtime - Quick Start Guide

## 🚀 Para Começar Agora (Local - Recomendado)

**Preparar ambiente (5 min):**

```bash
cd vm_runtime
bash setup-local.sh
# Responda "y" para iniciar o build
```

**O que acontece:**

- ✅ Instala: build-essential, python3, debootstrap, qemu-utils, Firecracker
- ✅ Inicia compilação do Linux 6.6 (~20-30 min com 12 cores)
- ✅ Então cria Ubuntu rootfs (~5-10 min)

**Total: ~30-40 minutos na primeira vez**

---

## 💡 Alternativa: Build Mais Rápido

Se a compilação ficar muito lenta, você pode:

1. **Usar Makefile:**

   ```bash
   make diagnose          # Verificar sistema
   make setup            # Instalar deps
   make build-kernel &   # Em background
   ```

2. **Paralellize (já feito automático):**

   ```bash
   make -j$(nproc)       # Usa todos os cores
   ```

3. **Skip e usar pré-compilado (futuro):**
   - Comentar as linhas no `Dockerfile.build` (linhas ~68-69)
   - Copiar artifacts de outro lugar

---

## ▶️ Executar Servidor

**Opção 1: Foreground (vê os logs)**

```bash
python3 executor.py 5000
```

**Opção 2: Background**

```bash
python3 executor.py 5000 &
```

**Testar:**

```bash
# Criar bundle de teste
mkdir -p test/workspace
echo '#!/bin/bash
echo "Hello"' > test/workspace/run.sh
chmod +x test/workspace/run.sh
cd test && tar -czf bundle.tar.gz workspace/

# Executar
curl -X POST --data-binary @bundle.tar.gz http://localhost:5000/execute | jq .
```

---

## 🐳 Alternativa: Docker

O Dockerfile foi otimizado com:

- ✅ Multi-stage build (reduce image size)
- ✅ Layer caching (cada `RUN` é um layer)
- ✅ `.dockerignore` (não copia unnecessary files)
- ✅ Health checks
- ✅ **Build automático completo** (kernel + rootfs)

**Usar:**

```bash
# Build completo (~40-50 min primeira vez)
docker build -f Dockerfile.build -t dnat-executor .

# Executar servidor automaticamente
docker run -p 5000:5000 dnat-executor

# Ou debug/shell
docker run -it dnat-executor /bin/bash
```

**Nota:** O build completo do Docker pode falhar devido a limitações de privilégios. Use o setup local (`bash setup-local.sh`) para funcionalidade completa.

---

## 📊 Monitorar Build

**Ver progresso do kernel:**

```bash
# Em outro terminal
watch -n 5 "du -sh /tmp/linux"
top  # Ver CPU/RAM
```

---

## ⚙️ Troubleshooting

| Problema                         | Solução                                      |
| -------------------------------- | -------------------------------------------- |
| `command not found: firecracker` | `bash setup-local.sh`                        |
| `kernel or rootfs not found`     | `bash build/ensure-image.sh`                 |
| Build muito lento                | `make diagnose` e verificar CPU/RAM          |
| VM timeout                       | Aumentar TIMEOUT em `vm/run-vm.sh` linha ~15 |
| Permission denied                | `sudo bash setup-local.sh`                   |

---

## 📁 Estrutura Final

Após o build:

```
vm_runtime/
├── artifacts/
│   ├── vmlinux              # Linux kernel (compilado)
│   └── rootfs.ext4          # Ubuntu root filesystem
├── input/                   # Bundle temporários
├── output/                  # Resultados (se salvo)
└── executor.py              # HTTP server pronto!
```

---

## 🔧 Próximos Passos

1. ✅ Setup completo
2. ✅ Kernel + rootfs compilados
3. ⏳ Testar executor com bundle
4. ⏳ Integrar com smart-contract

---

## 📚 Documentação Adicional

- [README.md](README.md) - Full documentation
- [Dockerfile Otimizado](Dockerfile.build) - Multi-stage, caching
- [diagnose.sh](diagnose.sh) - Verificar ambiente
- [Makefile](Makefile) - Comandos rápidos

---

**Boa sorte! 🚀**
