# E2 — Isolamento confidencial por job (o problema do Firecracker)

**Status:** DECISÕES FECHADAS (2026-10-14); falta só medir (E2.4, adiada: decidir antes de medir).
**Decisões relacionadas:** D4 (arquitetura OCI: CVM de uso único, container sem rede) e D3 (atestação implícita).
**Escopo:** a atestação é tratada como implícita em todo uso de computação confidencial e fica
fora desta etapa por ora (D3).
**Pré-requisito lido:** [E1 — auditoria](E1_auditoria_codigo.md), achados A13 e A14.

## E2.1 — O problema

**Ameaças a cobrir ao mesmo tempo:** (i) aplicação maliciosa e (ii) operador de infraestrutura.

**Estado atual (E1, A14):** na CVM o sistema roda em modo direto, sem Firecracker e sem
isolamento entre jobs. O Firecracker não roda na CVM por falta de virtualização aninhada.

**Por que a virtualização aninhada não é a resposta, mesmo quando disponível (D4):**
- Com a memória cifrada, o conteúdo da L2 não é lido pelo L0. Mas o L0 media saídas de VM e
  paginação aninhada, então observa um fluxo de eventos mais rico. O paper Nested SEV
  reconhece que o L0 observa as interações L1↔L2 e os padrões de acesso, e deixa canais
  laterais fora de escopo (Takiguchi & Kourai, OSDI'26, seção de modelo de ameaça).
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
| **A. CVM efêmera por job** | Uma CVM por execução, de uso único; com *warm pool* (D4) | Latência de provisionamento a medir. Rede negada tem de ser imposta **dentro do guest** (o firewall da nuvem é do operador) |
| **B. Azure Confidential Containers** | Child VM SNP por pod num nó L1 **não confidencial** ([docs AKS](https://learn.microsoft.com/en-in/azure/aks/confidential-containers-overview)) | Só Azure; hipervisor media a L2 (contra D4); sem números de latência; atestação da L2 **(a verificar)** |
| **C. CoCo *peer pods*** | Uma CVM por pod via API da nuvem, com Kata e atestação ([arquitetura](https://github.com/confidential-containers/cloud-api-adaptor/blob/v0.8.0/docs/architecture.md)) | **Descartada** (D4): exige Kubernetes; a documentação diz ser menos adequada a cargas curtas |
| **D. AWS Nitro Enclaves** | VM sem rede, só vsock, atestação por PCR ligada ao KMS | Confia na AWS; memória não cifrada pelo TEE **(a verificar)**; hipervisor media a enclave |
| **E. Sandbox sem virtualização na CVM** | gVisor, seccomp/Landlock, Wasm | Fronteira mais fraca que KVM; Wasm quebra wheels nativas. **Complemento** da A, não substituto |
| **F. VMPL/SVSM, TD partitioning, Nested SEV** | Mecanismos de pesquisa ou de uma só L2 | Não são produção para o nosso caso |

**Hipótese de trabalho:** A + E (CVM por job, com sandbox interno como defesa em profundidade).

### Desenho de rede da opção A (decidido, D4)
Três fases no guest: (1) com rede, para atestar e buscar ativos e chaves; (2) **sem rede**, com
a aplicação rodando; (3) com rede, só para devolver o resultado cifrado. Se a aplicação chegar a
root no guest, pode religar a rede; por isso o sandbox interno é defesa em profundidade, e a
imagem medida deve impedir a reconfiguração de rede pela aplicação. A rede é cortada **dentro do
guest**, porque o firewall da nuvem pertence ao operador: o container roda em namespace de rede
vazio, sem capacidade de rede, e as regras ficam fora do alcance da aplicação.

### Build plane
O código do desenvolvedor também é segredo (E1, A10), e o Firecracker também não roda na CVM de
build. A decisão de E2 vale para os dois planos.

## E2.3 — Critérios de comparação

1. Garantia frente ao operador (conteúdo)
2. **Superfície de observação do hipervisor** (canal lateral; critério novo, D4)
3. Garantia entre jobs / contra aplicação maliciosa
4. TCB
5. Latência de provisionamento e de execução
6. Custo (inclui CVMs ociosas do pool)
7. Disponibilidade real por nuvem
8. Esforço de implementação no protótipo
9. Portabilidade entre nuvens

## Propriedades P1–P8 (requisitos do executor)

"Sem perda significativa" precisa ser definido antes de medir. Propriedades que o desenho novo
deve manter em relação ao atual (microVM sem rede, artefato ext4 somente leitura):

| # | Propriedade | Hoje (microVM) | No executor OCI em CVM |
|---|---|---|---|
| P1 | A aplicação não tem caminho de rede durante a execução | Microvm sem pilha de rede | **Mantida** no executor próprio (D4): a CVM tem rede, mas o **container** roda sem rede (`--network none`, namespace de rede vazio), com dados montados, grava o resultado em volume e morre. Só o agente confiável da CVM usa a rede, antes e depois |
| P2 | Escape da aplicação fica contido | Exige escape do VMM Firecracker | **É aqui que está a diferença real**: a fronteira passa de hipervisor para namespaces/seccomp sobre o kernel do guest. Um escape do container (falha de kernel/runtime) dá root na CVM, e aí a NIC fica acessível. Contido pela **CVM de uso único** (D4) e reduzido por runtime reforçado |
| P3 | Nenhum estado sobrevive entre jobs | microVM e overlay descartados | CVM destruída por job; vale se o pool respeitar o uso único |
| P4 | Dataset e aplicação ilegíveis para o operador | Só na CVM; hoje a CVM1 vê tudo (E1) | Vale na granularidade da CVM; atestação implícita (D3) |
| P5 | Integridade do artefato | Hash do ext4 não é reproduzível (E1, A6) | Imagem fixada por *digest* e assinada **(a verificar)**; melhora se for imposto |
| P6 | Build isolado e sem exfiltrar o código | microVM de build com egress (E1, A10) | Build de OCI executa `RUN` arbitrário com rede: o problema **se generaliza** e precisa de build em duas fases |
| P7 | Política de execução imposta | Fixa no runner | Fixa no agente da CVM, que ignora a config da imagem (E2b.5) |
| P8 | Superfície de observação do hipervisor | Firecracker aninhado: maior | CVM plana: menor (D4) |

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

**Como provar depois:** reexecutar contra o executor OCI a suíte de ataques já
existente (T1 exfiltração de rede, T1b escape de filesystem, T2 dependência maliciosa, T3
limpeza, T4 isolamento entre CVMs, T5 controle de acesso), que mapeia diretamente em P1–P3, P5 e P6.

## E2.4 — Plano de medição (ADIADO — decidir primeiro, medir depois)

**Ciclo medido por job**, em fases:
1. chamada de API de criação → máquina rodando
2. boot do kernel (imagem mínima, UKI)
3. obtenção do relatório de atestação
4. liberação da chave
5. execução do job
6. destruição

**Variantes:** tamanho da máquina; imagem mínima × padrão; com e sem *warm pool*; SNP e/ou TDX
conforme a nuvem. **Baseline:** o modo direto atual e o Firecracker em VM comum, ambos com o
desligamento corrigido (o ~25 s atual é em grande parte artificial: espera de shutdown no `run-vm.sh`).

**Hipótese a testar (não medida):** o provisionamento da nuvem domina o ciclo e o boot do kernel
pesa pouco; o *warm pool* tira o provisionamento do caminho crítico ao custo de CVMs ociosas.

### Salvaguardas do warm pool (D4)
- claim de uso único **imposto pelo guest** (a CVM aceita um job e se destrói); o operador não
  consegue reutilizá-la
- sem disco persistente; nenhum dado de job antes do claim
- idade máxima de uma CVM ociosa **(valor a definir na medição)**
- dimensionamento do pool e custo por job **(a definir na medição)**
- atestação com nonce no claim: implícita, fora do escopo por ora

## Perguntas abertas
1. Em quais nuvens há conta e crédito para medir (Azure, GCP, AWS)? Define SNP × TDX.
2. Medir só a opção A, ou também B/C?
