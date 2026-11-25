#!/usr/bin/env bash
# No notebook: leva para a VM o código deste commit e os dois arquivos que não vêm de manifesto público.
#
#   tools/cloud/enviar.sh usuario@vm [--so-dados] [--permitir-sujo]
#
# Código: um git bundle do branch atual com as tags (a tag congelado-* vai junto), sem depender de chave
# do GitHub na VM. Lá ele vira ~/dnat-identity-validator no mesmo commit; se a pasta já existe, só
# atualiza (fetch do bundle e checkout do commit), sem apagar nada que a campanha gravou em
# $MODEL_GATE_DATA.
# Dados (para ~/model_gate_data na VM):
#   references/base_05b61d72bec3/refusal_dirs.safetensors   direção de recusa que monta a população F3
#       (fixada pelo sha em experiments/testes/populacao.py; não é a do Juiz, que ele mede sozinho)
#   battery/local_t807/                                     bateria local pequena do perfil ensaio
#
# Recusa commit sujo: o que vai para a VM tem de ser exatamente um commit (--permitir-sujo só para ensaio,
# e mesmo assim só o que está commitado viaja).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${1:?uso: tools/cloud/enviar.sh usuario@vm [--so-dados] [--permitir-sujo]}"; shift
SO_DADOS=0; SUJO=0
for a in "$@"; do
  case "$a" in
    --so-dados) SO_DADOS=1 ;;
    --permitir-sujo) SUJO=1 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
DATA="${MODEL_GATE_DATA:-$HOME/model_gate_data}"
cd "$REPO"

if [ "$SO_DADOS" = 0 ]; then
  sujo=$(git status --porcelain -- . ':(exclude)model_gate/results' ':(exclude)smart-contract/results' \
         ':(exclude)assets/test-results' ':(exclude)DSN2027/testes')
  if [ -n "$sujo" ] && [ "$SUJO" = 0 ]; then
    echo "repositório com mudanças não commitadas; commit antes (ou --permitir-sujo, que leva só o commitado):" >&2
    echo "$sujo" | head -20 >&2
    exit 1
  fi
  branch=$(git rev-parse --abbrev-ref HEAD); commit=$(git rev-parse HEAD)
  b=$(mktemp -d)/dnat.bundle
  git bundle create "$b" "$branch" --tags
  echo "enviando o código: $branch @ ${commit:0:12} ($(du -h "$b" | cut -f1))"
  scp -q "$b" "$HOST:dnat.bundle"
  ssh "$HOST" bash -s -- "$branch" "$commit" <<'EOF'
set -euo pipefail
branch=$1; commit=$2
if [ -d dnat-identity-validator/.git ]; then
  cd dnat-identity-validator
  git fetch -q "$HOME/dnat.bundle" "+refs/heads/$branch:refs/remotes/bundle/$branch" '+refs/tags/*:refs/tags/*'
else
  git clone -q "$HOME/dnat.bundle" dnat-identity-validator -b "$branch"
  cd dnat-identity-validator
fi
git -c advice.detachedHead=false checkout -q "$commit"
echo "na VM: $(pwd) @ $(git rev-parse --short=12 HEAD) $(git tag --points-at HEAD | tr '\n' ' ')"
EOF
fi

echo "enviando os dados do notebook"
ssh "$HOST" 'mkdir -p model_gate_data/references/base_05b61d72bec3 model_gate_data/battery/local_t807'
scp -q "$DATA/references/base_05b61d72bec3/refusal_dirs.safetensors" "$HOST:model_gate_data/references/base_05b61d72bec3/"
scp -q "$DATA/battery/local_t807/battery.json" "$HOST:model_gate_data/battery/local_t807/"
ssh "$HOST" 'cd model_gate_data && sha256sum references/base_05b61d72bec3/refusal_dirs.safetensors battery/local_t807/battery.json'
sha256sum "$DATA/references/base_05b61d72bec3/refusal_dirs.safetensors" "$DATA/battery/local_t807/battery.json" | sed 's/^/notebook: /'
echo
echo "próximo, na VM: cd dnat-identity-validator && tools/cloud/preparar_testes.sh --docker"
