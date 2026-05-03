FROM ipfs/kubo:release AS ipfs

FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV IPFS_PATH=/data/ipfs
ENV RPC_URL=http://127.0.0.1:8545
ENV IPFS_API_URL=http://127.0.0.1:5001
ENV WEB_PORT=3001
ENV EXECUTOR_URL=http://dnat-executor:5000
ENV PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl python3 tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ipfs /usr/local/bin/ipfs /usr/local/bin/ipfs

WORKDIR /app

COPY smart-contract/package.json smart-contract/package-lock.json ./smart-contract/
RUN cd smart-contract && npm ci

COPY smart-contract ./smart-contract
COPY docker/root-entrypoint.sh /usr/local/bin/root-entrypoint.sh

RUN chmod +x /usr/local/bin/root-entrypoint.sh \
    && mkdir -p /data/ipfs /app/smart-contract/executions

EXPOSE 3001 5001 8080 8545

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/root-entrypoint.sh"]
