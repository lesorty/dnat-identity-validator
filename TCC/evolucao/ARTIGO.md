# Pretensões do artigo

**Atualizado:** 2026-10-17, após conversa com o orientador (D-031, D-032).
**Status:** rumo definido; decisões propostas, testes e casos de uso **a detalhar pelo Steylor**.
**Alvo:** DSN 2027, Berlim (resumo 25/nov, artigo 02/dez/2026; D-033). Cronograma em
[../PLANO_DSN2027.md](../PLANO_DSN2027.md).

## Tese (rascunho)

Um sistema de computação confidencial para marketplace de dados e aplicações, em que as
aplicações são **imagens OCI** executadas em CVMs de uso único, e em que a segurança das
aplicações frente aos dados é verificada por um **Juiz de IA que é, ele próprio, uma aplicação
do sistema**.

## Contribuições pretendidas

| # | Contribuição | Papel no artigo | Base |
|---|---|---|---|
| C1 | **Juiz de IA**: análise do código de uma aplicação para dizer se é segura e se vaza dados, direta ou indiretamente | **Principal** | E4, D-016, D-032 |
| C2 | **Juiz como aplicação do sistema**: roda pelo mesmo pipeline confidencial, faz parte da whitelist e recebe qualquer aplicação como entrada. O sistema verifica a si mesmo sem um componente à parte | Arquitetural; sustenta a escalabilidade e o *future proof* | D-032 |
| C3 | **Aplicações em OCI** no lugar de Python + wheels em ext4: qualquer linguagem e ecossistema, com build seguro em duas fases | Pré-requisito e generalização | E2, E2b, D-010 a D-015 |

**Ordem de trabalho:** C3 primeiro (adaptar o sistema para OCI), depois C1 + C2.

## O que muda em relação ao LADC 2026

| Antes | Agora |
|---|---|
| Contribuição lida pelos revisores como "isolamento bem engenheirado" (separar planos, microVM) | Contribuição é o **Juiz de IA**: um resultado novo, não uma escolha de engenharia |
| Só Python + wheels | Qualquer aplicação empacotada como imagem OCI |
| Firecracker, que não roda em CVM (A14) | CVM de uso único por job, container sem rede (E2) |

## Escopo

**Dentro**
- Build e execução de imagens OCI em CVM (E2, E2b).
- Juiz de IA como aplicação whitelisted, com entrada = outra aplicação.
- Cifrar o dataset (A16, TODO).

**Fora, declarado como limitação ou trabalho futuro**
- Distribuição do sistema entre operadores (D-031). O operador continua sendo ponto único de
  disponibilidade e censura; o sigilo frente a ele depende da CVM e da atestação.
- Atestação detalhada (implícita, D-017 iii).
- Canais encobertos e laterais (limitação, D-014); vazamento pelo canal legítimo de resultado
  (X8) fora de escopo, mas é justamente o que o Juiz passa a enfrentar: **rever a D-014** quando
  as propriedades verificadas forem definidas.
- Imagem OCI pronta enviada pelo desenvolvedor (estacionada, brainstorm 05).

## Relação com as direções do brainstorm 01

| Direção | Situação |
|---|---|
| 1. Cadeia verificável build → execução | Compatível, fora do foco; o relatório do Juiz pode entrar nela no futuro |
| 2. Distribuição de confiança entre operadores | **Fora** (D-031) |
| 3. Build reproduzido por construtores independentes | **Fora do foco** (dependia de vários builders em domínios distintos) |
| 4. Política de saída | Absorvida em parte pelo Juiz |

## Pontos a detalhar (próximas conversas)

Centralizados em [JUIZ_IA.md](JUIZ_IA.md).

1. **Decisões propostas** sobre o Juiz (o Steylor traz).
2. **Ideias de testes**: como medir eficácia (detecção, falsos positivos) e custo.
3. **Casos de uso** pensados para o Juiz.
4. **Eficácia com baixo custo**: a principal dificuldade do trabalho (D-032).
5. Como o Juiz recebe a aplicação-alvo como entrada (imagem, fonte ou ambas) e onde fica o veredito.
6. Quem confia no Juiz: sua própria versão precisa estar fixada e verificável na whitelist.
