# Fase de testes na nuvem: do zero aos resultados de volta

Todo número do artigo sai daqui (regra de 12/11): VMs de nuvem, código congelado (T-1611), cada
pacote com a ficha da máquina. O que roda no notebook é verificação de funcionamento.

## 0. Antes, no notebook

```bash
make test                 # tudo passando
make congelar             # tag congelado-AAAAMMDD-HHMM com os hashes do Juiz e do prereg
git push origin main --tags
```

`make congelar` recusa repositório sujo e prereg com valores nulos (T-606). Para ensaiar o processo
antes disso: `make congelar ARGS=--ensaio` (tag `ensaio-congelado-*`, que a campanha não aceita
como congelada) e `make campanha ARGS=--sem-congelamento`.

## 1. A VM

- **Tipo:** 4 vCPU com BF16 acelerado (AVX-512 BF16 ou AMX) para o avaliador; na Azure, DCasv6 ou
  DCesv6 (CVM AMD SEV-SNP); na Oracle, E4/E5 com computação confidencial. Para o overhead (T-812),
  uma VM comum e uma CVM do mesmo tamanho.
- **Disco:** 100 GB (base 1 GB, avaliadores ~16 GB, população e campo ~35 GB).
- **Sistema:** Ubuntu 24.04 ou 22.04.

## 2. Preparar (uma vez por VM, ~30 min, idempotente)

```bash
git clone git@github.com:lesorty/dnat-identity-validator.git && cd dnat-identity-validator
git checkout congelado-AAAAMMDD-HHMM
tools/cloud/bootstrap.sh --judges          # --docker para a pilha Docker e o T-812
```

Instala Node e uv em versões fixas (conferidos pelo SHA-256), roda `make setup`, baixa e confere os
dados pelos manifestos versionados, grava a ficha da máquina e roda o `make doctor`. A ficha diz
logo se a VM tem BF16 acelerado e se é confidencial; se não tiver BF16, troque de família antes de
gastar horas.

## 3. Rodar (dentro de tmux: a campanha leva horas e não pode cair com o SSH)

```bash
tmux new -s campanha
make campanha-status      # o que vai rodar, o que está bloqueado, o que não tem script
make campanha             # roda os passos pendentes, na ordem, parando na primeira falha
make campanha PASSOS="vazao avaliador-qwen3guard"     # só esses
make campanha ARGS=--continuar                        # segue depois de uma falha
```

O estado e os logs ficam em `$MODEL_GATE_DATA/campanha/tst_<commit>/`; rodar de novo retoma de onde
parou. Passos com `bloqueio` no `tools/cloud/plano.yaml` só rodam com `ARGS=--forcar`.

## 4. Trazer de volta

```bash
make pacote               # na VM: .tar.gz com os resultados desta campanha, o registro, a ficha e os logs
scp usuario@vm:~/model_gate_data/pacotes/campanha_*.tar.gz .    # no notebook
make importar PACOTE=campanha_....tar.gz                        # em resultados_nuvem/<pacote>/
```

A aba Resultados da interface mostra cada arquivo importado como **nuvem**, ao lado da verificação
local do mesmo experimento, com a máquina, o tipo de VM e se o commit estava congelado. Commit
`resultados_nuvem/` para versionar o dado do artigo.

## 5. Desligar

Destrua a VM (ou desaloque) assim que o pacote estiver no notebook: o custo corre por hora.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `bootstrap.sh` | Prepara a VM (ferramentas fixas, ambientes, dados, ficha, doctor) |
| `fetch_data.sh` | Baixa e confere os dados pelos manifestos (`make dados`) |
| `machine_card.py` | Ficha da máquina (`make ficha`) |
| `plano.yaml` | Os passos da campanha, com comando e bloqueio de cada um |
| `campanha.py` | Executor: status, run (retoma, exige congelamento), pacote |
| `importar.sh` | Importa um pacote no repositório (`make importar`) |
| `../congelar.sh` | Fecha o sistema com a tag `congelado-*` (`make congelar`) |
