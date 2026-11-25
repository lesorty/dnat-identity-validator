#!/usr/bin/env bash
# Prepara a VM com GPU para os testes T1–T11, numa chamada, e termina com o pré-voo do ensaio.
# Rodar de dentro do repositório clonado, depois de tools/cloud/enviar_dados.sh (no notebook):
#
#   tools/cloud/preparar_testes.sh [--sem-gpu] [--docker]
#
#   --sem-gpu  não mexe em driver nem no torch (VM só de CPU)
#   --docker   instala Docker (T7: overhead da CVM; T8 com a pilha Docker)
#
# Idempotente: rodar de novo só completa o que falta. Passos:
#   1. bootstrap.sh --judges: ferramentas fixas, make setup, base, datasets, avaliadores do portão
#   2. dados da população (benignos, nocivos, degradantes), conferidos pelos manifestos
#   3. derivados de campo do Qwen (T1, T5), conferidos pelo manifesto
#   4. juiz de referência (rótulo), conferido pelo manifesto
#   5. o que vem do notebook (enviar_dados.sh): direção de recusa da população e bateria local do ensaio
#   6. GPU: driver da NVIDIA (>= 580), modo confidencial da placa, torch 2.15.0 com CUDA 13.2 por cima do
#      lock (model_gate/gpu/torch-cuda.txt, com hashes) e uma geração curta na GPU, determinística
#   7. ficha da máquina e pré-voo do perfil ensaio
#
# Na GPU o uv não pode sincronizar o ambiente de volta para o torch de CPU do lock: este script grava
# UV_NO_SYNC=1 em ~/.profile, e os perfis ensaio e nuvem já o passam aos passos.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"
GPU=1; DOCKER=()
for a in "$@"; do
  case "$a" in
    --sem-gpu) GPU=0 ;;
    --docker) DOCKER=(--docker) ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
DATA="${MODEL_GATE_DATA:-$HOME/model_gate_data}"
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
mgrun() { (cd "$REPO/model_gate" && uv run --frozen --no-sync python -m "$@"); }

step "1. bootstrap (ferramentas, ambientes, base, datasets, avaliadores do portão)"
tools/cloud/bootstrap.sh --judges "${DOCKER[@]}"
# o bootstrap roda make setup, que volta o torch ao de CPU do lock: o de CUDA entra no passo 6

step "2. dados da população"
tools/cloud/fetch_data.sh --population

step "3. derivados de campo do Qwen (T1, T5)"
mgrun experiments.field_download --check 2>/dev/null || mgrun experiments.field_download
mgrun experiments.field_download --check

step "4. juiz de referência (rótulo)"
mgrun experiments.testes.juiz_referencia

step "5. o que vem do notebook (tools/cloud/enviar_dados.sh)"
falta=0
for f in references/base_05b61d72bec3/refusal_dirs.safetensors battery/local_t807/battery.json; do
  if [ -f "$DATA/$f" ]; then echo "ok   $f"; else echo "FALTA $f"; falta=1; fi
done
if [ "$falta" = 1 ]; then
  echo "rode no notebook: tools/cloud/enviar_dados.sh <usuario@vm>   (e depois este script de novo)" >&2
  exit 3
fi

if [ "$GPU" = 1 ]; then
  step "6a. driver da NVIDIA"
  if ! command -v nvidia-smi >/dev/null || ! nvidia-smi >/dev/null 2>&1; then
    echo "sem driver: instalando com o instalador do Google (compute-gpu-installation)"
    f=$(mktemp -d)/cuda_installer.pyz
    curl -fsSL https://storage.googleapis.com/compute-gpu-installation-us/installer/latest/cuda_installer.pyz -o "$f"
    $SUDO python3 "$f" install_driver
    echo
    echo "o driver pode pedir reinício: reinicie a VM (sudo reboot) e rode este script de novo" >&2
    exit 4
  fi
  drv=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
  gpu=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)
  echo "GPU: $gpu · driver $drv"
  if [ "${drv%%.*}" -lt 580 ]; then
    echo "driver $drv < 580: o torch com CUDA 13.2 não roda. Atualize o driver (instalador do Google) e rode de novo." >&2
    exit 4
  fi

  command -v hashcat >/dev/null || $SUDO apt-get install -y -qq --no-install-recommends hashcat ocl-icd-libopencl1 >/dev/null \
    || echo "hashcat não instalado: o T10 segue sem a taxa da GPU"

  step "6b. modo confidencial da GPU"
  cc=$(nvidia-smi conf-compute -f 2>&1 || true); echo "$cc"
  rs=$(nvidia-smi conf-compute -grs 2>&1 || true); echo "$rs"
  if echo "$cc" | grep -qi "ON" && echo "$rs" | grep -qi "not ready"; then
    # Com o CC ligado, a placa só aceita trabalho depois do "ready state". A atestação da GPU (verificador
    # local da NVIDIA) não é feita aqui: fica registrada na ficha como não verificada.
    echo "marcando a GPU como pronta (nvidia-smi conf-compute -srs 1)"
    $SUDO nvidia-smi conf-compute -srs 1
  fi

  step "6c. torch com CUDA por cima do lock (hashes em model_gate/gpu/torch-cuda.txt)"
  py="$REPO/model_gate/.venv/bin/python"
  if ! "$py" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    uv pip install --python "$py" --no-deps --require-hashes -r model_gate/gpu/torch-cuda.txt \
      --index-url https://download.pytorch.org/whl/cu132 --extra-index-url https://pypi.org/simple \
      --index-strategy unsafe-best-match
  fi
  "$py" -c "import torch; assert torch.cuda.is_available(); print('torch', torch.__version__, 'CUDA', torch.version.cuda, '·', torch.cuda.get_device_name(0))"
  grep -q '^export UV_NO_SYNC=1' "$HOME/.profile" 2>/dev/null || {
    printf '\n# DNAT: o torch com CUDA está por cima do lock; o uv não pode sincronizar de volta\nexport UV_NO_SYNC=1\n' >> "$HOME/.profile"
  }
  export UV_NO_SYNC=1

  step "6d. geração curta na GPU, duas vezes, determinística (T-205)"
  t=$(mktemp -d)
  (cd model_gate && MODEL_GATE_DISPOSITIVO=cuda CUBLAS_WORKSPACE_CONFIG=:4096:8 \
     uv run --frozen --no-sync python -m experiments.check_determinism --n 2 --max-new-tokens 16 --out "$t")
  cat "$t/determinismo.json"; echo
fi

step "7. ficha da máquina e pré-voo do ensaio"
python3 -I tools/cloud/machine_card.py
python3 -I tools/testes/todos.py verificar --perfil "$([ "$GPU" = 1 ] && echo ensaio || echo mini)" || true
echo
echo "pronto. Próximo: tools/cloud/campanha_gpu.sh iniciar ensaio   (~30 min; depois: iniciar nuvem 1)"
