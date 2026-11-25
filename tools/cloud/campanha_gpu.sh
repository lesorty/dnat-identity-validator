#!/usr/bin/env bash
# Na VM: roda os testes como serviço do systemd, que sobrevive à queda do SSH e volta sozinho quando a VM
# Spot é reiniciada depois de uma preempção (os roteiros retomam de onde pararam).
#
#   tools/cloud/campanha_gpu.sh iniciar ensaio       # T1–T11 nos tamanhos do mini, na GPU (~30 min)
#   tools/cloud/campanha_gpu.sh iniciar nuvem 1      # fase 1: T1, T9, T10, T11, T2
#   tools/cloud/campanha_gpu.sh iniciar nuvem 2      # fase 2 (depois do congelamento): T3, T5, T6, T7, T8, T11, T4
#   tools/cloud/campanha_gpu.sh estado               # serviço, passo atual, GPU e a tabela dos testes
#   tools/cloud/campanha_gpu.sh log                  # acompanha a saída (Ctrl+C só sai do log)
#   tools/cloud/campanha_gpu.sh parar                # interrompe; iniciar de novo retoma
#
# Quando a rodada termina (com sucesso ou não), grava ~/.dnat-testes/<perfil>-<fase>.feito e o serviço
# não roda mais sozinho; iniciar de novo a mesma rodada apaga a marca e retoma o que faltou.
# Argumentos extras depois da fase vão para o make (ex.: ARGS=--sem-congelamento).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UNIT=dnat-testes
STATE="$HOME/.dnat-testes"
mkdir -p "$STATE"
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"

rodar() {   # chamado pelo serviço
  perfil=$1; fase=$2; shift 2
  marca="$STATE/$perfil-$fase.feito"
  if [ -f "$marca" ]; then echo "rodada $perfil/$fase já terminou ($(cat "$marca")); nada a fazer"; exit 0; fi
  echo "== $(date -Is) · rodada $perfil/$fase · $(git -C "$REPO" rev-parse --short=12 HEAD)"
  code=0
  make -C "$REPO" testes PERFIL="$perfil" FASE="$fase" "$@" || code=$?
  # 143/130: o serviço foi parado ou a VM está desligando (preempção) — não marca como feita, para retomar
  if [ "$code" != 143 ] && [ "$code" != 130 ]; then
    echo "$(date -Is) código $code" > "$marca"
    make -C "$REPO" testes-pacote PERFIL="$perfil" || true
  fi
  echo "== $(date -Is) · fim da rodada $perfil/$fase com código $code"
  exit "$code"
}

case "${1:-}" in
  iniciar)
    perfil=${2:?perfil: ensaio ou nuvem}; fase=${3:-todas}; shift $(( $# >= 3 ? 3 : 2 ))
    [ "$perfil" = nuvem ] && [ "$fase" = todas ] && { echo "na nuvem, diga a fase: 1 ou 2" >&2; exit 2; }
    rm -f "$STATE/$perfil-$fase.feito"
    python3 -I "$REPO/tools/testes/todos.py" verificar --perfil "$perfil" --fase "$fase" "${@#ARGS=}" || {
      echo; echo "o pré-voo achou pendências (acima). Rodar mesmo assim? [s/N]"; read -r r; [ "$r" = s ] || exit 1; }
    $SUDO tee /etc/systemd/system/$UNIT.service >/dev/null <<EOF
[Unit]
Description=DNAT: testes T1-T11 ($perfil, fase $fase)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$REPO
Environment=HOME=$HOME
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=UV_NO_SYNC=1
Environment=MODEL_GATE_DATA=${MODEL_GATE_DATA:-$HOME/model_gate_data}
ExecStart=$REPO/tools/cloud/campanha_gpu.sh _rodar $perfil $fase $*
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=60
StandardOutput=append:$STATE/servico.log
StandardError=append:$STATE/servico.log

[Install]
WantedBy=multi-user.target
EOF
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable $UNIT >/dev/null 2>&1
    $SUDO systemctl restart $UNIT
    echo "serviço $UNIT rodando ($perfil, fase $fase). Acompanhe: tools/cloud/campanha_gpu.sh log"
    ;;
  _rodar) shift; rodar "$@" ;;
  estado)
    systemctl --no-pager status $UNIT 2>/dev/null | head -5 || true
    command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
    ls "$STATE"/*.feito 2>/dev/null | sed 's#.*/#terminada: #' || true
    perfil=$(systemctl cat $UNIT 2>/dev/null | sed -n 's/.*_rodar \([a-z]*\) .*/\1/p' | head -1)
    python3 -I "$REPO/tools/testes/todos.py" status --perfil "${perfil:-ensaio}" || true
    ;;
  log) tail -n 80 -F "$STATE/servico.log" ;;
  parar)
    $SUDO systemctl stop $UNIT || true
    $SUDO systemctl disable $UNIT >/dev/null 2>&1 || true
    echo "parado. iniciar de novo a mesma rodada retoma de onde parou."
    ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
