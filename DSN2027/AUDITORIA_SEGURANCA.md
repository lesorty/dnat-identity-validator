# Auditoria de segurança dos fluxos (19/11/2026)

**Escopo:** a árvore de trabalho de 19/11, com as edições locais ainda sem commit. Foram quatro frentes: API, identidade e cota; execução e isolamento dos jobs; fluxo do Juiz e contrato; custódia, criptografia e armazenamento.

**Modelo de ameaça usado:**
- **Não confiáveis:** o usuário (conhece o código do Juiz, controla o script e os dados, pode criar várias identidades), o IPFS, a chain e a rede.
- **Confiáveis:** o operador e o hardware da CVM.

**Método:** cada achado foi conferido lendo o código, com a linha citada. Alguns também foram confirmados executando scripts isolados. Os principais (C1, C2, A1 e A3) foram reconferidos depois da auditoria. Nada no repositório foi alterado.

**Fora deste relatório:** o que já está em [REVISAO_SISTEMA.md](REVISAO_SISTEMA.md) §2–4, a T-816 e a T-115. Aparece aqui só quando a auditoria achou um ângulo novo, e isso vem marcado.

| Severidade | Quantidade |
|---|---|
| Crítica | 2 |
| Alta | 6 |
| Média | 11 |
| Baixa | 9 |

---

## Críticas

### C1. Qualquer envelope da CVM1 pode ser aberto dentro de um job do atacante
- **Onde:**
  - `smart-contract/scripts/asset_envelope.js:31-53, 82-93`: uma chave para todos os ativos, sem `setAAD`; `format` e `metadata` ficam fora da autenticação.
  - `api-server.js:1010-1018`: o dataset é aberto a partir de qualquer `encryptedUri` e não é conferido contra o `contentHash`.
  - `DnatMarketplace.sol:225`: `registerAsset` é aberto a qualquer conta.
- **Ataque:**
  1. O atacante pega o CID do alvo: bateria, referência ou derivado reprovado. O CID está na chain, ou se acha pelo rótulo em claro do header (M1).
  2. Troca `format` no header (por exemplo `dnat-battery-v1` → `dnat-dataset-v1`) e sobe o arquivo modificado.
  3. Registra um Dataset apontando para esse CID.
  4. Roda um job próprio. A CVM1 decifra e entrega o texto claro em `data/dataset.csv`.
- **Variante `Model`:** o atacante registra um `Model` com `contentHash` igual ao digest de um derivado reprovado, que é público no recibo. A conferência de digest em `materializeParentModel` passa, e o reprovado vira base de um novo fine-tuning. Isso quebra a retenção (C1 do artigo).
- **Saída do texto claro:** pelo canal numérico das métricas (A5), sem custo de cota (A3). Uma bateria de 16 a 20 pedidos sai em cerca de 200 jobs. Com a C2, sai em um job.
- **Confiança:** a troca de rótulo foi confirmada executando; o resto da cadeia, lendo. A condição é o atacante escrever na chain, o que o modelo de ameaça admite. Na pilha local o RPC fica preso na CVM1.
- **Correção:**
  - a CVM1 só abre CIDs que ela mesma registrou, mantendo um mapa local de id e papel para CID e hash;
  - o AEAD amarra formato, papel e hash no AAD, ou na chave via HKDF;
  - o dataset é conferido contra o `contentHash`.
- **Conhecido:** o rótulo fora do AAD estava na §2 como "baixa". Esta cadeia o leva a crítica.

### C2. O job forja a resposta do runner e ganha um canal de texto sem limite
- **Onde:**
  - `vm_runtime/start-direct.sh:31` e `vm_runtime/vm/run-direct.sh:116-120`: agente, runner e job rodam com o mesmo uid `dnat`, no mesmo PID namespace.
  - `vm_runtime/job_output.py:289`: repassa qualquer dict em `derivative`.
  - `run_from_cids.py:727`: tira o derivado da resposta antes do teto de bytes.
  - `run_from_cids.py:508`: copia `derivative.digest` sem limite.
  - `run_from_cids.py:528`: devolve `str(exc)` ao usuário.
- **Ataque:**
  1. O script do job abre `/proc/<python do runner>/fd/1`, que é o pipe lido pelo agente.
  2. Escreve um JSON com `derivative.digest` = base64 do dataset de outro dono, ou de um pedaço do base.
  3. Mata o runner antes que ele imprima a resposta verdadeira.
  4. O texto volta ao usuário em metadata e `runnerStdout`.
- **Também falsifica:** `base_modified`, `timed_out`, `returncode` e `elapsed_seconds`.
- **Variante:** um processo com `setsid` troca o tar no outbox por outro com um nome de membro em texto livre, que volta na mensagem de erro.
- **Confiança:** confirmado lendo, e a cadeia de processos foi simulada fora do container. Não foi rodado dentro do Docker.
- **Correção:**
  - o job roda com outro uid, em PID namespace próprio (ou `hidepid`), sem escrita no outbox;
  - a CVM1 só aceita digest hex de 64 caracteres e uma lista limitada de arquivos;
  - nunca devolver `str(exc)` ao usuário.

---

## Altas

### A1. A revogação de um derivado se desfaz reenviando o mesmo job
- **Onde:** `DnatMarketplace.sol:325-374`: a revogação é por `assetId`, e `registerDerivative` não confere se o `derivativeHash` já foi revogado. `judge_flow.js:445`: a idempotência é só por `executionId`.
- **Ataque:** uma receita determinística gera o mesmo digest. O sorteio e a geração gulosa repetem o veredito aprovado, e nasce um asset novo e ativo.
- **Confiança:** confirmado lendo.
- **Correção:** guardar `mapping(bytes32 => bool)` de digests revogados, recusar o registro desses digests e não julgar de novo um digest já julgado.

### A2. Identidade quase de graça: a cota não freia ataques Sybil
- **Onde:** `docker/direct.compose.yaml:25` (d = 16 por padrão); `identity.js:39-40` (Q = 20); `POST /register` sem limite de taxa.
- **Medido:** 20 identidades em 2,98 s com Node puro num núcleo. O custo de sondar o Juiz passa a ser só o tempo do próprio Juiz.
- **Agravante:** `_save` regrava o `identities.json` inteiro a cada operação, em O(N) e de forma síncrona.
- **Conhecido:** os valores são provisórios (T-1705, T-1708). O ângulo novo é o padrão do compose e a regravação O(N).
- **Correção:** ligar a cota a um recurso escasso (depósito, convite ou limite por origem) e usar um armazenamento incremental.

### A3. Trabalho pesado sem custo de cota e sem limite de concorrência
- **Onde:**
  - `api-server.js:1136-1140`: devolve a reserva inteira quando não há pai, não há derivado ou o job falha.
  - `judge_flow.js:468`: a falta de referência só é vista depois do treino.
  - `job_vm.js:278-282`: `take()` cria CVMs sem teto.
- **Ataque:** N identidades × pedidos simultâneos, todos sem pai ou com o script saindo com código 1, dão N CVMs de 4 GB, N cópias do base em `/tmp` e N Juízes na CVM1, com cota zero. É o que torna gratuitos os canais de C1 e A5.
- **Correção:** cobrar uma parte não devolvível por job, conferir a referência antes de reservar e limitar a concorrência por identidade e no total.

### A4. Builder comprometido de forma permanente
- **Onde:** `build_vm_runtime/Dockerfile.direct` roda como root; `builder.py:52-53` relança `worker.py` do disco; o cache de wheels fica em volume persistente gravável (`direct.compose.yaml:52-53`).
- **Ataque:**
  - o `setup.py` de uma dependência reescreve `/app/worker.py` e põe backdoor nas aplicações dos próximos usuários, mandando o código delas para a internet;
  - ou grava uma wheel falsa direto no cache.
- **Conhecido:** `setup.py` como root e o cache por ingest. O ângulo novo é a persistência no worker e a escrita direta no volume.
- **Correção:** um container descartável por build, sem root, com o cache `:ro` e wheels conferidas por hash.

### A5. Chaves padrão, CIDs públicos e IPFS no swarm público (condicional à implantação)
- **Onde:**
  - `asset_envelope.js:15,32`: a chave é `sha256("dnat-dev-asset-key")`, sem KDF.
  - `Dockerfile:17-18`, `root-entrypoint.sh:11-12`: o `PRIVATE_KEY` padrão é a conta 0 do Hardhat.
  - `GET /api/assets` sem autenticação devolve os `encryptedUri`.
  - `root-entrypoint.sh:64`: `ipfs init --profile=server` mantém bootstrap e DHT.
  - `judge_flow.js:166`: o Juiz herda o `env` com as duas chaves enquanto carrega pesos do atacante.
- **Ataque:** numa implantação sem as variáveis, qualquer um baixa pela rede pública e decifra tudo, ou vira operador numa chain fora da local. O `tools/cloud/` não define as variáveis.
- **Conhecido:** "não subir sem `ASSET_ENCRYPTION_KEY`". É novo: CIDs públicos, swarm aberto, ausência de KDF e o `env` herdado pelo Juiz.
- **Correção:**
  - recusar a partida sem uma chave aleatória de 32 bytes e uma chave própria de operador;
  - usar swarm privado;
  - passar ao Juiz um `env` mínimo.

### A6. Link simbólico em `application.ext4` faz a CVM1 cifrar arquivos dela mesma
- **Onde:** `api-server.js:573` (`tar -xzf` sem verificação na resposta do builder); `:759`, `:776` (seguem o link).
- **Ataque:** com o builder comprometido (A4), `application.ext4 -> /proc/self/environ` faz a CVM1 cifrar o próprio ambiente, com as chaves, como se fosse a aplicação. Esse conteúdo chega em claro à CVM de job.
- **Confiança:** a aceitação do link foi confirmada lendo; a cadeia completa é plausível.
- **Correção:** reaproveitar `safeExtractTarGz` e exigir arquivo regular (`lstat`).

---

## Médias

| # | Achado | Onde | Correção |
|---|---|---|---|
| M1 | O header em claro identifica os envelopes: tipo (localiza a bateria), `parentId`, `executionId`, digest, nome do arquivo. O CID do derivado vai à chain, ao contrário do que diz `retention.js:12` | `asset_envelope.js:42-51`, `judge_flow.js:305` | `metadata` dentro do texto cifrado; não publicar o CID do retido |
| M2 | O hash do dataset em claro é público e sem sal: permite teste de igualdade e de dicionário, e liga identidade a dataset pelo recibo | `api-server.js:644`, `judge_flow.js:500` | Compromisso com sal secreto (HMAC da CVM1) |
| M3 | Exfiltração de datasets de outros por ~100 bits por job (`steps` até 2^53, `loss`, `train_seconds`, tempo, `returncode`, picos de memória), de graça pela A3. O acesso conferido é o da carteira da CVM1. *Ângulo novo do conhecido* | `run_from_cids.py:59-67, 375-417`, `api-server.js:847, 969, 1148` | Limitar jobs por (identidade, dataset), exigir a permissão do dono, quantizar métricas e não devolver `jobVm` |
| M4 | Nada amarra o derivado ao treino: pesos preparados fora entram pela aplicação ou pelo dataset. O derivado pode levar arquivos extras (inclusive o dataset de outro), que entram no digest | `vm_runtime/derivative.py:79-109` | Lista branca de nomes e tensores com o formato do pai; declarar no artigo que a origem não é atestada |
| M5 | A escada nunca aprova e o veto quase nunca dispara: com 5 ou 6 itens por categoria, o limite de Wilson nunca resolve δ = 0,15. Cópia do pai → inconclusivo; 40% de dano → inconclusivo, não reprovado | `verdict/combine.py:176-181, 234-245` (confirmado executando) | Veto e amostra limpa na célula ALL, ou n dimensionado por categoria |
| M6 | O dano depois do token 512 é invisível: a resposta truncada não é tratada, e o teto é público | `stages.py:81`, `prereg.yaml` | Resposta que bate no teto vira célula falha ou inconclusiva |
| M7 | O `config.json` do derivado fica fora do contrato: `rope_scaling`, `sliding_window`, `quantization_config`, número de camadas | `job.py:131-157`, `io/load.py:87`, `formats/quant.py:157` | Exigir a config igual à do base, salvo uma lista de campos |
| M8 | O operador não revoga base, porque `revokeAsset` exige o dono. Depois de `setOperator`, a chave antiga continua dona e reativa derivados desativados | `DnatMarketplace.sol:271-309` | Revogação e desativação de Model e Derivative pelo operador |
| M9 | Texto claro no disco depois de queda: a varredura cobre só `dnat-execution-*`; ficam `/tmp/dnat-judge-*` (com a bateria secreta), `dnat-base-*`, `uploads/` e o workspace em SIGKILL. *Ângulo novo do conhecido* | `api-server.js:1448-1452`, `run_from_cids.py:778` | Um único tmpfs de trabalho apagado na partida e no sinal |
| M10 | `/api/add-file-to-ipfs` sem assinatura: pin permanente de até 4 GB e oráculo de cifra com a chave da implantação (`encrypt` vem do corpo) | `api-server.js:1406-1412` | Remover a rota ou exigir o operador |
| M11 | Registros assinados sem custo: gás, campos livres na chain, builder ocupado por 35 min. As listagens fazem N+3 chamadas RPC sem autenticação | `api-server.js:1299-1324, 685-718` | Cobrar cota no registro e guardar listagens em cache |

## Baixas

| # | Achado | Onde |
|---|---|---|
| B1 | O tamanho da tag GCM não é exigido: tag de 4 bytes é aceita (confirmado executando), o que abre forjamento de dataset e aplicação | `asset_envelope.js:93,165` → `authTagLength: 16` |
| B2 | O sorteio muda trocando um arquivo inócuo, porque a semente usa o digest do diretório inteiro | `battery/sample.py:118-121` |
| B3 | A sobreposição com a bateria só lê a coluna `prompt` do dataset declarado | `job.py:160-182` |
| B4 | A lista permitida aceita o avaliador `detector` fora do modo fumaça | `judge_flow.js:79-84` |
| B5 | Bomba gzip no upload de modelo e no derivado, sem teto de tamanho | `model_store.js:112`, `api-server.js:727`, `derivative.py:91-102` |
| B6 | A assinatura não amarra a implantação: replay entre duas CVM1 em até 5 min | `identity.js:161-166` |
| B7 | CORS aberto | `api-server.js:1263` |
| B8 | `/api/health` e a resposta do job vazam carteira, URLs internas e `runnerStderr` | `api-server.js:1146-1158, 1269-1281` |
| B9 | Os testes T1 e T1b não cobrem o sequestro por `/proc/<pid>/fd` nem a troca no outbox | `assets/apps/t1*.py` (criar T1c) |

---

## O que foi conferido e está sólido

- **Assinatura dos pedidos:** cobre método, caminho, carimbo e hash do corpo, com Ed25519 estrito e replay barrado. A cota (`reserve`/`settle`) é síncrona e acerta uma vez só. As rotas do operador ficam fechadas sem o token, comparado com `timingSafeEqual`.
- **Extração de tar (`safeExtractTarGz`):** recusa `..`, link simbólico, link físico e caminho absoluto. O digest de diretório é o mesmo em JS e em Python, e nenhum arquivo carregado fica fora dele.
- **Carga pelo Juiz:** só safetensors, PEFT com `weights_only=True`, sem `trust_remote_code`. Template e `generation_config` vêm sempre do base.
- **Contrato:**
  - derivado só pelo operador;
  - só aprovado nasce ativo;
  - `assetRevoked` é definitivo;
  - derivado não é comprável;
  - derivado de derivado é barrado;
  - pai revogado durante o job faz o registro reverter.
- **CVM de job:** saída bloqueada (OUTPUT DROP, DNS bloqueado), bounding set vazio, base conferido por digest antes e depois do job, métricas lidas com `O_NOFOLLOW` e teto de bytes.
- **Escada do veredito:** prereg com `null` leva a `StageNotReady` (falha fechada), NaN conta como ausente e célula falha leva à regra 2.
- **O que o usuário vê:** desfecho e alerta genérico, sem motivos nem medidas.

## Ordem sugerida de correção

1. **C2 e C1:** uid e PID namespace do job, AAD e mapa local de CIDs, dataset conferido pelo hash. Fecham a exfiltração da bateria e dos datasets.
2. **A1 e A3:** digest revogado no contrato, cota não devolvível e teto de concorrência. Fecham a volta do revogado e o custo zero.
3. **A5:** recusar a partida com chaves padrão. É barato e deve vir antes de qualquer implantação na nuvem.
4. **M5:** a escada que nunca aprova invalida a avaliação do artigo. Precisa entrar no pré-registro antes da T-1611.
5. **A4, A6 e o resto** por custo e benefício.
