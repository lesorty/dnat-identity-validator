#!/usr/bin/env bash
# Prepara a VM para os testes T1–T11. Rodar de dentro do repositório clonado, depois de tools/cloud/enviar.sh
# (no notebook).
#
#   tools/cloud/preparar_testes.sh [--sem-gpu] [--docker]          tudo numa VM só (com GPU, por padrão)
#   tools/cloud/preparar_testes.sh --disco [--populacao piloto]    numa VM BARATA, sem GPU: o disco que vira imagem
#   tools/cloud/preparar_testes.sh --so-gpu                        na a3 criada da imagem: só o que precisa da placa
#
#   --sem-gpu      não mexe em driver nem no torch (VM só de CPU)
#   --docker       instala Docker (T7: overhead da CVM; T8 com a pilha Docker)
#   --disco        passos 1–5, o torch com CUDA (instalar não precisa de placa) e o hashcat, sem ficha nem
#                  pré-voo. A hora da a3 é cara; a de uma n2 Spot, não. Depois: parar a VM e criar a imagem
#                  (tools/cloud/README.md, "Disco pronto").
#   --populacao P  com --disco: treina também os derivados do perfil P (T2 e T3; ex.: piloto), na CPU. Na a3,
#                  o passo populacao os reaproveita pela receita (derivatives/<nome>/testes_receita.json).
#   --com-driver   com --disco: tenta instalar o driver da NVIDIA sem a placa (o instalador do Google pode
#                  recusar; nesse caso ele entra na a3, com o --so-gpu)
#   --so-gpu       na a3 que subiu da imagem: confere que os dados estão lá e faz só os passos 6 e 7. NÃO roda
#                  o passo 1: o make setup (uv sync) voltaria o torch ao de CPU do lock e o de CUDA (~3 GB)
#                  teria de ser baixado de novo, com a a3 cobrando.
#
# Idempotente: rodar de novo só completa o que falta. Passos:
#   1. bootstrap.sh --judges: ferramentas fixas, make setup, base, datasets, avaliadores do portão
#   2. dados da população (benignos, nocivos, degradantes), conferidos pelos manifestos
#   3. derivados de campo do Qwen (T1, T5), conferidos pelo manifesto
#   4. juiz de referência (rótulo), conferido pelo manifesto
#   5. o que vem do notebook (enviar.sh): direção de recusa da população e bateria local do ensaio
#   6. GPU: driver da NVIDIA (>= 580), modo confidencial da placa, torch 2.15.0 com CUDA 13.2 por cima do
#      lock (model_gate/gpu/torch-cuda.txt, com hashes) e uma geração curta na GPU, determinística
#   7. ficha da máquina e pré-voo do perfil piloto
#
# Na GPU o uv não pode sincronizar o ambiente de volta para o torch de CPU do lock: este script grava
# UV_NO_SYNC=1 em ~/.profile, e os perfis ensaio, piloto e nuvem já o passam aos passos.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"
MODO=completo; GPU=1; DOCKER=(); POPULACAO=""; DRIVER=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sem-gpu) GPU=0 ;;
    --docker) DOCKER=(--docker) ;;
    --disco) MODO=disco; GPU=0 ;;
    --so-gpu) MODO=so-gpu ;;
    --populacao) POPULACAO=${2:?--populacao pede o perfil (ex.: piloto)}; shift ;;
    --com-driver) DRIVER=1 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
  shift
done
if [ -n "$POPULACAO" ] && [ "$MODO" != disco ]; then echo "--populacao só com --disco" >&2; exit 2; fi
if [ "$DRIVER" = 1 ] && [ "$MODO" != disco ]; then echo "--com-driver só com --disco" >&2; exit 2; fi
DATA="${MODEL_GATE_DATA:-$HOME/model_gate_data}"
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
mgrun() { (cd "$REPO/model_gate" && uv run --frozen --no-sync python -m "$@"); }
PY="$REPO/model_gate/.venv/bin/python"

instalar_driver() {   # o instalador do Google (compute-gpu-installation); devolve 0 se instalou
  f=$(mktemp -d)/cuda_installer.pyz
  curl -fsSL https://storage.googleapis.com/compute-gpu-installation-us/installer/latest/cuda_installer.pyz -o "$f"
  $SUDO python3 "$f" install_driver
}

torch_cuda() {   # torch com CUDA por cima do lock; instalar não precisa da placa, só usar
  if ! "$PY" -c "import torch, sys; sys.exit(0 if torch.version.cuda else 1)" 2>/dev/null; then
    uv pip install --python "$PY" --no-deps --require-hashes -r model_gate/gpu/torch-cuda.txt \
      --index-url https://download.pytorch.org/whl/cu132 --extra-index-url https://pypi.org/simple \
      --index-strategy unsafe-best-match
  fi
  "$PY" -c "import torch; print('torch', torch.__version__, 'CUDA', torch.version.cuda)"
  grep -q '^export UV_NO_SYNC=1' "$HOME/.profile" 2>/dev/null || {
    printf '\n# DNAT: o torch com CUDA está por cima do lock; o uv não pode sincronizar de volta\nexport UV_NO_SYNC=1\n' >> "$HOME/.profile"
  }
  export UV_NO_SYNC=1
}

hashcat_() {
  command -v hashcat >/dev/null || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq --no-install-recommends hashcat ocl-icd-libopencl1 >/dev/null; } \
    || echo "hashcat não instalado: o T10 segue sem a taxa da GPU"
}

if [ "$MODO" = so-gpu ]; then
  step "0. o disco veio pronto? (sem make setup: ele desfaria o torch com CUDA)"
  falta=0
  for f in references/base_05b61d72bec3/refusal_dirs.safetensors battery/local_t807/battery.json \
           models/Qwen__Qwen2.5-0.5B-Instruct models/Qwen__Qwen3Guard-Gen-4B models/openai__gpt-oss-20b; do
    if [ -e "$DATA/$f" ]; then echo "ok   $f"; else echo "FALTA $f"; falta=1; fi
  done
  [ -x "$PY" ] && echo "ok   ambiente do model_gate" || { echo "FALTA o ambiente do model_gate"; falta=1; }
  command -v node >/dev/null && echo "ok   node" || { echo "FALTA node"; falta=1; }
  if [ "$falta" = 1 ]; then
    echo "o disco não veio pronto: rode o preparar_testes.sh completo (sem --so-gpu) nesta VM" >&2
    exit 3
  fi
  # o código pode ter mudado depois da imagem (enviar.sh de novo): o contrato compila de novo se precisar
  (cd smart-contract && npx hardhat compile --quiet) || true
else
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

  step "5. o que vem do notebook (tools/cloud/enviar.sh)"
  falta=0
  for f in references/base_05b61d72bec3/refusal_dirs.safetensors battery/local_t807/battery.json; do
    if [ -f "$DATA/$f" ]; then echo "ok   $f"; else echo "FALTA $f"; falta=1; fi
  done
  if [ "$falta" = 1 ]; then
    echo "rode no notebook: tools/cloud/enviar.sh <usuario@vm> --so-dados   (e depois este script de novo)" >&2
    exit 3
  fi
fi

if [ "$MODO" = disco ]; then
  step "6. o que da GPU não precisa da placa: torch com CUDA e hashcat"
  torch_cuda
  hashcat_
  if [ "$DRIVER" = 1 ]; then
    instalar_driver || echo "o instalador do driver recusou sem a placa: ele entra na a3 (preparar_testes.sh --so-gpu)"
  fi

  if [ -n "$POPULACAO" ]; then
    step "6e. derivados do perfil $POPULACAO (T2 e T3), na CPU desta VM"
    for t in T2 T3; do
      mgrun experiments.testes.populacao --out "$DATA/preparo/populacao_${POPULACAO}_$t" --perfil "$POPULACAO" \
        --teste "$t" --threads "$(nproc)"
    done
  fi

  step "7. limpeza para a imagem"
  # a ficha desta VM barata não é a da a3: sai da pasta que vai para o bucket e para os pacotes
  if [ -d "$DATA/machine" ]; then
    mkdir -p "$DATA/preparo/fichas" && mv "$DATA/machine"/*.json "$DATA/preparo/fichas/" 2>/dev/null || true
  fi
  $SUDO apt-get clean
  echo "usuário: $(id -un) (entre na a3 com o MESMO usuário: os dados estão em $DATA)"
  df -h "$DATA" | tail -1
  echo
  echo "disco pronto. Próximo (tools/cloud/README.md, \"Disco pronto\"): pare esta VM, crie a imagem, confira"
  echo "TDX_CAPABLE na imagem, crie a a3 com ela e lá rode: tools/cloud/preparar_testes.sh --so-gpu"
  exit 0
fi

if [ "$GPU" = 1 ]; then
  step "6a. driver da NVIDIA"
  if ! command -v nvidia-smi >/dev/null || ! nvidia-smi >/dev/null 2>&1; then
    echo "sem driver: instalando com o instalador do Google (compute-gpu-installation)"
    instalar_driver
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

  hashcat_

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
  torch_cuda
  "$PY" -c "import torch; assert torch.cuda.is_available(); print('GPU vista pelo torch:', torch.cuda.get_device_name(0))"

  step "6d. geração curta na GPU, duas vezes, determinística (T-205)"
  t=$(mktemp -d)
  (cd model_gate && MODEL_GATE_DISPOSITIVO=cuda CUBLAS_WORKSPACE_CONFIG=:4096:8 \
     uv run --frozen --no-sync python -m experiments.check_determinism --n 2 --max-new-tokens 16 --out "$t")
  cat "$t/determinismo.json"; echo
fi

step "7. ficha da máquina e pré-voo do piloto"
python3 -I tools/cloud/machine_card.py
python3 -I tools/testes/todos.py verificar --perfil "$([ "$GPU" = 1 ] && echo piloto || echo mini)" || true
echo
echo "pronto. Próximo: tools/cloud/campanha_gpu.sh iniciar piloto   (~3 h; o ensaio, ~30 min, é opcional)"
