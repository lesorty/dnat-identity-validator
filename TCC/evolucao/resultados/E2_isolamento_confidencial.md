# E2 — Isolamento confidencial por job (o problema do Firecracker)

**Status:** PARCIAL (rascunho de 2026-10-12). E2.1–E2.3 discutidos; falta medir (E2.4).
**Decisões relacionadas:** D-005 (CVM por job, sem aninhamento), D-006 (warm pool de uso único).
**Pré-requisito lido:** [E1 — auditoria](E1_auditoria_codigo.md), achados A13 e A14.

## E2.1 — O problema

**Ameaças a cobrir ao mesmo tempo:** (i) aplicação maliciosa e (ii) operador de infraestrutura.

**Estado atual (E1, A14):** na CVM o sistema roda em modo direto, sem Firecracker e sem
isolamento entre jobs. O Firecracker não roda na CVM por falta de virtualização aninhada.

**Por que a virtualização aninhada não é a resposta, mesmo quando disponível (D-005):**
- Com a memória cifrada, o conteúdo da L2 não é lido pelo L0. Mas o L0 media saídas de VM e
  paginação aninhada, então observa um fluxo de eventos mais rico. O paper Nested SEV
  reconhece que o L0 observa as interações L1↔L2 e os padrões de acesso, e deixa canais
  laterais fora de escopo (Takiguchi & Kourai, OSDI'26, seção de modelo de ameaça).
- **Não verificado:** que a reconstrução de informação fica mais fácil com o tempo de execução
  no caso aninhado. É inferência plausível; falta referência.
- Consequência: tratar o aninhamento como algo a evitar, não como lacuna a fechar.

**O que existe hoje em termos de suporte (verificado em fontes):**
- **SEV-SNP:** convidados SNP não suportam virtualização (patches de SNP aninhado no Hyper-V,
  [RFC](https://lkml.iu.edu/hypermail/linux/kernel/2302.1/05249.html)). O patch da Microsoft
  protege só a L2; Hecate e OpenHCL protegem L1 e L2, mas só uma L2 por L1 (VMPL, sem
  virtualização de MMU) ([OSDI'26](https://www.usenix.org/system/files/osdi26-takiguchi.pdf)).
- **TDX:** TD Partitioning permite até 4 VMs num TD, com uma L2 não modificada por L1;
  plataformas citadas: Hyper-V e Azure DCesv5/ECesv5
  ([Intel](https://www.intel.com/content/www/us/en/developer/articles/technical/tdx-performance-isolated-partitioned-vms.html)).
  Suporte no KVM upstream: **não encontrado**.
- **Firecracker com SNP/TDX:** não encontrei issue nem suporte. Cloud Hypervisor tem SNP, mas a
  documentação principal diz que é só em MSHV.
- **GCP:** não confirmei se há virtualização aninhada em CVMs.

## E2.2 — Opções

| Opção | Descrição | Observações / pontos em aberto |
|---|---|---|
| **A. CVM efêmera por job** | Uma CVM por execução, de uso único; com *warm pool* (D-006) | Latência de provisionamento a medir. Rede negada tem de ser imposta **dentro do guest** (o firewall da nuvem é do operador) |
| **B. Azure Confidential Containers** | Child VM SNP por pod num nó L1 **não confidencial** ([docs AKS](https://learn.microsoft.com/en-in/azure/aks/confidential-containers-overview)) | Só Azure; hipervisor media a L2 (contra D-005); sem números de latência; atestação da L2 **(a verificar)** |
| **C. CoCo *peer pods*** | Uma CVM por pod via API da nuvem, com Kata e atestação ([arquitetura](https://github.com/confidential-containers/cloud-api-adaptor/blob/v0.8.0/docs/architecture.md)) | Parecida com a A, mas exige Kubernetes e container OCI como artefato; a própria documentação diz ser menos adequada a cargas pequenas e de curta duração; sem benchmarks públicos de latência. Detalhes na seção "CoCo peer pods" abaixo |
| **D. AWS Nitro Enclaves** | VM sem rede, só vsock, atestação por PCR ligada ao KMS | Confia na AWS; memória não cifrada pelo TEE **(a verificar)**; hipervisor media a enclave |
| **E. Sandbox sem virtualização na CVM** | gVisor, seccomp/Landlock, Wasm | Fronteira mais fraca que KVM; Wasm quebra wheels nativas. **Complemento** da A, não substituto |
| **F. VMPL/SVSM, TD partitioning, Nested SEV** | Mecanismos de pesquisa ou de uma só L2 | Não são produção para o nosso caso |

**Hipótese de trabalho:** A + E (CVM por job, com sandbox interno como defesa em profundidade).

### Desenho de rede da opção A (a especificar)
Três fases no guest: (1) com rede, para atestar e buscar ativos e chaves; (2) **sem rede**, com
a aplicação rodando; (3) com rede, só para devolver o resultado cifrado. Se a aplicação chegar a
root no guest, pode religar a rede; por isso o sandbox interno é defesa em profundidade, e a
imagem medida deve impedir a reconfiguração de rede pela aplicação.

### Build plane
O código do desenvolvedor também é segredo (E1, A10), e o Firecracker também não roda na CVM de
build. A decisão de E2 vale para os dois planos.

## E2.3 — Critérios de comparação

1. Garantia frente ao operador (conteúdo)
2. **Superfície de observação do hipervisor** (canal lateral; critério novo, D-005)
3. Garantia entre jobs / contra aplicação maliciosa
4. TCB
5. Latência de provisionamento e de execução
6. Custo (inclui CVMs ociosas do pool)
7. Disponibilidade real por nuvem
8. Esforço de implementação no protótipo
9. Portabilidade entre nuvens

## CoCo peer pods — o que é (verificado nas fontes)

**Ideia:** um pod do Kubernetes roda dentro de **uma VM própria, criada pela API da nuvem**,
em vez de rodar num container do nó ou numa microVM aninhada. A VM é irmã do nó (primeiro
nível), não convidada dentro dele, e é uma CVM (SEV-SNP ou TDX). Por isso não precisa de
virtualização aninhada nem de bare metal.

**Componentes** ([arquitetura](https://github.com/confidential-containers/cloud-api-adaptor/blob/v0.8.0/docs/architecture.md)):
- No nó (**fora da TCB**): `containerd-shim-kata-v2` e o `cloud-api-adaptor`, que traduz o ciclo
  de vida do sandbox em chamadas à API da nuvem e abre um túnel VXLAN até a VM do pod.
- Na VM do pod (**dentro da TCB**): `kata-agent`, `agent-protocol-forwarder` e o
  *attestation agent*.
- Atestação: modelo IETF RATS. O *attestation agent* é o *attester*, o KBS (*Key Broker
  Service*) o *relying party* e o *attestation service* o *verifier*. O **Trustee** reúne KBS e
  verificador e fica num ambiente confiável **separado** do cluster que roda a carga
  ([Red Hat](https://docs.redhat.com/en/documentation/openshift_sandboxed_containers/1.12/html/deploying_red_hat_build_of_trustee_for_workloads_running_on_microsoft_azure/trustee-discover_azure-trustee)).
  Na Azure ele suporta CVMs SEV-SNP e TDX, e há registro de GA em OpenShift auto-gerenciado
  (issue KATA-3746; confirmar nas notas de versão).

**Ciclo:** criar o pod → o adaptor cria a VM pela API da nuvem e o túnel → os comandos
(`CreateContainer` etc.) vão pelo túnel até o `kata-agent` → apagar o pod apaga a VM.

**Pontos que pesam para nós:**
- **Kubernetes é obrigatório** (nós, DaemonSet, webhook, controladores). É uma dependência
  grande para um protótipo hoje feito com Docker Compose.
- **O artefato passa a ser uma imagem de container (OCI)**, não o `application.ext4` atual. O
  build plane teria de produzir uma imagem. Cifrar e assinar imagens é suportado pelo CoCo
  **(a verificar)**.
- A documentação diz que a abordagem é **menos adequada a cargas pequenas e de curta duração**
  (custo extra de tempo e recursos por sandbox, caminho de rede mais complexo), que é o nosso
  caso. Um sinal contra, a medir depois.
- **Não há *warm pool* nativo** na documentação que li **(a verificar)**. A D-006 teria de ser
  implementada por cima.
- Imagens grandes baixadas dentro da VM alongam o startup; a mitigação documentada é embutir a
  imagem na VM do pod.
- O adaptor e o runtime ficam fora da TCB: o operador ainda escolhe *quando* e *quantas* VMs
  criar. A integridade vem da atestação e da política, não da orquestração.

**Relação com a Azure:** usa tipos DCasv5/ECasv5 (SNP) e também TDX. A Azure tem ainda os
Confidential Containers no ACI (grupo de containers numa *utility VM* SNP), citados no plano de
ressubmissão; ainda não verifiquei esse caminho, que dispensa Kubernetes.

## Critérios de equivalência de segurança para adotar peer pods + OCI (D-008)

"Sem perda significativa" precisa ser definido antes de medir. Propriedades que o desenho novo
deve manter em relação ao atual (microVM sem rede, artefato ext4 somente leitura):

| # | Propriedade | Hoje | Em peer pods (ponto de atenção) |
|---|---|---|---|
| P1 | A aplicação não tem caminho de rede durante a execução | Microvm sem pilha de rede | **Mantida** no executor próprio (D-010): a CVM tem rede, mas o **container** roda sem rede (`--network none`, namespace de rede vazio), com dados montados, grava o resultado em volume e morre. Só o agente confiável da CVM usa a rede, antes e depois |
| P2 | Escape da aplicação fica contido | Exige escape do VMM Firecracker | **É aqui que está a diferença real**: a fronteira passa de hipervisor para namespaces/seccomp sobre o kernel do guest. Um escape do container (falha de kernel/runtime) dá root na CVM, e aí a NIC fica acessível. Contido pela **CVM de uso único** (D-005/D-006) e reduzido por runtime reforçado |
| P3 | Nenhum estado sobrevive entre jobs | microVM e overlay descartados | CVM destruída por job; vale se o pool respeitar o uso único |
| P4 | Dataset e aplicação ilegíveis para o operador | Só na CVM; hoje a CVM1 vê tudo (E1) | Atestação + KBS (Trustee) fora do cluster; melhora o desenho atual |
| P5 | Integridade do artefato | Hash do ext4 não é reproduzível (E1, A6) | Imagem fixada por *digest* e assinada **(a verificar)**; melhora se for imposto |
| P6 | Build isolado e sem exfiltrar o código | microVM de build com egress (E1, A10) | Build de OCI executa `RUN` arbitrário com rede: o problema **se generaliza** e precisa de build em duas fases |
| P7 | Política de execução imposta | Fixa no runner | Política Rego do kata-agent e *initdata* **(a verificar o que dá para travar)** |
| P8 | Superfície de observação do hipervisor | Firecracker aninhado: maior | CVM plana: menor (D-005) |

**Ponto crítico (corrigido em 2026-10-12): P2, não P1.** A aplicação não tem rede porque roda
num container sem namespace de rede, enquanto o agente da CVM, confiável, é o único que usa a
rede. O que se troca em relação ao Firecracker é a **fronteira de isolamento** (hipervisor →
kernel do guest). O resíduo é um escape de container que vire root na CVM e use a NIC. Para
aceitar a troca: runtime reforçado (gVisor/runsc ou runc rootless com seccomp, capacidades
removidas, rootfs somente leitura, sem dispositivos), CVM de uso único e a limitação declarada.

**Ganho de generalização:** o contrato deixa de ser "Python + wheels em ext4" e passa a ser "uma
imagem OCI"; qualquer linguagem e ecossistema entram, e o reuso de dependências sem
recompilação (contraste com o SGX) continua valendo. A tese de supply chain se amplia: o build
de imagens (base images, registries, camadas, `RUN`) é uma superfície maior.

**Como provar depois (D-007):** reexecutar contra o runtime de pods a suíte de ataques já
existente (T1 exfiltração de rede, T1b escape de filesystem, T2 dependência maliciosa, T3
limpeza, T4 isolamento entre CVMs, T5 controle de acesso), que mapeia diretamente em P1–P3, P5 e P6.

## E2.4 — Plano de medição (ADIADO — D-007; decidir primeiro, medir depois)

**Ciclo medido por job**, em fases:
1. chamada de API de criação → máquina rodando
2. boot do kernel (imagem mínima, UKI)
3. obtenção do relatório de atestação
4. liberação da chave
5. execução do job
6. destruição

**Variantes:** tamanho da máquina; imagem mínima × padrão; com e sem *warm pool*; SNP e/ou TDX
conforme a nuvem. **Baseline:** o modo direto atual e o Firecracker em VM comum, ambos com o
desligamento corrigido (o ~25 s atual é em grande parte artificial, E1 do plano de ressubmissão).

**Hipótese a testar (não medida):** o provisionamento da nuvem domina o ciclo e o boot do kernel
pesa pouco; o *warm pool* tira o provisionamento do caminho crítico ao custo de CVMs ociosas.

### Salvaguardas do warm pool (D-006), a especificar
- atestação com nonce fresco no momento do claim
- claim de uso único imposto pelo guest (a CVM aceita um job e se destrói)
- sem disco persistente; nenhum dado de job antes do claim
- idade máxima de uma CVM ociosa
- dimensionamento do pool e custo por job

## Perguntas abertas
1. Em quais nuvens há conta e crédito para medir (Azure, GCP, AWS)? Define SNP × TDX.
2. Medir só a opção A, ou também B/C?
3. Referência para o efeito do tempo de execução sobre a reconstrução via canal lateral
   (nested e não nested).
