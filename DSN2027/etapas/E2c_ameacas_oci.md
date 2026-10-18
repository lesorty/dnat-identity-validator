# E2c — Build e execução OCI: problemas de segurança e soluções

**Status:** decisões fechadas em 2026-10-18 (§10); nada medido. Consolida o que está espalhado
em E1, E2 e E2b e acrescenta três frentes novas: **CVM que só fala com o DNAT**, **apps que
precisam de rede** e **o Juiz apontando tentativas de acesso externo**.
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
| E1 Execução: preparação | CVM: **só o DNAT**, de saída | agente puxa imagem, dataset e chaves | nenhum código não confiável rodando ainda |
| E2 Execução: app | app: **nenhuma**; CVM: só o DNAT | app + dataset decifrado | exfiltração por rede (R1–R8), escape (X1), canais de saída (S1–S5) |
| E3 Execução: devolução | CVM: **só o DNAT** | resultado cifrado | app que virou root tentando outro destino (R5–R8) |

## 2. Execução: a CVM só fala com o DNAT (R)

**Objetivo:** a app não alcança **nada** fora do DNAT, mesmo que vire root no espaço de
usuário da CVM, e o dono do dataset consegue conferir a política aplicada.

**Duas ideias de base**
- **Modelo de puxar:** a CVM de execução **nunca recebe requisição**. O agente sobe, abre uma
  conexão de saída por mTLS ao DNAT e **puxa** o job (imagem e dataset cifrados, chaves). Não há
  porta aberta na CVM em nenhum momento.
- **Configurar no boot e jogar fora o poder de mudar:** uma regra de firewall sozinha não
  basta, porque root a apaga. A regra "só o DNAT" é carregada pelo PID 1 da imagem medida e,
  em seguida, **ninguém na CVM mantém a capacidade de alterá-la**.

**Por que tirar o terminal não basta:** escapar do container é um exploit de kernel ou de
runtime executado pelo código da própria app (Python faz qualquer syscall; a imagem traz o
binário que quiser). Tirar shell, SSH e console da CVM é endurecimento (R6), não impede o escape.

| # | Problema | Solução | Camada |
|---|---|---|---|
| R1 | A app abre um socket para fora | Container em **namespace de rede vazio** (`--network none`): só `lo` | Container |
| R2 | A app fala com algum serviço local que tenha rede | Modelo de puxar: nada escuta na CVM; nenhum socket Unix montado no container; namespaces de IPC e PID próprios | Container |
| R3 | A app vira root (escape do container) | **Ninguém é root no container:** usuário comum, namespace de usuário, `no-new-privileges`, sem setuid, sem capacidades; **seccomp** mínimo, negando `socket()` para `AF_INET`, `AF_INET6`, `AF_PACKET`, `AF_NETLINK`, `AF_VSOCK`; **gVisor (runsc)**: a app fala com um kernel em espaço de usuário, e o "root" dela é root no sandbox; para chegar à CVM precisa quebrar o gVisor **e** o kernel, passando pelo filtro de syscalls do gVisor | Container |
| R4 | *(rebaixada a desejável)* Derrubar a interface enquanto houver processo da app | Root a religa; com R5 deixa de ser necessária. Fica só como camada extra | CVM |
| R5 | Root em espaço de usuário na CVM muda firewall ou interface | **PID 1 no boot**, antes de qualquer outro processo: nftables com saída só para `IP_DO_DNAT:443` (IP fixo, **sem DNS**, que é canal clássico de exfiltração), IMDS (`169.254.169.254`) e vsock/hvsock bloqueados, entrada fechada. Em seguida **remove do bounding set** de todos os processos `CAP_NET_ADMIN`, `CAP_NET_RAW`, `CAP_BPF`, `CAP_SYS_MODULE` e `CAP_SYS_RAWIO`. O bounding set nunca cresce de volta: root em espaço de usuário não mexe mais em interface, firewall, BPF ou módulos. O agente não precisa delas (TLS de saída não exige) | CVM |
| R6 | Root altera o kernel ou persiste algo | **Kernel lockdown** (modo confidencialidade), carga de módulos desligada, rootfs somente leitura com **dm-verity**, sem disco persistente; imagem mínima **sem shell, SSH nem console serial** (console serial da nuvem desabilitado) | CVM |
| R7 | A app usa a chave do agente para mandar dados ao próprio DNAT | mTLS com **certificado do DNAT fixado** na imagem (só o DNAT verdadeiro); o DNAT trata **tudo** o que recebe da CVM como saída, que passa pelo portão e pelo Juiz. Mandar ao DNAT não vaza nada além do canal legítimo | DNAT |
| R8 | App com **exploit de kernel** desfaz R5 e R6 por dentro | A mesma regra repetida **fora da CVM**: sub-rede privada sem IP público, sem NAT e sem saída padrão para a internet (sub-rede privada do Azure **a verificar**); NSG liberando só o DNAT | Nuvem |
| R9 | O dono do dataset precisa confiar que tudo foi aplicado | Regras, perfil seccomp, flags do runtime e lista de capacidades fazem parte da **imagem medida**; o recibo de execução leva o hash da política. Atestação implícita (D3) | Prova |

**Quem consegue o quê**

| Atacante | Resultado |
|---|---|
| App dentro do container | Sem rede (R1–R3) |
| App que vira root em espaço de usuário na CVM | **Sem rede além do DNAT**: não muda firewall nem interface (R5, R6); o que mandar ao DNAT vira saída (R7) |
| App com execução de código no kernel da CVM | Desfaz tudo dentro da CVM; segura só a rede da nuvem (R8) |
| Operador em conluio com a app | Abre a rede da nuvem; **limitação declarada** |

**O que sobra (limitação declarada):** exploit de kernel somado a conluio do operador, e os
canais laterais da CVM observáveis pelo operador (CPU, memória, tempo), já fora do escopo (D3).

**(a verificar)**
- O runtime, ao criar o namespace de usuário do container, não recupera capacidades que
  alcancem a rede principal da CVM (`CAP_NET_ADMIN` no namespace do container só vale para a
  rede vazia dele).
- O gVisor com `--network=none` roda sem as capacidades removidas em R5.
- Lockdown, dm-verity e desligamento de hvsock na imagem de CVM do Azure.

## 3. Outros problemas da execução (X), a partir de E2b.5

| # | Problema | Solução |
|---|---|---|
| X1 | Escape de container | R3 (gVisor, usuário sem root, namespace de usuário, seccomp); CVM de uso único |
| X2 | Camadas maliciosas (links, caminhos `../`, bombas de descompressão) | Desempacotar com ferramenta atual fora do container, validar caminhos, limitar tamanho e número de camadas |
| X3 | Imagem pede privilégios (caps, volumes, dispositivos, usuário root) | O agente **ignora a config da imagem**, exceto `Entrypoint/Cmd/WorkingDir/Env`; impõe sem capacidades, `no-new-privileges`, rootfs somente leitura, `/tmp` em tmpfs limitado, sem dispositivos |
| X4 | Saída como arquivo hostil (links, FIFOs, tamanho enorme) | Ler a saída como dado: só arquivos regulares, sem seguir links, limite de tamanho e de quantidade |
| X5 | Esgotamento de recursos | Limites de cgroup (memória, CPU, PIDs), disco e tempo; abortar o job |
| X6 | Movimento lateral entre planos | mTLS entre planos (fecha A9); CVM sem porta aberta (modelo de puxar, R2) |
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
| B2 | Rede da fase de fetch aberta para a internet inteira | **Sem lista de imagens ou registries aprovados**: a CVM de fetch não tem código nem chave, então pode buscar em qualquer registry ou índice público. Toda a saída passa por um **proxy de registro** que anota cada download (vira `materials` da proveniência) e bloqueia só faixas privadas, IMDS e a rede interna da plataforma |
| B3 | Escape do container na fase de fetch alcança chave e agente | **Opção B** (E2b.3): CVM de fetch própria, que fala só com o proxy e o DNAT e nunca vê código nem chave; a CVM de assemble tem o desenho da execução (§2: só DNAT, R5–R8, gVisor) e confere as dependências recebidas pelos hashes. A opção A (cortar a rede depois do fetch) foi descartada pelo mesmo motivo da R4: root religa |
| B4 | Pacote trocado (typosquatting, *dependency confusion*, versão mutável) | Lockfile com hashes recomendado; qualquer `FROM` aceito, com tag resolvida para digest pelo builder e registrada; SBOM gerado no builder (ex.: syft) e varredura de vulnerabilidades conhecidas (ex.: osv-scanner/grype) **(ferramentas a escolher)**; SBOM vai para o Juiz |
| B5 | Dependência adultera o artefato na fase sem rede | Integridade, não sigilo: assinatura + reprodução por N builders (E2b.4) |
| B6 | Segredo do desenvolvedor (token de repositório privado) fica numa camada | Montagem de segredo do motor de build, nunca `ARG`/`ENV`; varredura de segredos antes de assinar |
| B7 | Imagem não reprodutível impede conferir o digest | Timestamps fixos (`SOURCE_DATE_EPOCH`), ordem fixa, bases pelo digest registrado no fetch; `reproducible: não` declarado quando falhar |
| B8 | Cache compartilhado envenenado (A12) | Cache por dono, ou sem cache entre donos no MVP |
| B9 | Imagem trocada entre builder e executor | Proveniência assinada + digest no ledger, verificados pelo executor (E2b.4) |
| B10 | Código do desenvolvedor legível em trânsito ou em repouso (IPFS) | Imagem cifrada com chave por ativo, como o dataset (fecha A2 para a app) |
| B11 | Motor de build com rede por fase | BuildKit aceita `--network=none` no build e `RUN --network=none` por instrução; Buildah tem `--network none`; Kaniko arquivado. **(a verificar nas versões usadas)** |

## 8. Como provar (suíte de ataques)

| Teste | Problemas cobertos | Resultado esperado |
|---|---|---|
| T1 exfiltração de rede (`t1_network_exfil`) | R1, R3, J2 | Conexão negada; tentativa no recibo; Juiz reprova |
| T1-root: processo root em espaço de usuário na CVM tenta apagar o nftables, subir interface, carregar módulo e conectar fora do DNAT | R5, R6 | Todas as operações negadas (`EPERM`) |
| T1-kernel (simulado): regra da CVM removida por fora, conexão a destino externo | R8 | Barrada pela sub-rede/NSG |
| T1-IMDS / vsock / DNS | R5 | Negado |
| T1b escape de filesystem (`t1b_fs_escape`) | X2, X3, X4 | Contido |
| T2 dependência maliciosa (`t2_malicious_dep`) no build | B1, B2 | Fase com rede não tem código; fase com código não tem rede |
| T3 limpeza / T4 entre CVMs | X1, P3 | Nada sobrevive ao job |
| Canais secundários: app que codifica bits em exit code, stderr e tempo | S1–S3 | Comprador recebe só sucesso/falha e tempo em faixa |

## 9. Prioridade para o DSN

| Prioridade | Itens |
|---|---|
| **Obrigatório (executor mínimo)** | R1–R3 (com gVisor), R5, R6 (lockdown, sem módulos, imagem mínima), R7, R8, S1, S2, X3, X4, X5; J1 e J2 (modo seccomp) no Juiz |
| **Desejável** | R4, dm-verity (R6), J2 com sinkhole, build em duas fases (B1–B3), B4, B6 |
| **Discussão / limitação** | N1(b,c), S3–S5, reprodução com N builders (B5, B7), exploit de kernel + conluio, canais laterais |

## 10. Decidido em 2026-10-18 (D2, D4)
1. Rede no MVP: **opção (a)**, rede zero; o broker (b) entra só na discussão.
2. Tentativa de rede sem tag: **reprovado**; sinal só estático e fraco: inconclusivo.
3. L2 detecta por **seccomp em modo log** (J2-i); o sinkhole (J2-ii) fica desejável.
4. Rede da execução (revisto no mesmo dia): **a CVM só fala com o DNAT**: modelo de puxar,
   regra no boot + remoção de capacidades, lockdown, gVisor e sub-rede/NSG obrigatórios;
   derrubar a interface (R4) rebaixado a desejável, porque root a religa.
5. Build (B3): **opção B**, uma CVM de fetch (só proxy e DNAT, sem código nem chave) e uma de
   assemble com o desenho da execução (só DNAT). A opção A cai pelo mesmo motivo da R4.
6. Imagens: **qualquer imagem-base e qualquer registry**, sem lista de aprovadas. O proxy do
   fetch só anota (não filtra destinos públicos); o builder fixa o digest e o registra.

## 11. Pendências
- Os três itens **(a verificar)** do §2.
- Medir o custo da opção B do build (CVM extra e transferência das dependências).
- Verificar no Azure: sub-rede privada sem saída padrão, NSG só para o DNAT, console serial desabilitado.
