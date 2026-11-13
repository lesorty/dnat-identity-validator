# Reaproveita apenas o binario do IPFS sem carregar a imagem completa no runtime final.
FROM ipfs/kubo:release AS ipfs
# uv para o ambiente do Juiz (model_gate, T-807/T-815): Python 3.12 e torch de CPU fixados no uv.lock.
FROM ghcr.io/astral-sh/uv:0.12.20 AS uv

# CVM1: frontend/API local, node Hardhat e cliente IPFS.
FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
# Endpoints padrao usados quando tudo roda na rede Docker local.
ENV IPFS_PATH=/data/ipfs
ENV RPC_URL=http://127.0.0.1:8545
ENV IPFS_API_URL=http://127.0.0.1:5001
ENV WEB_PORT=3001
ENV EXECUTOR_URL=http://dnat-executor:5000
ENV BUILDER_URL=http://dnat-builder:5100
ENV PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
ENV ASSET_ENCRYPTION_KEY=dnat-dev-asset-key

# `e2fsprogs` e `tar` sao usados para preparar/inspecionar artefatos ext4 vindos do builder.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl e2fsprogs python3 tar tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ipfs /usr/local/bin/ipfs /usr/local/bin/ipfs
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

# Copia lockfiles antes para aproveitar cache de `npm ci`.
COPY smart-contract/package.json smart-contract/package-lock.json ./smart-contract/
RUN cd smart-contract && npm ci

COPY smart-contract ./smart-contract
COPY docker/root-entrypoint.sh /usr/local/bin/root-entrypoint.sh

# O Juiz roda como segundo job a partir da CVM1 (modo direto, T-807): o ambiente do model_gate vem
# do uv.lock (dependências antes do código, para o cache). O hash do Juiz cobre src/, pyproject e lock.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_LINK_MODE=copy \
    DNAT_MODEL_GATE_DIR=/app/model_gate
COPY model_gate/pyproject.toml model_gate/uv.lock ./model_gate/
RUN cd model_gate && uv sync --frozen --no-dev --no-install-project
COPY model_gate/src ./model_gate/src
COPY model_gate/prereg.yaml ./model_gate/prereg.yaml
COPY model_gate/experiments/judge_local_prereg.yaml ./model_gate/experiments/judge_local_prereg.yaml
RUN cd model_gate && uv sync --frozen --no-dev

# O diretorio `executions` guarda bundles/resultados produzidos pela CVM1.
RUN chmod +x /usr/local/bin/root-entrypoint.sh \
    && mkdir -p /data/ipfs /app/smart-contract/executions

EXPOSE 3001 5001 8080 8545

# `tini` evita processos zumbis porque o entrypoint sobe varios filhos de longa duracao.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/root-entrypoint.sh"]
