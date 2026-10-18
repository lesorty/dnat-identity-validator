# Decisões

Só as decisões que guiam o trabalho hoje. Detalhes e justificativas nos documentos citados; o
histórico completo (IDs antigos D-0xx, inclusive o que foi descartado) está na tag `ladc-2026`.

## D1 · Rumo
- **Alvo:** DSN 2027 (Berlim), regular paper, 11 páginas com tudo; resumo **25/nov/2026**, artigo
  **02/dez/2026**. Cronograma em [PLANO.md](PLANO.md).
- **Contribuição principal:** o **Juiz de IA**, que diz se uma aplicação vaza dados não permitidos.
- **Pré-requisito:** aplicações em **imagem OCI** no lugar de Python + wheels em ext4.

*Absorve D-032 e D-033 (2026-10-17/18, com o orientador).*

## D2 · Juiz de IA
- **É uma aplicação do próprio sistema**, na whitelist por natureza, que recebe outra aplicação
  como entrada e devolve um veredito (aprovado · aprovado com portão · reprovado · inconclusivo).
- **MVP** ([JUIZ_IA.md](JUIZ_IA.md) §9): benchmark de **agregação, transformação e ML** sobre dados
  tabulares sintéticos com canários; **verdade de referência estilo CTF** (o atacante entrega app +
  decodificador; vale se a tarefa é cumprida e o canário sai da saída); camada **L2 com variação
  do segredo**.
- **Acesso externo:** sem tag de rede no dataset, tentativa de rede observada em L2 (seccomp em
  modo log) ⇒ **reprovado**; sinal só estático e fraco ⇒ inconclusivo ([E2c](etapas/E2c_ameacas_oci.md) §6).
- **Batalha:** atacantes de ponta (Anthropic, OpenAI, Google, abertos grandes) × defensores baratos
  (abertos em GPU na nuvem e por API), no máximo um defensor caro; **API até US$ 100**.

*Absorve D-032, D-035 e D-036.*

## D3 · Escopo do artigo
- **Sem distribuição** do sistema: a CVM basta; o operador segue como ponto único de
  disponibilidade e censura (limitação declarada).
- **Atestação implícita**, fora do escopo.
- **Vazamento pela saída legítima** é o alvo do Juiz; **canais laterais** são limitação declarada.
- **Pesos de modelo privados** (caso U1): só como motivação.
- **Imagem OCI pronta** enviada pelo desenvolvedor: estacionada ([E2b](etapas/E2b_build_oci.md) §E2b.7).

*Absorve D-014, D-017 (atestação), D-029, D-031 e D-034.*

## D4 · Arquitetura OCI
- **Execução:** uma **CVM de uso único** por job, de um *warm pool* de CVMs nunca usadas, sem
  virtualização aninhada. A app roda num **container sem rede** (namespace vazio, rootfs somente
  leitura, sem capacidades nem dispositivos); só o agente da CVM usa a rede, antes e depois.
- **Build:** o builder entrega a **imagem OCI pronta**; o executor só a recebe com o dataset, sem
  registry. O **dataset nunca entra no build**. Dockerfile livre; imagem **assinada** e
  **varrida** antes de sair do builder; o executor revalida. Duas fases em **duas CVMs de uso
  único** (E2b §3, opção B): a de **fetch** baixa as dependências falando só com o proxy de
  registries e o DNAT, sem nunca ver código nem chave; a de **assemble** recebe código e
  dependências (conferidas por hash), monta sem rede e assina, com o mesmo desenho de rede da
  execução (só o DNAT, abaixo).
- **A CVM só fala com o DNAT** ([E2c](etapas/E2c_ameacas_oci.md) §2): a app roda sem rede (namespace
  vazio, seccomp sem sockets de rede, gVisor, sem root); a CVM **puxa** o job e nunca escuta; o
  PID 1 carrega no boot a regra "saída só para o DNAT, sem DNS" e **remove de todos os processos
  as capacidades de mudar rede, BPF e módulos**; kernel em lockdown, imagem sem shell nem console;
  mTLS com o certificado do DNAT fixado, e o DNAT trata tudo o que recebe como saída. Fora da
  CVM, sub-rede sem saída para a internet e NSG só para o DNAT (cobre exploit de kernel). Derrubar
  a interface durante o job fica só desejável. Exploit de kernel + conluio do operador: limitação.
  App que precisa de rede: **proibida no MVP**; o *broker* por socket Unix fica como extensão.
- Detalhes: [E2](etapas/E2_isolamento_confidencial.md), [E2b](etapas/E2b_build_oci.md) e [E2c](etapas/E2c_ameacas_oci.md).

*Absorve D-005, D-006, D-009, D-010, D-011, D-013, D-015 e D-017 (execução).*
