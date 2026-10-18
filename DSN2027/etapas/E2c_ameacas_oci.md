# E2c — Build e execução OCI: problemas de segurança e soluções

**Status:** decisões fechadas em 2026-10-18 (§10); nada medido. Consolida o que está espalhado em E1, E2 e E2b e acrescenta
três frentes novas: **garantia de execução sem rede**, **apps que precisam de rede** e **o Juiz
apontando tentativas de acesso externo**. Nada aqui foi medido.
**Decisões relacionadas:** D3, D4 ([DECISOES.md](../DECISOES.md)); Juiz em D2 ([JUIZ_IA.md](../JUIZ_IA.md)).
**Convenção:** cada problema tem um ID (R = rede na execução, X = outros da execução, S = canais
de saída, N = apps com rede, J = Juiz, B = build). Itens não conferidos levam **(a verificar)**.

## 0. Premissas

1. **Sem confidencialidade aninhada** (D4). Dois motivos:
   - *Suporte:* SNP não virtualiza dentro do convidado; TDX Partitioning só no Hyper-V/Azure e
     sem KVM upstream; Firecracker sem SNP/TDX (E2.1). Não escala para várias nuvens.
   - *Segurança:* mesmo com memória cifrada, o L0 media as saídas de VM e a paginação aninhada
     da L2 e vê mais eventos que numa CVM plana (Nested SEV, OSDI'26). O aninhamento piora a
     superfície de canal lateral em relação à confidencialidade normal.
   - Consequência: **uma CVM plana de uso único por job**, e o isolamento interno é feito no
     kernel do convidado (container reforçado), não por hipervisor.
2. **Duas ameaças ao mesmo tempo:** a aplicação maliciosa (quer tirar dado do dataset) e o
   operador da infraestrutura (quer ler dataset e código). O conluio entre os dois é tratado à parte.
3. **O único canal permitido de saída é o resultado legítimo**, julgado pelo Juiz e pelo portão
   (D2). Todo o resto (rede, logs, tempo, tamanho) precisa ser fechado ou quantizado.

## 1. Mapa do ciclo e onde estão os riscos

| Fase | Rede | Quem está presente | Riscos principais |
|---|---|---|---|
| B1 Build: fetch | sim, restrita | lockfile, imagens-base; **sem código, sem chave** | dependência maliciosa, escape do container de build (B1–B4) |
| B2 Build: assemble | **não** | código + dependências baixadas + chave de assinatura | adulteração do artefato, segredo nas camadas (B5–B8) |
| Entrega | canal mTLS | imagem cifrada + proveniência | imagem trocada, código lido em trânsito ou em repouso (B9, B10) |
| E1 Execução: preparação | sim, só o agente | agente, chaves, imagem, dataset | nenhum código não confiável rodando ainda |
| E2 Execução: app | **não** | app + dataset decifrado | exfiltração por rede (R1–R7), escape (X1), canais de saída (S1–S5) |
| E3 Execução: devolução | sim, só o agente | resultado cifrado | processo residual da app usando a rede (R5) |

## 2. Garantia de execução sem rede (R)

Objetivo: **nenhum byte sai da CVM durante a execução da app**, mesmo se a app chegar a root
no convidado, e a ausência de rede ser **verificável** pelo dono do dataset.
A solução é em camadas; cada uma cobre a falha da anterior.

| # | Problema | Solução | Camada |
|---|---|---|---|
| R1 | A app abre um socket para a internet | Container em **namespace de rede vazio** (`--network none`): só `lo` | Container |
| R2 | A app usa `lo` ou um socket Unix para falar com o agente ou outro serviço local que tenha rede | Agente **não escuta** em `lo` durante E2; nenhum socket Unix montado no container; namespace de IPC e PID próprios | Container |
| R3 | Falha do kernel do convidado alcançável por syscalls de rede (escape via pilha de rede) | **seccomp** negando `socket()` para `AF_INET`, `AF_INET6`, `AF_PACKET`, `AF_NETLINK`, `AF_VSOCK` (só `AF_UNIX`); **gVisor (runsc)** com rede desligada, que tira a pilha de rede do kernel do caminho; Landlock com regras de TCP como reforço (Linux ≥ 6.7, **a verificar** no kernel da CVM) | Syscall |
| R4 | Escape do container vira root na CVM e usa a NIC | **Corte temporal:** o agente derruba a interface (ou desassocia o driver) **antes** de iniciar a app e só a religa **depois** que o cgroup do job estiver vazio (`cgroup.events: populated 0`). Enquanto existe processo da app, não existe rede | CVM |
| R5 | Root obtido em E2 deixa um processo escondido esperando a rede voltar em E3 | (a) imagem da CVM com **kernel lockdown**, sem carga de módulos, rootfs somente leitura e sem disco persistente; (b) em E3, **nftables com egress só para o plano de controle**, regra por cgroup/UID do agente, com mTLS; (c) a CVM é destruída logo após E3; (d) **opção forte (a avaliar):** a devolução sai por outra via que não a NIC da CVM de execução (ver nota abaixo) | CVM |
| R6 | Rotas fora da NIC: IMDS da nuvem (`169.254.169.254`), vsock/hvsock, porta serial, dispositivos virtio | Sem dispositivos no container; IMDS bloqueado no nftables da CVM; `AF_VSOCK` negado no seccomp; desabilitar hvsock/vsock no convidado se não for usado **(a verificar no Azure)** | CVM |
| R7 | App sem conluio com o operador manda dado para um servidor qualquer | Egress da CVM restrito também **no firewall da nuvem** (NSG) ao plano de controle. Não protege contra operador em conluio, mas fecha o caso comum de graça | Nuvem |
| R8 | O dono do dataset precisa **confiar** que tudo isso foi aplicado | A política (perfil seccomp, flags do runtime, regras nftables, script do agente) faz parte da **imagem medida** da CVM; o recibo de execução carrega o hash da política; contadores da NIC (`tx_bytes`) antes/depois de E2 entram no recibo como evidência (não como prova, pois root os altera). Atestação implícita (D3) | Prova |

**Nota sobre R5(d).** Se o resultado sair por outra CVM, a CVM de execução nunca religa a
rede depois de rodar código não confiável. Caminhos possíveis: disco efêmero cifrado
transferido para uma CVM de devolução, ou a CVM só se desliga e o agente da plataforma lê o
volume de saída **(viabilidade a verificar no Azure)**. Custo: mais uma peça no ciclo. Para o
MVP basta R1–R4 + R5(a–c); R5(d) fica como reforço.

**O que sobra (limitação declarada):** canais laterais da CVM observáveis por um operador em
conluio (uso de CPU, padrão de acesso à memória, tempo), já fora do escopo (D3).

## 3. Outros problemas da execução (X), a partir de E2b.5

| # | Problema | Solução |
|---|---|---|
| X1 | Escape de container | gVisor ou runc/crun rootless atualizado; **usuário sem root** dentro do container; namespace de usuário; CVM de uso único |
| X2 | Camadas maliciosas (links, caminhos `../`, bombas de descompressão) | Desempacotar com ferramenta atual fora do container, validar caminhos, limitar tamanho e número de camadas |
| X3 | Imagem pede privilégios (caps, volumes, dispositivos, usuário root) | O agente **ignora a config da imagem**, exceto `Entrypoint/Cmd/WorkingDir/Env`; impõe sem capacidades, `no-new-privileges`, rootfs somente leitura, `/tmp` em tmpfs limitado, sem dispositivos |
| X4 | Saída como arquivo hostil (links, FIFOs, tamanho enorme) | Ler a saída como dado: só arquivos regulares, sem seguir links, limite de tamanho e de quantidade |
| X5 | Esgotamento de recursos | Limites de cgroup (memória, CPU, PIDs), disco e tempo; abortar o job |
| X6 | Movimento lateral entre planos | mTLS entre planos (fecha A9); agente sem porta aberta durante E2 |
| X7 | Imagem e dataset legíveis pelo operador | Imagem e dataset cifrados em repouso e em trânsito; chave liberada só para a CVM (atestação implícita, D3); disco só em tmpfs ou cifrado |
| X8 | Executor roda uma imagem diferente da julgada | Verificação de proveniência e digest (E2b.4); veredito do Juiz vinculado ao digest (JUIZ_IA §1) |

## 4. Canais de saída secundários (S)

Com a rede fechada, a app ainda pode codificar dado em tudo que o comprador vê além do resultado.

| # | Canal | Solução |
|---|---|---|
| S1 | **Logs / stderr** devolvidos ao comprador | Não devolver logs da app; se forem necessários, tratar como saída e passar pelo portão |
| S2 | **Código de saída** e mensagens de erro (até 8 bits por execução) | Devolver só sucesso/falha |
| S3 | **Tempo de execução** | Reportar tempo arredondado ou em faixas; opcional: completar até o fim da faixa |
| S4 | **Tamanho da saída** | Limite de tamanho por tag; opcional: preencher até faixas fixas |
| S5 | **Várias execuções** (ataque de diferença) | Orçamento de execuções por compra e checagem entre saídas (JUIZ_IA L4) |

S1 e S2 são baratos e entram no executor mínimo; S3–S5 ficam como desejável/limitação.

## 5. Apps que precisam de rede (N)

Há aplicações legítimas que consultam um serviço externo (ex.: API de IA). Abrir a rede
reabre o canal que o desenho fecha: o que vai na requisição é vazamento para o provedor e,
se a chave for do desenvolvedor, para o desenvolvedor (painel de logs) ou para um endpoint
dele disfarçado de API.

| # | Problema | Opções |
|---|---|---|
| N1 | App legítima precisa de um serviço externo | **(a) MVP: proibido.** Rede zero; app que precisa de rede é reprovada (com motivo claro). **(b) Capacidade mediada:** o container continua sem rede e recebe um **socket Unix** para um *broker* da plataforma, que fala com o serviço; o broker usa **chave da plataforma**, aplica a lista de destinos permitida pelo dono do dataset e registra o corpo das requisições. **(c) Serviço dentro da CVM:** modelo aberto rodando ao lado (exige GPU confidencial **a verificar**); rede zero mantida |
| N2 | O conteúdo da requisição vaza dado | Na opção (b), a requisição é **mais uma saída**: passa pelo portão (L4) e o Juiz a trata como sumidouro, igual ao resultado |
| N3 | O dono do dataset não sabe que haverá rede | Tag explícita do dono (ex.: `rede:api-ia:<provedor>`); sem a tag, vale rede zero |

**Recomendação:** (a) no MVP e no artigo; (b) descrita como extensão na discussão, porque
preserva a garantia de "container sem rede" e encaixa no modelo de tags.

## 6. O Juiz verificando acesso externo (J)

Mesmo sem rede na execução, **tentar** acessar a rede é evidência: num processamento de dados
sem finalidade de rede, uma tentativa de conexão é o sinal mais claro de intenção de exfiltrar.

| # | Problema | Solução |
|---|---|---|
| J1 | Detectar a intenção no código | **L1 estática:** imports e chamadas de rede (`socket`, `requests`, `urllib`, `httpx`, `subprocess` com `curl`/`wget`, DNS), URLs e IPs literais (inclusive ofuscados), dependências com capacidade de rede, binários de rede na imagem |
| J2 | Detectar a tentativa ao rodar | **L2 dinâmica:** a plataforma roda a app com dados sintéticos em dois modos: (i) **seccomp em modo log/notificação**, registrando cada `socket()`/`connect()` negado; (ii) **sumidouro de rede falso** (*sinkhole*): uma rede interna isolada com DNS e HTTP(S) falsos que respondem a tudo e registram destino e conteúdo. O modo (ii) revela o que a app mandaria; como os dados são sintéticos, dá para procurar o **canário dentro do tráfego** |
| J3 | App só tenta a rede com dados reais (gatilho) | Em produção a tentativa é negada pelo seccomp e **registrada no recibo**; o portão (L4) marca a execução e o dono decide |
| J4 | App legítima que usa rede (N1) | O Juiz confere destinos e conteúdo contra a tag do dono; destino fora da lista ou canário no tráfego reprova |
| J5 | Como entra no veredito | Sem tag de rede: tentativa de rede ⇒ **reprovado** (ou inconclusivo, se só estática e fraca); com tag: destino fora da lista ⇒ reprovado. A evidência vai para L3 no relatório de L2 |

O sinkhole roda **na plataforma**, não dentro do Juiz (JUIZ_IA §8, ponto de desenho), e é ele
próprio isolado: nenhuma rota real para fora. Para o benchmark, `t1_network_exfil` vira um
caso positivo de J2, e cada tarefa ganha uma variante "vaza pela rede" ao lado das variantes
que vazam pela saída.

## 7. Build (B)

| # | Problema | Solução |
|---|---|---|
| B1 | Dependência maliciosa exfiltra o **código** durante o build (A10) | Duas fases (E2b.3): o código só chega na fase sem rede |
| B2 | Rede da fase de fetch aberta para a internet inteira | Egress só por um **proxy com lista de registries** (PyPI, registry das imagens-base) que registra o que foi baixado; o registro vira `materials` da proveniência |
| B3 | Escape do container na fase de fetch alcança chave e agente | Opção A (mesma CVM, entrega tardia do código e da chave) ou B (CVM de fetch separada) (E2b.3) |
| B4 | Pacote trocado (typosquatting, *dependency confusion*, versão mutável) | Lockfile com hashes recomendado; `FROM` por digest; SBOM gerado no builder (ex.: syft) e varredura de vulnerabilidades conhecidas (ex.: osv-scanner/grype) **(ferramentas a escolher)**; SBOM vai para o Juiz |
| B5 | Dependência adultera o artefato na fase sem rede | Integridade, não sigilo: assinatura + reprodução por N builders (E2b.4) |
| B6 | Segredo do desenvolvedor (token de repositório privado) fica numa camada | Montagem de segredo do motor de build, nunca `ARG`/`ENV`; varredura de segredos antes de assinar |
| B7 | Imagem não reprodutível impede conferir o digest | Timestamps fixos (`SOURCE_DATE_EPOCH`), ordem fixa, bases por digest; `reproducible: não` declarado quando falhar |
| B8 | Cache compartilhado envenenado (A12) | Cache por dono, ou sem cache entre donos no MVP |
| B9 | Imagem trocada entre builder e executor | Proveniência assinada + digest no ledger, verificados pelo executor (E2b.4) |
| B10 | Código do desenvolvedor legível em trânsito ou em repouso (IPFS) | Imagem cifrada com chave por ativo, como o dataset (fecha A2 para a app) |
| B11 | Motor de build com rede por fase | BuildKit aceita `--network=none` no build e `RUN --network=none` por instrução; Buildah tem `--network none`; Kaniko arquivado. **(a verificar nas versões usadas)** |

## 8. Como provar (suíte de ataques)

| Teste | Problemas cobertos | Resultado esperado |
|---|---|---|
| T1 exfiltração de rede (`t1_network_exfil`) | R1, R3, J2 | Conexão negada; tentativa no recibo; Juiz reprova |
| T1-root: app com escape simulado (root na CVM) tenta a NIC em E2 e espera E3 | R4, R5 | Interface derrubada em E2; egress de E3 só para o plano de controle |
| T1-IMDS / vsock | R6 | Negado |
| T1b escape de filesystem (`t1b_fs_escape`) | X2, X3, X4 | Contido |
| T2 dependência maliciosa (`t2_malicious_dep`) no build | B1, B2 | Fase com rede não tem código; fase com código não tem rede |
| T3 limpeza / T4 entre CVMs | X1, P3 | Nada sobrevive ao job |
| Canais secundários: app que codifica bits em exit code, stderr e tempo | S1–S3 | Comprador recebe só sucesso/falha e tempo em faixa |

## 9. Prioridade para o DSN

| Prioridade | Itens |
|---|---|
| **Obrigatório (executor mínimo)** | R1, R2, R3 (seccomp), R4, S1, S2, X3, X4, X5; J1 e J2 (modo seccomp) no Juiz |
| **Desejável** | gVisor (R3), R5(a–c), R6, R7, J2 com sinkhole, build em duas fases (B1–B3), B4, B6 |
| **Discussão / limitação** | R5(d), N1(b,c), S3–S5, reprodução com N builders (B5, B7), canais laterais |

## 10. Decidido em 2026-10-18 (D2, D4)
1. Rede no MVP: **opção (a)**, rede zero; o broker (b) entra só na discussão.
2. Tentativa de rede sem tag: **reprovado**; sinal só estático e fraco: inconclusivo.
3. L2 detecta por **seccomp em modo log** (J2-i); o sinkhole (J2-ii) fica desejável.
4. Obrigatórias na D4: **R1–R4**; R5–R7 desejáveis.

## 11. Pendências
- Verificar no Azure: derrubar a NIC com o job rodando e religar; hvsock; lockdown do kernel.
