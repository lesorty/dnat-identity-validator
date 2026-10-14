# E2b — Build seguro de imagens OCI

**Status:** RASCUNHO (2026-10-14). Decisões fechadas; especificação em rascunho; nada medido (D-007).
**Decisões relacionadas:** D-009 a D-015.
**Origem das ideias:** [brainstorm/02_build_oci.md](../brainstorm/02_build_oci.md).
**Itens marcados (a verificar)** dependem de teste ou de fonte ainda não consultada.

## E2b.1 — Problema e contrato

O builder constrói a aplicação como **arquivo OCI pronto para executar**, sem dataset (D-009,
D-010). O executor só o recebe, verifica e roda num container sem rede dentro de uma CVM de uso
único (D-011). O build concentra a superfície restante: `RUN` arbitrário, imagens-base,
camadas e cache. Achado de partida: **A10** (E1), a microVM de build tem egress para a internet
com o código do desenvolvedor presente.

## E2b.2 — Decisões do build OCI

| # | Decisão | Status |
|---|---|---|
| 1 | Dockerfile livre, sem gabaritos fixos (D-013) | aceita |
| 2 | `FROM` fixado por digest, sem curadoria nossa | aceita, por validar, prioridade menor |
| 3 | Build em duas fases: fetch (rede, sem código) e assemble (sem rede) | aceita, especificada em E2b.3 |
| 4 | Build em CVM de uso único | aceita |
| 5 | Motor de build rootless | rejeitada (a VM descartável é a fronteira; se houver motor, evitar Kaniko, arquivado) |
| 6 | Imagem assinada pelo builder atestado | aceita, especificada em E2b.4 |
| 7 | Build reproduzível, selado junto com a assinatura (D-015) | aceita, viabilidade a verificar |
| 8 | Varredura de saída básica antes de assinar (D-015) | aceita; evolui para agentes (E4) |
| 9 | Cache particionado por dono | baixa prioridade |
| 10 | X8 fora de escopo; X7 limitação declarada (D-014) | aceita |

Os ataques de uma imagem comprometida contra o executor (X1–X6 do brainstorm) viram
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
| 1. fetch | build `--target deps` | **só os arquivos declarados** como de dependência (lockfile, manifesto) | sim, com as faixas privadas bloqueadas como hoje (`build-vm.sh:174-186`) |
| 2. assemble | build `--target app --network=none` | contexto completo (código + dependências já baixadas) | **nenhuma** |

Por que fecha A10: na fase 1 o código **não existe** no contexto. Um `COPY . /app` ali falha ou
copia só os arquivos declarados. Na fase 2 não há rota de rede, então uma dependência maliciosa
que rode em `setup.py` não tem para onde exfiltrar.

**Risco residual da fase 1: escape do container de build.** Uma dependência maliciosa não
vaza o código pelo contexto (ele não existe ali), mas pode **escapar do container** e cair na
CVM de build, que tem rede e pode conter código, agente e chave de assinatura. A atestação mede
o boot, não o estado em execução; um agente adulterado poderia assinar uma declaração forjada.
Por isso o desenho precisa dizer **quando o código e a chave chegam à CVM**. Duas opções, ambas
em consideração:

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A. Mesma CVM, entrega tardia** | Fase 1 roda sem código e sem chave na CVM. Ao terminar, a rede da CVM é cortada; só então chegam o código e a chave de assinatura (gerada depois) e roda a fase 2 | Uma CVM por build; simples | Um escape na fase 1 ainda cai na CVM que depois assinará: o agente pode ter sido adulterado. Reduz a exposição do código, **não** elimina a falsificação de assinatura |
| **B. CVM de fetch separada** | A fase 1 roda numa CVM própria, de uso único, que nunca vê código nem chave. Entrega só as dependências (wheelhouse/camadas), verificadas por hash, à CVM de assemble, que é quem recebe o código e assina | Um escape na fase 1 não alcança código nem chave; o assemble é limpo | Uma CVM a mais por build; transferência das dependências entre CVMs; hashes das dependências precisam ser conhecidos ou registrados |

Recomendação provisória: **A como base** e **B como reforço** quando a integridade da assinatura
for crítica. Decisão final depois das medições de custo (D-007).

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
- Imagens-base são baixadas na fase 1 (fixadas por digest) e usadas offline na fase 2.
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
1. Relatório de atestação válido e medição do builder na **lista permitida**.
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
- Onde fica a lista permitida de medições de builders (ledger, controle ou ambos) → E3/E5.
- Como o segundo builder obtém a fonte sem violar a confidencialidade do código → E3/E5.
- Formato exato do `subject`: digest do manifesto OCI ou do arquivo inteiro.

## E2b.5 — Requisitos do executor (X1–X6)

O executor **não confia** na imagem nem na varredura do builder:

| Ataque | Requisito |
|---|---|
| X1 escape de container | Runtime atualizado e reforçado (D-011); CVM de uso único |
| X2 camadas/links maliciosos | Desempacotar com ferramenta atual, validar, limitar tamanho e camadas |
| X3 imagem pede privilégios | Ignorar a config da imagem; impor sem capacidades, `no-new-privileges`, rootfs somente leitura, sem dispositivos |
| X4 saída como armazenamento hostil | Ler a saída como dado: só arquivos regulares, sem seguir links, com limite de tamanho |
| X5 esgotamento de recursos | Limites de cgroup, disco e tempo; abortar o job |
| X6 movimento lateral | mTLS entre planos; política de rede restritiva |

## E2b.6 — Pendências e próximo passo

- Escolher entre as opções A e B da fase 1 (entrega tardia na mesma CVM ou CVM de fetch separada).
- Validar `FROM` por digest (D-013 ii) e a viabilidade do build reproduzível.
- Verificar as flags do motor de build (E2b.3) e o estado das ferramentas (Kaniko arquivado).
- Medições (tempo de build em duas fases, custo da reprodução) ficam para depois das decisões (D-007).
