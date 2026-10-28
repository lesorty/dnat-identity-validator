# Decisões

Só as decisões que guiam o trabalho hoje. Detalhes e justificativas nos documentos citados; o
histórico completo (IDs antigos D-0xx, inclusive o que foi descartado) está na tag `ladc-2026`.

## D1 · Rumo
- **Alvo:** DSN 2027 (Berlim), regular paper, 11 páginas com tudo; resumo **25/nov/2026**, artigo
  **02/dez/2026**. Cronograma em [PLANO.md](PLANO.md).
- **Tema (2026-10-27, com o orientador):** **proteção de modelos abertos** no DNAT. Pesos e
  derivados ficam sob custódia na CVM e todo derivado passa por um **portão de liberação** antes
  de virar ativo. Escrito como **dependabilidade** (manter a recusa sob modificação do modelo, com
  falhas acidentais e maliciosas, detecção e contenção) e como **proteção da cadeia de suprimentos
  de modelos**. Base: [E7](etapas/E7_decisao_rumo.md), [E8](etapas/E8_alinhamento_dsn.md),
  [E9](etapas/E9_testes_validos.md).
- **Descartados:** o Juiz generalista de vazamento em código (amplo demais) e o mercado de bug
  bounty sobre a cadeia de software ([E5](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/etapas/E5_alt_bug_bounty.md), na tag `archive/juiz-bounty-2026-10`). A ideia de bounty fica
  como **extensão**: prêmio para quem mostrar uma entrada ou um derivado que explora o modelo.
- **Modelos abertos têm custo zero (2026-10-28):** o sistema não vende acesso ao modelo; base e
  derivados são abertos, e a plataforma pode cobrar só a computação dos jobs. O que limita as
  tentativas de quem ataca o portão é uma **cota de jobs por usuário** (T-101, decisão 11). É
  uma mudança de apresentação: o `purchaseAccess` do código fica como herança do mercado.
- **Problema** ([E10](etapas/E10_problema.md) §5): garantir que nenhum derivado comprometido seja
  liberado (o dano nas âncoras não sobe mais que δ em relação ao pai, por categoria, sem perder
  utilidade; T-106 e [E14](etapas/E14_especificacao_juiz.md) §5), contra o usuário com os pesos
  dentro da CVM.
  Junto: representatividade injeção × campo (RQ), recibo atestado e bounty como extensão.
  Exportação de pesos fica fora.

*Absorve D-032 e D-033 (2026-10-17/18) e a decisão de 2026-10-27. O orientador lembrou que o
formato de modelo também resolve a exposição de código confidencial na saída, limitação do Juiz.*

## D2 · Portão de liberação (o Juiz aplicado a modelos)
- **É uma aplicação do próprio sistema**, na whitelist, que recebe um **derivado de modelo** (e
  não código) e devolve um veredito: aprovado, reprovado ou inconclusivo.
- **Julga o resultado, não o script:** fine-tuning legítimo e obliteração podem ter o mesmo código.
- **Avaliação:** população de derivados por classe de falha, com verdade de referência
  independente, teste cego com obliterados públicos e atacante adaptativo ([E9](etapas/E9_testes_validos.md) §3).
- **Orçamento:** tudo em CPU com modelos pequenos. Uma GPU confidencial entra como **segunda
  bancada** (T-111): uma amostra de derivados roda também nela, com o kernel real de 4 e 8 bits,
  para conferir os vereditos da CPU e medir o custo.

*Substitui o D2 do Juiz de código (histórico no git).*

## D3 · Escopo do artigo
- **Sem distribuição** do sistema: a CVM basta; o operador segue como ponto único de
  disponibilidade e censura (limitação declarada).
- **Atestação implícita**, fora do escopo.
- **Pesos de modelo (caso U1) passam a ser o caso principal.**
- **Canais laterais** e falhas de hardware na CVM são limitação declarada; a integridade de
  memória da CVM é premissa.

*Absorve D-014, D-017 (atestação), D-029, D-031 e D-034.*

## D4 · Arquitetura OCI
- **Execução:** uma **CVM de uso único** por job, de um *warm pool* de CVMs nunca usadas, sem
  virtualização aninhada. A app roda num **container sem rede** (namespace vazio, rootfs somente
  leitura, sem capacidades nem dispositivos); só o agente da CVM usa a rede, antes e depois.
- **Build:** o builder entrega a **imagem OCI pronta**; o executor só a recebe com o dataset, sem
  registry. O **dataset nunca entra no build**. Dockerfile livre; imagem **assinada** e
  **varrida** antes de sair do builder; o executor revalida. **Qualquer imagem-base, de qualquer
  registry**, sem lista de aprovadas: o builder resolve a tag para digest e o registra. Duas fases em **duas CVMs de uso
  único** (E2b §3, opção B): a de **fetch** baixa as dependências falando só com o proxy de
  registro (aberto a qualquer registry público, anota cada download) e o DNAT, sem nunca ver código nem chave; a de **assemble** recebe código e
  dependências (conferidas por hash), monta sem rede e assina, com o mesmo desenho de rede da
  execução (só o DNAT, abaixo).
- **Todo build é atestado:** o desenvolvedor envia fonte, Dockerfile e lockfile, **nunca a
  imagem pronta** (E2b §E2b.7, por simplicidade). O dono do dataset pode exigir reprodução por
  N ≥ 2 builders.
- **A CVM só fala com o DNAT** ([E2c](etapas/E2c_ameacas_oci.md) §2): a app roda sem rede (namespace
  vazio, seccomp sem sockets de rede, gVisor, sem root); a CVM **puxa** o job e nunca escuta; o
  PID 1 carrega no boot a regra "saída só para o DNAT, sem DNS" e **remove de todos os processos
  as capacidades de mudar rede, BPF e módulos**; kernel em lockdown, imagem sem shell nem console;
  mTLS com o certificado do DNAT fixado, e o DNAT trata tudo o que recebe como saída. Fora da
  CVM, sub-rede sem saída para a internet e NSG só para o DNAT (cobre exploit de kernel). Derrubar
  a interface durante o job fica só desejável. Exploit de kernel + conluio do operador: limitação.
  App que precisa de rede: **proibida no MVP**; o *broker* por socket Unix fica como extensão.
- **Piloto (2026-10-28, T-102):** CVMs reais na nuvem (Azure, AWS ou Oracle, pelo custo). A CVM1
  é o plano de controle; a **CVM2** é o builder, numa CVM separada; cada job (fine-tuning, Juiz,
  medição do pai) roda numa **CVM de uso único**, direto na CVM, **sem container**, com o script
  sem rede; cada sessão de inferência tem a sua CVM de uso único. **Não há microVM:** o
  Firecracker não roda numa CVM, e o caminho com ele no código (`run-vm.sh`, `build-vm.sh`) é
  legado. Container sem rede, gVisor e build em duas fases ficam como alvo. Segurança no mínimo
  para o artigo: IPFS local como está, atestação real só se a avaliação precisar.
- Detalhes: [E2](etapas/E2_isolamento_confidencial.md), [E2b](etapas/E2b_build_oci.md) e [E2c](etapas/E2c_ameacas_oci.md).

*Absorve D-005, D-006, D-009, D-010, D-011, D-013, D-015 e D-017 (execução). O piloto foi decidido
na T-102 do backlog (aba Decisões).*

## D5 · Base teórica (2026-10-27)
- **Base:** os 13 artigos da camada 1 da [E12](etapas/E12_base_teorica.md) §2, lidos por
  inteiro, sustentam o texto. A camada 2 (5 artigos) é lida nas seções-chave; a camada 3 só se
  cita.
- **Espinha do texto:** as afirmações A1–A5 da E12 §3:
  - a recusa não sobrevive à derivação;
  - proteger nos pesos não basta;
  - detectar só funciona sob custódia;
  - o derivado tenta enganar o portão;
  - a avaliação exige medida válida e população representativa.
- **Acervo:** `pesquisa/artigos/` fica só com a base, organizada por camada e tema
  ([índice](../pesquisa/artigos/README.md)). Os outros 40 PDFs saíram do repositório e seguem no
  histórico do git (commit `f0fba2a`).
- **Formato liberado** (Egashira et al. 2024): o portão avalia o derivado em precisão cheia e nas
  quantizações *zero-shot* comuns (LLM.int8, NF4, FP4), e a plataforma só libera os formatos
  avaliados. A quantização condicionada entra como variante de F4.
- **A implementação ainda não começa:** antes do piloto, o plano de trabalho é consolidado a
  partir da base.

## D6 · Especificação do Juiz (2026-10-28)
- **Status:** decidida em 28/10 (T-114). Os pontos da E14 §17 ficam como pauta para o orientador;
  uma objeção entra como task nova. Provisória só a geração única do S1, até o dia 1 do piloto. A especificação está na
  [E14](etapas/E14_especificacao_juiz.md), que junta as decisões T-101 a T-113 do épico J1.
- **Propriedade:** o dano nas âncoras não sobe mais que δ em relação ao pai, por categoria (teto
  0,15), em todos os formatos liberados. Aprovado quer dizer "não regrediu", não "seguro".
- **Veredito:** aprovado, reprovado ou inconclusivo. Só a bateria comportamental (S1) reprova por
  mérito; S2 e S3 levam no máximo a inconclusivo, a FPR 5% nos benignos. O inconclusivo fica
  retido e nunca é liberado, nem pelo operador.
- **Formatos:** precisão cheia, LLM.int8, NF4 e FP4, tudo ou nada, em CPU com o código do serviço;
  GPU confidencial como segunda bancada. Os pesos nunca saem.
- **Bateria:** um terço das âncoras é secreto, de três fontes em partes iguais, cifrado no pacote
  do Juiz com a chave só na CVM1, trocado a cada versão e revelado depois.
- **Execução:** cada job (medição do pai, fine-tuning, Juiz) numa CVM de uso único; o Juiz é o
  segundo job, disparado pela CVM1. Todo veredito gera recibo com hashes no contrato.
- **Custo zero:** modelos abertos sem preço; a cota de jobs por usuário limita o atacante.

*Substitui, nos pontos da E14 §15, a E13 §3.3 e o item "Problema" da D1.*
