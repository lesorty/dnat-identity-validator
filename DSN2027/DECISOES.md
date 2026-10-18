# Decisões vigentes

Só o que vale hoje, agrupado por tema; os IDs são os originais. O histórico completo (inclusive o
que foi descartado, como a distribuição do sistema) está na tag git `ladc-2026`.
Status: **ACEITA** ou **PROVISÓRIA** (depende de algo pendente).

## Rumo

### D-033 · ACEITA · 2026-10-18
Alvo: **DSN 2027 (Berlim)**, regular paper, 11 páginas com tudo, IEEE CS, double-blind. Resumo
em **25/nov/2026**, artigo em **02/dez/2026**. Cronograma em [PLANO.md](PLANO.md).

### D-032 · ACEITA · 2026-10-17 (com o orientador)
Foco, nesta ordem: (i) **aplicações em imagem OCI** no lugar de Python + wheels em ext4;
(ii) **contribuição principal: o Juiz de IA**, que analisa o código de uma aplicação e diz se ela é
segura e se vaza dados. O Juiz é **uma aplicação do próprio sistema**, na whitelist por natureza,
que recebe outra aplicação como entrada. Dificuldade central: ser eficaz e barato.
Trabalho centralizado em [JUIZ_IA.md](JUIZ_IA.md).

### D-031 · ACEITA · 2026-10-17 (com o orientador)
**Não distribuir o sistema.** Executar em CVM, em tese atestável, não deixa ganho de confiança
que justifique o custo. Consequência a declarar no artigo: o operador continua sendo ponto único
de disponibilidade e censura; o sigilo frente a ele depende da CVM.

## Execução

### D-005 · ACEITA
A fronteira de isolamento por job é **a própria CVM** (uma por job, curta e efêmera). Sem
virtualização aninhada: o hipervisor que media uma VM aninhada observa mais eventos (canal
lateral). Nenhuma opção elimina o canal lateral; vira limitação declarada.

### D-006 · ACEITA
Efemeridade por **uso único**: *warm pool* de CVMs pré-iniciadas e nunca usadas, cada uma
consumida por um job e destruída. Salvaguardas: uso único imposto pelo guest, sem disco
persistente, idade máxima e tamanho do pool definidos na medição.

### D-010 · ACEITA
Contrato entre os planos: o **builder** entrega a aplicação como **arquivo OCI pronto para
executar**; o **executor** recebe esse arquivo e o dataset, executa e devolve o resultado. Sem
registry e sem *pull* no caminho de execução.

### D-011 · ACEITA
A aplicação roda num **container sem rede** dentro da CVM de uso único: namespace de rede vazio,
dados montados antes de iniciar, resultado gravado em volume, container descartado ao final. Só
o agente confiável da CVM usa a rede. Runtime reforçado: sem capacidades, rootfs somente leitura,
sem dispositivos (gVisor ou runc rootless com seccomp).

### D-017 · ACEITA
Fechamento da E2: executor próprio (sem Kubernetes nem peer pods). **Atestação implícita** em todo
uso de computação confidencial e fora do escopo. Rede em três fases no guest: com rede para buscar
ativos, sem rede para executar, com rede só para devolver o resultado.

## Build OCI

### D-009 · ACEITA
O build produz **só a aplicação**. O dataset nunca entra no build: chega na execução, cifrado,
montado somente leitura. N aplicações e M datasets geram N builds.

### D-013 · ACEITA
**Dockerfile livre**, sem gabaritos. `FROM` fixado por digest (por validar, prioridade menor).
Motor rootless rejeitado (a CVM descartável já é a fronteira). Imagem final **assinada** pelo
builder, como vínculo do artefato a um builder medido.

### D-015 · ACEITA
**Varredura de saída** básica no builder antes de assinar (segredos, setuid, links, tamanho); o
executor revalida. Build reproduzível fica registrado como desejável, fora do foco.

### D-029 · ESTACIONADA
Imagem OCI pronta enviada pelo desenvolvedor: não agora. O build continua feito pelo builder.
Análise em [etapas/E2b_build_oci.md](etapas/E2b_build_oci.md) §E2b.7.

## Escopo e ameaças

### D-014 · ACEITA (revista em 2026-10-18)
**Canais encobertos e laterais (X7):** limitação declarada. **Vazamento pelo canal legítimo de
resultado (X8):** deixa de estar fora de escopo; **é o alvo do Juiz** (D-032).

### D-018 · ACEITA
Cifrar o dataset no IPFS (A16): **feito na branch `feat/cvm-direct-mode-deploy`** (commit
`a668d0b`), falta integrar na `main`. Ledger em memória (A17) não é problema agora.

## Método

### D-007 · ACEITA
Decidir antes de medir. Nuvem de testes: **Azure**.
