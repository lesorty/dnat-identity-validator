# Etapas da discussão

Pedido de origem (2026-10-12): verificar as ideias no código; registrar as direções 1, 2 e 3;
avaliar tornar o sistema distribuído para remover a confiança em um operador ou provedor
único; e resolver o problema do Firecracker, que hoje não roda dentro de computação
confidencial. Cada etapa termina com um documento em `resultados/`.

**Mudança de rumo (2026-10-17, D-031, D-032):** com o orientador, decidiu-se **não distribuir**
o sistema (E3 arquivada). O foco passa a ser OCI (E2, E2b) e, como contribuição principal, o
**Juiz de IA** (E4). Pretensões do artigo em [ARTIGO.md](ARTIGO.md).

| # | Etapa | Pergunta que responde | Entregável | Status |
|---|---|---|---|---|
| E0 | Organização | Onde e como registrar ideias e decisões? | Este diretório, `README.md`, `DECISOES.md` | ✅ concluída (2026-10-12) |
| E1 | Auditoria do código | O que o código realmente garante hoje, frente às direções 1–3? | `resultados/E1_auditoria_codigo.md` | ✅ concluída (2026-10-12) |
| E2 | Isolamento confidencial por job | Como substituir ou complementar o Firecracker para ter isolamento por job **e** confidencialidade frente ao operador? | `resultados/E2_isolamento_confidencial.md` | ✅ decisões fechadas (D-017); falta só medir (E2.4, depois das decisões) |
| E2b | Build seguro de imagens OCI | Como construir imagens OCI de código não confiável sem perder as garantias do build atual (ext4)? | `resultados/E2b_build_oci.md` | 🔄 decisões fechadas (D-012 a D-015); duas fases e assinatura especificadas em rascunho; faltam verificações (a verificar) |
| E3 | Descentralização | Distribuir o sistema entre operadores e provedores aumenta a confiança de fato? O que vale e o que não vale fazer? | `resultados/E3_descentralizacao.md` | 🗄️ arquivada (D-031): desenho concluído, **não será seguido** |
| E4 | Juiz de IA (verificação por agentes) | Como um Juiz de IA, executado como aplicação do sistema, verifica de forma eficaz e barata se uma aplicação é segura e não vaza dados (D-016, D-032)? | `resultados/E4_verificacao_agentes.md` | 🔄 **contribuição principal** (D-032); trabalho centralizado em `JUIZ_IA.md` |
| E5 | Síntese | Qual é a arquitetura-alvo v2, a tese e o roteiro (SAC → DSN), considerando E1, E2, E2b e E4? | `resultados/E5_arquitetura_alvo.md` + decisões em `DECISOES.md` | ⏳ |

## Escopo de cada etapa pendente

### E2 — Isolamento confidencial por job (o problema do Firecracker)
- Estado da arte: virtualização aninhada em CVMs (AMD SEV-SNP, Intel TDX) nas nuvens públicas;
  TDX *TD Partitioning*; SNP VMPLs e SVSM (COCONUT-SVSM); Kata Containers e Confidential
  Containers (CoCo), inclusive *peer pods*; Azure Confidential Containers (ACI/AKS);
  AWS (SEV-SNP em EC2, Nitro Enclaves); GCP Confidential VMs e Confidential Space;
  sandboxes sem virtualização dentro da CVM (gVisor, Landlock/seccomp, Wasm).
- Para cada opção: garantia frente ao operador, garantia entre jobs, TCB, custo de boot,
  disponibilidade real hoje, esforço de implementação no protótipo.
- Saída: recomendação de 1–2 caminhos e o que medir.

### E3 — Descentralização
- Ameaças que restam **mesmo com** CVM: operador único (disponibilidade, censura, rollback,
  escolha de qual CVM recebe a chave), fabricante único (bugs de TEE: CacheWarp, Heracles,
  BadRAM, WeSee/Heckler…), provedor de nuvem único (firmware, chaves de assinatura).
- Mecanismos: atestação verificada on-chain; liberação de chave por limiar (threshold/DKG)
  entre comitê de CVMs; execução replicada heterogênea (AMD + Intel, nuvens diferentes);
  logs de transparência; consenso apenas no plano de controle.
- Trabalhos e sistemas a verificar: Ekiden/Oasis, Secret Network, Phala/dstack, CCF
  (Microsoft), Marlin Oyster, Flashbots SUAVE/TEE-builders, Automata (verificação on-chain de
  atestação), Trustee/KBS (CoCo), Sigstore/Rekor.
- Saída: o que realmente melhora a confiança (e o que só adiciona custo), com prós, contras
  e dificuldade técnica.

### E4 — Verificação por agentes de IA
- Caso: código conhecido e dados privados; o código é verificável, mas o esforço é proibitivo.
- Propriedades de segurança declaradas pelo usuário (não vazar dados, direta ou indiretamente).
- Evolui a varredura de saída da E2b. Só planejamento por ora; perguntas em `brainstorm/03_agentes_verificacao.md`.

### E5 — Síntese
- Arquitetura-alvo v2 combinando E1–E4 com as direções 1–3.
- Nova formulação de tese e de contribuições.
- O que entra no SAC (texto) e no DSN (código + medição), com estimativa de esforço.
- Decisões a aprovar, registradas em `DECISOES.md`.
