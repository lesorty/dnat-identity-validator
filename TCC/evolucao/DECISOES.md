# Registro de decisões

Formato: data · decisão · motivo · referência. Mais recente no topo.
Status possíveis: **ACEITA**, **PROVISÓRIA** (aceita, mas depende de algo pendente),
**DESCARTADA**, **SUBSTITUÍDA** (aponta para a decisão nova).

---

### 2026-10-18 · D-033 · ACEITA
**Decisão:** O alvo é o **DSN 2027 (Berlim)**, regular paper (11 páginas com tudo, IEEE CS,
double-blind): resumo em **25/nov/2026**, artigo em **02/dez/2026**. Implementação, escrita e
revisão em cerca de seis semanas. A contribuição principal é o **Juiz de IA**. O
`PLANO_RESSUBMISSAO.md` (SAC → DSN → SBRC) fica substituído pelo `PLANO_DSN2027.md`.
**Ref.:** [../PLANO_DSN2027.md](../PLANO_DSN2027.md)

### 2026-10-17 · D-032 · ACEITA
**Decisão (com o orientador):** O foco do artigo passa a ser, nesta ordem: (i) **adaptar o
sistema para aplicações em imagem OCI**, no lugar do contrato atual Python + wheels em ext4
(E2, E2b); (ii) **contribuição principal: um Juiz de IA** que analisa o código de uma aplicação e
verifica se ela é segura, se vaza dados etc. (E4, ampliando a D-016).
**Arquitetura do Juiz:** para ser escalável e *future proof*, o analisador é **apenas mais uma
aplicação do sistema**, executada pelo mesmo pipeline confidencial. Ela age como juiz das outras
aplicações e faz parte da **whitelist** por natureza, para que qualquer aplicação possa ser
passada como entrada para ela.
**Principal dificuldade (a discutir depois):** tornar a análise eficaz e, se possível, barata.
**A detalhar pelo Steylor:** decisões propostas, ideias de testes e casos de uso.
**Ref.:** [ARTIGO.md](ARTIGO.md) · [brainstorm/03_agentes_verificacao.md](brainstorm/03_agentes_verificacao.md)

### 2026-10-17 · D-031 · ACEITA
**Decisão (com o orientador):** **Não seguir com a distribuição do sistema.** O desenho da E3
(D-019 a D-030) fica **DESCARTADO** e arquivado como registro; nada dele será implementado.
**Motivo:** como o sistema executa em máquina confidencial e, em tese, atestável, distribuí-lo
não traz ganho significativo de confiança que justifique o custo.
**Consequências:** (i) a atestação volta a ser **implícita** e fora do escopo, como na D-017
(iii); a revisão feita pela D-021 é desfeita. (ii) Continua valendo a **D-018**: cifrar o dataset
(A16) é TODO; o ledger em memória (A17) não é problema. (iii) Na D-022, as camadas que dependiam
da rede (E3, chave consumida no contrato; E6, idade pelo bloco) ficam por rever; as demais
seguem. (iv) A imagem OCI pronta continua **estacionada** (D-029 iii). (v) As direções 2 e 3 do
brainstorm 01 saem do foco.
**Limitação a declarar:** o operador continua sendo ponto único para disponibilidade e censura;
o sigilo frente a ele depende da CVM e da atestação.
**Ref.:** [resultados/E3_descentralizacao.md](resultados/E3_descentralizacao.md) (arquivado)

### 2026-10-14 · D-030 · DESCARTADA (D-031)
**Decisão:** **E3 concluída.** A arquitetura distribuída (D-018 a D-029) fica consolidada no
documento de resultados, com três diagramas (arquitetura, execução e pagamento, build
confidencial). Consequências registradas: o plano de medição da E2.4 inclui atestação, sorteio,
liberação t de N e custo das transações na L1; a CVM de fetch separada vira o padrão da E2b.
**Pendente para depois da arquitetura:** literatura, caso âncora, *bootstrap* da admissão e
parâmetros (N, t, stake, fatias, prazos).
**Ref.:** [resultados/E3_descentralizacao.md](resultados/E3_descentralizacao.md)

### 2026-10-14 · D-029 · DESCARTADA em parte (D-031; item iii continua estacionado)
**Decisão:** (i) A chave do código chega aos builders pela **opção B**: após o sorteio, o cliente
do desenvolvedor cifra `K_code` para a chave pública atestada de cada builder sorteado; `K_code`
nunca fica armazenada na rede. (ii) O build continua **feito pela rede**, como no desenho atual.
(iii) A possibilidade de o desenvolvedor enviar a **imagem OCI pronta** fica **ESTACIONADA** para
análise futura (níveis de origem 0/1/2 na política do dataset).
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §12 ·
[brainstorm/05_imagem_pronta.md](brainstorm/05_imagem_pronta.md)

### 2026-10-14 · D-028 · DESCARTADA (D-031)
**Decisão:** (i) O D1 usa a **L1** (Ethereum) por ora, o que evita o sequenciador único de uma
L2. (ii) O algoritmo de **artefato único com N builders** (líder sorteado cifra com `K_app`, os
demais conferem o digest e assinam) está aceito; o item (vi) da D-027 passa a ACEITO.
**Pendente (resolvido na D-029):** como a chave do código chega aos builders.

### 2026-10-14 · D-027 · DESCARTADA (D-031)
**Decisão:** (i) "Validador" na D-025 (iii) = servir no **comitê de verificação** do DNAT, não
validar a blockchain. (ii) **Peers de armazenamento** também servem nesse comitê, com stake.
(iii) **Pagamento só por execução** (fim da compra única); o comitê de chaves recebe uma fatia.
(iv) Moeda: **ETH** por ora. (v) Pagamentos **visíveis** na rede pública (I7 aceito).
(vi) **Build confidencial:** fase 1 (fetch, com rede, sem código) separada da fase 2 (assemble,
sem rede, em CVM atestada que recebe a chave do código do comitê); a separação em CVMs distintas
(opção B da E2b.3) vira o padrão com builders abertos; um líder sorteado cifra a imagem com
`K_app` nova e os demais conferem o digest antes de assinar.
**Pendente:** L1 × L2.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §8, §12

### 2026-10-14 · D-026 · DESCARTADA (D-031)
**Decisão:** A **D9** (lista de medições permitidas) fica registrada no desenho como no §11 do
brainstorm 04: qualquer um propõe com stake, builders sorteados reproduzem a imagem a partir do
código público, votação por stake e prazo de contestação. **Não será implementada no projeto**;
entra só como desenho e trabalho futuro.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §11

### 2026-10-14 · D-025 · DESCARTADA (D-031)
**Decisão:** Aplicação da regra sem nós especiais (D-024). (i) **Builders:** N sorteados entre os
admitidos. (ii) **Executores:** sorteio ponderado por stake entre os elegíveis pela política do
dataset. (iii) **Admissão:** comitê de verificação de atestação sorteado entre nós já admitidos;
**todo nó que ocupa um papel remunerado em cripto também tem de servir como validador** nesse
comitê. (iv) **Aleatoriedade:** beacon da própria rede, gerado por consenso; sem oráculo externo.
(v) **Contrato sem chave de admin**; mudanças só por votação com prazo de contestação.
**Pendente:** D9 (lista de medições), em explicação; L1 × L2 (sequenciador); como peers de
armazenamento, que não rodam CVM, cumprem o item (iii).
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §11

### 2026-10-14 · D-024 · DESCARTADA (D-031)
**Decisão:** Comitê de chaves aberto, sem membros fixos. (i) Partes de cada chave em N nós, limiar
t, ajustável pela política do dataset. (ii) **Seleção por sorteio verificável ponderado por
stake**; cada vaga exige stake, o que torna a corrupção cara. (iii) Uma vaga por chip físico
(`CHIP_ID` da atestação). (iv) Partes só dentro de CVMs atestadas. (v) Rotação proativa das partes.
(vi) Substituição de nós que caem, com prova de vida e perda de stake. (vii) Dono pode recriar o
comitê; sem dono, perda é a falha segura.
**Regra geral derivada (D-023 ii):** todo papel com poder é preenchido por sorteio ponderado por
stake entre quem cumpre requisitos objetivos, e qualquer um pode denunciar mau comportamento.
**Pendente (propostas no §11):** sorteio de builders e executores, comitê de verificação para
admissão, D9 por proposta + reprodução + votação, aleatoriedade da própria rede, contrato sem
admin, e o **sequenciador de L2**, que é um nó especial.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §10–§11

### 2026-10-14 · D-023 · DESCARTADA (D-031)
**Decisão:** (i) O D1 usa **rede pública** (L1 ou L2 a detalhar). (ii) **Princípio de
igualdade:** nenhum participante é especial por natureza; um papel privilegiado (validar, guardar
partes de chave, admitir peers) só pode vir de algoritmo de consenso ou seleção aberta, nunca de
identidade fixa. (iii) Caso âncora e verificação da literatura ficam **para depois de fechar a
arquitetura**.
**Consequências:** o multisig de stakeholders da D9 e o comitê de chaves em consórcio deixam de
valer como desenho; quem participa do comitê e quem admite peers precisa ser definido sob o
princípio (ii). Os diagramas que dizem "validadores dos stakeholders" ficam desatualizados.
**Pendente:** papéis na admissão (item 3), a conversar.

### 2026-10-14 · D-022 · PROVISÓRIA (camadas E3 e E6 revistas pela D-031)
**Decisão:** A garantia de CVM executora nova e de uso único segue as seis camadas E1–E6 do
brainstorm 04 §9 (código medido, chave efêmera por instância, chave consumida no contrato, nonce
no claim, política sem debug/migração, idade máxima).
**Condição:** aceita se os mecanismos se confirmarem na verificação (campos de política SNP/TDX,
caso do paravisor na Azure).
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §9

### 2026-10-14 · D-021 · DESCARTADA (D-031)
**Decisão:** Consolidação da E3. (i) Entram no desenho distribuído: **D1** (ledger distribuído),
**D3** (armazenamento em peers IPFS, com incentivo da D-020), **D4** (comitê de chaves, D-019),
**D5 + D6** (executores abertos com fila on-chain), **D7** (quórum de builders) e **D9** (registro
on-chain das medições permitidas). (ii) Os três pontos do brainstorm 04 §3 são aceitos como
premissas: abrir executores muda o modelo de ameaça (ataques físicos); integridade e sigilo
puxam em direções opostas; e **a atestação volta ao escopo** no nível de desenho, revendo o
item (iii) da D-017 (a atestação passa a ser o mecanismo de admissão de peers). (iii) Adota-se
a **política por dataset** como solução por ora: o dono do dataset escolhe o nível de executor
exigido (nuvens conhecidas, qualquer CVM atestada, ou replicação heterogênea, D11).
**Ficam fora por ora:** D8, D11 como padrão (só como opção da política), D12, D13.
**Pendente:** escolha da rede do D1 (consórcio, L2 pública ou híbrido).
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md)

### 2026-10-14 · D-020 · DESCARTADA (D-031)
**Decisão:** O armazenamento fica como está (blockchain para validação, IPFS para os dados): o D3
está resolvido. Adota-se como proposta o **pagamento por execução**, dividido entre os donos dos
ativos, os peers de armazenamento que serviram os blocos e o nó executor (CVM verificada), tudo
em cripto. Objetivo: incentivar a replicação dos ativos populares e a entrada de executores.
**Pendente:** escolha da rede (§7 do brainstorm 04: tensão entre consórcio e rede pública),
prova de quem serviu os dados (proposta: recibo do executor atestado) e os problemas I1–I7.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §8

### 2026-10-14 · D-019 · DESCARTADA (D-031)
**Decisão:** O **D4** (chave por ativo custodiada por um comitê de nós, liberada por limiar só
com compra on-chain, pedido assinado e executor atestado) é adotado como direção da E3.
**Motivo:** garante que só quem tem direito recebe acesso e tira do sistema a maior parte da
confiança centralizada (A2). Desenho detalhado a fazer.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md)

### 2026-10-14 · D-018 · ACEITA
**Decisão:** (i) **A16 (dataset em claro no IPFS) vira TODO**: cifrar o dataset. (ii) **A17**
(ledger em memória, reimplantado a cada boot) **não é problema no momento**.
**Ref.:** [brainstorm/04_descentralizacao.md](brainstorm/04_descentralizacao.md) §0

### 2026-10-14 · D-017 · ACEITA (revisão do item iii pela D-021 desfeita pela D-031)
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

### 2026-10-14 · D-016 · ACEITA (ampliada pela D-032: vira a contribuição principal)
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
