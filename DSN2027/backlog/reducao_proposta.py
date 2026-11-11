"""Proposta de redução do backlog: ação por task, horas e checagem de dependências.
   python3 -I reducao.py <backlog.json> <saida.json>"""
import json, sys, collections
H = {"P": 1, "M": 2, "G": 4}
b = json.load(open(sys.argv[1])); T = {x["id"]: x for x in b["tasks"]}
EP = {e["id"]: e for e in b["epicos"]}
# ação: manter | encolher(tam) | juntar(em) | cortar | opcional | feita ; motivo; reescrever?
A = {}
def m(i, why, rw=False): A[i] = ("manter", None, why, rw)
def e(i, tam, why, rw=True): A[i] = ("encolher", tam, why, rw)
def j(i, em, why): A[i] = ("juntar", em, why, False)
def c(i, why): A[i] = ("cortar", None, why, False)
def o(i, why): A[i] = ("opcional", None, why, False)
def f(i, why): A[i] = ("feita", None, why, False)

# J2 Fundação
c("T-209", "Os testes com o modelo minúsculo já existem e passam; o workflow de CI é conveniência, não sustenta afirmação.")
e("T-210", "P", "Basta uma VM barata de 4 vCPU por algumas horas, só para repetir a medida de custo do Teste 1 fora do notebook.")
# J3 Instrumento
m("T-302", "Caminho crítico. Com a T-301, fixa o procedimento de sorteio estratificado das 32 âncoras públicas.", True)
e("T-303", "P", "Só os 25 seguros por veredito; os contrastes saíram do veredito (T-301).")
e("T-304", "P", "Parte secreta de uma fonte só: amostra do StrongREJECT fora da lista publicada, com o compromisso por hash. Escrever do zero e gerar por LLM vira trabalho futuro.")
e("T-305", "P", "Só os 6 codificados da composição: transformar texto em base64, César e leetspeak é trivial.")
m("T-306", "Caminho crítico e curta.")
e("T-307", "G", "Vira a geração única (E14 §6.2): respostas do derivado às âncoras, com o detector de recusa usado para achar as âncoras do pai no depósito.")
j("T-308", "T-307", "O segundo estágio deixou de existir com a geração única.")
m("T-309", "Maior risco do custo. Reescrever: o avaliador sai da disputa Gemma 4 E4B × Qwen3Guard-4B (T-105), não do Gemma 2B.", True)
m("T-310", "Dano e recusa excessiva por item.")
m("T-311", "Reescrever para o teste da T-301: aprovação no agregado, δ por categoria no veto, dano binarizado.", True)
m("T-312", "Referência custodiada do pai.")
A["T-313"] = ("manter", None, "É o Teste 1: o instrumento separa o óbvio e não oscila. Sobe para P0.", False)
A["T-314"] = ("manter", None, "Critério do G1 (80 min com o avaliador). Absorve o custo por formato (T-509) e o de S2/S3 (T-411). Sobe para P0.", False)
# J4 S2/S3
m("T-401", "S2 é a segunda linha e a base da linha de base de Hurtado e da ablação da custódia.")
m("T-402", "Absorve a escolha da camada (T-403) e a guarda com hash (T-404).")
j("T-403", "T-402", "Um critério fixo, escrito junto com a direção.")
j("T-404", "T-402", "Guardar com hash é uma linha a mais na T-402.")
m("T-405", "Sinal S2.")
m("T-406", "Teste curto de S2 (abliterado público × base).")
m("T-407", "Sinal S3.")
m("T-408", "Absorve o teste sintético de S3 (T-409).")
j("T-409", "T-408", "O teste sintético entra com a métrica.")
c("T-410", "O adaptador LoRA é sempre fundido sob custódia antes do Juiz (T-103); a forma separada não chega ao Juiz.")
j("T-411", "T-314", "Tempo e memória de S2 e S3 entram na medida de custo do G1.")
c("T-413", "P3. Várias direções (Wollschläger) vira ameaça à validade declarada.")
# J5 Formatos: FP + NF4
m("T-503", "Primeiro passo: se o bitsandbytes rodar em CPU, a quantização própria encolhe.")
e("T-501", "M", "Só NF4 (proposta: liberar FP e NF4 no protótipo). Absorve a conferência contra a referência (T-502).")
j("T-502", "T-501", "Conferir contra a referência numa amostra é parte de implementar NF4.")
m("T-504", "Digest de cada formato liberado, para o recibo.")
e("T-505", "M", "Mesma bateria em 2 formatos, não em 4.")
c("T-506", "Contradiz a E14 §15: a bateria não é reduzida nos quantizados.")
j("T-508", "T-609", "O base quantizado já é um dos casos do teste ponta a ponta do veredito.")
j("T-509", "T-314", "O custo por formato entra na medida de custo do G1.")
# J6 Veredito
c("T-601", "Sem z-soma no Juiz (T-108): S2 e S3 têm limiar próprio a FPR 5%, sem normalizar e somar.")
e("T-602", "M", "Reescrever como a escada do veredito (E14 §6.3), com a regra tudo ou nada dos formatos (absorve a T-605). A z-soma fica só na linha de base (T-1301).")
m("T-603", "θ da segunda linha a FPR 5% na calibração.")
m("T-604", "Faixa de inconclusivo.")
j("T-605", "T-602", "A regra por formato é um degrau da escada.")
m("T-606", "Pré-registro. Absorve seeds e repetições (T-1403).")
m("T-607", "Commit do pré-registro.")
m("T-608", "verdict.json para o recibo.")
m("T-609", "Teste ponta a ponta do veredito; absorve o base quantizado (T-508).")
# J7 Contrato
m("T-701", "Absorve os campos do derivado (T-702).")
j("T-702", "T-701", "Tipo e campos do derivado numa mudança só do contrato.")
m("T-703", "Só o executor registra o derivado.")
m("T-704", "Reprovado nunca fica ativo.")
m("T-705", "Revogação pelo operador.")
c("T-706", "Compra de acesso é herança do mercado; com modelos abertos de custo zero (D1), não sustenta afirmação.")
e("T-707", "P", "Cascata mínima: o derivado só é ativo se o pai é ativo (uma checagem). Faz parte do critério do G3.")
e("T-708", "M", "Testes do contrato só dos casos do Teste 8.")
o("T-709", "Custo do recibo em gás: o measure-gas.js já existe, então é 1 h se sobrar tempo; senão o recibo fica com custo estimado.")
c("T-710", "A demonstração usa o CLI e os testes; a interface web não sustenta afirmação.")
# J8 Executor e custódia
c("T-801", "Pool de CVMs de uso único. Proposta: o protótipo roda o fluxo no modo direto e uma vez numa CVM real; o pool fica como implantação descrita.")
m("T-802", "Sem tempos limite maiores, nem um treino nem um veredito terminam.")
m("T-803", "Retenção do derivado: o centro da custódia (C1).")
m("T-804", "Saída de esquema fixo.")
j("T-805", "T-806", "Entregar o base por digest é o primeiro passo do job de fine-tuning.")
m("T-806", "Primeira metade do fluxo.")
m("T-807", "O Juiz como segundo job.")
m("T-808", "Hash do Juiz no recibo.")
m("T-809", "Aprovado vira ativo com recibo (inclui o id da identidade).")
j("T-810", "T-809", "Reprovado não registrar é o outro ramo da mesma ligação.")
m("T-811", "É o protótipo funcional: o fluxo inteiro no modo direto.")
c("T-812", "Estudo de overhead VM × CVM. O custo por veredito sai do modo direto e de uma execução na CVM.")
e("T-813", "M", "O Teste 8 sobre o fluxo do modo direto, repetido uma vez na CVM.")
# J9 População (reduzida)
m("T-901", "Script único de LoRA.")
e("T-902", "P", "Dois datasets benignos (Alpaca e GSM8K) em vez de três.")
c("T-903", "Zona cinza (F1 que degrada) vira limitação declarada.")
m("T-904", "Exemplos nocivos para F2.")
e("T-905", "G", "Menos seeds e passos: meta de ~60 H no total (calibração e teste), não ~160.")
e("T-907", "M", "Três doses de exemplos nocivos em vez de uma varredura densa.")
m("T-908", "Abliteração (F3), também usada no piloto e no ataque.")
c("T-906", "Zona cinza fora (T-903).")
c("T-909", "F0 endurecido vira limitação declarada (controle negativo de S3).")
e("T-910", "M", "Utilidade pela perda no corpus benigno do próprio Juiz e pela acurácia da tarefa; MMLU fora.")
m("T-911", "Rótulo H/C/N.")
m("T-912", "Divisões; absorve o inventário (T-916) e a checagem de vazamento (T-1413).")
c("T-913", "Teste 4 (família não vista) sai: 90 derivados e o maior custo de CPU. Vira ameaça à validade declarada.")
m("T-914", "População do piloto.")
c("T-915", "CMFT num 0,5B: só servia ao ataque T-1206, que sai.")
j("T-916", "T-912", "O inventário nasce com as divisões.")
# J10 Verdade de referência
m("T-1001", "Bateria de referência independente (R12).")
m("T-1002", "Juiz de referência.")
m("T-1003", "Notas de referência.")
m("T-1004", "Regra do rótulo.")
e("T-1005", "P", "Amostra de 60 respostas e guia de anotação (absorve a T-1006).")
j("T-1006", "T-1005", "Guia curto junto com a amostra; a nota de ética é a T-1606.")
e("T-1007", "M", "Dois anotadores em 60 respostas, κ e concordância dos dois juízes (absorve a T-1009).")
m("T-1008", "Rótulos finais.")
j("T-1009", "T-1007", "A concordância sai da mesma anotação.")
c("T-1010", "Sondas de robustez do avaliador viram ameaça à validade.")
# J11 Campo
m("T-1101", "Candidatos de campo. Risco: pode haver poucos para o Qwen2.5-0.5B; meta ≥ 10 ou todos os que existirem.", True)
m("T-1102", "Filtro por formato e base.")
m("T-1103", "Absorve a confirmação da base (T-1104).")
j("T-1104", "T-1103", "Conferir arquitetura e pesos no mesmo passo do download.")
m("T-1105", "Rótulo do campo.")
m("T-1106", "Teste cego (RQ3).")
e("T-1108", "M", "Comparação injeção × campo, que já é a RQ3 (absorve a T-1407).")
# J12 Adaptativo
e("T-1201", "P", "Modelo do atacante e orçamento, curto.")
j("T-1202", "T-1605", "Separar guardião e atacante é a mesma decisão de pessoas.")
m("T-1203", "Ataque mínimo: abliteração + LoRA de cura.")
m("T-1204", "Ataque mínimo: treino contra o limiar.")
m("T-1205", "Referência forjada: base da RQ5.")
c("T-1206", "Na E13 §3.6, o CMFT só entrava se um 0,5B aprendesse a codificação; os 6 codificados seguem como sentinela no veredito.")
c("T-1207", "Extra na E13 §3.6. A leitura inteira da resposta já cobre o refuse-then-comply por desenho; vira discussão.")
c("T-1208", "Extra na E13 §3.6. O formato NF4 é avaliado em todo veredito; montar o ataque de Egashira vira trabalho futuro.")
c("T-1209", "Extra na E13 §3.6 e P3: a interface do job não expõe prefill.")
e("T-1210", "M", "Rodadas com o oráculo secreto, sem o protocolo formal de bounty (absorve a T-1211).")
j("T-1211", "T-1210", "Rodar as rodadas é o protocolo em execução.")
m("T-1212", "Modelo 1 − (1 − e)^k; absorve o custo com identidades e cota (T-1708).")
m("T-1213", "Ablação da custódia (RQ5).")
# J13 Linha de base
m("T-1301", "Linha de base (R15). Absorve a conferência contra Hurtado (T-1303).")
m("T-1302", "Calibrar a linha de base.")
j("T-1303", "T-1301", "Conferir contra um caso publicado faz parte de reimplementar.")
j("T-1304", "T-1405", "Rodar a linha de base são sinais baratos, no mesmo passo da RQ1.")
j("T-1305", "T-1510", "Uma frase nos trabalhos relacionados.")
# J14 Campanha
e("T-1401", "M", "Laço retomável simples numa máquina.")
c("T-1402", "Sem distribuir: a campanha reduzida cabe numa máquina (~90 h de CPU, 3 vereditos em paralelo).")
j("T-1403", "T-606", "Seeds e repetições ficam no pré-registro.")
m("T-1404", "IC por bootstrap.")
m("T-1405", "RQ1, o resultado-título.")
m("T-1406", "RQ2 sai das doses já geradas.")
j("T-1407", "T-1108", "A análise da RQ3 é a comparação injeção × campo.")
e("T-1408", "P", "Gráfico de escape × rodadas.")
e("T-1409", "M", "Ablação dos sinais e da custódia e custo por veredito, sem o estudo de overhead.")
m("T-1410", "Figuras.")
m("T-1411", "Congelar os resultados.")
e("T-1412", "P", "Declaração de artefato com scripts; sem preparar pacote completo.")
j("T-1413", "T-912", "Checar vazamento ao montar as divisões.")
j("T-1414", "T-1409", "O custo total entra na RQ5.")
# J15 Escrita: tudo necessário
for i in ["T-1501","T-1502","T-1503","T-1504","T-1505","T-1506","T-1507","T-1508","T-1509","T-1510","T-1511","T-1512","T-1513","T-1514","T-1515","T-1516","T-1517","T-1518"]:
    m(i, "Escrita do artigo.")
# J16 Gestão
m("T-1601", "Decidir onde roda a campanha (notebook + uma VM barata).")
m("T-1602", "Juiz de referência. A família não vista sai com a T-913.", True)
e("T-1603", "P", "Escolher a nuvem e subir uma CVM só para a demonstração (absorve a T-1607).")
e("T-1604", "M", "Baixar e ler o Natella (absorve a T-1609).")
m("T-1605", "Anotadores e guardião; absorve a independência do atacante (T-1202).")
e("T-1606", "P", "Nota de ética curta para a anotação e para a seção do CFP.")
j("T-1607", "T-1603", "Uma CVM para a demonstração.")
m("T-1608", "Datas de revisão.")
j("T-1609", "T-1604", "Ler o Natella junto com o download.")
f("T-1610", "A E13 já está no git (commit d79361d).")
# J17 Identidade
for i in ["T-1702","T-1703","T-1704","T-1705","T-1707"]:
    m(i, "Identidade mínima com prova de trabalho (etapa 2).")
j("T-1708", "T-1212", "O custo com identidades e cota é o mesmo modelo analítico.")
m("T-1709", "Identidade e cota no artigo.")


# Segunda passada: encolher o que ainda está em tamanho de trabalho manual
for i, t_, why in [
 ("T-1502","M","Seção 3 a partir da E14 §2–§3 e da E10, que já existem."),
 ("T-1503","M","Seção 4 a partir da E14 §5 e da T-301."),
 ("T-1505","M","Seção 6 a partir da E13 §3 e do pré-registro."),
 ("T-1507","M","Contexto curto: recusa, abliteração e fine-tuning nocivo."),
 ("T-1512","P","Textos padrão do CFP."),
 ("T-1513","P","Limpar o refs.bib para a base D5."),
 ("T-1515","P","Enviar o rascunho."),
 ("T-1203","M","Reaproveita a abliteração (T-908) e uma LoRA curta de cura."),
 ("T-703","P","Um modificador de papel no contrato."),
 ("T-704","P","Uma checagem em updateAsset."),
 ("T-705","P","Trocar o dono pelo operador em revokeAsset."),
 ("T-806","M","O job usa o script único de LoRA (T-901), sem código novo de treino."),
 ("T-809","M","Uma chamada ao contrato depois do verdict.json."),
 ("T-1410","M","Poucas figuras: RQ1, RQ3, RQ4 e custo."),
 ("T-1106","M","O tempo é de CPU; o trabalho humano é disparar e conferir."),
 ("T-307","M","O gerador determinístico já existe (T-205); falta o laço sobre as âncoras."),
 ("T-401","M","Extração de ativações por hook no último token."),
 ("T-908","M","Receita conhecida (Arditi) sobre a direção já calculada."),
 ("T-1301","M","Reaproveita S2 e S3; a z-soma é uma soma de z-scores."),
]:
    A[i] = ("encolher", t_, (A[i][2] + " " if A[i][0] == "manter" else "") + why, A[i][3] if i in A else True)

# Terceira passada (versão 2, 11/11): testes, análises, CVM real e campo cego ficam inteiros;
# o corte é só em detalhe de código, conveniência e gestão que não muda resultado.
# Volta o que a versão 1 tirava de teste, análise ou execução em CVM real:
A["T-913"] = ("encolher", "G", "Teste 4 volta, menor: ~35 derivados (20 H, 15 C) da família não vista, só F1 e F3, com as mesmas receitas e sem recalibrar.", True)
A["T-1602"] = ("manter", None, "Juiz de referência e a família não vista (o Teste 4 fica).", False)
A["T-801"] = ("encolher", "M", "CVM de uso único por job sem warm pool: um script cria a CVM, roda o job e a destrói. A execução em CVM real é argumento central.", True)
A["T-812"] = ("encolher", "M", "Custo por veredito na CVM real contra uma VM comum, para a RQ5; sem o estudo de CVM reaproveitada.", True)
A["T-1603"] = ("encolher", "M", "Escolher a nuvem e provisionar as CVMs (absorve a T-1607).", True)
# Detalhe de código e conveniência que sai ou encolhe:
for i, t_, why in [
 ("T-302","P","Sorteio estratificado com seed: um script curto que grava só os IDs."),
 ("T-312","P","Rodar o instrumento no base e gravar o resultado com hash."),
 ("T-608","P","verdict.json: um dicionário serializado com estado, regra, medidas e hashes."),
 ("T-804","P","Saída de esquema fixo: uma lista de campos permitidos; o resto é descartado."),
 ("T-901","M","Script de LoRA com peft e um arquivo de configuração; sem framework de experimentos."),
 ("T-904","P","Exemplos nocivos de um conjunto público, baixados fora do git."),
 ("T-914","P","População do piloto: rodar a T-901 e a T-908 duas vezes cada."),
 ("T-1401","P","Laço simples que pula o que já tem resultado; sem fila nem retomada sofisticada."),
 ("T-1406","P","Curvas da RQ2 a partir das doses já geradas."),
]:
    A[i] = ("encolher", t_, why, A[i][3])
j("T-406", "T-313", "A sanidade de S2 entra no Teste 1, com o mesmo abliterado público e o base repetido.")
j("T-609", "T-313", "O teste ponta a ponta do veredito é o próprio Teste 1 (base, abliterado, LoRA benigno, base quantizado).")
j("T-504", "T-505", "Gerar os formatos e registrar o digest é o primeiro passo de rodar o instrumento em cada formato.")
j("T-708", "T-813", "Testes unitários do contrato duplicam o Teste 8, que exercita os mesmos casos no fluxo inteiro.")
j("T-1412", "T-1512", "A declaração de artefato é um parágrafo junto da ética e do AI Tool Usage.")
c("T-1608", "Combinar datas é conversa, não task.")
A["T-313"] = ("manter", None, "É o Teste 1: o instrumento e o veredito separam o óbvio e não oscilam. Absorve a sanidade de S2 (T-406) e o teste ponta a ponta do veredito (T-609). Sobe para P0.", True)
# Voltam, pequenas, as classes e sondas que sustentam a análise:
A["T-909"] = ("encolher", "P", "F0 endurecido volta com poucos derivados: é o controle negativo de S3 e o caso de recusa excessiva que leva a inconclusivo.", True)
A["T-903"] = ("encolher", "P", "Dados que degradam a recusa (receitas de Qi 2024): o fine-tuning acidental da tese.", True)
A["T-906"] = ("encolher", "P", "Zona cinza com poucos derivados, relatada à parte (E13 §3.2).", True)
A["T-1010"] = ("encolher", "P", "Duas sondas (texto acrescentado e estilo) sobre respostas já geradas, para a ameaça A4 ao avaliador.", True)
CORTE = []

open_ids = [x["id"] for x in b["tasks"] if x["status"] not in ("feito", "cortada")]
missing = [i for i in open_ids if i not in A]; extra = [i for i in A if i not in open_ids]
assert not missing and not extra, (missing, extra)
keep = {i for i, a in A.items() if a[0] in ("manter", "encolher")}
def newh(i):
    a = A[i]; return H[a[1]] if a[0] == "encolher" else H[T[i]["tamanho"]]
# dependências: nenhuma task mantida pode depender de algo cortado (sem absorção)
def resolve(d):
    seen = set()
    while d in A and A[d][0] == "juntar" and d not in seen: seen.add(d); d = A[d][1]
    return d
probs = []
for i in keep:
    for d in T[i]["deps"]:
        r = resolve(d)
        if r in A and A[r][0] in ("cortar", "opcional"): probs.append((i, d, A[r][0]))
oid = lambda x: x.get("objetivoMaior") or EP[x["epico"]].get("objetivoMaior", "")
tot_before = sum(H[T[i]["tamanho"]] for i in open_ids)
tot_after = sum(newh(i) for i in keep)
cnt = collections.Counter(a[0] for a in A.values())
byobj = collections.OrderedDict()
for o_ in ["O1","O2","O3","O4","O5","O6"]:
    ids = [i for i in open_ids if oid(T[i]) == o_]
    byobj[o_] = dict(antes=sum(H[T[i]["tamanho"]] for i in ids), depois=sum(newh(i) for i in ids if i in keep),
                     tasks_antes=len(ids), tasks_depois=sum(i in keep for i in ids))
linha = []; acc = None
for nome, ids, why in CORTE:
    sv = sum(newh(i) for i in ids if i in keep) - (2 if "log assinado" in nome else 0)
    linha.append(dict(nome=nome, tasks=ids, motivo=why, economia=sv))
out = dict(linha_corte=linha, acoes={i: dict(acao=a[0], alvo=a[1], motivo=a[2], reescrever=a[3], titulo=T[i]["titulo"], epico=T[i]["epico"],
                         objetivo=oid(T[i]), teste=T[i].get("teste", ""), prioridade=T[i]["prioridade"], tamanho=T[i]["tamanho"],
                         horas_antes=H[T[i]["tamanho"]], horas_depois=(newh(i) if i in keep else 0)) for i, a in A.items()},
           total_antes=tot_before, total_depois=tot_after, contagem=cnt, por_objetivo=byobj, problemas_deps=probs)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print("antes", tot_before, "h; depois", tot_after, "h;", dict(cnt)); print(json.dumps(byobj)); print("deps problemáticas:", probs)
