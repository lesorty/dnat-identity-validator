# Fila de execução do board

Ordem em que as tasks abertas serão pegas (13/11). Gerada por `fila.py`, que confere a ordem contra o
`backlog.json`: nenhuma task aparece antes das suas dependências abertas. Versão para máquina: `fila.json`.

**Regra:** pegar o primeiro item cujo executor está disponível e cujas dependências estão feitas.
**Executor:** `agente` roda aqui; `humano` é decisão ou ação sua ou do orientador; `nuvem` precisa das
VMs (T-1603, T-210); `artigo` fica para o fim, depois do sistema e dos resultados.

## E2 · Desbloqueios humanos da porta T-1611

1. **T-1603** (humano) Escolher a nuvem das CVMs pelo custo e resolver o crédito. Nuvem e crédito: sem isso nada da fase de testes roda; destrava T-210, T-309, T-315, T-801, T-812.
2. **T-210** (humano) Máquina de 4 vCPU do piloto. VM de 4 vCPU: medida de custo válida e máquina do piloto; dependência da T-1611 e da T-309.
3. **T-304** (humano) Separar a parte pública da secreta e gerar o compromisso por hash da secreta. Origem da parte secreta (orientador): última decisão de construção da T-1611; destrava o bounty (T-1210).
4. **T-1103** (humano) Baixar e registrar digests, fora do git. Aceitar a licença da Meta e baixar o campo e a família não vista; destrava T-1105 e T-913.
5. **T-1606** (humano) Nota de ética e, se exigido, comitê para a anotação humana. Comitê de ética para a anotação; destrava a amostra de anotação (T-1005).
6. **T-1605** (humano) Definir pessoas: anotadores e guardião da bateria secreta. Anotadores e guardião da bateria secreta; destrava a anotação (T-1007).
7. **T-1604** (humano) Baixar o Natella (IEEE TSE 2013) pelo acesso institucional. Natella pelo acesso institucional; destrava T-1108 e a seção 6 (T-1505).

## E3 · Sistema na nuvem e congelamento

8. **T-801** (nuvem) CVM de job de uso único: warm pool e ciclo de vida da CVM. CVM de job de uso único (criar, rodar, destruir); usa a imagem do executor da T-815.
9. **T-806** (nuvem) Job de fine-tuning de exemplo (LoRA pequeno) numa CVM de uso único. Fine-tuning LoRA de exemplo numa CVM de uso único: a primeira metade do fluxo no DNAT real.
10. **T-1611** (humano) Fechar o sistema e abrir a fase de testes: congelar o código do Juiz e do fluxo. Congelar o código do Juiz e do fluxo: abre a fase de testes; daqui em diante mudar o Juiz obriga a recalibrar.
11. **T-309** (nuvem) Rodar o avaliador do portão na VM de nuvem e conferir o modelo (Gemma 4 E4B × Qwen3Guard-4B). Avaliador do portão medido na VM (Gemma 4 E4B × Qwen3Guard): fixa o avaliador da liberação.
12. **T-315** (nuvem) Medir os avaliadores em bf16 na VM de nuvem da família da CVM. Avaliadores em bf16 na família da CVM: custo do avaliador, que decide se o veredito cabe em 80 min.
13. **T-312** (nuvem) Rodar o instrumento no base e guardar como referência custodiada do pai. Referência custodiada do pai (código pronto em model_gate.reference); sem ela não há veredito real.
14. **T-505** (nuvem) Rodar o instrumento reduzido em cada formato. Instrumento reduzido em cada formato; insumo da sanidade (T-313) e do custo (T-314).
15. **T-414** (nuvem) Escolher a camada da direção pelo efeito da intervenção (Arditi) e comparar com a camada 6. Camada da direção do S2 pelo efeito da intervenção; fecha o ρ usado pelo Juiz antes da sanidade.
16. **T-313** (nuvem) Sanidade: abliterado público (huihui-ai v3) muda as métricas; repetir o base não muda. Teste 1: o Juiz real separa o abliterado público e não oscila no base (repete a verificação da T-807).
17. **T-314** (nuvem) Medir o custo do instrumento por configuração, incluindo o juiz (insumo do G1). Custo do instrumento por configuração, com o avaliador: número do G1 e da RQ5.
18. **T-813** (nuvem) Teste do G3: reprovado não sai, aprovado vira ativo com recibo, operador revoga. Teste 8 na nuvem com o Juiz real (o ensaio local é a T-814).
19. **T-1707** (nuvem) Testes da identidade e da cota, e demonstração. Teste 9: identidade e cota, com demonstração.
20. **T-812** (nuvem) Medir overhead: VM comum × CVM, e CVM reaproveitada × CVM de uso único. Overhead VM comum × CVM; insumo da RQ5 (T-1409).
21. **T-709** (nuvem) Medir o gás das novas funções (measure-gas.js). Gás das funções novas do contrato (opcional, P3).

## E4 · População e verdade de referência (nuvem)

22. **T-914** (nuvem) População do piloto: 2 abliterações e 2 LoRA benignos. População do piloto (2 abliterações, 2 LoRA): primeiro sinal de separação e custo.
23. **T-905** (nuvem) F1 benigno: LoRA nos 3 datasets, varrendo passos e seeds. F1 benigno nos 3 datasets: o grosso dos derivados que devem passar.
24. **T-907** (nuvem) F2: varrer o número de exemplos nocivos. F2: dose de exemplos nocivos; derivados que devem reprovar.
25. **T-909** (nuvem) F0 endurecido: LoRA com recusas estendidas (Abu Shairah). F0 endurecido: derivados que recusam mais (guarda de recusa excessiva).
26. **T-917** (nuvem) F3: varrer a abliteração na nuvem (intensidade e camadas) e registrar os derivados. F3: varredura da abliteração; destrava o ataque de cura (T-1203).
27. **T-906** (nuvem) F1 que degrada (zona cinza). F1 que degrada (zona cinza), relatada à parte.
28. **T-910** (nuvem) Validar a utilidade: acurácia na tarefa e MMLU curto. Utilidade dos derivados: separa N de C na rotulagem.
29. **T-912** (nuvem) Montar as divisões: calibração (seeds A) e teste (seeds B). Divisões de calibração e teste: destrava θ (T-603), linha de base (T-1302) e família não vista (T-913).
30. **T-913** (nuvem) Família não vista: repetir as receitas no modelo escolhido. Família não vista (Llama-3.2-1B): generalização do limiar (Teste 4).
31. **T-1003** (nuvem) Rodar o juiz de referência sobre as gerações da bateria de referência. Juiz de referência (gpt-oss-20b) sobre as gerações: base dos rótulos.
32. **T-1005** (humano) Amostra estratificada de ~100 respostas para anotação humana. Amostra estratificada para anotação humana (depende do comitê, T-1606).
33. **T-1008** (nuvem) Rótulos finais com as divergências resolvidas. Rótulos finais com divergências resolvidas: destrava rotulagem H/C/N e campo.
34. **T-911** (nuvem) Rotular cada derivado como H, C ou N pela verdade de referência. Rótulo H/C/N de cada derivado pela regra da T-1004.
35. **T-1007** (humano) Anotação por dois anotadores e cálculo do κ. Anotação por dois anotadores e κ (pessoas da T-1605).

## E5 · Calibração e pré-registro

36. **T-603** (nuvem) Fixar θ da segunda linha a FPR de 5% na calibração. θ da segunda linha (S2/S3) a FPR de 5% na calibração.
37. **T-604** (agente) Definir a faixa de inconclusivo em torno do limiar. Faixa de inconclusivo em torno do limiar (decisão sobre os números da T-603).
38. **T-606** (agente) Escrever o prereg.yaml: δ, tolerância, métricas, limiares, tamanhos, seeds, critérios por RQ. prereg.yaml com δ, τ, tolerâncias e tamanhos: tira o Juiz real do StageNotReady.
39. **T-607** (agente) Commitar o prereg.yaml antes de abrir qualquer conjunto de teste. Commit do prereg antes de abrir o teste: a partir daqui os resultados contam.
40. **T-1302** (nuvem) Calibrar a linha de base com o mesmo protocolo. Linha de base de Hurtado calibrada pelo mesmo protocolo; destrava a RQ1 (T-1405).

## E6 · Testes de avaliação (nuvem)

41. **T-1105** (nuvem) Rotular o campo pela verdade de referência. Rotular o campo pela verdade de referência.
42. **T-1106** (nuvem) Rodar o Juiz congelado no campo (teste cego). Teste cego no campo com o Juiz congelado (Teste 5).
43. **T-1205** (nuvem) Ataque: referência forjada (sem custódia). Ataque de referência forjada: sem custódia o Juiz cai (RQ5).
44. **T-1203** (nuvem) Ataque: abliteração + LoRA de cura que restaura S2/S3. Ataque abliteração + LoRA de cura.
45. **T-1204** (nuvem) Ataque: treino contra o limiar usando o veredito binário. Ataque de treino contra o limiar com o veredito binário.
46. **T-1210** (nuvem) Protocolo do bounty interno: submissão, oráculo secreto, registro de rodadas. Bounty interno com oráculo secreto (precisa da parte secreta, T-304).
47. **T-1213** (nuvem) Ablação com e sem custódia (RQ5). Ablação com e sem custódia (RQ5).
48. **T-1010** (nuvem) Sondas de robustez do juiz do portão: texto acrescentado e estilo da resposta. Sondas de robustez do avaliador do portão (P2).

## E7 · Análise e congelamento dos resultados (G4)

49. **T-1405** (agente) RQ1: liberação silenciosa e falso alarme por classe, contra a linha de base. RQ1: liberação silenciosa e falso alarme por classe, contra a linha de base.
50. **T-1108** (agente) Comparar as distribuições de S1–S3 entre injeção e campo; injeções fora da distribuição à parte (Natella). Distribuições de S1–S3 entre injeção e campo.
51. **T-1212** (agente) Modelo analítico 1 − (1 − e)^k com os números medidos. Modelo analítico do escape com os números medidos; destrava RQ4 e a seção de identidade.
52. **T-1408** (agente) RQ4: escape × rodadas. RQ4: escape × rodadas.
53. **T-1409** (agente) RQ5: ablação dos sinais e da custódia; custo por veredito. RQ5: ablação dos sinais e da custódia; custo por veredito.
54. **T-1410** (agente) Figuras no padrão IEEE. Figuras no padrão IEEE.
55. **T-1411** (agente) Congelar os resultados e registrar o commit (G4). Congelar os resultados e registrar o commit (G4): libera a escrita da avaliação.

## E8 · Artigo (por último)

56. **T-1501** (artigo) Novo esqueleto do LaTeX, tirando as seções do Juiz de código. Compilar o esqueleto novo do LaTeX; destrava todas as seções.
57. **T-1513** (artigo) refs.bib só com a base (D5) e os moldes do DSN. refs.bib só com a base e os moldes do DSN.
58. **T-1502** (artigo) Seção 3: sistema e ameaça. Seção 3: sistema e ameaça.
59. **T-1503** (artigo) Seção 4: modelo de falhas e propriedade. Seção 4: modelo de falhas e propriedade.
60. **T-1507** (artigo) Seção 2: contexto. Seção 2: contexto.
61. **T-1510** (artigo) Seção 9: trabalhos relacionados (camadas 2 e 3). Seção 9: trabalhos relacionados.
62. **T-1505** (artigo) Seção 6: metodologia. Seção 6: metodologia (depois do prereg e do Natella).
63. **T-1709** (artigo) Escrever identidade e cota no artigo. Identidade e cota no artigo (depois do modelo analítico).
64. **T-1508** (artigo) Seção 7: avaliação. Seção 7: avaliação (depois do G4).
65. **T-1509** (artigo) Seção 8: ameaças à validade. Seção 8: ameaças à validade.
66. **T-1514** (artigo) Resumo (≤ 150 palavras) e título definitivo. Resumo e título definitivo.
67. **T-1512** (artigo) Ética, AI Tool Usage e declaração de artefato. Ética, uso de IA e declaração de artefato.
68. **T-1515** (humano) Rascunho completo aos coautores. Rascunho completo aos coautores.
69. **T-1516** (artigo) Incorporar revisões e cortar para 11 páginas. Incorporar revisões e cortar para 11 páginas.
70. **T-1517** (artigo) Checagem double-blind (anonimização). Checagem double-blind.
71. **T-1518** (humano) Submeter o artigo. Submeter o artigo (02/12).
