#!/bin/bash
# Entrada da CVM de job no modo direto em container (T-815). Precisa de CAP_NET_ADMIN só para
# montar a regra; depois troca para o usuário dnat sem nenhuma capability.
#
# Rede entra-só: o agente aceita conexões (a CVM1 chama /execute e /derivative/<token>) e responde
# por elas; nenhuma conexão nova sai daqui, nem consulta de DNS. É a emulação local do grupo de segurança da CVM de uso
# único (T-801): o script do job não tem por onde vazar o dataset.
set -euo pipefail

if [ "${DNAT_EGRESS_LOCK:-1}" = "1" ]; then
    for ipt in iptables ip6tables; do
        command -v "$ipt" >/dev/null 2>&1 || continue
        "$ipt" -P OUTPUT DROP
        # O DNS do Docker (127.0.0.11) responde pela loopback e encaminha para fora: é um túnel de
        # exfiltração (T1 pegou). A CVM de job não resolve nomes; a CVM1 conecta nela pelo IP.
        if [ "$ipt" = iptables ]; then
            "$ipt" -A OUTPUT -d 127.0.0.11 -j DROP
        fi
        "$ipt" -A OUTPUT -o lo -j ACCEPT
        "$ipt" -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    done
    echo "egress lock: saída nova bloqueada (só respostas a conexões de entrada)"
fi

exec setpriv --reuid=dnat --regid=dnat --init-groups --inh-caps=-all --bounding-set=-all \
    python3 /app/executor.py "${PORT:-5000}"
