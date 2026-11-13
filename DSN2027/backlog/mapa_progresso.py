"""Regenera o painel Progresso do Mapa a partir do backlog (versão pós-redução).
   python3 -I progresso.py <backlog.json> <mapa_vivo.html> <saida.html>"""
import collections, datetime as dt, functools, html, json, sys
BK, SRC, OUT = sys.argv[1:4]
TODAY = dt.date(2026, 11, 13)
H = {"P": 1, "M": 2, "G": 4}
e = html.escape
b = json.load(open(BK)); T = b["tasks"]; t = {x["id"]: x for x in T}
EP = {x["id"]: x for x in b["epicos"]}; MK = {m["id"]: m for m in b["marcos"]}
done = {k for k, v in t.items() if v["status"] == "feito"}
cut = {k for k, v in t.items() if v["status"] == "cortada"}
closed = done | cut
h = lambda x: H[x["tamanho"]]
d = lambda s: dt.date.fromisoformat(s[:10])
br = lambda day: f"{day.day:02d}/{day.month:02d}"
oid = lambda x: x.get("objetivoMaior") or EP[x["epico"]].get("objetivoMaior", "")
OB = [o for o in b["objetivos"] if not o.get("tipo")]
TS = sorted([o for o in b["objetivos"] if o.get("tipo") == "teste"], key=lambda o: o["numero"])
META = next(o for o in b["objetivos"] if o.get("tipo") == "meta")

done_h = sum(h(x) for x in T if x["id"] in done)
open_ts = [x for x in T if x["id"] not in closed]
open_h = sum(h(x) for x in open_ts)
total_h = done_h + open_h
p0_open = sum(h(x) for x in open_ts if x["prioridade"] == "P0")
p1_open = sum(h(x) for x in open_ts if x["prioridade"] == "P1")
sub = d(MK["SUB"]["data"]); days_left = (sub - TODAY).days
by_day = collections.Counter()
for x in T:
    if x["id"] in done: by_day[d(x.get("atualizado") or "2026-10-28")] += h(x)
pts, acc = [], 0
for day in sorted(by_day): acc += by_day[day]; pts.append((day, acc))

@functools.lru_cache(None)
def L(i): return (0 if i in closed else h(t[i])) + max((L(x) for x in t[i]["deps"] if x in t), default=0)
def chain(i):
    p = [i]
    while True:
        ds = [x for x in t[p[-1]]["deps"] if x in t and x not in closed]
        if not ds: return p[::-1]
        p.append(max(ds, key=L))
crit = chain(max((x["id"] for x in open_ts), key=L)); crit_h = sum(h(t[i]) for i in crit)
cg = collections.OrderedDict()
for i in crit: cg.setdefault(t[i]["epico"], []).append(i)

# ---------- gráfico de horas ----------
X0, X1 = dt.date(2026, 10, 28), sub
W, HH, ml, mr, mt, mb = 680, 280, 44, 128, 14, 34
ymax = 300 if total_h <= 290 else 440
xs = lambda day: ml + (day - X0).days / (X1 - X0).days * (W - ml - mr)
ys = lambda v: mt + (1 - v / ymax) * (HH - mt - mb)
g = [f'<svg class="pg-chart" viewBox="0 0 {W} {HH}" role="img" aria-label="Horas feitas por data e ritmo necessário até a submissão">']
for v in range(0, ymax + 1, 50 if ymax <= 300 else 100):
    g.append(f'<line class="pg-grid" x1="{ml}" x2="{W-mr}" y1="{ys(v):.1f}" y2="{ys(v):.1f}"/><text class="pg-ax" x="{ml-8}" y="{ys(v)+4:.1f}" text-anchor="end">{v}</text>')
for k in range(0, (X1 - X0).days + 1, 7):
    day = X0 + dt.timedelta(days=k)
    g.append(f'<text class="pg-ax" x="{xs(day):.1f}" y="{HH-12}" text-anchor="middle">{br(day)}</text>')
g.append(f'<line class="pg-total" x1="{ml}" x2="{W-mr}" y1="{ys(total_h):.1f}" y2="{ys(total_h):.1f}"/><text class="pg-lbl" x="{W-mr+8}" y="{ys(total_h)+4:.1f}">total {total_h} h</text>')
g.append(f'<line class="pg-today" x1="{xs(TODAY):.1f}" x2="{xs(TODAY):.1f}" y1="{mt}" y2="{HH-mb}"/><text class="pg-ax pg-today-t" x="{xs(TODAY)+5:.1f}" y="{mt+10}">hoje</text>')
g.append(f'<line class="pg-need" x1="{xs(TODAY):.1f}" y1="{ys(done_h):.1f}" x2="{xs(sub):.1f}" y2="{ys(total_h):.1f}"/><text class="pg-lbl" x="{W-mr+8}" y="{ys(total_h)+20:.1f}">tudo: {open_h/days_left:.0f} h/dia</text>')
g.append(f'<line class="pg-need p0" x1="{xs(TODAY):.1f}" y1="{ys(done_h):.1f}" x2="{xs(sub):.1f}" y2="{ys(done_h+p0_open):.1f}"/><text class="pg-lbl p0" x="{W-mr+8}" y="{ys(done_h+p0_open)+4:.1f}">só P0: {p0_open/days_left:.1f} h/dia</text>'.replace(".0 h/dia"," h/dia"))
g.append('<path class="pg-done" d="' + " ".join(f"{'M' if k == 0 else 'L'}{xs(a):.1f},{ys(v):.1f}" for k, (a, v) in enumerate(pts)) + '"/>')
for a, v in pts: g.append(f'<circle class="pg-dot" cx="{xs(a):.1f}" cy="{ys(v):.1f}" r="3.5"/>')
la, lv = pts[-1]
g.append(f'<text class="pg-lbl acc" x="{xs(la)-6:.1f}" y="{ys(lv)-10:.1f}" text-anchor="end">{lv} h feitas</text></svg>')
burn = "".join(g)

# ---------- marcos ----------
span = (X1 - X0).days; mrows, mdots = [], []
for m in b["marcos"]:
    md = d(m["data"]); ts = [x for x in T if x["marco"] == m["id"] and x["id"] not in cut]
    n, nd = len(ts), sum(x["id"] in done for x in ts)
    if nd == n: st, cls = "fechado", "ok"
    elif m["id"] == "ESP": st, cls = "J1 fechado; 1 task de apoio aberta", "ok"
    elif md < TODAY: st, cls = f"vencido há {(TODAY-md).days} dias", "bad"
    elif (md - TODAY).days <= 7: st, cls = f"em {(md-TODAY).days} dias", "warn"
    else: st, cls = f"em {(md-TODAY).days} dias", "muted"
    pct = round(100 * nd / n) if n else 100
    mrows.append(f'<li><span class="pg-mdate">{br(md)}</span><span class="pg-mid">{e(m["id"])}</span><span class="pg-mname">{e(m["nome"])}</span><span class="pg-chip {cls}">{e(st)}</span><span class="pg-mbar" style="--p:{pct}%"><i></i></span><span class="pg-mnum">{nd}/{n}</span></li>')
    mdots.append(f'<span class="pg-tdot {cls}" style="left:{(md-X0).days/span*100:.2f}%" title="{e(m["id"])} · {br(md)}"></span>')
track = (f'<div class="pg-track" aria-hidden="true"><span class="pg-tline"></span>{"".join(mdots)}<span class="pg-tnow" style="left:{(TODAY-X0).days/span*100:.2f}%"></span></div>'
         f'<div class="pg-tends" aria-hidden="true"><span>{br(X0)}</span><span>hoje {br(TODAY)}</span><span>{br(X1)}</span></div>')

# ---------- épicos ----------
FASE = {1: "Conceber o Juiz", 2: "Construir o Juiz", 3: "O Juiz dentro do DNAT", 4: "Avaliar o Juiz", 5: "Transversais"}
groups = []
for f in sorted({x["fase"] for x in b["epicos"]}):
    rows = []
    for ep in [x for x in b["epicos"] if x["fase"] == f]:
        ts = [x for x in T if x["epico"] == ep["id"]]
        th = sum(map(h, ts)); dh = sum(h(x) for x in ts if x["id"] in done); ch = sum(h(x) for x in ts if x["id"] in cut)
        nd, n = sum(x["id"] in done for x in ts), sum(x["id"] not in cut for x in ts); left = th - dh - ch
        o = ep.get("objetivoMaior", "")
        rows.append(f'<li><span class="pg-eid">{e(ep["id"])}</span><span class="pg-ename">{e(ep["titulo"])}{f"<span class=pg-eo>{o}</span>" if o else ""}</span>'
                    f'<span class="pg-ebar" role="img" aria-label="{dh} de {th} horas feitas, {ch} cortadas"><i class="d" style="width:{100*dh/th:.1f}%"></i><i class="c" style="width:{100*ch/th:.1f}%"></i></span>'
                    f'<span class="pg-enum">{nd}/{n} · {"pronto" if left == 0 else f"faltam {left} h"}</span></li>')
    groups.append(f'<div class="pg-egroup"><h4>{f} · {e(FASE[f])}</h4><ul class="pg-elist">{"".join(rows)}</ul></div>')

# ---------- caminho crítico ----------
crit_html = "".join(f'<li><span class="pg-cid">{e(ep)}</span><b>{e(EP[ep]["titulo"])}</b><small>{len(ids)} tasks · {sum(h(t[i]) for i in ids)} h</small><span class="pg-cfirst">{e(ids[0])} → {e(ids[-1])}</span></li>' for ep, ids in cg.items())

# ---------- custo ----------
COST = [("T-208 · bateria inteira, comprimento real", 444, ""), ("T-208 · só âncoras e 50 do XSTest", 169, ""),
        ("T-301 · 79 itens, 12 configurações, lote 1", 86, ""), ("Redução v2 · FP e NF4, 4 configurações, lote 1 (estimativa)", 29, "est")]
cost_html = "".join(f'<li><span class="pg-clbl">{e(n)}</span><span class="pg-cbar"><i class="{c}" style="width:{100*v/450:.1f}%"></i><span class="pg-c80" style="left:{100*80/450:.2f}%"></span></span><span class="pg-cnum">{v} min · {v/80:.2f}×</span></li>' for n, v, c in COST)

# ---------- próximas P0 ----------
nxt = [x for x in open_ts if x["prioridade"] == "P0" and all(y in closed for y in x["deps"])]
nxt_html = "".join(f'<li><span class="pg-nid">{e(x["id"])}</span><span>{e(x["titulo"])}</span><small>{oid(x)} · {e(x["epico"])} · {h(x)} h{" · caminho crítico" if x["id"] in crit else ""}</small></li>' for x in nxt)

# ---------- objetivos e testes ----------
cards = []
for o in OB:
    ts = [x for x in T if oid(x) == o["id"] and x["id"] not in cut]
    tot, dn = sum(map(h, ts)), sum(h(x) for x in ts if x["id"] in done)
    p0 = sum(h(x) for x in ts if x["prioridade"] == "P0" and x["id"] not in done)
    eps = sorted({x["epico"] for x in ts if EP[x["epico"]].get("objetivoMaior") == o["id"]}, key=lambda j: int(j[1:]))
    extra = [x["id"] for x in ts if x.get("objetivoMaior")]
    m = MK[o["marco"]]; mst, mcls = ("vencido", "bad") if m["data"] < str(TODAY) else (f'{m["data"][8:10]}/{m["data"][5:7]}', "muted")
    free = sorted([x for x in ts if x["id"] not in closed and all(y in closed for y in x["deps"])], key=lambda x: (x["prioridade"], int(x["id"][2:])))
    nx = "".join(f'<li><b>{e(x["id"])}</b> {e(x["titulo"][:70] + ("…" if len(x["titulo"]) > 70 else ""))} <small>{x["prioridade"]}</small></li>' for x in free[:3])
    warn = '<p class="pg-owarn">Nenhuma task P0: tudo aqui é P1.</p>' if p0 == 0 and dn < tot else ""
    tests = ", ".join(str(x["numero"]) for x in TS if x["pai"] == o["id"]) or "nenhum"
    cards.append(f'''<article class="pg-obj"><header><span class="pg-oid">{e(o["id"])}</span><h4>{e(o["nome"])}</h4><span class="pg-chip {mcls}">{e(m["id"])} · {e(mst)}</span></header>
      <p class="pg-opr"><b>Pronto quando</b> {e(o["pronto"])}</p>
      <p class="pg-odf"><span>Testes</span> {e(tests)}</p>
      <p class="pg-odf"><span>Defende</span> {e(o["defende"])} <span>· épicos</span> {e(", ".join(eps))}{(" <span>· e</span> " + e(", ".join(extra))) if extra else ""}</p>
      <div class="pg-obar" role="img" aria-label="{dn} de {tot} horas feitas"><i style="width:{100*dn/tot if tot else 0:.1f}%"></i></div>
      <p class="pg-onum">{dn} de {tot} h feitas · P0 em aberto: {p0} h · {len(ts)} tasks</p>{warn}
      <div class="pg-onext"><span>Próximas, já desbloqueadas</span><ul>{nx or "<li>Nenhuma desbloqueada ainda.</li>"}</ul></div></article>''')
trows = []
for x in TS:
    ts = [y for y in T if y.get("teste") == x["id"] and y["id"] not in cut]; nd = sum(y["id"] in done for y in ts)
    trows.append(f'<li><span class="pg-tn">{x["numero"]}</span><div><b>{e(x["nome"])}</b> <span class="pg-tm">{e(x["pai"])} · {e(x["rq"])} · marco {e(x["marco"])} · {nd}/{len(ts)} tasks</span><p>{e(x["pronto"])}</p><p class="pg-ta">Amostra: {e(x["amostra"])}</p></div></li>')

late = [m["id"] for m in b["marcos"] if m["id"] != "ESP" and d(m["data"]) < TODAY and any(x["marco"] == m["id"] and x["id"] not in closed for x in T)]
g3 = [x for x in T if x["marco"] == "G3" and x["id"] not in cut]
PANEL = f'''<div class="panel" id="p-progresso" data-tab="progresso" hidden>
<section class="pg">
  <div class="sec-head"><h2>Progresso</h2><p class="lede">Onde o trabalho está até a submissão de {br(sub)}, depois da <a href="https://claude.ai/artifact/J9jERdCKczAsvk3YWvJbSr">redução v2</a> de 11/11, que cortou o que faltava sem tirar nenhum teste. Faltam {open_h} h, contando a T-709, opcional. Retrato de {br(TODAY)}/{TODAY.year}, calculado do backlog (P = 1 h, M = 2 h, G = 4 h; as tasks cortadas saem da conta); o estado vivo fica no <a href="https://claude.ai/artifact/2CB9dWqRXKFdv7APZCtcbF">Backlog do Juiz</a>.</p></div>

  <div class="pg-tiles">
    <div><b>{days_left} dias</b><span>até a submissão ({br(sub)})</span></div>
    <div><b>{done_h} de {total_h} h</b><span>feitas ({round(100*done_h/total_h)}%), {len(done)} tasks</span></div>
    <div><b>{p0_open} h</b><span>de P0 em aberto, em {sum(1 for x in open_ts if x["prioridade"]=="P0")} tasks</span></div>
    <div><b>{len(late)} marcos</b><span>vencidos sem fechar ({", ".join(late)})</span></div>
  </div>

  <div class="pg-block pg-goals">
    <h3>O que queremos e para que serve cada task</h3>
    <div class="pg-meta"><span class="eyebrow">Meta</span><p><b>{e(META["nome"])}</b> {e(META["texto"])}</p></div>
    <p class="pg-note">Cada task serve a um destes seis objetivos, pelo épico (as da J16, gestão, têm o seu próprio). A ordem é O1 → O2 → O4 → O5; o O3 e o O6 são construídos ao lado e provados na fase de testes (TST), depois que o G3 fecha o sistema. As tasks que executam ou analisam um teste levam também o número dele. No <a href="https://claude.ai/artifact/2CB9dWqRXKFdv7APZCtcbF">Backlog do Juiz</a>, cada cartão mostra o objetivo e o teste, e dá para filtrar por eles.</p>
    <div class="pg-objs">{"".join(cards)}</div>
    <h4 class="pg-th">Os testes, na ordem em que rodam</h4>
    <ol class="pg-tests">{"".join(trows)}</ol>
  </div>

  <div class="pg-block">
    <h3>Horas feitas e o ritmo que falta</h3>
    <p class="pg-note">Fazer tudo o que ficou até {br(sub)} pede {open_h/days_left:.0f} h por dia; só o P0, {p0_open/days_left:.1f} h por dia. O P1 em aberto soma {p1_open} h.</p>
    <figure class="dfig pg-fig"><div class="dscroll">{burn}</div>
      <figcaption class="pg-legend"><span><i class="k-done"></i>feito</span><span><i class="k-need"></i>ritmo para fazer tudo</span><span><i class="k-p0"></i>ritmo para o P0</span></figcaption></figure>
    <ul class="pg-events">
      <li><span>28/10</span>Especificação do Juiz fechada (J1, E14 e D6)</li>
      <li><span>05/11</span>Fundação quase pronta (J2) e primeira medida de custo (T-208)</li>
      <li><span>09/11</span>Identidade cara e cota por veredito decididas (T-1701, D7)</li>
      <li><span>11/11</span>Composição da bateria (T-301), objetivos e testes numerados, identidade mínima e redução v2</li>
      <li><span>12/11</span>Construção local: escada e saída do veredito, formatos, revogação em cascata, cota, cliente de identidade, orquestrador, juiz de referência e rascunhos do artigo (D8)</li>
    </ul>
  </div>

  <div class="pg-block">
    <h3>Marcos</h3>
    {track}
    <ul class="pg-marcos">{"".join(mrows)}</ul>
  </div>

  <div class="pg-two">
    <div class="pg-block">
      <h3>Caminho crítico</h3>
      <p class="pg-note">A cadeia mais longa do que falta: {len(crit)} tasks em sequência, {crit_h} h, mesmo com tudo o mais em paralelo. Começa pela {e(crit[0])}, já desbloqueada.</p>
      <ol class="pg-crit">{crit_html}</ol>
    </div>
    <div class="pg-block">
      <h3>Custo do veredito</h3>
      <p class="pg-note">Só a geração do S1, para um derivado que não regrediu, contra a meta de 80 min em 4 vCPU. Com FP e NF4 (redução v2) a geração cabe com folga; falta medir o avaliador (T-309) e repetir numa VM (T-210).</p>
      <ul class="pg-cost">{cost_html}</ul>
      <p class="pg-c80l"><span></span>meta de 80 min</p>
    </div>
  </div>

  <div class="pg-block">
    <h3>Épicos</h3>
    <p class="pg-note">Horas feitas sobre o total de cada épico; o trecho listrado foi cortado ou juntado em outra task na redução v2. Os detalhes de cada épico estão na aba Épicos.</p>
    <div class="pg-egrid">{"".join(groups)}</div>
  </div>

  <div class="pg-two">
    <div class="pg-block">
      <h3>Riscos e pendências</h3>
      <ul class="pg-risks">
        <li class="bad"><b>Marcos vencidos.</b> {", ".join(late)} passaram sem fechar, e o G3 vence em {(d(MK["G3"]["data"])-TODAY).days} dias com {sum(x["id"] in done for x in g3)} de {len(g3)} tasks feitas.</li>
        <li class="bad"><b>O ritmo.</b> O que falta pede ~{open_h/days_left:.0f} h por dia até {br(sub)}; o ritmo até aqui foi de ~{done_h/(TODAY-X0).days:.0f} h por dia.</li>
        <li class="warn"><b>Todo dado do artigo sai da nuvem.</b> População, rótulos, calibração, campo, custo e ablação rodam nas VMs de nuvem (Azure ou Oracle) no TST, depois do fechamento do sistema (T-1611); a máquina local só constrói e verifica com fumaça. Isso concentra a carga de CPU entre 16/11 e 21/11.</li>
        <li class="warn"><b>O avaliador só será medido na nuvem (T-309, T-315, fase de testes).</b> A geração cabe nos 80 min com FP e NF4, mas o avaliador lendo cada resposta pode custar mais que ela: a medida parcial do notebook (Qwen3Guard em float32, ~264 min por veredito) é só pista.</li>
        <li class="warn"><b>Decisões com o orientador.</b> A redução v2 revê seis decisões (formatos FP e NF4, população menor, Teste 4 menor, CVM sem warm pool, parte secreta de uma fonte, três ataques), e a T-301 propõe a aprovação no agregado; junto com os pontos da E14 §17. A escolha do juiz de referência (gpt-oss-20b, T-1002) é proposta de 12/11 e também passa por ele.</li>
        <li class="warn"><b>A construção local acabou.</b> O que resta depende da nuvem (T-210, T-801, T-414 e a CVM da T-807), do orientador (T-304), de pessoas (T-1605), de acesso (T-1604), do aceite da licença da Meta (T-1103), do comitê (T-1606) ou do LaTeX (T-1501). Sem o Juiz como segundo job, nenhum job bom acerta a cota: cada um fica com 5 reservados.</li>
        <li class="warn"><b>Recursos decididos em 12/11, com pendência.</b> Máquinas da campanha (T-1601), juiz de referência e família não vista (T-1602) e nuvem (T-1603: Azure e Oracle) estão decididos; faltam o crédito, o tipo de VM e a licença da Meta.</li>
      </ul>
    </div>
    <div class="pg-block">
      <h3>Pode começar agora</h3>
      <p class="pg-note">As tasks P0 cujas dependências estão feitas.</p>
      <ul class="pg-next">{nxt_html}</ul>
    </div>
  </div>
</section>
</div>
'''
src = open(SRC, encoding="utf-8").read()
nl = src.index("\n"); assert src.startswith("<!doctype html>"); src = src[nl + 1:].rstrip()
assert src.endswith("</body></html>"); src = src[:-len("</body></html>")].rstrip() + "\n"
a = src.index('<style>\n/* ===== progresso ===== */'); se = src.index("</style>", a) + len("</style>")
p0 = src.index('<div class="panel" id="p-progresso"'); p1 = src.index('<div class="panel" id="p-epicos"')
assert a < se <= p0 < p1
css = src[a:se]
src = src[:a] + css + "\n" + PANEL + src[p1:]
open(OUT, "w", encoding="utf-8").write(src)
print("ok", len(src), "aberto", open_h, "h; feito", done_h, "; P0", p0_open, "; crit", crit[0], "→", crit[-1], crit_h, "h; próximas", [x["id"] for x in nxt], "; vencidos", late)
