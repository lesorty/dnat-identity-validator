# Revisão do sistema (15/11/2026)

Varredura de bugs em três frentes independentes (lado DNAT: contrato, CVM1, CVM de job, builder e
pilha Docker; o Juiz: `model_gate`; requisitos × código), remake da interface e o que falta para o
sistema funcionar como proposto. Cada achado de bug foi conferido no código; os marcados
CONFIRMADO foram reproduzidos (teste ou script).

## 1. O que foi feito nesta revisão

### Interface (`smart-contract/web/`)

Página única em português, sem scripts de terceiros (antes: React, ReactDOM e Babel do unpkg sem
versão fixa, numa página que guarda a chave da identidade). Cinco abas:

| Aba | O que mostra ou faz |
|---|---|
| Modelos | Cada base custodiada, se a referência do pai foi depositada, e os derivados julgados: veredito, usável, retido ou revogado, Juiz e identidade do recibo. Depósito de base assinado. |
| Treinar | Fluxo guiado: base, dados (custodiados ou CSV novo), receita de fine-tuning (existente ou script novo) e o custo em cota antes de disparar. A compra de acesso some da vista. |
| Meus jobs | Só os jobs da identidade que pede (rota assinada): estado do derivado e veredito, sem stdout, motivos nem alertas. |
| Juiz | A escada de decisão como o código a aplica hoje, a cota por veredito, as versões liberadas, o pacote da bateria e as referências por base, e as ações do operador (CLI no host). |
| Identidade | Criar (prova de trabalho no navegador), importar, exportar e esquecer; saldo, reservado, gasto e vereditos. |
| Resultados (16/11) | Verificações locais em duas visões: por experimento (o que responde, teste e objetivo, números de destaque, conferências e arquivos) e todas as runs (arquivos de resultado e o registro de execuções agrupado por run, com filtros). Cada arquivo abre o relatório renderizado ou o JSON; cada run, as métricas. Rotas em `scripts/results_api.js`. |

Rotas novas de leitura em `scripts/ui_api.js`: `GET /api/models`, `GET /api/judge`,
`GET /api/quota-rules` e `GET /api/my/jobs` (assinada). As páginas antigas `assets.html` e
`executions.html` saíram; a segunda mostrava stdout e stderr de qualquer execução.

Verificada num Chrome headless pelo DevTools Protocol, em 1280 e 390 px: navegação pelas cinco
abas, identidade criada pela própria página, sem erro de JavaScript e sem rolagem horizontal.

### Bugs corrigidos, com teste

| Achado | Onde | Correção |
|---|---|---|
| Um revert travava a carteira da CVM1 para sempre (nonce local à frente; qualquer pedido que revertesse bastava). CONFIRMADO | `api-server.js` | `ResettingNonceManager`: em erro, o contador volta a ser lido da cadeia |
| `revoke-asset` e `update-asset` sem autenticação, com a carteira da CVM1 dona de tudo: qualquer um revogava ou reativava um modelo. CONFIRMADO | `api-server.js` | Rotas do operador só com `DNAT_OPERATOR_TOKEN` (cabeçalho `X-Operator-Token`); sem a variável, fechadas. Vale também para `GET /api/executions[/:id]`, com o id validado |
| A revogação de um ativo não era definitiva: reativar o pai trazia de volta os derivados da cascata. CONFIRMADO | contrato | `assetRevoked`: `updateAsset(newActive=true)` recusa depois de `revokeAsset` |
| Chave de acesso em `abi.encodePacked(uriD, uriA, user)`: URIs que se concatenam igual, ou o mesmo URI da vítima, davam acesso ao par pago. CONFIRMADO | contrato | Chave por ids em `abi.encode`; URI de dataset ou aplicação único; `hasAccess` por URI vira busca do id |
| `run-from-cids` aceitava `user`, `pythonBin` e `ipfsApiUrl` do corpo: dono do derivado escolhido pelo cliente, executável do `spawn` e SSRF que entregava os CIDs custodiados | `api-server.js` | Só `datasetId`, `applicationId` e `parentModelId` vêm da rede |
| `GET /api/identity/__proto__` poluía o protótipo de todo objeto do processo. CONFIRMADO | `identity.js` | Id só de 64 hex e `Object.hasOwn` |
| O digest do modelo deixava fora `README*`/`LICENSE*` de qualquer extensão e diretórios-link: um shard `README.safetensors` citado no índice trocava os pesos sem mudar o digest. CONFIRMADO | `io/load.py` | Só documentação fica fora; link simbólico é erro; todo shard do índice tem de estar no digest. Os digests de base, fumaça e campo não mudaram |
| O S1, o S2 e a utilidade usavam o template e o `generation_config` do derivado: um `chat_template.jinja` que injeta "recuse" ou um `sequence_bias` faziam um abliterado passar. CONFIRMADO | `stages.py` | Sempre o tokenizador e a configuração de geração do base, como na referência do pai |
| NaN em ρ, E1 ou na perda de CE passava pela escada como aprovado; o esquema barrava fora do `try`, e o job morria sem `job_result.json`. CONFIRMADO | `combine.py`, `job.py` | Não finito conta como ausente (`signal_missing`, `utility_missing`); erro ao emitir vira falha registrada |
| A regra 4 aceitava sinal de um formato só cobrindo células de outros | `combine.py` | Um sinal por formato julgado |
| A referência do pai podia ter outro tamanho de corpus de utilidade | `stages.py` | Exige o mesmo `n` |
| Um `.py` que é link entrava no Juiz sem entrar no hash | `judge_package.py` | Link simbólico é erro |

Testes: contrato e CVM1 com 144 passando (4 novos), `model_gate` com 301 mais 5 novos.

## 2. Bugs encontrados e não corrigidos

Ficam aqui porque mudam infraestrutura, pedem decisão ou não cabem sem testar a pilha Docker.

| Gravidade | Achado | Proposta |
|---|---|---|
| Alta | A CVM de job aceita conexões de entrada da rede `dnat-runtime`, onde está o builder, que roda como root o `setup.py` das dependências do usuário e tem saída para a internet. O RPC do Hardhat (8545, conta do operador desbloqueada) e a API do IPFS ficam alcançáveis. PLAUSÍVEL | INPUT DROP na CVM de job, exceto a CVM1; builder em outra rede; não publicar 8545 e 5001; não subir sem `ASSET_ENCRYPTION_KEY` |
| Alta | Cache de wheels compartilhado sem conferência: a wheel devolvida pelo build de um usuário entra no ext4 do seguinte. PLAUSÍVEL | Só wheels com hash conhecido, ou cache por dono |
| Alta | Qualquer entrada do Juiz que não confere (prereg, bateria, avaliador, dataset) reprova o derivado; a E14 §4 reprova só por derivado ou pai. CONFIRMADO | Decisão: reprovar só por derivado e pai; o resto vira falha com reembolso |
| Média | Desligar a CVM1 no meio de um job deixa texto claro em `/tmp`, containers `dnat-job-*` vivos e reservas presas | Registrar as CVMs entregues e destruí-las no `close()`; limpeza na partida |
| Média | Recibo gravado com a cota devolvida, se o `tx.wait()` falha depois da mineração | Acertar a cota antes, ou reconciliar por `DerivativeRegistered` |
| Média | `purchase-access` segue sem assinatura e paga com a carteira da CVM1; o acesso é da CVM1, não da identidade | Ligar o acesso à identidade, ou tirar a compra do fluxo (D1: custo zero) |
| Média | Modo static (padrão do `direct.compose.yaml`) reaproveita o executor entre usuários; processo com `setsid` sobrevive ao job | Tornar o provedor docker o padrão |
| Baixa | Base64 com preâmbulo não é decodificado (o bloco codificado está desligado); sobreposição do dataset ignora JSONL em formato `messages`; multipart de até 4 GB lido antes da assinatura; pedidos vistos só em memória; rótulo do envelope fora do AAD; dataset e receita revogados seguem rodando para quem comprou | Ver relatórios |

## 3. O que falta para funcionar como proposto

Separado do que só espera a nuvem (T-1603, T-210).

1. **O S2 trava o veredito real.** `stages.signals` exige a direção na referência e a regra 4
   exige `rho_min`; sem direção válida (T-414: nenhuma no Qwen2.5-0.5B pelo procedimento de
   Arditi), nenhum derivado é aprovado. Depende da decisão da T-414 e muda código, não só o
   prereg.
2. **O `verdict.json` e as respostas são apagados.** O recibo guarda o hash de um arquivo que deixa
   de existir; nem o operador nem o auditor do G3 conferem motivos ou respostas. Falta cifrar e
   guardar os dois (IPFS ou CVM1) antes do `rmSync`.
3. **O Juiz roda dentro da CVM1**, não numa CVM de uso único (D6). Nenhuma task cobre; a T-807
   está "feita" com essa promessa no título.
4. **O operador não tem ferramentas.** Faltam revogar derivado por CLI ou rota, a reavaliação,
   manter ou reprovar um inconclusivo e recibos encadeados das ações (E14 §9, §11).
5. **Falha do job:** sem 3 tentativas e sem recibo de falha; o veto do S1 se perde se um estágio
   posterior cai (E14 §9).
6. **Medição do pai:** a E14 §3 a quer automática no depósito, com estado inapto; hoje o operador
   deposita a referência à mão (D8). Uma das duas tem de mudar.
7. **O ativo aprovado não tem uso:** não há inferência dentro da plataforma, e nada consulta
   `isDerivativeUsable` fora dos testes; liberar e reter não se distinguem na prática (C1).
8. **Tempo como canal:** o veredito volta na mesma resposta HTTP; a E15 §2 promete publicação em
   T0 + T_max.
9. **Parte secreta da bateria:** sem ela não há bounty (RQ4) nem a guarda secreta × pública
   (T-304, decisão humana).
10. **Requisitos sem task:** condição C_job, multiturno como sentinela, cache por (digest, Juiz),
    base inapto, remedir referências na troca de versão do Juiz, 3 tentativas, T_max e
    reavaliação. Nenhum aparece na fila, nem como cortado.
11. **Artefato:** a T-1412 (pacote e README de reprodução) foi cortada, mas a declaração de
    artefato (T-1512) e o CFP o pedem.

## 4. Contradições a resolver

- **Formatos:** E14 §8, D5, D6 e o artigo §5 dizem quatro (FP, LLM.int8, NF4, FP4); o código usa FP
  e NF4 (redução v2). Atualizar os documentos ou o código.
- **Artigo §5** promete C_job, 16 âncoras secretas, seis codificações, nova tentativa em CVM nova,
  CVM de uso único para o Juiz, auditor que confere o veredito e retirada pelo dono. Nada disso
  existe ainda.
- **Hash que não confere:** E14 §4 reprova; a CVM1 pega antes e devolve falha com reembolso.
- **Reativação pelo dono:** a E14 diz que o dono nunca reativa; `updateAsset(false)` seguido de
  `updateAsset(true)` ainda reativa um aprovado (a revogação por `revokeAsset` já ficou definitiva).
- **Id no recibo:** a T-1706 foi cortada para não pôr o id on-chain, mas o código o põe (segue a
  E14). Corrigir o backlog.
- **Custo zero (D1)** × compra de acesso no fluxo e preços no contrato.
- **Custo do depósito do base:** a E14 §18.4 diz 1; o código não cobra.
- **Parte secreta:** D8 diz n = 20; E14 §7.2 e o artigo, 16.
- **S2/S3 por formato** (E14 §4 e código) × só em precisão cheia (E13 §3.3).

## 5. Decisões pedidas

1. **T-414:** papel do S2 no veredito (recomendação: fora do veredito, só relatado) e se o S3 segue
   a mesma regra. Destrava o item 1 da §3.
2. **Entrada que não confere:** reprovar só por derivado e pai (E14 §4) ou manter o reprova-tudo.
3. **Medição do pai:** automática no depósito (E14 §3) ou depósito pelo operador (D8).
4. **Compra de acesso:** tirar do fluxo (D1) ou ligar à identidade.
5. **O que entra antes da T-1611:** dos itens 2 a 8 da §3, quais viram task de construção e quais
   vão para Limitações no artigo.
