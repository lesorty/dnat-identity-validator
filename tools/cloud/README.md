# Fase de testes na nuvem: do zero aos resultados de volta

Todo número do artigo sai daqui (regra de 12/11): VMs de nuvem, código congelado (T-1611), cada
pacote com a ficha da máquina. O que roda no notebook é verificação de funcionamento.

## Caminho com GPU confidencial no GCP (desde 25/11)

Do notebook à campanha em quatro comandos. Os detalhes de cada um estão no próprio script.

```bash
# no notebook (repositório limpo, no commit que vai rodar)
tools/cloud/enviar.sh usuario@vm             # código por git bundle (sem chave do GitHub na VM) e 2 arquivos locais
# na VM
cd dnat-identity-validator
tools/cloud/preparar_testes.sh --docker      # dados, campo, juiz de referência, driver, torch com CUDA, ficha, pré-voo
#   (ou disco pronto: --disco numa VM barata, imagem, e --so-gpu na a3; ver "Disco pronto" abaixo)
tools/cloud/campanha_gpu.sh iniciar piloto   # PRIMEIRO (26/11): os 11 reduzidos, ~3 h; DSN2027/testes/HORAS_GPU.md §0
tools/cloud/campanha_gpu.sh iniciar ensaio   # opcional, ~30 min: os 11 testes nos tamanhos do mini, na GPU
tools/cloud/campanha_gpu.sh iniciar nuvem 1  # depois do ensaio: fase 1 (T1, T9, T10, T11, T2)
#   revisar a proposta do T2, preencher prereg.yaml, commit, make congelar; no notebook: enviar.sh de novo
tools/cloud/campanha_gpu.sh iniciar nuvem 2  # fase 2 (T3, T5, T6, T7, T8, T11, T4)
tools/cloud/campanha_gpu.sh estado | log | parar
```

- **VM:** `a3-highgpu-1g` (1 H100 80 GB, Intel TDX, 26 vCPU, ~234 GB de RAM) com Confidential VM e GPU
  confidencial, nas zonas us-central1-a, us-east5-a ou europe-west4-c. Só existe em **Spot** ou
  **flex-start**: crie com a ação de término **STOP** (não DELETE), para o disco sobreviver à preempção.
  Disco de 200 GB. Imagem Ubuntu 22.04/24.04 com suporte a TDX.
- **Preempção:** a campanha roda como serviço do systemd (`dnat-testes`). Quando a VM volta, o serviço
  volta sozinho e os roteiros retomam do item em que pararam. Uma rodada que terminou não roda de novo.
- **GPU:** o model_gate roda em float32 na GPU, guloso e determinístico (`MODEL_GATE_DISPOSITIVO=cuda`).
  As contas dos sinais (direção do S2, ΔW e SVD do S3, arredondamento dos formatos) continuam na CPU. O
  Juiz recusa comparar um derivado medido na GPU com um pai medido na CPU. O T1 compara o mesmo
  veredito na CPU e na GPU.
- **Paralelo:** dois vereditos ao mesmo tempo na placa (`MG_PARALELO`); o rótulo usa lotes de 16 no
  juiz de referência. O sinal de vida de cada passo grava a memória e o uso da GPU, para ajustar.
- **Travado:** um passo que fica 60 min sem escrever nada (30 no ensaio) é morto e conta como falha,
  em vez de deixar a GPU parada cobrando.
- **Cópia fora da VM:** `DNAT_BUCKET=gs://<bucket>/<pasta> tools/cloud/campanha_gpu.sh iniciar ...` copia
  os testes, o acompanhamento, a ficha e o log do serviço para o bucket depois de cada passo. No fim,
  sobem os dois pacotes: o leve, sem textos gerados, que vai para o git, e o completo, com textos,
  referências e adaptadores, que fica fora do git. Crie a VM com escopo de escrita no Storage.
- **Estado da ida ao GCP:** o que está pronto, o que falta decidir e o que fica salvo onde estão em
  `DSN2027/testes/IDA_AO_GCP.md`.
- **O ensaio primeiro.** Ele não é dado do artigo: serve para ver, em meia hora, que tudo carrega e roda
  na GPU e quanto cada passo leva, antes das horas da campanha.

### Disco pronto: o preparo numa VM barata (26/11)

O preparo leva ~1 h, e quase tudo nele é download (~80 GB de modelos) e instalação, que não precisam de
GPU. Esse trabalho vai para uma VM barata, que vira uma **imagem**. A a3 sobe dessa imagem e só faz o que
precisa da placa (~5–15 min).

**Não testei estes comandos do gcloud no projeto.** Confira as flags antes, principalmente as do TDX.

```bash
# 0. a imagem Ubuntu precisa ter TDX_CAPABLE (a mesma que a a3 usaria)
gcloud compute images describe-from-family ubuntu-2404-lts-amd64 --project=ubuntu-os-cloud \
  --format='value(guestOsFeatures)'

# 1. VM barata (Spot), na zona onde a a3 vai rodar, com escrita no Storage
gcloud compute instances create dnat-preparo --zone=ZONA --machine-type=n2-standard-8 \
  --provisioning-model=SPOT --instance-termination-action=STOP \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=200GB --boot-disk-type=pd-balanced --scopes=storage-rw
tools/cloud/enviar.sh usuario@IP                                  # no notebook (código e os 2 arquivos locais)
tools/cloud/preparar_testes.sh --disco --populacao piloto         # na VM barata (~1 h, mais o treino dos LoRA)

# 2. a imagem (a VM barata pode ser apagada depois)
gcloud compute instances stop dnat-preparo --zone=ZONA
gcloud compute images create dnat-piloto --source-disk=dnat-preparo --source-disk-zone=ZONA
gcloud compute images describe dnat-piloto --format='value(guestOsFeatures)'   # tem de listar TDX_CAPABLE
gcloud compute instances delete dnat-preparo --zone=ZONA

# 3. a a3, da imagem
gcloud compute instances create dnat-a3 --zone=ZONA --machine-type=a3-highgpu-1g \
  --confidential-compute-type=TDX --maintenance-policy=TERMINATE \
  --provisioning-model=SPOT --instance-termination-action=STOP \
  --image=dnat-piloto --boot-disk-size=200GB --scopes=storage-rw
tools/cloud/preparar_testes.sh --so-gpu                           # na a3: driver, modo confidencial, teste curto
DNAT_BUCKET=gs://<bucket>/<pasta> tools/cloud/campanha_gpu.sh iniciar piloto
```

O que a imagem leva e o que fica para a a3:

| Etapa | Onde |
|---|---|
| ferramentas, ambientes, base, datasets, Qwen3Guard, gpt-oss-20b, campo, dados da população | VM barata (`--disco`) |
| torch com CUDA e hashcat (instalar não precisa da placa) | VM barata |
| derivados LoRA e abliterados do piloto, treinados na CPU (`--populacao piloto`); a a3 os reaproveita pela receita | VM barata |
| driver da NVIDIA (`--com-driver` tenta na VM barata; o instalador pode recusar sem a placa) | a3, se não entrou na imagem (~10 min e um reinício) |
| modo confidencial da placa, teste curto de determinismo, ficha e pré-voo | a3 (`--so-gpu`) |

**Cuidados:**

- **Na a3, use `--so-gpu`, nunca o `preparar_testes.sh` sem flags.** O completo roda o `make setup`, que
  devolve o torch ao de CPU (`uv sync`), e aí o torch com CUDA (~3 GB) teria de ser baixado de novo.
- **Mesmo usuário nas duas VMs.** Os dados ficam em `~/model_gate_data`. Se o SSH entrar com outro
  usuário na a3, nada é encontrado e o `--so-gpu` avisa.
- **Código depois da imagem:** rode o `enviar.sh` de novo para a a3; ele só atualiza o código. Se o
  `uv.lock` mudou, a imagem precisa ser refeita.
- **Imagem sem `TDX_CAPABLE`:** recrie-a com `--guest-os-features`, listando as mesmas marcas da imagem
  Ubuntu de origem.
- **Fichas:** as da VM barata vão para `preparo/fichas/`, fora do que sobe para o bucket. A ficha que vale é
  a da a3, gravada pelo `--so-gpu` e pelo T1.
- **Depois do piloto, guarde a imagem.** Ela custa centavos por mês e serve para a campanha.

O caminho em CPU abaixo continua valendo (VM sem GPU: `preparar_testes.sh --sem-gpu`).

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

**Testes T1 a T11 (caminho principal desde 24/11):** `tools/testes/README.md`. Em resumo:

```bash
tmux new -s campanha
make testes-verificar PERFIL=nuvem FASE=1     # pré-voo; nada roda
make testes PERFIL=nuvem FASE=1               # T1, T9, T10, T11, T2
#   revisar a proposta do T2, preencher model_gate/prereg.yaml (T-606), commit, make congelar, git pull na VM
make testes PERFIL=nuvem FASE=2               # T3, T5, T6, T7, T8, T11, T4
make testes-pacote PERFIL=nuvem
```

O executor de passos soltos abaixo (plano.yaml) continua para as medidas avulsas:

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
| `enviar.sh` | No notebook: código (git bundle) e os 2 arquivos locais para a VM |
| `preparar_testes.sh` | Na VM: tudo o que os testes T1–T11 precisam, GPU inclusive, e o pré-voo; `--disco` numa VM barata e `--so-gpu` na a3 que sobe da imagem |
| `campanha_gpu.sh` | Na VM: a rodada como serviço do systemd (sobrevive a SSH e preempção) |
| `../../model_gate/gpu/torch-cuda.txt` | torch 2.15.0 com CUDA 13.2 e as bibliotecas da NVIDIA, com hashes |
| `bootstrap.sh` | Prepara a VM (ferramentas fixas, ambientes, dados, ficha, doctor) |
| `fetch_data.sh` | Baixa e confere os dados pelos manifestos (`make dados`) |
| `machine_card.py` | Ficha da máquina (`make ficha`) |
| `plano.yaml` | Os passos da campanha, com comando e bloqueio de cada um |
| `campanha.py` | Executor: status, run (retoma, exige congelamento), pacote |
| `importar.sh` | Importa um pacote no repositório (`make importar`) |
| `../congelar.sh` | Fecha o sistema com a tag `congelado-*` (`make congelar`) |
