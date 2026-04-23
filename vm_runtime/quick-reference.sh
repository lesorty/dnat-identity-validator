#!/bin/bash
# Quick reference card - print this for your desk!
# Run: bash quick-reference.sh

cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════════╗
║               DNAT VM Runtime - Quick Reference Card                       ║
╚════════════════════════════════════════════════════════════════════════════╝

🎯 PRIMEIRA VEZ (30-50 min):

  cd vm_runtime
  bash setup-local.sh
  # Escolha "y" para iniciar build
  
  # Resultado: artifacts/vmlinux + artifacts/rootfs.ext4


📝 FAZER BUILD MANUAL:

  make diagnose              # Verificar sistema
  make setup                 # Instalar deps
  make build                 # Compilar kernel + rootfs
  # ou separado:
  make build-kernel &        # Kernel (~20-30 min, background)
  make build-rootfs          # Rootfs (~5-10 min)


▶️ EXECUTAR SERVIDOR:

  python3 executor.py 5000


✅ TESTAR:

  # Terminal 1:
  python3 executor.py 5000 &
  
  # Terminal 2:
  curl -X POST --data-binary @bundle.tar.gz http://localhost:5000/execute | jq .
  
  # ou:
  make test-local


🐳 COM DOCKER:

  docker build -f Dockerfile.build -t dnat-executor .
  docker run -it dnat-executor /bin/bash


🆘 PROBLEMAS:

  Problema                          Solução
  ───────────────────────────────── ────────────────────────────────
  firecracker: command not found    bash setup-local.sh
  kernel or rootfs not found        make build
  Build muito lento                 make diagnose (verificar CPU/RAM)
  Permission denied                 sudo bash setup-local.sh


📊 TEMPOS ESPERADOS:

  Instalar deps:      ~10 min  (uma vez)
  Compilar kernel:    ~20-30 min (parallelizado)
  Criar rootfs:       ~5-10 min
  ─────────────────────────────
  TOTAL (1ª vez):     ~40-50 min
  Próximas vezes:     ~2 seg (VM startup)


📁 ARQUIVOS PRINCIPAIS:

  setup-local.sh                 Script setup automático
  diagnose.sh                    Verificar ambiente
  Makefile                       Comandos rápidos
  QUICKSTART.md                  Guia rápido
  DOCKERFILE_OPTIMIZATIONS.md    Melhorias do Dockerfile
  SETUP_COMPLETE.md              Setup completo (na raiz)
  README.md                      Documentação completa


💡 DICAS:

  • Parallelizar: export MAKEFLAGS="-j$(nproc --all)"
  • Ver progresso: watch -n 5 "du -sh /tmp/linux"
  • Background: python3 executor.py 5000 & 
  • Limpar: make clean-all


🚀 WORKFLOW TÍPICO:

  1. bash setup-local.sh       (setup + build)
  2. python3 executor.py 5000  (start server)
  3. curl -X POST ...          (send bundle)
  4. jq .                      (parse result)


📞 SUPORTE:

  cat QUICKSTART.md
  cat DOCKERFILE_OPTIMIZATIONS.md
  bash diagnose.sh


╔════════════════════════════════════════════════════════════════════════════╗
║  Boa sorte! Enquanto o kernel compila, leia os .md files 📚              ║
╚════════════════════════════════════════════════════════════════════════════╝
EOF
