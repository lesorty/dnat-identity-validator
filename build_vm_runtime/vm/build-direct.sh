#!/bin/bash
# =============================================================================
# Runner de build DIRETO (sem microVM). Contrapartida do `run-direct.sh` do
# plano de execucao, e existe pelo mesmo motivo: uma VM confidencial (SEV-SNP /
# TDX) nao expoe virtualizacao aninhada, entao o Firecracker do `build-vm.sh`
# nao pode ser lancado la dentro.
#
# Fidelidade ao caminho da microVM: este script NAO reimplementa a build. Ele
# chama exatamente o mesmo `build_application_artifact.py` que o guest chama em
# `/opt/dnat/build_application_artifact.py`, com exatamente os mesmos argumentos
# montados por `rootfs/runner`. O artefato produzido e, portanto, o mesmo; o que
# muda e apenas a fronteira de isolamento em que a build roda.
#
# Contrato identico ao de build-vm.sh:
#   entrada  $1  bundle .tar.gz com `source/application.py` e `manifest.json`
#   saida    $2  bundle .tar.gz com `application.ext4`, `build-result.json`,
#                `build-stdout.txt`, `build-stderr.txt` e `wheelhouse/*.whl`
#   erro         JSON em stdout + exit != 0 (worker.py repassa a builder.py)
#
# O QUE SE PERDE em relacao ao build-vm.sh, e precisa constar do artigo:
#   - a build passa a rodar no namespace do proprio builder, e nao numa microVM
#     descartavel: uma dependencia maliciosa (T2/T2b) alcanca o container do
#     plano de build, e nao mais so um guest efemero;
#   - some o filtro de egress por iptables/TAP, porque nao ha mais guest para
#     filtrar: a build herda a rede do container;
#   - o estado por requisicao deixa de ser destruido junto com a microVM e passa
#     a depender da limpeza do WORKDIR abaixo.
# O cache de wheels continua sendo o unico estado duravel, como no caminho
# original, e continua sendo montado somente-leitura para a build.
# =============================================================================
set -uo pipefail

BUNDLE_PATH="${1:-}"
OUTPUT_BUNDLE_PATH="${2:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_BUILDER="$ROOT/guest-tools/build_application_artifact.py"
WHEEL_CACHE_SOURCE_DIR="${WHEEL_CACHE_SOURCE_DIR:-/var/dnat/wheel-cache}"
APPLICATION_ARTIFACT_NAME="application.ext4"
BUILD_RESULT_FILE="build-result.json"
BUILD_STDOUT_FILE="build-stdout.txt"
BUILD_STDERR_FILE="build-stderr.txt"
BUILD_TIMEOUT_SECONDS="${BUILD_DIRECT_TIMEOUT_SECONDS:-1800}"

# Ubuntu 24.04 (imagem do runtime do builder) marca o Python do sistema como
# externally-managed (PEP 668), e o `pip install --target` do
# build_application_artifact.py falharia. O rootfs do guest e Jammy, anterior a
# essa politica, e por isso o caminho da microVM nunca precisou disto. Definir a
# variavel aqui mantem o ajuste contido neste arquivo, sem tocar no script de
# build compartilhado entre os dois caminhos.
export PIP_BREAK_SYSTEM_PACKAGES=1

json_string() {
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

emit_error() {
    echo "{\"error\": $(json_string "$1")}"
}

WORKDIR=""
cleanup() {
    [ -n "$WORKDIR" ] && rm -rf "$WORKDIR"
}
trap cleanup EXIT

[ -f "$BUNDLE_PATH" ] || { emit_error "Build bundle not found"; exit 1; }
[ -n "$OUTPUT_BUNDLE_PATH" ] || { emit_error "Output bundle path not provided"; exit 1; }
[ -f "$ARTIFACT_BUILDER" ] || { emit_error "Artifact builder not found: $ARTIFACT_BUILDER"; exit 1; }

WORKDIR="$(mktemp -d)"
EXTRACT_DIR="$WORKDIR/bundle"
PACKAGE_DIR="$WORKDIR/response"
WHEELHOUSE_DIR="$PACKAGE_DIR/wheelhouse"
mkdir -p "$EXTRACT_DIR" "$PACKAGE_DIR" "$WHEELHOUSE_DIR"

if ! tar -xzf "$BUNDLE_PATH" -C "$EXTRACT_DIR" 2>"$WORKDIR/tar.err"; then
    emit_error "failed to extract build bundle: $(head -c 500 "$WORKDIR/tar.err")"
    exit 1
fi

SOURCE_PATH="$EXTRACT_DIR/source/application.py"
MANIFEST_PATH="$EXTRACT_DIR/manifest.json"
[ -f "$SOURCE_PATH" ]   || { emit_error "source/application.py missing from build bundle"; exit 1; }
[ -f "$MANIFEST_PATH" ] || { emit_error "manifest.json missing from build bundle"; exit 1; }

# Os campos sao lidos exatamente como `rootfs/runner` os le, incluindo o
# json.dumps em `dependencies`, para que a linha de comando do builder seja
# byte a byte a mesma nos dois caminhos.
read_manifest() {
    python3 - "$MANIFEST_PATH" <<'PY'
import json, sys
m = json.loads(open(sys.argv[1], encoding="utf-8").read())
print(str(m.get("name", "")))
print(str(m.get("description", "")))
print(str(m.get("framework", "python")))
print(json.dumps(m.get("dependencies", "")))
PY
}

if ! MANIFEST_FIELDS="$(read_manifest 2>"$WORKDIR/manifest.err")"; then
    emit_error "failed to parse manifest.json: $(head -c 500 "$WORKDIR/manifest.err")"
    exit 1
fi
APP_TITLE="$(sed -n '1p' <<<"$MANIFEST_FIELDS")"
APP_DESCRIPTION="$(sed -n '2p' <<<"$MANIFEST_FIELDS")"
APP_FRAMEWORK="$(sed -n '3p' <<<"$MANIFEST_FIELDS")"
APP_DEPENDENCIES="$(sed -n '4p' <<<"$MANIFEST_FIELDS")"

# Cache de wheels em copia somente-leitura. No caminho da microVM o cache entra
# como disco `is_read_only: true`; aqui a copia cumpre o mesmo papel, impedindo
# que a build escreva direto no unico estado duravel do plano. Quem popula o
# cache continua sendo o worker.py, depois da build, a partir do wheelhouse.
CACHE_ARG=()
WHEEL_CACHE_USED=false
if find "$WHEEL_CACHE_SOURCE_DIR" -maxdepth 1 -type f -name '*.whl' -print -quit 2>/dev/null | grep -q .; then
    CACHE_RO="$WORKDIR/wheel-cache-ro"
    mkdir -p "$CACHE_RO"
    cp "$WHEEL_CACHE_SOURCE_DIR"/*.whl "$CACHE_RO"/ 2>/dev/null || true
    chmod -R a-w "$CACHE_RO" 2>/dev/null || true
    CACHE_ARG=(--wheel-cache-dir "$CACHE_RO")
    WHEEL_CACHE_USED=true
fi

BUILT_ARTIFACT="$WORKDIR/$APPLICATION_ARTIFACT_NAME"

timeout "$BUILD_TIMEOUT_SECONDS" python3 "$ARTIFACT_BUILDER" \
    --source-file "$SOURCE_PATH" \
    --output-image "$BUILT_ARTIFACT" \
    --title "$APP_TITLE" \
    --description "$APP_DESCRIPTION" \
    --framework "$APP_FRAMEWORK" \
    --dependencies "$APP_DEPENDENCIES" \
    --output-wheelhouse-dir "$WHEELHOUSE_DIR" \
    "${CACHE_ARG[@]}" \
    >"$PACKAGE_DIR/$BUILD_STDOUT_FILE" 2>"$PACKAGE_DIR/$BUILD_STDERR_FILE"
BUILD_RC=$?

if [ "$BUILD_RC" -ne 0 ] || [ ! -f "$BUILT_ARTIFACT" ]; then
    python3 - "$BUILD_RC" "$PACKAGE_DIR/$BUILD_STDOUT_FILE" "$PACKAGE_DIR/$BUILD_STDERR_FILE" <<'PY'
import json, sys
rc = int(sys.argv[1])
def tail(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()[-4000:]
    except OSError:
        return ""
print(json.dumps({
    "error": "direct build failed",
    "buildResult": {"returncode": rc},
    "stdout": tail(sys.argv[2]),
    "stderr": tail(sys.argv[3]),
}))
PY
    exit 1
fi

mv "$BUILT_ARTIFACT" "$PACKAGE_DIR/$APPLICATION_ARTIFACT_NAME"

# Mesmo payload que `rootfs/runner` grava no disco de saida, para que worker.py
# e a api-server nao percebam diferenca entre os dois caminhos.
python3 - "$PACKAGE_DIR/$BUILD_RESULT_FILE" "$APP_DEPENDENCIES" "$WHEEL_CACHE_USED" "$(basename "$SOURCE_PATH")" <<'PY'
import json, sys
out, deps_raw, cache_used, source_name = sys.argv[1:5]
try:
    deps = json.loads(deps_raw)
except json.JSONDecodeError:
    deps = deps_raw
json.dump({
    "returncode": 0,
    "sourceFileName": source_name,
    "dependencies": deps,
    "wheelCacheUsed": cache_used == "true",
    # Marca explicita de que esta build NAO passou por uma microVM. Sem isto, um
    # resultado colhido em CVM seria indistinguivel de um colhido com isolamento.
    "isolation": "direct",
}, open(out, "w", encoding="utf-8"), indent=2)
PY

tar -C "$PACKAGE_DIR" -czf "$OUTPUT_BUNDLE_PATH" .
