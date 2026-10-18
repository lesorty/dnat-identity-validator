# Brainstorm 04 — Descentralização: onde peers abertos ajudam (E3)

**Origem:** conversa de 2026-10-14, abertura da E3.
**Status:** ENCERRADO e ARQUIVADO (D-031: não distribuir). Consolidado em [resultados/E3_descentralizacao.md](../resultados/E3_descentralizacao.md)
(D-018 a D-030). Este arquivo guarda o histórico da discussão; seções antigas podem citar
desenhos depois revistos (ex.: consórcio, multisig, comitê fixo). Literatura ainda não
consultada: tudo que depende de fonte externa está **(a verificar)**.
**Base auditada:** `main` @ `aa05b92`.
**Relacionados:** [E1](../resultados/E1_auditoria_codigo.md) · [E2](../resultados/E2_isolamento_confidencial.md) ·
[E2b](../resultados/E2b_build_oci.md) · [direções 1–3](01_direcoes_contribuicao.md)

## 0. Dois achados novos no código (complementam a E1)

| # | Achado | Evidência | Sev. | Por que importa para a E3 |
|---|---|---|---|---|
| A16 · **TODO (D-018)** | **O dataset é publicado no IPFS em claro.** Só a aplicação é cifrada; o dataset vai direto para `addFileToIpfsFlow` e volta sem decifrar | `smart-contract/scripts/api-server.js:704-705` (registro), `:860-861` (execução) | 🔴 | Hoje o sigilo do dataset depende de o nó IPFS ser privado. **Qualquer** distribuição do armazenamento (outros peers, pinning, gateway) vaza o dataset. É pré-requisito de tudo abaixo |
| A17 · **não é problema agora (D-018)** | **O ledger é um nó Hardhat único, em memória, e o contrato é reimplantado a cada boot** da CVM1. Compras e ativos somem quando o container reinicia | `docker/root-entrypoint.sh:78`, `:87-89` | 🔴 | O "ledger" não tem nenhuma das propriedades que justificam um ledger (persistência, ordem, resistência a rollback). O operador reescreve a história reiniciando um processo |

## 1. Hipótese de partida (de 01, a testar aqui)

Com CVM e atestação, distribuir **não aumenta muito o sigilo** (quem garante o sigilo é o TEE),
mas pode aumentar muito a **verificabilidade**, a **disponibilidade**, a **resistência à censura**
e a **tolerância à falha de um fabricante de TEE**. A exceção é a **custódia de chaves**: aí
distribuir aumenta o sigilo de fato, porque remove o único ponto que vê tudo (A2).

## 2. Mapa: cada ponto centralizado do sistema e a forma distribuída

Graus de abertura usados abaixo:
- **C (consórcio):** peers conhecidos e autorizados (donos de dados, desenvolvedores, operadores).
- **O (aberto com admissão):** qualquer um entra, desde que prove algo (atestação de um hardware
  da lista permitida, *stake*).
- **L (livre):** qualquer um entra, sem prova.

| # | Ponto centralizado hoje | Evidência | Forma distribuída | Grau | Ganho real | Custo / risco |
|---|---|---|---|---|---|---|
| D1 | **Ledger** num nó Hardhat único e efêmero | A17 | Rede de validadores: consórcio (Besu/QBFT, cada stakeholder um validador) ou L2 pública | C ou L | Persistência, ordem, não-repúdio, sem rollback pelo operador; dá sentido ao ledger (R2 dos revisores) | Latência e gas (há medição de gas em `measure-gas.js`); escolher consórcio × pública muda a tese |
| D2 | **Carteira custodial única** | A3 | Cada participante assina as próprias transações (carteira no navegador); o servidor vira cliente sem privilégio | — | Pré-requisito: sem isso nenhum peer é dono de nada on-chain | Baixo; muda UX e API |
| D3 | **Armazenamento**: um nó IPFS na CVM1 | `root-entrypoint.sh:66-71` | Donos fixam (*pin*) os próprios blobs; vários peers de pinning; endereçamento por conteúdo já dá integridade | O ou L | Disponibilidade e resistência à censura (o operador não consegue "perder" um ativo) | **Só depois de A16** (cifrar o dataset). Com tudo cifrado o risco é quase nulo: os peers guardam só cifrado |
| D4 | **Chave global** na CVM1 | A2 | Chave **por ativo**, custodiada por um **comitê de N nós de chave** (limiar t-de-N, Shamir ou DKG). Cada nó libera sua parte só se: (i) a compra existe on-chain; (ii) o pedido está assinado pelo comprador (A4); (iii) a atestação do executor bate com a lista permitida | C (nós de chave em donos/operadores distintos) ou O | **O maior ganho de sigilo da E3**: comprometer menos de t nós não entrega nada. Pode impor o **limite de execuções por compra** (A5): cada liberação é um evento on-chain | Alto: DKG/limiar, rotação, disponibilidade do comitê. Referências: key manager do Oasis/Ekiden, Secret Network, KMS do Phala/dstack **(a verificar)** |
| D5 | **Executor único** (CVM3) | `EXECUTOR_URL`, `api-server.js:18` | **Mercado aberto de executores**: qualquer peer com CVM atestada reivindica jobs de uma fila on-chain, recebe as chaves do comitê (D4) e devolve resultado cifrado + recibo assinado | O | Disponibilidade, sem operador único, concorrência de preço; a escolha "qual CVM recebe a chave" sai do operador | **Ponto delicado, ver §3.1**: num grau aberto, o atacante pode ser **dono do hardware** (ataques físicos como BadRAM passam a ser viáveis) |
| D6 | **Orquestração**: a CVM1 escolhe o executor e despacha | `api-server.js:833-920` | Fila de jobs no contrato; executores leem eventos; *timeout* + reatribuição; o servidor vira só interface | O | Fim da censura e da escolha seletiva pelo operador | Médio; reorganiza a API |
| D7 | **Builder único** (CVM2) | `BUILDER_URL`, `api-server.js:22` | **N builders independentes** refazem o build e assinam o digest (direção 3, D-015); a política exige ≥ N assinaturas concordantes | C ou O | Integridade do artefato frente a um builder comprometido | Depende de build reproduzível (a verificar); o 2º builder precisa ver o código, o que se resolve com D4 liberando a fonte só a builders atestados (responde ao ponto aberto da E2b.4) |
| D8 | **Cache de dependências** compartilhado e sem proveniência | A12, `worker.py:63-92` | Cache endereçado por conteúdo (IPFS/registry), entrada aceita só com assinatura de ≥ k builders ou hash do índice oficial | O | Mitiga envenenamento do cache (T6) | Ganho modesto; com OCI vira cache de camadas |
| D9 | **Lista de medições permitidas** (builders e executores) e **verificação de atestação**: inexistentes | A1; ponto aberto da E2b.4 | Registro on-chain das medições, governado por multisig dos stakeholders; verificação on-chain (Automata) ou por comitê de verificadores **(a verificar)** | C | Torna a admissão de D4–D7 auditável; qualquer um confere quais binários são aceitos | Médio; verificação on-chain de SNP/TDX é cara (a verificar custo) |
| D10 | **Histórico de execuções** só local na CVM1 | A5, `api-server.js:949-988` | Recibo de execução ancorado on-chain (hash), resultado cifrado no IPFS para o comprador | — | Rastreabilidade e não-repúdio (direção 1) | Baixo, com D1 e D3 |
| D11 | **Execução replicada heterogênea** (não existe) | — | O mesmo job em k executores de fabricantes/nuvens diferentes (AMD SNP + Intel TDX); o contrato compara os hashes dos resultados | O | **Integridade** frente a um TEE quebrado (CacheWarp, Heckler/WeSee etc., a verificar quais afetam integridade) | **Piora o sigilo**: k cópias do dataset, basta um TEE vazar. Exige aplicação determinística. Deve ser **política opcional do dono do dataset**, não padrão |
| D12 | **Verificação por agentes** (E4, futura) | brainstorm 03 | Vários verificadores independentes (modelos/operadores distintos) e relatório por quórum | O | Reduz confiança num único agente | Futura; só registrar a compatibilidade |
| D13 | Interface web / API | `api-server.js:996+` | Qualquer um roda o cliente; nada privilegiado nele | L | Pequeno | Pequeno; só faz sentido depois de D2 e D6 |

## 3. Pontos que mudam a análise

### 3.1 Abrir os executores muda o modelo de ameaça do TEE
Na nuvem, o adversário do TEE é o operador da nuvem, que dificilmente faz ataque físico. Num
mercado aberto (D5), qualquer um pode alugar ou comprar a máquina **para atacar o job**: ataques
que exigem acesso físico ou controle do firmware (BadRAM, entre outros, a verificar a lista)
ficam ao alcance do adversário. Saídas possíveis:
- **Abertura em camadas:** o dono do dataset escolhe o nível exigido (só nuvens públicas
  conhecidas, qualquer CVM atestada, ou replicação heterogênea). Se a atestação permite provar
  em qual nuvem a CVM roda é **(a verificar)**.
- **Consórcio** em vez de aberto: os executores são de operadores conhecidos.

### 3.2 A atestação volta ao escopo
A D-017 deixou a atestação implícita e fora do escopo. Em qualquer forma aberta (D4, D5, D7, D9),
**a atestação é o mecanismo de admissão**: sem ela, abrir peers equivale a confiar em
desconhecidos. A E3 não fecha sem rever o item (iii) da D-017, ao menos no nível de desenho.

### 3.3 Integridade e sigilo puxam em direções opostas
Replicar (D7, D11) melhora integridade e piora sigilo (mais cópias, mais TEEs para quebrar).
Limiar de chaves (D4) melhora sigilo e piora disponibilidade (precisa de t nós no ar). O texto
deve dizer qual propriedade cada mecanismo compra e qual paga.

### 3.4 Consenso só no plano de controle
Nenhum dado (dataset, aplicação, resultado) passa por consenso. O ledger ordena eventos (compra,
admissão, liberação de chave, recibo); os dados vão por armazenamento endereçado por conteúdo e
canais atestados. Isso mantém o custo do consenso independente do tamanho do dataset.

## 4. Casos de uso concretos (o P5 dos revisores: quem opera o quê)

| Caso | Donos de dados | Desenvolvedores | Quem seriam os peers | Grau natural |
|---|---|---|---|---|
| **Validação de CNH / identidade** (as apps `cnh-signature-validator.py` e `cnh-qrcode.py` já existem) | DETRANs estaduais / Senatran | Bancos, fintechs, cartórios | Cada DETRAN opera um nó de chave (D4) e um validador (D1); executores em nuvens distintas | **C** |
| Pesquisa clínica multi-hospitalar | Hospitais | Grupos de pesquisa, farmacêuticas | Hospitais como nós de chave e de armazenamento; executores contratados | C → O |
| Dados abertos governamentais com microdados sensíveis (ex.: estatística pública) | Órgãos de estatística | Pesquisadores | Órgão + universidades | C |
| Mercado aberto de dados e modelos | Qualquer um | Qualquer um | Executores e builders abertos com atestação e *stake* | O |

O caso CNH é o mais forte para o artigo: o repositório já tem as aplicações, os stakeholders são
naturalmente múltiplos e mutuamente desconfiados (estados diferentes, setor público × privado), e
o consórcio é o grau realista. Um mercado totalmente livre pode ficar como extensão.

## 5. Primeira triagem (proposta, para discutir)

| Valor | Itens | Comentário |
|---|---|---|
| **Pré-requisito** (sem isso nada mais vale) | A16 (cifrar o dataset), D2 (carteiras próprias), A4 (pedido assinado) | Baratos; mexem no código existente |
| **Alto valor, custo baixo/médio** | D1 (ledger persistente em consórcio), D3 (armazenamento distribuído), D9 (registro de medições), D10 (recibos on-chain) | Dão sentido ao ledger e respondem ao R2 |
| **Alto valor, custo alto** | D4 (comitê de chaves por limiar), D5+D6 (executores abertos com fila on-chain) | D4 é a contribuição de sigilo; D5 a de disponibilidade e anticensura |
| **Condicional** | D7 (quórum de builders), D11 (replicação heterogênea) | D7 depende de build reproduzível; D11 só como política opcional |
| **Baixo valor agora** | D8, D12, D13 | Registrar e não implementar |

## 6. Perguntas para decidir

1. **Grau de abertura alvo:** consórcio (C), aberto com admissão (O), ou C no artigo e O como extensão?
2. **Caso de uso âncora:** validação de CNH com DETRANs como peers?
3. **Atestação:** reabrir o item (iii) da D-017 para a E3, ao menos no desenho?
4. **Ledger:** consórcio permissionado (Besu/QBFT) ou L2 pública?
5. **Prioridade:** D4 (sigilo) ou D5/D6 (disponibilidade/anticensura) como contribuição principal da E3?
6. Os achados A16 e A17 entram já no SAC como limitação ou correção?

## 7. D1 em detalhe: o que é "um ledger melhor"

**O que o ledger faz no DNAT.** Registra ativos (dono, preço, CID, hash), registra compras e
paga os donos. É a **fonte de verdade** sobre quem tem direito a quê. Com o D4, passa a ser
também o que o comitê de chaves consulta antes de liberar uma chave: se o ledger mente, o
comitê libera a chave para quem não devia.

**O problema de um nó único.** Quem controla o único nó controla essa verdade: pode inventar
uma compra que não houve, esconder uma que houve (censura), reordenar transações ou apagar
história. Hoje isso é ainda mais forte, porque o servidor também assina tudo com uma carteira só
(A3). Distribuir o ledger significa que **nenhum participante sozinho** consegue fazer isso.

**Opções** (todas rodam o contrato Solidity atual sem reescrever; tempos e custos **a verificar**):

| Opção | Quem valida os blocos | Quem pode trapacear | Finalidade | Custo por transação | Pagamentos com valor real |
|---|---|---|---|---|---|
| **Consórcio permissionado** (Hyperledger Besu com QBFT) | Os stakeholders (ex.: cada DETRAN um validador) | Só um conluio de ≥ 1/3 dos validadores | Imediata (BFT), segundos | ~zero (gas pode ser 0) | Não por si só: a moeda da rede não tem mercado |
| **L2 pública** (rollup sobre Ethereum: Arbitrum, Optimism, Base) | Um sequenciador ordena; a Ethereum garante a integridade | O sequenciador pode atrasar/censurar por um tempo; não pode forjar estado | Segundos (soft); minutos a horas para finalidade na L1 | Centavos | Sim (ETH, stablecoins) |
| **L1 pública** (Ethereum) | Milhares de validadores | Praticamente ninguém | ~13 min | Alto e variável | Sim |

**Tensão com o modelo de incentivos (§8):** recompensar peers abertos em cripto pede uma rede
**pública** (L2), onde a moeda tem valor; o caso CNH com DETRANs pede um **consórcio**. Um
desenho híbrido é possível: contrato e pagamentos numa L2 pública, comitê de chaves (D4) em
consórcio. Fica como pergunta.

**Custo de privacidade de uma rede pública:** compras e execuções ficam visíveis para todos
(quem comprou acesso a qual dataset, quando, quantas vezes). Para dados de identidade isso pode
ser sensível **(a avaliar)**.

## 8. Modelo de incentivos: pagamento por execução (proposta do Steylor, D-020)

**Ideia.** O usuário paga **por execução**. Cada pagamento é dividido entre:
1. **Donos dos ativos** (dataset e aplicação): o preço deles;
2. **Peers de armazenamento** que forneceram os blocos cifrados ao executor: um pequeno bônus;
3. **Nó executor** que rodou o job numa CVM verificada: um pequeno bônus.

Todos os ativos são negociados em cripto. Ativos populares passam a ser guardados por muitos
peers (mais demanda, mais bônus) e nós se candidatam a executar desde que usem uma CVM verificada.

**Esclarecimento de termos.** Os dados ficam no **IPFS**, não na blockchain; a blockchain guarda
só o CID, o hash e o preço. "Quem armazena" = quem fixa os blocos cifrados no IPFS. "CVM
verificada" = CVM cuja **medição do runtime do executor** está na lista permitida (D9); a
aplicação em si é verificada pelo digest e pela assinatura do builder (E2b.4), não pela medição
da CVM.

**Fluxo esboçado**
1. Comprador deposita o valor da execução em **escrow** no contrato e assina o pedido (A4).
2. Um executor admitido reivindica o job (fila on-chain, D6) e deposita uma garantia (*stake*).
3. O executor busca os blocos no IPFS e anota **quais peers serviram quais blocos**.
4. O comitê (D4) libera as chaves ao executor atestado; o job roda.
5. O executor publica um **recibo assinado**: `(id do job, H(resultado cifrado), peers que
   serviram e bytes de cada um)`.
6. O contrato verifica a assinatura do recibo e divide o escrow. Sem recibo até o prazo: o
   comprador é reembolsado e a garantia do executor é cortada.

**Por que a CVM resolve a prova de armazenamento.** O IPFS não prova quem serviu os dados. Mas o
executor é código medido e atestado: o que ele declara no recibo é confiável na medida da
atestação. Isso dispensa uma prova de armazenamento à parte (estilo Filecoin). A escolha dos
peers de onde buscar também fica no código medido (ex.: aleatória entre os que anunciam o CID),
o que impede o operador do executor de favorecer os próprios peers.

**Verificação barata no contrato.** Verificar uma atestação SNP/TDX on-chain é caro **(a
verificar)**. Alternativa: o executor gera uma chave dentro da CVM e a **registra uma vez**, com a
atestação verificada pelo comitê ou por D9; daí em diante cada recibo é só uma assinatura
comum (`ecrecover`), barata.

**Problemas em aberto**
| # | Problema | Direção de solução |
|---|---|---|
| I1 | **Ativos pouco usados** não atraem peers e podem sumir | O dono continua responsável por fixar o próprio ativo; o bônus é só para os populares |
| I2 | **Sybil:** uma pessoa com muitas identidades de armazenamento | Pagar por **bytes servidos** ao executor, não por fixar; várias identidades não aumentam o que é servido |
| I3 | O comitê de chaves (D4) também trabalha | Incluir uma fatia para os nós de chave? |
| I4 | Mudança no contrato: hoje `purchaseAccess` paga uma vez (`DnatMarketplace.sol:214-265`) | Passar a escrow por execução; decidir se a compra única continua existindo |
| I5 | Token próprio ou moeda da rede | Recomendação: **sem token próprio** (escopo, regulação; Lei 14.478/2022 a verificar); usar a moeda nativa ou uma stablecoin |
| I6 | Executor que reivindica e não entrega | Garantia (*stake*) cortada e prazo de reatribuição |
| I7 | Privacidade dos pagamentos numa rede pública | Ver §7 |

## 9. Como garantir que a CVM executora é nova e de uso único

**O que se quer provar.** Não dá para provar *quando* uma CVM foi ligada. O que importa (D-006) é
outra coisa: **esta CVM nunca processou outro job**. Isso se prova em camadas independentes:

| # | Camada | Mecanismo | O que impede |
|---|---|---|---|
| E1 | **Código medido** | A atestação cobre todo o boot (firmware, kernel, initrd, cmdline; UKI) e o rootfs somente leitura (dm-verity). Sem disco persistente. Esse código implementa o uso único: aceita um job, apaga as chaves e desliga | O operador mudar o comportamento: qualquer alteração muda a medição e o peer é recusado pela lista D9 |
| E2 | **Chave efêmera por instância** | Gerada na RAM no boot e ligada ao relatório (`REPORT_DATA = H(chave pública)`). Só aquela instância a tem | Que outra CVM se passe por esta |
| E3 | **Uso único no contrato** | Cada chave de instância é registrada uma vez; ao receber um job, o contrato a marca como **consumida**. O comitê não libera chaves para uma chave consumida | Reuso da CVM, mesmo que o guest tenha um bug: o ledger impõe sozinho |
| E4 | **Frescor no claim** | O comitê envia um nonce; a CVM responde com um relatório novo sobre `H(chave ‖ nonce ‖ job)` | Replay de um relatório antigo; prova que a instância está viva e tem a chave agora |
| E5 | **Sem clonagem nem snapshot** | Política do guest com debug e migração desligados (SNP: bits de política sem debug e sem agente de migração; TDX: `ATTRIBUTES.DEBUG = 0`, não migrável). A política aparece no relatório e é conferida pelo comitê **(a verificar campos exatos)** | O operador ler, copiar ou restaurar a memória da CVM para rodar o job duas vezes |
| E6 | **Idade máxima** | O bloco do registro da chave dá o horário; o contrato recusa chaves mais velhas que X | CVMs ociosas por tempo demais no warm pool (salvaguarda da D-006) |

**O que continua fora.** O operador pode desligar a CVM (disponibilidade, coberta por stake e
prazo); canais laterais (D-005, D-014). Na Azure, a raiz medida é o *paravisor* da Microsoft com
vTPM, e a imagem do guest é medida pelos PCRs, o que põe o paravisor na TCB **(a verificar)**.

## 10. Comitê de chaves: captura e perda (em discussão, sob D-023)

**Esclarecimento.** A chave nunca vai para o comprador. Vai para a **CVM executora escolhida pela
rede**; o comprador recebe só o resultado, cifrado com a chave pública dele.

**Parâmetro central:** com N partes e limiar t, capturar exige t partes; perder exige N − t + 1.
Subir t dificulta o conluio e facilita a perda; o ajuste é por dataset (política).

**Impedir que um peer junte t partes (captura)**
| Mecanismo | Ideia |
|---|---|
| Sorteio aleatório verificável | Comitê de cada ativo sorteado on-chain (VRF/beacon), ponderado por stake; ninguém escolhe onde cai |
| Custo de Sybil | Cada vaga exige stake; muitas identidades custam proporcionalmente |
| Uma vaga por chip físico | O relatório SNP traz o `CHIP_ID` do processador; o contrato limita a uma vaga por chip **(TDX: a verificar)** |
| Partes dentro de CVMs | Mesmo com t partes, o operador não as lê: estão na memória cifrada e só o código medido as usa. Capturar exige t partes **e** quebrar o TEE |
| Rotação proativa (*proactive resharing*) | Periodicamente as partes são refeitas sem reconstruir a chave; partes antigas viram lixo, então não dá para acumular ao longo do tempo |
| Diversidade obrigatória | Limite de partes por fabricante (AMD/Intel), lido da atestação |

**Impedir que a chave se perca (disponibilidade)**
| Mecanismo | Ideia |
|---|---|
| Limiar t < N | Tolera até N − t nós perdidos |
| Redistribuição | Quando um nó sai ou cai, os demais repassam uma parte nova a um substituto sorteado, sem remontar a chave |
| Prova de vida + stake | Nós respondem a desafios periódicos; quem some perde stake e é substituído antes de o comitê chegar a t |
| Nós de chave não são efêmeros | Ao contrário dos executores, precisam durar; a parte fica na RAM da CVM e a resiliência vem da redundância, não de disco (selar no disco prende a parte ao chip, que pode morrer) |
| Dono como último recurso | O dono do ativo pode guardar a própria chave e recriar o comitê. Sem dono e com mais de N − t perdas, o ativo se perde: **falha segura** (perder é melhor que vazar) |

## 11. Sem nós especiais: revisão de todos os papéis (D-023, D-024)

**Regra.** Todo papel com poder é preenchido por **sorteio verificável ponderado por stake** entre
quem cumpre os requisitos objetivos (atestação, stake), nunca por identidade fixa. Quem age mal
perde stake, e **qualquer um** pode apresentar a prova do mau comportamento e ganhar parte dela.

| Papel | Antes | Sob a regra | Status |
|---|---|---|---|
| Validadores (D1) | Stakeholders | Validadores da rede pública (PoS) | ✅ D-023 |
| Comitê de chaves (D4) | Grupo fixo | Sorteio por stake, uma vaga por chip, rotação, substituição (§10) | ✅ D-024 |
| Builders (D7) | Quem reivindica | N builders **sorteados** entre os admitidos | ✅ D-025 |
| Executores (D5/D6) | Quem reivindica primeiro | **Sorteio ponderado por stake** entre os elegíveis pela política do dataset. Reivindicar por ordem favorece o mais rápido e o maior | ✅ D-025 |
| Peers de armazenamento (D3) | Qualquer um | Qualquer um; o executor escolhe aleatoriamente de quem buscar (código medido) | ✅ D-020 |
| Admissão de nós novos | Comitê fixo | **Comitê de verificação sorteado** entre nós já admitidos; um quórum assina e o contrato aceita. Verificação direta pelo contrato quando for barata. **Todo nó que recebe cripto também tem de servir nesse comitê** | ✅ D-025 |
| Lista de medições (D9) | Multisig de stakeholders | Qualquer um propõe uma medição com stake. Aceitação exige (i) builders sorteados reproduzindo a imagem do runtime com a mesma medição, (ii) votação ponderada por stake e (iii) prazo de contestação (*timelock*) | ✅ desenho, sem implementação (D-026) |
| Fonte de aleatoriedade | — | Beacon da própria rede, gerado por consenso (ex.: RANDAO da Ethereum). Um oráculo externo (ex.: VRF de terceiros) seria um nó especial. Viés possível do último proponente **(a verificar)** | ✅ D-025 |
| Administração do contrato | Nenhuma (o contrato atual não tem `owner`) | Manter **sem chave de admin**; atualização só por votação com *timelock* | ✅ D-025 |
| Fiscalização (*slashing*) | — | Qualquer um denuncia com prova e recebe parte do stake cortado | proposta |
| Dono do ativo | Dono | Continua com poder **sobre o próprio ativo** (preço, política, recriar o comitê). É propriedade, não privilégio na rede | ✅ |

**Dois riscos que a regra cria**
- **Sequenciador de L2 é um nó especial.** Numa L2 comum, um único sequenciador ordena as
  transações. Para cumprir a regra: usar a L1, ou uma L2 com sequenciamento descentralizado
  (*based rollup*), ou ao menos inclusão forçada pela L1 como saída **(a verificar opções)**.
- **Concentração de stake.** Peso por stake favorece quem tem mais capital. É aceito pelo
  princípio (vem do consenso), mas é atenuado pelo teto de uma vaga por chip e pela diversidade
  de fabricante.

## 12. Build sem que ninguém veja o código (D-027)

**Princípio.** "Ninguém vê" = nenhum **operador** vê. O código só existe em claro dentro de uma
CVM atestada, rodando código medido; a chave do código vem do comitê (D4) e só para builders
sorteados e atestados.

**Fluxo**
1. **Fase 1 (fetch, com rede, sem código):** baixa dependências e imagens-base declaradas.
   Dependências são públicas: aqui não há segredo, só integridade (hashes do lockfile).
2. **Fase 2 (assemble, sem rede, em CVM):** a CVM recebe a chave do código do comitê, decifra o
   código **dentro dela**, junta com as dependências e monta a imagem OCI.
3. **Varredura e proveniência** dentro da CVM (E2b.4).

**Por que a separação de CVMs (opção B da E2b.3) passa a ser o padrão.** Com builders abertos,
uma dependência maliciosa que escape do container na fase 1 cairia na CVM que depois recebe o
código e a chave. Fazendo a fase 1 numa CVM (ou máquina) separada, que nunca recebe código nem
chave, esse caminho fecha. A fase 2 recebe só as dependências, conferidas por hash.

**Um único artefato com N builders**
1. Os N builders sorteados fazem a fase 2 independentemente e calculam o digest da imagem.
2. Um **líder sorteado** entre eles gera uma chave nova `K_app`, cifra a imagem, publica no IPFS
   e divide `K_app` entre o comitê de chaves.
3. O líder envia `K_app` aos outros N − 1 builders por canal atestado; cada um decifra o blob
   publicado e confere que o digest é **igual ao do próprio build**.
4. Cada builder assina `(digest, CID do blob cifrado)`. O contrato ativa a app com ≥ N
   assinaturas iguais.
Resultado: chave aleatória, um só blob, e qualquer builder desonesto é detectado pela divergência
de digest. O executor recebe só `K_app`, nunca a chave do código-fonte.

**Quem tem o código durante o build**
- **Desenvolvedor:** já é dono do código. Cifra localmente com `K_code` nova e publica o blob no IPFS.
- **Rede, peers, operadores:** só o blob cifrado e partes de chave cifradas.
- **CVMs de fase 2 sorteadas:** as únicas que remontam `K_code` e veem o código, em memória
  cifrada; destruídas ao fim (uso único).

Como `K_code` chega às CVMs (em aberto):
| Opção | Como | Prós | Contras |
|---|---|---|---|
| **A. Pelo comitê** | O dev divide `K_code` em partes e cifra cada uma para a chave pública atestada de um nó do comitê; o comitê libera às CVMs sorteadas | O dev pode ficar offline após enviar | `K_code` fica guardada na rede, sem necessidade depois do build |
| **B. Direto às CVMs sorteadas** | Após o sorteio, o cliente do dev cifra `K_code` para a chave pública atestada de cada builder sorteado e publica | `K_code` nunca fica armazenada; exposição mínima | O dev precisa estar online numa segunda rodada |

Em ambas, o envio pode ser público (on-chain ou IPFS): cada parte cifrada só abre dentro da CVM
cuja chave foi atestada e registrada no contrato. O dataset, ao contrário, **precisa** do comitê,
porque a execução acontece depois, com o dono offline.

## 13. Literatura a verificar (escopo da E3, ETAPAS.md)
Ekiden/Oasis (key manager), Secret Network, Phala/dstack (KMS), CCF (Microsoft), Marlin Oyster,
Flashbots SUAVE/TEE-builders, Automata (atestação on-chain), Trustee/KBS (CoCo), Sigstore/Rekor;
lista de ataques a TEE que exigem acesso físico × só software (BadRAM, CacheWarp, Heckler, WeSee,
Heracles).
