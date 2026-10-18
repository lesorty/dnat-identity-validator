# E3 — Descentralização

**Status:** 🗄️ **ARQUIVADO (2026-10-17, D-031).** Decidiu-se com o orientador não distribuir o
sistema: executar em CVM atestável não deixa ganho de confiança que justifique o custo. Este
documento fica como registro da análise.
**Status original:** CONCLUÍDA (2026-10-14). Arquitetura decidida (D-018 a D-029). Nada implementado nem
medido (D-007). Verificação da literatura e caso âncora adiados para depois da arquitetura
(D-023 iii): tudo que depende de fonte externa está marcado **(a verificar)**.
**Base auditada:** `main` @ `aa05b92`.
**Discussão completa:** [brainstorm/04_descentralizacao.md](../brainstorm/04_descentralizacao.md) ·
ideia estacionada: [brainstorm/05_imagem_pronta.md](../brainstorm/05_imagem_pronta.md)
**Diagramas:** [arquitetura](../diagramas/E3_arquitetura.svg) ·
[execução e pagamento](../diagramas/E3_execucao.svg) · [build confidencial](../diagramas/E3_build.svg)

## E3.1 — Pergunta e resposta

**Pergunta (ETAPAS):** distribuir o sistema entre operadores e provedores aumenta a confiança de
fato? O que vale e o que não vale fazer?

**Resposta.** Sim, em quatro frentes, e com dois custos que precisam ser declarados.

| Frente | Antes | Depois | Mecanismo |
|---|---|---|---|
| **Sigilo frente a quem guarda chaves** | Uma chave global na CVM1 (A2) | Chave por ativo em partes, t de N, só remontada dentro de CVM atestada | Comitê de chaves sorteado por stake (D4) |
| **Verificabilidade e anticensura** | Um operador decide quem executa e o que vale (A3, A4, A5) | Pedido, sorteio, recibo e pagamento públicos e ordenados por consenso | Ethereum L1, contrato sem admin, sorteios on-chain |
| **Disponibilidade** | Um nó IPFS, um builder, um executor | Qualquer peer armazena, builda ou executa, com incentivo | Pagamento por execução dividido entre os participantes |
| **Ausência de nós especiais** | O operador da CVM1 era especial por natureza | Todo papel com poder vem de sorteio ponderado por stake | Princípio de igualdade (D-023, D-024) |

**O que distribuir não resolve:** o sigilo do dado *durante* a execução continua dependendo do
TEE. Isso confirma a hipótese do brainstorm 01, com uma exceção: na custódia de chaves,
distribuir aumenta o sigilo de fato.

**Custos declarados:** (i) abrir os executores permite que o adversário seja **dono do hardware**
(ataques físicos, ex.: BadRAM); (ii) replicar execução melhora a integridade e **piora o sigilo**.
Os dois viram escolha do dono do dataset na política (D-021).

## E3.2 — Achados novos no código

| # | Achado | Evidência | Decisão |
|---|---|---|---|
| A16 | O dataset é publicado no IPFS **em claro**; só a aplicação é cifrada | `smart-contract/scripts/api-server.js:704-705`, `:860-861` | **TODO**: cifrar o dataset (D-018). Pré-requisito de qualquer armazenamento distribuído |
| A17 | Ledger em nó Hardhat único, em memória, reimplantado a cada boot | `docker/root-entrypoint.sh:78`, `:87-89` | Não é problema no momento (D-018); some com a L1 |

## E3.3 — Princípios

1. **Igualdade (D-023, D-024).** Nenhum nó é especial por natureza. Todo papel com poder é
   preenchido por **sorteio verificável ponderado por stake** entre quem cumpre requisitos
   objetivos (atestação, stake). Quem age mal perde stake; qualquer um pode denunciar com prova e
   receber parte do stake cortado. O dono de um ativo manda só no próprio ativo: é propriedade,
   não privilégio na rede.
2. **Atestação como admissão (D-021).** Com peers abertos, a atestação é o que separa uma CVM
   legítima de um desconhecido. Revisa o item (iii) da D-017: a atestação volta ao escopo, no
   nível de desenho.
3. **Consenso só no plano de controle.** Dados (dataset, aplicação, resultado) nunca passam por
   consenso; o ledger ordena eventos e o IPFS guarda blobs cifrados endereçados por conteúdo.
4. **Política por dataset (D-021).** O dono escolhe o nível de executor exigido, a replicação e o
   limiar t de N.
5. **Falha segura.** Perder um ativo é preferível a vazá-lo.

## E3.4 — Componentes e papéis

| Papel | Quem pode ser | Requisito | Como é escolhido | Recebe | Nunca vê em claro |
|---|---|---|---|---|---|
| **Rede (D1)** | Validadores da Ethereum | Os da própria rede | PoS da Ethereum | — | Nada: só hashes, CIDs e assinaturas |
| **Contrato** | — | Sem chave de admin; mudança só por votação com prazo de contestação | — | — | — |
| **Comitê de verificação** | Todo nó que recebe cripto, inclusive peers de armazenamento | Stake | Sorteio por stake | Parte da fatia de admissão **(parâmetro)** | — |
| **Comitê de chaves (D4)** | Qualquer CVM atestada | Stake; uma vaga por chip físico | Sorteio por stake, por ativo; rotação periódica | Fatia de cada execução | A chave inteira (só uma parte) |
| **CVM de fetch (fase 1)** | Qualquer builder admitido | Atestação, stake | Sorteio por stake | Fatia do build **(parâmetro)** | Código |
| **CVMs de assemble (fase 2, D7)** | Qualquer builder admitido | Atestação, stake | N sorteadas por stake, uma delas líder | Fatia do build | — (vê o código só dentro da CVM) |
| **Executores (D5, D6)** | Qualquer CVM atestada, nova e de uso único | Atestação, stake, nível exigido pela política | Sorteio por stake entre os elegíveis | Bônus por execução + stake de volta | — (vê dados só dentro da CVM) |
| **Peers IPFS (D3)** | Qualquer um | Stake (para servir no comitê de verificação) | O executor escolhe aleatoriamente de quem buscar | Bônus por bytes servidos | Tudo: só guarda blobs cifrados |
| **Comprador** | Qualquer um | Carteira própria | — | Resultado cifrado para a chave dele | Dataset e aplicação |
| **Dono do dataset / desenvolvedor** | Qualquer um | Carteira própria | — | Preço do ativo por execução | O ativo do outro |

**Aleatoriedade:** beacon da própria rede, gerado por consenso (RANDAO); sem oráculo externo
(D-025). **Moeda:** ETH (D-027). **Pagamentos:** visíveis on-chain (D-027).

## E3.5 — Fluxos

### F1 — Admissão de um nó
1. A CVM gera um par de chaves na RAM e obtém o relatório de atestação com
   `REPORT_DATA = H(chave pública)`.
2. Um **comitê de verificação sorteado** confere: assinatura do fabricante, medição na lista D9,
   política (sem debug, sem migração), `CHIP_ID`, nível de plataforma.
3. Um quórum assina; o contrato registra a chave do nó, o nível e o stake depositado.
**Pendente:** *bootstrap* — os primeiros nós não têm comitê que os verifique. Caminho coerente com
a igualdade: verificação direta pelo contrato na partida, ainda que cara **(a verificar custo)**.

### F2 — Registro de dataset
1. O dono cifra o dataset localmente com chave nova (A16) e publica o blob no IPFS.
2. O contrato sorteia o comitê de chaves do ativo; o dono divide a chave em N partes, cada uma
   cifrada para a chave pública atestada de um nó.
3. O dono registra CID, hash, preço e política (nível de executor, replicação, t de N).

### F3 — Build confidencial (D-027, D-028, D-029) · [diagrama](../diagramas/E3_build.svg)
1. O desenvolvedor cifra o código com `K_code` e publica no IPFS.
2. Pede o build no contrato (CID, hashes de Dockerfile e lockfile, N).
3. O contrato sorteia a CVM de fetch, N CVMs de assemble e um líder.
4. **Fase 1:** a CVM de fetch baixa dependências e bases da internet **sem nunca receber o
   código** e publica o resultado no IPFS, por hash. CVM separada da fase 2 por padrão: um escape
   na fase 1 não alcança código nem chave.
5. O cliente do desenvolvedor cifra `K_code` para a chave pública de **cada** CVM de assemble
   sorteada (opção B). `K_code` nunca fica armazenada na rede.
6. **Fase 2:** cada CVM de assemble busca código e dependências, corta a rede, decifra o código
   **dentro dela**, monta a imagem OCI, roda a varredura e calcula o digest.
7. O líder cifra a imagem com `K_app` nova, publica no IPFS, divide `K_app` com o comitê de
   chaves e a envia às outras CVMs, que conferem se o digest é o mesmo do próprio build.
8. Cada builder assina `(digest, CID)`; o contrato ativa a aplicação com N assinaturas iguais.
   Builder desonesto é detectado pela divergência de digest. As CVMs são destruídas.

### F4 — Execução e pagamento · [diagrama](../diagramas/E3_execucao.svg)
1. O comprador assina o pedido (dataset, app, chave pública dele) e deposita o valor em escrow.
2. O contrato sorteia o executor por stake entre os elegíveis pela política (k executores de
   fabricantes distintos, se a política pedir replicação). O executor trava stake.
3. A CVM busca os blobs cifrados nos peers IPFS, escolhidos aleatoriamente pelo código medido, e
   anota quem serviu quantos bytes.
4. Envia ao comitê um relatório novo sobre `H(chave ‖ nonce ‖ job)`. Cada nó confere no ledger:
   pagamento, pedido assinado, executor sorteado, chave não consumida. Com t partes, a CVM monta
   as chaves do dataset e de `K_app`.
5. Confere o digest e as assinaturas da imagem, roda o container sem rede, cifra o resultado para
   o comprador, publica no IPFS e se destrói.
6. Publica o recibo assinado `(job, H(resultado), peers e bytes)`. O contrato verifica a
   assinatura (`ecrecover`) e divide o escrow: donos (preço), peers fornecedores (bytes), executor
   (bônus + stake), comitê (fatia). Sem recibo no prazo: reembolso e corte de stake.

## E3.6 — Garantias

### Comitê de chaves: captura e perda (D-024)
Com N partes e limiar t: capturar exige t partes; perder exige N − t + 1.

| Contra captura | Contra perda |
|---|---|
| Sorteio por stake; ninguém escolhe onde cai | t < N: tolera N − t nós perdidos |
| Cada vaga custa stake (Sybil caro) | Redistribuição a substitutos sem remontar a chave |
| Uma vaga por chip físico (`CHIP_ID`; TDX a verificar) | Prova de vida; quem some perde stake |
| Partes só em CVMs: capturar exige t partes **e** quebrar o TEE | Nós de chave duráveis; resiliência por redundância, não por disco |
| Rotação proativa: partes antigas viram lixo | Dono pode recriar o comitê; sem dono, falha segura |

### CVM executora nova e de uso único (D-022, provisória)
O que se prova não é *quando* a CVM ligou, e sim que **ela nunca processou outro job**.

| # | Camada | Impede |
|---|---|---|
| E1 | Boot medido (UKI, rootfs dm-verity, sem disco persistente); o código impõe um job só | Mudar o comportamento sem mudar a medição |
| E2 | Chave efêmera gerada na RAM e ligada ao relatório | Outra CVM se passar por esta |
| E3 | Chave **consumida** no contrato ao receber o job | Reuso, mesmo com bug no guest |
| E4 | Nonce no claim | Replay de relatório antigo |
| E5 | Política sem debug e sem migração, conferida no relatório | Clonar ou restaurar a memória |
| E6 | Idade máxima a partir do bloco de registro | CVMs ociosas por tempo demais |

### Código do desenvolvedor no build (D-027, D-029)
Só existe em claro na máquina do desenvolvedor e na memória cifrada das CVMs de assemble
sorteadas, destruídas ao fim. Rede, peers e operadores veem só blobs e partes cifrados.

## E3.7 — Modelo de ameaça: o que muda

| Tema | Efeito | Tratamento |
|---|---|---|
| Adversário dono do hardware | Ataques físicos ao TEE ficam viáveis (BadRAM: SPD adulterado cria aliases de memória e permite ler/repor memória cifrada e forjar atestação no SEV-SNP; corrigido por firmware) **(a verificar detalhes)** | Nível de executor na política; diversidade de fabricante |
| Replicação | + integridade, − sigilo (k cópias) | Só como opção da política |
| Concentração de stake | Mais capital, mais vagas | Aceito pelo princípio; atenuado por uma vaga por chip |
| Viés do beacon | O último proponente pode influenciar o RANDAO **(a verificar)** | Declarar; avaliar atraso no uso do beacon |
| Privacidade dos pagamentos | Quem comprou o quê fica público | Aceito (D-027) |
| Canais laterais, X8 | Sem mudança | Continuam limitação declarada e fora de escopo (D-005, D-014) |

## E3.8 — O que vale e o que não vale

| Categoria | Itens |
|---|---|
| **Adotado** | D1 (Ethereum L1), D3 (peers IPFS com incentivo), D4 (comitê de chaves), D5+D6 (executores abertos, sorteio por stake), D7 (N builders + líder), comitê de verificação, recibos on-chain, pagamento por execução, contrato sem admin, carteiras próprias e pedido assinado (fecham A3 e A4) |
| **Opção da política do dataset** | Nível de executor, replicação heterogênea (D11), t de N |
| **Desenho sem implementação** | D9: qualquer um propõe uma medição com stake, builders sorteados reproduzem a imagem a partir do código público, votação por stake, prazo de contestação (D-026) |
| **Estacionado** | Imagem OCI pronta enviada pelo desenvolvedor, níveis 0/1/2 (D-029); verificação por agentes (D12 → E4) |
| **Baixo valor, não fazer** | D8 (cache distribuído de dependências), D13 (frontend distribuído: qualquer um já pode rodar o cliente) |
| **Descartado** | Consórcio de stakeholders e multisig na D9 (ferem a igualdade, D-023); L2 por ora (sequenciador único, D-028); oráculo externo de aleatoriedade (D-025) |

## E3.9 — Impacto em outras etapas e no código

**E2 / E2.4 (medição).** Além do ciclo da CVM, medir: atestação e verificação pelo comitê, nonce
no claim, sorteio, liberação t de N e o **custo das transações na L1** por execução (pedido,
sorteio, recibo, liquidação), com cerca de 12 s por bloco e gas por transação **(a verificar
números)**; o `smart-contract/scripts/measure-gas.js` serve de base. O warm pool (D-006) passa a
ser alimentado por sorteio, não por reivindicação.

**E2b.** A CVM de fetch separada (opção B da E2b.3) vira o padrão. Os pontos abertos da E2b.4
ficam respondidos: a lista de medições é a D9; o segundo builder obtém o código pela opção B.

**E4.** A verificação por agentes entra como papel futuro sob a mesma regra (verificadores
sorteados por stake).

**E5.** Tese candidata: *marketplace confidencial sem operador*, em que build, custódia de chaves
e execução são papéis abertos, sorteados por stake e admitidos por atestação, com recibo
verificável on-chain.

**Código (quando implementar).**
- Contrato: escrow por execução; registro de nós (chave atestada, nível, stake, `CHIP_ID`);
  sorteios; chaves de instância consumidas; recibos e divisão do pagamento; prazos e cortes.
- Cliente: carteira própria; cifrar o dataset (A16); pedido assinado; envio de partes de chave
  cifradas para nós atestados.
- Novos serviços: nó de chave, nó de verificação, agentes de CVM de fetch, assemble e execução.

## E3.10 — Pendências

**Para o desenho**
- *Bootstrap* da admissão (primeiros nós).
- Parâmetros: N, t, stake mínimo, fatias de cada papel, prazos, idade máxima das CVMs.
- Como a fatia de admissão remunera o comitê de verificação.

**(a verificar), depois da arquitetura (D-023 iii)**
- Literatura: Ekiden/Oasis, Secret Network, Phala/dstack, CCF, Marlin Oyster, Flashbots
  SUAVE/TEE-builders, Automata, Trustee/KBS, Sigstore/Rekor; protocolos de redistribuição
  proativa de partes.
- BadRAM e outros ataques físicos × só software (CacheWarp, Heckler, WeSee, Heracles).
- Campos de política e `CHIP_ID` no SNP; equivalentes no TDX; paravisor da Azure na TCB.
- Custo de verificar atestação on-chain; viés do RANDAO; tempos e gas na Ethereum.
- Caso âncora (adiado).
