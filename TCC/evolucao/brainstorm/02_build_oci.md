# Brainstorm 02 — Build seguro de imagens OCI

**Origem:** conversa de 2026-10-12, após D-009, D-010, D-011.
**Status:** levantamento inicial. Nada aqui foi verificado em fontes; marcado **(a verificar)**.
**Relacionados:** D-012 · [E1, achados A10–A12](../resultados/E1_auditoria_codigo.md) ·
[E2](../resultados/E2_isolamento_confidencial.md)

## Contexto

Contrato do desenho v2: o builder constrói a aplicação como **arquivo OCI pronto para executar**
(sem dataset, D-009); o executor só o recebe, verifica e roda num container sem rede (D-011).
Os riscos de execução ficaram contidos; o **build** concentra a superfície restante.

## Por que OCI é mais arriscado que ext4

| Superfície | ext4 atual | OCI |
|---|---|---|
| Código executado durante o build | `pip install` de wheels (sdist ainda executa `setup.py`) | Instruções arbitrárias de build (`RUN`) com rede, mais `setup.py`, `postinstall` etc. |
| Origem do conteúdo | Wheels de um índice | **Imagens-base** de registry, tags mutáveis, camadas de terceiros |
| Ferramenta de build | Script próprio dentro de microVM | Motor de build (BuildKit, buildah, kaniko...) que costuma exigir privilégios **(a verificar)** |
| Formato | ext4 simples | Manifesto, camadas, config, histórico; segredos podem ficar em camadas |
| Cache | Cache de wheels | Cache de camadas: vetor de envenenamento |
| Reprodutibilidade | Não reproduzível (UUID/timestamps, E1 A6) | Possível com timestamps fixos, mas não por padrão **(a verificar)** |
| Exfiltração do código do dev | Existe hoje (E1, A10) | Mesmo problema, com mais oportunidades |

## Alavancas de projeto (ideias a avaliar)

1. **Não aceitar Dockerfile arbitrário.** O desenvolvedor entrega *manifesto + lockfile* e o
   builder gera o Dockerfile a partir de **gabaritos fixos** por ecossistema. Reduz a
   expressividade, que é onde mora a superfície. Custo: menos liberdade.
2. **Imagens-base curadas e assinadas pela plataforma**, fixadas por *digest*, mínimas
   (distroless ou equivalente). Nada de `FROM` livre.
3. **Build em duas fases** (herda A10): (a) *fetch* com rede e **sem o código do app**, só
   dependências com hashes fixados; (b) *assemble* **sem rede**, com o código e as
   dependências já baixadas.
4. **Build numa CVM de uso único** (mesmo padrão do executor, D-006): sem estado entre builds,
   atestada. O código do desenvolvedor fica protegido do operador.
5. **Motor de build sem privilégios** (rootless, sem daemon) **(a verificar qual está
   mantido hoje, p.ex. status do kaniko)**.
6. **Cache particionado por aplicação/dono**, com conteúdo endereçado por hash; sem cache
   compartilhado entre donos (T6).
7. **Saída assinada**: o builder atestado assina o *digest* da imagem e a proveniência
   (fonte + lockfile → imagem); o executor só roda imagem assinada por um builder medido.
8. **Saída reproduzível** (timestamps fixos, ordem de camadas determinística), para a
   direção 3 (builders independentes) **(a verificar viabilidade)**.
9. **Varredura do resultado** (sem segredos, sem binários setuid, tamanho máximo) antes de
   assinar.

## Triagem das alavancas (2026-10-12)

| Alavanca | Status | Nota |
|---|---|---|
| 1. Gabaritos fixos | **ELIMINADA** como requisito | Limita demais a aplicação. A contenção (3 e 4) dá a proteção principal. Aceita-se Dockerfile livre; manifesto simples só como atalho opcional. A imposição das duas fases num Dockerfile livre exige convenção (build multi-estágio) **(a verificar)** |
| 2. Bases curadas e assinadas pela plataforma | **SUBSTITUÍDA, substituto POR VALIDAR** | Custo de curadoria e manutenção. Substituto: `FROM` fixado por *digest*, sem assinatura nossa. Prioridade menor que 3 e 4; validar depois (D-013) |
| 3. Build em duas fases | promissora | Fecha A10 |
| 4. Build em CVM de uso único | promissora | Mesmo padrão do executor |
| 5. Motor de build sem privilégios | **REJEITADA** | O build já roda numa VM separada e de uso único, que é a fronteira; rootless não acrescenta proteção relevante e pode impedir builds que exigem root real ou mounts. Se um dia houver motor de build, evitar Kaniko (arquivado) |
| 6. Cache particionado | baixa prioridade | Ver nota abaixo |
| 7. Saída assinada pelo builder atestado *(item "6" na numeração do chat)* | **APROVADA, como incremento de atestação** | Não altera a segurança do ambiente que executa o build. Garante que o executor só rode imagem produzida por um builder medido (integridade do artefato entre build e execução). Ver D-013 |
| 8. Saída reproduzível | em aberto | Liga à direção 3 |
| 9. Varredura da saída | em aberto | |

*(Numeração deste arquivo; no chat a lista foi numerada de 1 a 6 com itens agrupados.)*

## O que uma imagem de build comprometida pode fazer ao executor

Para o executor, **imagem comprometida = aplicação maliciosa**, e a imagem é código **e** dado
não confiáveis. Vetores (exemplos de CVEs de runtime a verificar por versão):

| # | Ataque | Mitigação |
|---|---|---|
| X1 | **Escape de container** por falha de kernel/runtime (ex.: runc CVE-2019-5736, CVE-2024-21626) **(a verificar)** | Runtime atualizado e reforçado (D-011); CVM de uso único |
| X2 | **Extração da imagem** como vetor: camadas com caminhos/links maliciosos (travessia, *symlink*) | Desempacotar com ferramenta atual, validar a imagem, limitar tamanho e número de camadas |
| X3 | **Configuração da imagem pede privilégios** (usuário root, capacidades, volumes, dispositivos, setuid) | O executor **ignora** o que a imagem pede e impõe a própria configuração: sem capacidades, `no-new-privileges`, rootfs somente leitura, sem dispositivos |
| X4 | **Resultado como armazenamento hostil**: *symlink* na pasta de saída para arquivo da CVM (chaves, agente) | O agente lê a saída como dado: sem seguir links, só arquivos regulares, limite de tamanho |
| X5 | **Esgotamento de recursos** (disco, memória, *fork bomb*, camadas gigantes) | Limites de cgroup, disco e tempo; abortar o job |
| X6 | **Movimento lateral** pela NIC da CVM após um escape, contra a API sem autenticação dos outros planos (E1, A9) | mTLS entre planos; política de rede restritiva |
| X7 | **Canal encoberto**: a aplicação codifica o dataset em sinais visíveis ao operador (tempo, padrão de memória/E/S) | Limitação declarada (D-005); duração fixa e cotas reduzem a banda |
| X8 | **Vazar o dataset pelo resultado**: build adulterado faz o app gravar o dataset na saída, que vai ao comprador | Não é falha do executor: o canal legítimo. Exige **integridade do build** (proveniência, build reproduzido; direções 1 e 3) e/ou **política de saída** (direção 4) |

**O "sem rede" cobre quais?** Impede a exfiltração direta e o movimento lateral **a partir do
container** (X6), enquanto não houver escape. **Não** cobre X2, X3, X4, X5, X7 e X8, e cobre X1 só
parcialmente: após um escape o atacante cai na CVM, que **tem rede** (D-011). Os ataques que
passam pelo canal de resultado (X4, X8) ou por sinais observáveis (X7) contornam por
construção a ausência de rede.

**Classificação (2026-10-12):**
- **Classe A, ataques à CVM (X1–X6):** tratados por **endurecimento da CVM executora**, que faz
  parte da imagem medida (verificável por atestação). Viram requisitos de engenharia do
  executor: runtime atualizado, configuração imposta, desempacotamento validado, saída lida
  como dado, limites de recursos, mTLS. X1 mantém resíduo (falha de kernel ainda desconhecida).
- **Classe B, ataques por canais legítimos (X7, X8):** o app não precisa quebrar nada; o
  endurecimento da CVM é irrelevante. **Decisão D-014:** X8 fora de escopo (declarado);
  X7 limitação declarada. Não são tratados neste artigo.

**Observação central:** o caso X8 é a consequência mais séria de um build comprometido, porque o
dono do dataset aprovou uma aplicação e recebe outra. É o argumento mais forte para a
verificabilidade do build.

## Perguntas em aberto

- Quão restritivo pode ser o contrato (manifesto + gabarito) sem perder a generalização que
  motivou o OCI?
- Quais ecossistemas entram primeiro (Python, Node, R...) e como cada gabarito resolve
  dependências com hashes fixados?
- O que o builder compromete se for corrompido? Pelo desenho, uma imagem maliciosa **não**
  exfiltra o dataset (container sem rede), mas pode **adulterar o resultado**; a assinatura e
  a proveniência limitam isso.
- Builder de uso único + cache particionado: custo de boot e de re-download.

## Reforço à tese

O build como superfície de supply chain em pipelines confidenciais fica **mais forte** com OCI:
o problema real e generalizado é construir imagens de código não confiável. Liga-se às
direções 1 (proveniência) e 3 (build reproduzido).
