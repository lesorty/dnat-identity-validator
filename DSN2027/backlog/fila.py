"""Fila de execução do board (13/11; T-814 e T-815 feitas, o sistema fecha no modo direto): a ordem em que as tasks abertas serão pegas, por etapa.

Gera fila.json (para consumo automático) e FILA.md (para leitura) e confere a ordem contra o
backlog.json: toda dependência aberta de uma task tem de aparecer antes dela na fila, e toda task
aberta do board tem de estar na fila uma vez.

Regra de consumo: pegar o primeiro item da fila cujo `executor` está disponível e cujas
dependências estão feitas (status feito ou cortada no backlog). `executor`:
    agente   roda aqui, sem nuvem nem decisão humana
    humano   ação ou decisão sua ou do orientador (o agente só prepara)
    nuvem    o agente executa, mas precisa das VMs de nuvem (T-1603, T-210)
    artigo   escrita do artigo: só depois do sistema e dos resultados (preferência registrada)

    python3 DSN2027/backlog/fila.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (etapa, objetivo da etapa, [(task, executor, por que nesta posição / o que destrava)])
ETAPAS = [
    ("E2", "Desbloqueios humanos da porta T-1611", [
        ("T-1603", "humano", "Nuvem e crédito: sem isso nada da fase de testes roda; destrava T-210, T-309, T-315, T-801, T-812."),
        ("T-210", "humano", "VM de 4 vCPU: medida de custo válida e máquina do piloto; dependência da T-1611 e da T-309."),
        ("T-304", "humano", "Origem da parte secreta (orientador): última decisão de construção da T-1611; destrava o bounty (T-1210)."),
        ("T-1103", "humano", "Aceitar a licença da Meta e baixar o campo e a família não vista; destrava T-1105 e T-913."),
        ("T-1606", "humano", "Comitê de ética para a anotação; destrava a amostra de anotação (T-1005)."),
        ("T-1605", "humano", "Anotadores e guardião da bateria secreta; destrava a anotação (T-1007)."),
        ("T-1604", "humano", "Natella pelo acesso institucional; destrava T-1108 e a seção 6 (T-1505)."),
    ]),
    ("E3", "Sistema na nuvem e congelamento", [
        ("T-801", "nuvem", "CVM de job de uso único (criar, rodar, destruir); usa a imagem do executor da T-815."),
        ("T-806", "nuvem", "Fine-tuning LoRA de exemplo numa CVM de uso único: a primeira metade do fluxo no DNAT real."),
        ("T-1611", "humano", "Congelar o código do Juiz e do fluxo: abre a fase de testes; daqui em diante mudar o Juiz obriga a recalibrar."),
        ("T-309", "nuvem", "Avaliador do portão medido na VM (Gemma 4 E4B × Qwen3Guard): fixa o avaliador da liberação."),
        ("T-315", "nuvem", "Avaliadores em bf16 na família da CVM: custo do avaliador, que decide se o veredito cabe em 80 min."),
        ("T-312", "nuvem", "Referência custodiada do pai (código pronto em model_gate.reference); sem ela não há veredito real."),
        ("T-505", "nuvem", "Instrumento reduzido em cada formato; insumo da sanidade (T-313) e do custo (T-314)."),
        ("T-414", "nuvem", "Camada da direção do S2 pelo efeito da intervenção; fecha o ρ usado pelo Juiz antes da sanidade."),
        ("T-313", "nuvem", "Teste 1: o Juiz real separa o abliterado público e não oscila no base (repete a verificação da T-807)."),
        ("T-314", "nuvem", "Custo do instrumento por configuração, com o avaliador: número do G1 e da RQ5."),
        ("T-813", "nuvem", "Teste 8 na nuvem com o Juiz real (o ensaio local é a T-814)."),
        ("T-1707", "nuvem", "Teste 9: identidade e cota, com demonstração."),
        ("T-812", "nuvem", "Overhead VM comum × CVM; insumo da RQ5 (T-1409)."),
        ("T-709", "nuvem", "Gás das funções novas do contrato (opcional, P3)."),
    ]),
    ("E4", "População e verdade de referência (nuvem)", [
        ("T-914", "nuvem", "População do piloto (2 abliterações, 2 LoRA): primeiro sinal de separação e custo."),
        ("T-905", "nuvem", "F1 benigno nos 3 datasets: o grosso dos derivados que devem passar."),
        ("T-907", "nuvem", "F2: dose de exemplos nocivos; derivados que devem reprovar."),
        ("T-909", "nuvem", "F0 endurecido: derivados que recusam mais (guarda de recusa excessiva)."),
        ("T-917", "nuvem", "F3: varredura da abliteração; destrava o ataque de cura (T-1203)."),
        ("T-906", "nuvem", "F1 que degrada (zona cinza), relatada à parte."),
        ("T-910", "nuvem", "Utilidade dos derivados: separa N de C na rotulagem."),
        ("T-912", "nuvem", "Divisões de calibração e teste: destrava θ (T-603), linha de base (T-1302) e família não vista (T-913)."),
        ("T-913", "nuvem", "Família não vista (Llama-3.2-1B): generalização do limiar (Teste 4)."),
        ("T-1003", "nuvem", "Juiz de referência (gpt-oss-20b) sobre as gerações: base dos rótulos."),
        ("T-1005", "humano", "Amostra estratificada para anotação humana (depende do comitê, T-1606)."),
        ("T-1008", "nuvem", "Rótulos finais com divergências resolvidas: destrava rotulagem H/C/N e campo."),
        ("T-911", "nuvem", "Rótulo H/C/N de cada derivado pela regra da T-1004."),
        ("T-1007", "humano", "Anotação por dois anotadores e κ (pessoas da T-1605)."),
    ]),
    ("E5", "Calibração e pré-registro", [
        ("T-603", "nuvem", "θ da segunda linha (S2/S3) a FPR de 5% na calibração."),
        ("T-604", "agente", "Faixa de inconclusivo em torno do limiar (decisão sobre os números da T-603)."),
        ("T-606", "agente", "prereg.yaml com δ, τ, tolerâncias e tamanhos: tira o Juiz real do StageNotReady."),
        ("T-607", "agente", "Commit do prereg antes de abrir o teste: a partir daqui os resultados contam."),
        ("T-1302", "nuvem", "Linha de base de Hurtado calibrada pelo mesmo protocolo; destrava a RQ1 (T-1405)."),
    ]),
    ("E6", "Testes de avaliação (nuvem)", [
        ("T-1105", "nuvem", "Rotular o campo pela verdade de referência."),
        ("T-1106", "nuvem", "Teste cego no campo com o Juiz congelado (Teste 5)."),
        ("T-1205", "nuvem", "Ataque de referência forjada: sem custódia o Juiz cai (RQ5)."),
        ("T-1203", "nuvem", "Ataque abliteração + LoRA de cura."),
        ("T-1204", "nuvem", "Ataque de treino contra o limiar com o veredito binário."),
        ("T-1210", "nuvem", "Bounty interno com oráculo secreto (precisa da parte secreta, T-304)."),
        ("T-1213", "nuvem", "Ablação com e sem custódia (RQ5)."),
        ("T-1010", "nuvem", "Sondas de robustez do avaliador do portão (P2)."),
    ]),
    ("E7", "Análise e congelamento dos resultados (G4)", [
        ("T-1405", "agente", "RQ1: liberação silenciosa e falso alarme por classe, contra a linha de base."),
        ("T-1108", "agente", "Distribuições de S1–S3 entre injeção e campo."),
        ("T-1212", "agente", "Modelo analítico do escape com os números medidos; destrava RQ4 e a seção de identidade."),
        ("T-1408", "agente", "RQ4: escape × rodadas."),
        ("T-1409", "agente", "RQ5: ablação dos sinais e da custódia; custo por veredito."),
        ("T-1410", "agente", "Figuras no padrão IEEE."),
        ("T-1411", "agente", "Congelar os resultados e registrar o commit (G4): libera a escrita da avaliação."),
    ]),
    ("E8", "Artigo (por último)", [
        ("T-1501", "artigo", "Compilar o esqueleto novo do LaTeX; destrava todas as seções."),
        ("T-1513", "artigo", "refs.bib só com a base e os moldes do DSN."),
        ("T-1502", "artigo", "Seção 3: sistema e ameaça."),
        ("T-1503", "artigo", "Seção 4: modelo de falhas e propriedade."),
        ("T-1507", "artigo", "Seção 2: contexto."),
        ("T-1510", "artigo", "Seção 9: trabalhos relacionados."),
        ("T-1505", "artigo", "Seção 6: metodologia (depois do prereg e do Natella)."),
        ("T-1709", "artigo", "Identidade e cota no artigo (depois do modelo analítico)."),
        ("T-1508", "artigo", "Seção 7: avaliação (depois do G4)."),
        ("T-1509", "artigo", "Seção 8: ameaças à validade."),
        ("T-1514", "artigo", "Resumo e título definitivo."),
        ("T-1512", "artigo", "Ética, uso de IA e declaração de artefato."),
        ("T-1515", "humano", "Rascunho completo aos coautores."),
        ("T-1516", "artigo", "Incorporar revisões e cortar para 11 páginas."),
        ("T-1517", "artigo", "Checagem double-blind."),
        ("T-1518", "humano", "Submeter o artigo (02/12)."),
    ]),
]


def main() -> int:
    backlog = json.loads((HERE / "backlog.json").read_text())
    tasks = {t["id"]: t for t in backlog["tasks"]}
    closed = {k for k, t in tasks.items() if t["status"] in ("feito", "cortada")}
    open_ids = set(tasks) - closed
    seen, problems, items = [], [], []
    for etapa, objetivo, rows in ETAPAS:
        for tid, executor, motivo in rows:
            t = tasks.get(tid)
            if t is None:
                problems.append(f"{tid} não existe no backlog")
                continue
            if tid in closed:
                problems.append(f"{tid} já está {t['status']}")
            pend = [d for d in t["deps"] if d in tasks and d not in closed]
            late = [d for d in pend if d not in seen]
            if late:
                problems.append(f"{tid} aparece antes das dependências {late}")
            seen.append(tid)
            items.append({"ordem": len(items) + 1, "etapa": etapa, "task": tid, "titulo": t["titulo"],
                          "executor": executor, "prioridade": t["prioridade"], "tamanho": t["tamanho"],
                          "marco": t["marco"], "deps_abertas": pend, "motivo": motivo})
    dup = {x for x in seen if seen.count(x) > 1}
    missing = open_ids - set(seen)
    if dup:
        problems.append(f"repetidas: {sorted(dup)}")
    if missing:
        problems.append(f"abertas fora da fila: {sorted(missing)}")
    if problems:
        print("\n".join(problems))
        return 1

    doc = {"schema": "dnat.fila.v1", "gerado_em": "2026-11-13",
           "regra": "pegar o primeiro item cujo executor está disponível e cujas dependências estão feitas",
           "etapas": [{"id": e, "objetivo": o} for e, o, _ in ETAPAS], "itens": items}
    (HERE / "fila.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    lines = ["# Fila de execução do board", "",
             "Ordem em que as tasks abertas serão pegas (13/11). Gerada por `fila.py`, que confere a ordem contra o",
             "`backlog.json`: nenhuma task aparece antes das suas dependências abertas. Versão para máquina: `fila.json`.", "",
             "**Regra:** pegar o primeiro item cujo executor está disponível e cujas dependências estão feitas.",
             "**Executor:** `agente` roda aqui; `humano` é decisão ou ação sua ou do orientador; `nuvem` precisa das",
             "VMs (T-1603, T-210); `artigo` fica para o fim, depois do sistema e dos resultados.", ""]
    for etapa, objetivo, rows in ETAPAS:
        lines += [f"## {etapa} · {objetivo}", ""]
        for it in (x for x in items if x["etapa"] == etapa):
            lines.append(f"{it['ordem']}. **{it['task']}** ({it['executor']}) {it['titulo']}. {it['motivo']}")
        lines.append("")
    (HERE / "FILA.md").write_text("\n".join(lines))
    print(f"ok: {len(items)} tasks em {len(ETAPAS)} etapas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
