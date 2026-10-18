# E2b — Build seguro de imagens OCI

**Status:** RASCUNHO. Decisões fechadas; especificação em rascunho; nada medido.
No MVP do DSN o build em duas fases é **desejável**; o obrigatório é o executor OCI ([PLANO.md](../PLANO.md)).
**Decisões relacionadas:** D3, D4 ([DECISOES.md](../DECISOES.md)).
**Itens marcados (a verificar)** dependem de teste ou de fonte ainda não consultada.

## E2b.1 — Problema e contrato

O builder constrói a aplicação como **arquivo OCI pronto para executar**, sem dataset (D4). O executor só o recebe, verifica e roda num container sem rede dentro de uma CVM de uso
único (D4). O build concentra a superfície restante: `RUN` arbitrário, imagens-base,
camadas e cache. Achado de partida: **A10** (E1), a microVM de build tem egress para a internet
com o código do desenvolvedor presente.

## E2b.2 — Decisões do build OCI

| # | Decisão | Status |
|---|---|---|
| 1 | Dockerfile livre, sem gabaritos fixos (D4) | aceita |
| 2 | **Qualquer imagem-base, de qualquer registry**, sem lista de aprovadas nem curadoria; o builder resolve a tag para digest no fetch e registra | aceita em 2026-10-18 |
| 3 | Build em duas fases: fetch (rede, sem código) e assemble (sem rede) | aceita, especificada em E2b.3 |
| 3b | Cada fase na sua CVM (opção B): fetch fala só com o proxy; assemble só com o DNAT | aceita em 2026-10-18, E2b.3 |
| 4 | Build em CVM de uso único | aceita |
| 5 | Motor de build rootless | rejeitada (a VM descartável é a fronteira; se houver motor, evitar Kaniko, arquivado) |
| 6 | Imagem assinada pelo builder atestado | aceita, especificada em E2b.4 |
| 7 | Build reproduzível, selado junto com a assinatura (D4) | aceita, viabilidade a verificar |
| 8 | Varredura de saída básica antes de assinar (D4) | aceita; evolui para agentes (E4) |
| 9 | Cache particionado por dono | baixa prioridade |
| 10 | X8 fora de escopo; X7 limitação declarada (D3) | aceita |
| 11 | Imagem OCI pronta do desenvolvedor aceita como origem nível 0 | aceita em 2026-10-18 (padrão nível 0), E2b.7 |

Os ataques de uma imagem comprometida contra o executor (X1–X6) viram
**requisitos do executor** (E2b.5).

## E2b.3 — Imposição das duas fases sobre Dockerfile livre

**Objetivo:** fechar A10 sem restringir o Dockerfile. Nenhuma instrução executada com **rede**
pode ver o **código** do desenvolvedor.

**Por que não confiar no Dockerfile:** o desenvolvedor pode escrever `RUN pip install` em
qualquer ponto. A separação precisa ser imposta **pelo builder** com mecanismos do motor, não
por boa-fé do Dockerfile.

**Mecanismo: dois estágios nomeados e contextos de build distintos.**

Convenção do Dockerfile (o builder valida a estrutura e rejeita se faltar):

```dockerfile
FROM python@sha256:<digest> AS deps      # fase 1: com rede
COPY requirements.lock /
RUN pip wheel --require-hashes -r /requirements.lock -w /wheels

FROM deps AS app                         # fase 2: sem rede
COPY . /app
RUN pip install --no-index --find-links=/wheels -r /requirements.lock && pip install --no-index /app
```

Execução pelo builder, na CVM de build (uso único):

| Fase | Comando (esboço, a verificar nas flags do motor) | Contexto | Rede |
|---|---|---|---|
| 1. fetch | build `--target deps` | **só os arquivos declarados** como de dependência (lockfile, manifesto) | só o **proxy de registro** (E2c B2), aberto a qualquer registry ou índice público; hoje o protótipo só bloqueia as faixas privadas (`build-vm.sh:174-186`) |
| 2. assemble | build `--target app --network=none` | contexto completo (código + dependências já baixadas) | **nenhuma** |

Por que fecha A10: na fase 1 o código **não existe** no contexto. Um `COPY . /app` ali falha ou
copia só os arquivos declarados. Na fase 2 não há rota de rede, então uma dependência maliciosa
que rode em `setup.py` não tem para onde exfiltrar.

**Risco residual da fase 1: escape do container de build.** Uma dependência maliciosa não
vaza o código pelo contexto (ele não existe ali), mas pode **escapar do container** e cair na
CVM de build, que tem rede e pode conter código, agente e chave de assinatura. A atestação mede
o boot, não o estado em execução; um agente adulterado poderia assinar uma declaração forjada.
Por isso o desenho precisa dizer **quando o código e a chave chegam à CVM**. Duas opções foram
consideradas:

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A. Mesma CVM, entrega tardia** | Fase 1 roda sem código e sem chave na CVM. Ao terminar, a rede da CVM é cortada; só então chegam o código e a chave de assinatura (gerada depois) e roda a fase 2 | Uma CVM por build; simples | Um escape na fase 1 ainda cai na CVM que depois assinará: o agente pode ter sido adulterado. Reduz a exposição do código, **não** elimina a falsificação de assinatura |
| **B. CVM de fetch separada** | A fase 1 roda numa CVM própria, de uso único, que nunca vê código nem chave. Entrega só as dependências (wheelhouse/camadas), verificadas por hash, à CVM de assemble, que é quem recebe o código e assina | Um escape na fase 1 não alcança código nem chave; o assemble é limpo | Uma CVM a mais por build; transferência das dependências entre CVMs; hashes das dependências precisam ser conhecidos ou registrados |

**Decidido em 2026-10-18: opção B.** A opção A corta a rede *depois* que código de terceiros já
rodou com rede; root obtido por escape na fase 1 pode religá-la ou adulterar o agente que vai
receber o código e a chave. É o mesmo defeito da R4 da execução (E2c §2), e contraria a regra
"configurar no boot e jogar fora o poder de mudar". Com B, cada CVM é configurada no boot para
um único destino:

| CVM (uso único, do *warm pool*) | Fala com | Vê código? | Tem a chave? |
|---|---|---|---|
| **Fetch** | só o proxy de registro (que deixa passar **qualquer** registry ou índice público e anota cada download) e o DNAT, para entregar as dependências | não | não |
| **Assemble** | só o DNAT, com o mesmo desenho da CVM de execução (E2c §2: R5 regra no boot + remoção de capacidades, R6 lockdown, R7 mTLS fixado, R8 sub-rede/NSG; gVisor no container do build) | sim | sim, gerada nela |

Passagem entre elas: a CVM de fetch entrega o wheelhouse/camadas **ao DNAT**, que repassa à de
assemble; a de assemble confere cada pacote contra os hashes do lockfile e o registro do proxy
antes de usar. Escape na fase 1 não alcança código nem chave. Custo: uma CVM a mais por build e
a transferência das dependências **(a medir)**.

**O que o desenvolvedor declara:** a lista de arquivos de dependência (p.ex.
`requirements.lock`, `package-lock.json`). Todo o resto é código e só entra na fase 2.

**Consequências para o desenvolvedor**
- Passos que precisam de rede **e** do código (ex.: `pip install .` que baixa dependências) não
  funcionam; devem ser separados em "baixar" (fase 1) e "instalar offline" (fase 2).
- Falha na fase 2 por falta de rede é erro do desenvolvedor, com mensagem clara.
- A lista de dependências é visível na rede na fase 1; é declarada, aceita.

**Limites (declarados)**
- Dependências maliciosas ainda podem **adulterar o resultado do build**: isso é integridade,
  não confidencialidade, e é tratado por assinatura e reprodução (E2b.4).
- Imagens-base: **qualquer uma**. O desenvolvedor pode usar tag; o builder resolve para digest na
  fase 1, baixa e registra o digest na proveniência; a fase 2 usa só esse digest, offline.
  Imagem-base maliciosa é o mesmo caso de dependência maliciosa: integridade, não sigilo
  (escape na fase 1 não alcança código nem chave; na fase 2 não há rede).
- Não impomos `--require-hashes` num Dockerfile livre; só recomendamos. O ganho é para a
  reprodutibilidade, não para A10.

**Alternativas avaliadas**

| Alternativa | Por que não |
|---|---|
| B. O builder reescreve o Dockerfile | Frágil; depende de entender a semântica de qualquer Dockerfile |
| C. Build inteiro offline com proxy ou espelho de pacotes | Exige uma solução por ecossistema; guardar como reforço, não como base |
| D. Confiar na convenção sem contextos separados | Não impõe nada; o código estaria presente na fase com rede |

**(a verificar):** que o motor escolhido aceite `--network=none` por fase e contexto por alvo;
que o cache da fase 1 seja reutilizado na fase 2 na mesma CVM.

## E2b.4 — Assinatura e proveniência (com reprodutibilidade)

**Objetivo:** o executor só roda imagem **produzida por um builder medido**, a partir de fonte
e lockfile conhecidos, e qualquer um pode conferir que o build foi fiel.

**1. O que o builder produz**

| Artefato | Conteúdo |
|---|---|
| Arquivo OCI | A aplicação construída (sem dataset) |
| **Declaração de proveniência** (estilo in-toto/SLSA) | `subject`: digest da imagem; `materials`: hash da fonte, do lockfile, do Dockerfile e **digests de todas as bases**; `builder`: medição da CVM; `scan`: resultado da varredura; `reproducible`: sim/não |
| **Assinatura** | Sobre a declaração, com chave gerada **dentro da CVM de build**, uma por build |
| **Relatório de atestação** | Com `REPORT_DATA = hash(chave pública ‖ declaração)`, o que vincula chave, declaração e medição |

**2. O que o executor verifica, na ordem, antes de desempacotar**
1. Relatório de atestação válido e medição do builder **ou da CVM de ingestão** (imagem pronta,
   E2b.7) na **lista permitida**; nível de origem ≥ mínimo do dataset.
2. Assinatura da declaração com a chave vinculada ao relatório.
3. O digest do arquivo OCI recebido é o `subject` da declaração.
4. A varredura passou (e é refeita pelo executor, ver E2b.5).
5. O `contentHash` registrado na compra no ledger confere com o digest (substitui o hash do
   ext4 não reproduzível, A6).

Falhou qualquer passo, o job não executa.

**3. Reprodutibilidade selada com a assinatura**
- O digest só é estável se o build for determinístico: timestamps fixos, ordem de camadas
  fixa, dependências por hash, bases por digest **(viabilidade a verificar com Dockerfile
  livre)**.
- **Reproduzir só adiciona garantia com um segundo builder** que refaça o build e assine o
  mesmo digest. Política: uma imagem pode exigir ≥ N assinaturas de builders medidos distintos.
  N = 1 é o baseline (só atesta o builder); N ≥ 2 detecta um builder comprometido (digests
  divergem).
- Se o build não for reprodutível, `reproducible: não` entra na declaração e a garantia cai
  para a do N = 1. Isso é explícito, não silencioso.

**4. Varredura de saída (decisão 8)**
Roda no builder, **antes de assinar**, por um agente confiável fora do container de build.
Verifica: segredos nas camadas, binários setuid, links e caminhos suspeitos, tamanho e número
de camadas. O resultado entra na declaração. É filtro de falha antecipada e proteção do
desenvolvedor contra vazamento de segredos, **não** prova de que a imagem é benigna.

**Pontos em aberto**
- Onde fica a lista permitida de medições de builders (atestação implícita por ora, D3).
- Formato exato do `subject`: digest do manifesto OCI ou do arquivo inteiro.

## E2b.5 — Requisitos do executor (X1–X6)

O executor **não confia** na imagem nem na varredura do builder:

| Ataque | Requisito |
|---|---|
| X1 escape de container | Runtime atualizado e reforçado (D4); CVM de uso único |
| X2 camadas/links maliciosos | Desempacotar com ferramenta atual, validar, limitar tamanho e camadas |
| X3 imagem pede privilégios | Ignorar a config da imagem; impor sem capacidades, `no-new-privileges`, rootfs somente leitura, sem dispositivos |
| X4 saída como armazenamento hostil | Ler a saída como dado: só arquivos regulares, sem seguir links, com limite de tamanho |
| X5 esgotamento de recursos | Limites de cgroup, disco e tempo; abortar o job |
| X6 movimento lateral | mTLS entre planos; política de rede restritiva |

## E2b.6 — Pendências e próximo passo

- Medir o custo da opção B (CVM extra e transferência das dependências).
- Validar a resolução tag → digest no fetch e a viabilidade do build reproduzível.
- Verificar as flags do motor de build (E2b.3) e o estado das ferramentas (Kaniko arquivado).
- Medições (tempo de build em duas fases, custo da reprodução) ficam para depois das decisões.

## E2b.7 — Imagem OCI pronta enviada pelo desenvolvedor (ACEITA em 2026-10-18)

**Pergunta:** se o desenvolvedor já tem o código, por que não envia a imagem pronta?
**Resposta curta:** pode. A imagem pronta entra como **origem nível 0**, ao lado do build atestado.

### 1. O que muda e o que não muda

| Aspecto | Imagem do builder (nível 1–2) | Imagem pronta (nível 0) |
|---|---|---|
| Sigilo do dataset | Isolamento da execução (E2c §2) | **Igual.** A execução já trata toda imagem como hostil (X1–X6, R1–R9); imagem maliciosa = app maliciosa, o caso que o desenho já cobre |
| Vínculo fonte → imagem | Proveniência assinada pelo builder | **Nenhum.** O que roda é o que o desenvolvedor enviou |
| O Juiz julga | Fonte + imagem | **A própria imagem** (sistema de arquivos extraído); binário compilado opaco tende a **inconclusivo**; L2 (dinâmico) funciona igual |
| Supply chain da máquina do desenvolvedor | Coberta pelas duas fases | Risco do desenvolvedor (declarado) |
| Recibo | Medição do builder + digest | Digest + `origem: desenvolvedor` |

Ou seja, o nível 0 não enfraquece o sigilo do dataset; enfraquece a **transparência** (o que o
Juiz consegue ver) e a **proveniência** (quem garante como a imagem foi feita).

### 2. Política: nível de origem mínimo por dataset

- **0:** imagem enviada pelo desenvolvedor.
- **1:** build atestado (duas CVMs, E2b.3/E2b.4).
- **2:** N ≥ 2 builders concordantes (reprodução, E2b.4 §3).

**Padrão: 0** (qualquer imagem é aceita, decidido em 2026-10-18). O dono do dataset pode exigir
nível 1 ou 2; o recibo sempre informa o nível.

### 3. Fluxo de ingestão (CVM de ingestão)

A ingestão substitui o builder; não executa nada da imagem, só a desempacota e examina.

1. **Entrega:** upload ao DNAT por mTLS (arquivo OCI layout ou `docker save`), ou referência
   `registry/repo@sha256:…` de **qualquer** registry, baixada pelo mesmo caminho da CVM de fetch
   (proxy de registro, E2c B2). Credencial de registry privado só como montagem de segredo (B6).
2. **CVM de ingestão de uso único**, com o desenho de rede da execução (só o DNAT, E2c §2): a
   imagem contém o código do desenvolvedor, que é sigiloso (B10).
3. **Normalização:** aceita OCI e Docker v2; índice multiplataforma → escolhe o manifesto da
   arquitetura do executor; confere digests de todas as camadas; limites de tamanho e número de
   camadas (X2, X5).
4. **Varredura** (a mesma de E2b.4 §4): setuid, links e caminhos suspeitos, segredos (aviso ao
   desenvolvedor), SBOM e vulnerabilidades conhecidas (B4); SBOM e sistema de arquivos vão para
   o Juiz.
5. **Config da imagem:** só `Entrypoint`/`Cmd`/`WorkingDir`/`Env` são lidos; usuário,
   capacidades, volumes e portas são ignorados (X3).
6. **Cifra** com a chave do ativo (B10) e **declaração de ingestão** assinada pela CVM de
   ingestão (chave gerada nela, vinculada ao relatório de atestação): `subject` = digest,
   `origem: desenvolvedor`, `scan`, SBOM. Assinatura do desenvolvedor (ex.: cosign) é opcional e
   só identifica o autor; não prova nada sobre o build.

### 4. Executor

E2b.4 §2 passo 1 passa a aceitar **declaração de builder ou de ingestão**, desde que o nível de
origem atenda ao mínimo do dataset. Os demais passos (assinatura, digest, varredura refeita,
`contentHash` no ledger) são iguais.

### 5. Promoção de nível

Se o desenvolvedor também enviar fonte + Dockerfile e o builder reproduzir **o mesmo digest**, a
imagem sobe para nível 1 (ou 2 com N builders). Depende de reprodutibilidade (B7), difícil com
Dockerfile livre; sem ela a imagem fica no nível 0.

### 6. Pendências
- Juiz sobre imagem sem fonte: como apresentar o sistema de arquivos (lista de arquivos,
  scripts legíveis, binários marcados como opacos) e taxa esperada de inconclusivos.
- Ferramentas de normalização e SBOM sobre imagem pronta **(a escolher)**.
