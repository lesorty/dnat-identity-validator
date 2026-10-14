# Registro de decisões

Formato: data · decisão · motivo · referência. Mais recente no topo.
Status possíveis: **ACEITA**, **PROVISÓRIA** (aceita, mas depende de algo pendente),
**DESCARTADA**, **SUBSTITUÍDA** (aponta para a decisão nova).

---

### 2026-10-14 · D-017 · ACEITA
**Decisão:** Fechamento das decisões da E2. (i) **Peer pods e Kubernetes descartados**: a
D-008 fica **SUBSTITUÍDA pela D-010** (executor próprio). (ii) **D-010 e D-005 passam a ACEITAS**.
(iii) **Atestação tratada como implícita** em todo uso de computação confidencial; fica fora do
escopo por ora (inclui o nonce no claim do warm pool e a liberação de chaves por atestação).
(iv) Confirmados o **desenho de rede da opção A** (três fases no guest; rede cortada dentro do
guest; container em namespace vazio) e as **salvaguardas do warm pool** (uso único imposto pelo
guest, sem disco persistente, idade máxima e tamanho do pool definidos na medição).
(v) **Referência sobre o efeito do tempo de execução no canal lateral removida do pendente**:
será testada pelo Steylor depois das decisões; permanece como inferência não fonteada.
**Pendente da E2:** só a medição (E2.4, D-007).
**Ref.:** [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)

### 2026-10-14 · D-016 · ACEITA
**Decisão:** Abre-se uma frente nova, **E4: verificação de aplicações por agentes de IA**, para o
caso de **código conhecido e dados privados**, em que o código é verificável mas o esforço é
proibitivo. O usuário declara propriedades de segurança exigidas (ex.: não vazar dados, direta
ou indiretamente, inclusive por fuzzing ou máscara) e agentes verificam a aplicação contra elas.
**Motivo:** o DNAT cobre bem código secreto com dados públicos; o caso inverso fica sem
solução prática de verificação. A frente evolui a varredura de saída (D-015) e é **futura**:
só planejamento por ora.
**Ref.:** [brainstorm/03_agentes_verificacao.md](brainstorm/03_agentes_verificacao.md)

### 2026-10-14 · D-015 · ACEITA
**Decisão:** (i) **Build reproduzível** aprovado, **selado junto com a assinatura** do builder
atestado: a declaração de proveniência registra se o build é reproduzível e a política pode
exigir N assinaturas de builders distintos que concordem no digest. Só agrega garantia com um
segundo builder; viabilidade com Dockerfile livre **a verificar**. (ii) **Varredura de saída**
aprovada, básica (segredos, setuid, links, tamanho), antes de assinar; o executor revalida
tudo. Evolui para verificação por agentes (D-016).
**Também:** especificada a imposição das duas fases (estágios `deps`/`app`, contextos e rede
distintos) e a assinatura/proveniência, ambas no E2b (rascunho).
**Ref.:** [resultados/E2b_build_oci.md](resultados/E2b_build_oci.md)

---

### 2026-10-12 · D-014 · ACEITA
**Decisão:** (i) **X8 (vazamento do dataset pelo canal legítimo de resultado) está FORA DE
ESCOPO** do artigo e será declarado como tal no modelo de ameaça, com a política de saída
(direção 4) como trabalho futuro. (ii) **X7 (canais encobertos/laterais)** é tratado como
**limitação declarada**, inerente a TEEs (D-005), sem mitigação própria.
**Consequência:** a motivação do build verificável deixa de incluir "impedir que o dataset saia
pelo resultado". Continua valendo: confidencialidade do código do desenvolvedor durante o build
(E1, A10), integridade do resultado e contenção de um executor atacado via imagem (classe A).
**Coerência:** já previsto no backlog do artigo como item F3a (fora de escopo: vazamento pelo
canal legítimo, citando o VDDPI como linha complementar).
**Ref.:** [brainstorm/02_build_oci.md](brainstorm/02_build_oci.md)

### 2026-10-12 · D-013 · ACEITA
**Decisão:** (i) **Sem gabaritos fixos**: o build aceita Dockerfile livre, protegido por
contenção (duas fases e CVM de uso único), não por restrição de expressividade. (ii) **Sem
imagens-base curadas e assinadas pela plataforma**: o `FROM` deve ser fixado por *digest*.
**Motivo:** gabaritos limitam a generalização que motivou o OCI; a curadoria de bases tem custo
de manutenção sem proporcional ganho, e a fixação por digest é verificação barata (comparar hash).
**Atualização (mesma data):** (ii) fica **POR VALIDAR** e com prioridade menor que as alavancas
3 (duas fases) e 4 (CVM de uso único). Não será detalhada agora.
**Atualização 2:** a alavanca 5 (motor de build sem privilégios) está **REJEITADA**: o build já
roda numa VM separada e de uso único; rootless não ajuda e pode limitar aplicações.
**Atualização 3:** a assinatura da imagem final pelo builder atestado (alavanca 7 do arquivo,
"6" no chat) está **APROVADA como incremento de atestação**, ciente de que **não muda a
segurança do ambiente que executa o build**; só vincula o artefato a um builder medido.
**Ref.:** [brainstorm/02_build_oci.md](brainstorm/02_build_oci.md)

### 2026-10-12 · D-012 · ACEITA
**Decisão:** O **build de imagens OCI** passa a ser o principal tema de segurança em aberto e
ganha etapa própria (E2b), antes da E3.
**Motivo:** construir uma imagem OCI expõe uma superfície muito maior que montar um ext4
(instruções de build que executam código, imagens-base, camadas, cache, ferramentas com
privilégio). O ext4 era montado a partir de wheels; uma imagem aceita muito mais.
**Ref.:** [brainstorm/02_build_oci.md](brainstorm/02_build_oci.md)

### 2026-10-12 · D-011 · ACEITA
**Decisão:** Na execução, a aplicação roda num **container sem rede** dentro de uma CVM de uso
único: namespace de rede vazio, dados montados antes de iniciar, resultado gravado em volume,
container descartado ao final. A CVM tem rede, mas só o agente confiável a usa (antes e
depois). O runtime é **reforçado** (gVisor/runsc ou runc rootless com seccomp, sem
capacidades, rootfs somente leitura, sem dispositivos).
**Motivo:** mantém a propriedade "a aplicação não tem caminho de rede" (P1). A diferença
frente ao Firecracker é a fronteira (hipervisor → kernel do guest, P2), declarada como
limitação e mitigada por uso único e runtime reforçado.
**Ref.:** [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)

### 2026-10-12 · D-010 · ACEITA (D-017)
**Decisão:** Contrato entre os planos no desenho v2: o **builder** produz e salva a aplicação
como **arquivo OCI já construído e pronto para executar**; o **executor** só recebe esse arquivo
OCI e o dataset, executa e deixa o resultado no armazenamento. Sem registry e sem *pull* no
caminho de execução. O controle orquestra e guarda as chaves.
**Pontos a especificar:** verificação de *digest*/assinatura do OCI pelo executor; chaves
liberadas por atestação (e não decifradas no controle); resultado cifrado dentro do guest antes
de sair da CVM; rede só nas fases de entrada e saída.
**Relação:** inclina a D-008 para o **executor próprio** (sem peer pods e sem Kubernetes).

---

### 2026-10-12 · D-009 · ACEITA
**Decisão:** O build produz **só a aplicação** (imagem/artefato com o app e suas dependências).
O dataset **nunca entra no build**; é entregue em tempo de execução, cifrado, como entrada
montada somente leitura. Com N aplicações e M datasets há **N builds**, não N×M.
**Motivo:** mantém a invariante atual (o dataset não chega ao plano de build, que tem rede e
roda código não confiável) e evita rebuild a cada novo dataset. A assinatura da imagem cobre só
a aplicação; o vínculo com o dataset vem da compra no ledger.

### 2026-10-12 · D-008 · SUBSTITUÍDA (pela D-010, via D-017)
**Nota (mesma data):** a D-008 mistura duas decisões separáveis, a revisar: (i) **formato do
artefato** (OCI em vez de ext4) e (ii) **orquestração** (peer pods/Kubernetes ou executor próprio
que recebe a imagem pronta). O executor próprio dispensa peer pods.
**Decisão:** Adotar **peer pods do CoCo + imagens OCI** como caminho candidato para generalizar
as aplicações suportadas (outras linguagens, sem o contrato ext4/wheels), **condicionado** à
demonstração de que não há perda significativa de segurança frente ao desenho atual, segundo os
critérios de equivalência P1–P8 do documento de E2. Se algum critério crítico não puder ser
atendido, o fallback é a opção A (CVM por job feita por nós) ou o ACI Confidential Containers.
**Motivo:** generalização (linguagens e ecossistemas) e reaproveitamento de atestação e
liberação de chave prontas, ao custo de Kubernetes e de mudar o artefato para OCI.
**Cuidado na Azure:** o AKS Confidential Containers usa child VMs **aninhadas** (conflita com
D-005); peer pods usam CVMs irmãs. Não confundir os dois caminhos.
**Ref.:** [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)

### 2026-10-12 · D-007 · ACEITA
**Decisão:** Medições e testes práticos de todas as etapas (inclusive E2.4) ficam para depois
das decisões. A ordem é: decidir primeiro, medir depois. A nuvem de testes é a **Azure**.
**Motivo:** as medições dependem de escolhas de arquitetura ainda em aberto.

### 2026-10-12 · D-006 · ACEITA
**Decisão:** A efemeridade será garantida por **uso único**, não por boot sob demanda: um
*warm pool* de CVMs pré-iniciadas e nunca usadas, cada uma consumida por exatamente um job
e destruída depois. Nenhum dado de job entra numa CVM antes do claim.
**Motivo:** uma CVM ociosa que nunca viu dados é tão limpa quanto uma recém-criada, e o
provisionamento da nuvem sai do caminho crítico. O custo (CVMs ociosas) só se justifica se a
medição de E2 mostrar que o provisionamento domina a latência.
**Salvaguardas a especificar:** atestação com nonce fresco no momento do claim; claim de uso
único imposto pelo próprio guest; sem disco persistente; idade máxima de uma CVM ociosa;
dimensionamento do pool e custo por job.
**Ref.:** [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)

### 2026-10-12 · D-005 · ACEITA (D-017)
**Decisão:** A fronteira de isolamento por job é **a própria CVM** (uma por job, curta,
efêmera). Virtualização aninhada (microVM dentro de CVM, ou L2 mediada por hipervisor) é
descartada como mecanismo de isolamento confidencial.
**Motivo:** mesmo com a memória cifrada, um L0 que media as saídas de VM e a paginação aninhada
observa um fluxo de eventos mais rico (canal lateral); o paper Nested SEV (OSDI'26) deixa isso
fora de escopo e reconhece que o L0 observa as interações L1↔L2 e os padrões de acesso.
Execuções curtas e de uso único limitam a janela de observação. Nenhuma opção elimina o canal
lateral; a diferença é de superfície, e isso vira limitação declarada no modelo de ameaça.
**Nota (D-017):** a afirmação de que a reconstrução fica mais fácil com o tempo de execução no
caso aninhado é inferência não fonteada; será testada depois pelo Steylor.
**Ref.:** [resultados/E2_isolamento_confidencial.md](resultados/E2_isolamento_confidencial.md)

### 2026-10-12 · D-004 · ACEITA
**Decisão:** A direção 1 (cadeia verificável build → execução) sai da pauta das etapas E2 e E3;
só se confere a compatibilidade com ela na E5.
**Motivo:** a direção 1 é uma camada de protocolo sobre a topologia atual. As escolhas de E2/E3
não podem impedi-la (chave por ativo, resultado cifrado para o comprador, recibo assinado).

### 2026-10-12 · D-003 · PROVISÓRIA
**Decisão:** A discussão de rumo será feita em etapas (E1 auditoria → E2 isolamento
confidencial → E3 descentralização → E5 síntese), cada uma com um documento de resultados.
**Motivo:** os temas dependem uns dos outros (o que for decidido sobre o Firecracker muda o
que faz sentido distribuir) e são grandes demais para uma única rodada.
**Ref.:** [ETAPAS.md](ETAPAS.md)

### 2026-10-12 · D-002 · ACEITA
**Decisão:** As direções 1 (cadeia verificável build → execução), 2 (distribuição de
confiança entre operadores) e 3 (build reproduzido por construtores independentes) ficam
registradas como candidatas para a evolução do trabalho. A escolha final de tese fica para a E5.
**Motivo:** preferência do Steylor após o brainstorm de 2026-10-12.
**Ref.:** [brainstorm/01_direcoes_contribuicao.md](brainstorm/01_direcoes_contribuicao.md)

### 2026-10-12 · D-001 · ACEITA
**Decisão:** Ideias, decisões e resultados sobre o rumo do trabalho ficam em `TCC/evolucao/`,
separados do plano tático de ressubmissão (`TCC/PLANO_RESSUBMISSAO.md`).
**Motivo:** o plano de ressubmissão tem prazo curto (SAC 16/out); a evolução da arquitetura
tem horizonte maior (DSN e depois) e precisa de histórico próprio.
**Ref.:** [README.md](README.md)
