#!/usr/bin/env python3
"""Order-analysis suite — gooi een reasoning_live.jsonl erin, krijg alle DV-metrieken.

Familie 1 (acties): actieverdeling + drift, economie/regime-kwadrant,
subgroep-detectie (combined-graph Leiden op transfers+berichten), twee-lagen
lidmaatschap (vast vs split, drempel tau), per-groep karakterisering, attack-structuur.

Gebruik: python3 order_suite.py <reasoning_live.jsonl> [--alpha 0.5] [--tau 0.6]
"""
import json, sys, math, argparse
from collections import defaultdict, Counter
import numpy as np

try:
    import igraph as ig
    import leidenalg
    HAVE_LEIDEN = True
except ImportError:
    HAVE_LEIDEN = False

PRIMARY = ['transfer', 'hold', 'take', 'strengthen_self', 'strengthen_other']

def cat(a):
    if a is None: return 'hold'
    a = str(a).lower()
    if a.startswith('invest') or a == 'transfer': return 'transfer'
    if a.startswith('take') or a == 'attack': return 'take'
    if 'arm_self' in a or 'strengthen_self' in a: return 'strengthen_self'
    if 'arm' in a or 'strengthen' in a: return 'strengthen_other'
    if a.startswith('drop') or a.startswith('invite'): return 'hold'  # rewire -> ignore at T2
    return 'hold'

def gini(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs); s = sum(xs)
    if n == 0 or s <= 0: return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * s) - (n + 1) / n

def normsym(X):
    Y = X / X.max() if X.max() > 0 else X
    return (Y + Y.T) / 2

def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]

def parse(lines):
    agents = set()
    T = defaultdict(float)   # transfer volume i->j (run-aggregaat)
    Mc = defaultdict(float)  # gerichte berichten i->j
    attacks = []             # (round, attacker, target)
    per_round = []           # {round, counts, sumR, Rs(dict)}
    for d in lines:
        ag = d.get('agents', {})
        agents.update(ag.keys())
        cc = Counter(); Rs = {}
        bf = d.get('bilateral_flows') or {}
        for aid, info in ag.items():
            c = cat(info.get('action')); cc[c] += 1
            R = info.get('resources')
            if R is not None: Rs[aid] = R
            if c == 'take':
                attacks.append((d.get('round'), aid, info.get('target')))
            # fallback: reconstrueer transfer-flow uit acties als bilateral_flows leeg is
            if not bf and c == 'transfer' and info.get('target'):
                amt = (info.get('breakdown') or {}).get('invest_cost', 1.0) or 1.0
                T[(aid, info['target'])] += amt
        for k, v in bf.items():
            if '→' in k:
                a, b = k.split('→'); T[(a, b)] += v
        for m in d.get('messages', []):
            to = m.get('to')
            tos = to if isinstance(to, list) else ([] if to in (None, 'all') else [to])
            for t in tos:
                Mc[(m.get('from'), t)] += 1
        per_round.append({'round': d.get('round'), 'counts': cc, 'sumR': sum(Rs.values()), 'Rs': Rs})
    return sorted(agents), T, Mc, attacks, per_round

def economy(per_round):
    R0 = per_round[0]['sumR']; Rn = per_round[-1]['sumR']; n = len(per_round) - 1
    pr = ((Rn / R0) ** (1 / n) - 1) * 100 if R0 > 0 and Rn > 0 and n > 0 else 0.0
    tot = (Rn / R0 - 1) * 100 if R0 > 0 else 0.0
    finalRs = list(per_round[-1]['Rs'].values())
    g = gini(finalRs)
    top = max(finalRs) / sum(finalRs) * 100 if finalRs and sum(finalRs) > 0 else 0.0
    alive = sum(1 for x in finalRs if x > 1.0)
    if pr > 0.3:   reg = 'HEGEMONIE' if top >= 15 else 'BLOEI'
    elif pr < -0.3: reg = 'VEROVERING' if top >= 15 else 'NIVELLERING'
    else:          reg = 'VLAK-ongelijk' if top >= 15 else 'VLAK-gelijk'
    return pr, tot, g, top, alive, len(finalRs), reg

def action_dist_drift(per_round):
    overall = Counter()
    for r in per_round:
        for k, v in r['counts'].items(): overall[k] += v
    tot = sum(overall.values()) or 1
    dist = {k: 100 * overall.get(k, 0) / tot for k in PRIMARY}
    # drift vanaf ronde 3
    drifts = []
    prev = None
    for r in per_round:
        n = sum(r['counts'].values()) or 1
        p = np.array([r['counts'].get(k, 0) / n for k in PRIMARY])
        if prev is not None and r['round'] is not None and r['round'] >= 3:
            drifts.append(0.5 * np.abs(p - prev).sum())
        prev = p
    drift = float(np.mean(drifts)) if drifts else 0.0
    cons = [max(r['counts'].values()) / (sum(r['counts'].values()) or 1) for r in per_round if r['counts']]
    cmean = float(np.mean(cons)) if cons else 0.0
    cstd = float(np.std(cons)) if cons else 0.0
    return dist, drift, cmean, cstd

def subgroups(agents, T, Mc, alpha):
    idx = {a: i for i, a in enumerate(agents)}; n = len(agents)
    Tm = np.zeros((n, n)); Mm = np.zeros((n, n))
    for (a, b), v in T.items():
        if a in idx and b in idx: Tm[idx[a], idx[b]] += v
    for (a, b), v in Mc.items():
        if a in idx and b in idx: Mm[idx[a], idx[b]] += v
    A = alpha * normsym(Tm) + (1 - alpha) * normsym(Mm)
    edges, w = [], []
    for i in range(n):
        for j in range(i + 1, n):
            if A[i, j] > 0: edges.append((i, j)); w.append(A[i, j])
    g = ig.Graph(n=n, edges=edges); g.es['weight'] = w
    part = leidenalg.find_partition(g, leidenalg.RBConfigurationVertexPartition,
                                    weights='weight', seed=42)
    return np.array(part.membership), part.modularity, A, Tm, idx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path'); ap.add_argument('--alpha', type=float, default=0.5)
    ap.add_argument('--tau', type=float, default=0.6)
    args = ap.parse_args()
    lines = load(args.path)
    agents, T, Mc, attacks, per_round = parse(lines)
    name = args.path.split('/')[-1].replace('_reasoning_live.jsonl', '')
    print(f"\n{'='*70}\n{name}   (N={len(agents)}, rondes={len(per_round)})\n{'='*70}")

    pr, tot, g, top, alive, N, reg = economy(per_round)
    print(f"\n[ECONOMIE]  {reg}   {pr:+.2f}%/ronde ({tot:+.1f}% tot) | Gini {g:.2f} | top {top:.0f}% | alive {alive}/{N}")

    dist, drift, cmean, cstd = action_dist_drift(per_round)
    print(f"\n[ACTIEVERDELING] " + " ".join(f"{k.split('_')[0] if 'strength' not in k else k[10:]}:{dist[k]:.0f}%" for k in PRIMARY))
    print(f"[DRIFT] {drift:.3f}  (laag=stabiel, hoog=wisselt)")
    print(f"[CONSENSUS] mean {cmean:.2f} (eensgezindheid) | std {cstd:.2f} (golf: hoog=eenheid breekt+herstelt)")

    npunch = Counter()
    lastR = per_round[-1]['Rs']
    pu = pd = 0
    for rd, a, t in attacks:
        ra, rt = lastR.get(a), lastR.get(t)
        if ra is None or rt is None: continue
        if rt > ra: pu += 1
        elif rt < ra: pd += 1
    # mob: max distinct attackers op één target per ronde, gemiddeld
    by_round_target = defaultdict(lambda: defaultdict(set))
    for rd, a, t in attacks:
        if t: by_round_target[rd][t].add(a)
    mob = np.mean([max((len(s) for s in tg.values()), default=0) for tg in by_round_target.values()]) if by_round_target else 0
    print(f"\n[ATTACKS] {len(attacks)} | punch-up {pu} / down {pd} | mob (gem max aanvallers/target/ronde) {mob:.1f}")

    if not HAVE_LEIDEN:
        print("\n[SUBGROEPEN] leidenalg niet beschikbaar — overgeslagen."); return
    memb, Q, A, Tm, idx = subgroups(agents, T, Mc, args.alpha)
    K = len(set(memb))
    print(f"\n[SUBGROEPEN] alpha={args.alpha}  ->  {K} clubs, modulariteit Q={Q:.3f}  (tau={args.tau})")
    n = len(agents)
    # home-shares
    share = np.zeros((n, K))
    for i in range(n):
        s = np.array([A[i, memb == c].sum() for c in range(K)]); ssum = s.sum() or 1
        share[i] = s / ssum
    vast_total = 0
    for c in sorted(range(K), key=lambda c: -(memb == c).sum()):
        mem = [i for i in range(n) if memb[i] == c]
        # tribuut-indicator: top intra-club transfer-ontvanger-aandeel
        sub = Tm[np.ix_(mem, mem)]; inflow = sub.sum(axis=0)
        centr = inflow.max() / inflow.sum() if inflow.sum() > 0 else 0
        king = agents[mem[int(inflow.argmax())]] if inflow.sum() > 0 else '-'
        # interne wederkerigheid
        recip_pairs = mut = 0
        for x in range(len(mem)):
            for y in range(len(mem)):
                if x != y and sub[x, y] > 0:
                    recip_pairs += 1
                    if sub[y, x] > 0: mut += 1
        recip = mut / recip_pairs if recip_pairs else 0
        # actiemix per club (over hele run, leden)
        memset = set(agents[i] for i in mem)
        cc = Counter()
        for d in lines:
            for aid, info in d.get('agents', {}).items():
                if aid in memset: cc[cat(info.get('action'))] += 1
        ct = sum(cc.values()) or 1
        mix = " ".join(f"{k[:4]}:{100*cc.get(k,0)/ct:.0f}" for k in PRIMARY)
        # action-entropie van de club (genormaliseerd Shannon over 5 vaste categorieen)
        ps = [cc.get(k, 0) / ct for k in PRIMARY]
        Hc = -sum(p * math.log(p) for p in ps if p > 0) / math.log(len(PRIMARY))
        vast = [agents[i] for i in mem if share[i, c] >= args.tau]
        split = [agents[i] for i in mem if share[i, c] < args.tau]
        vast_total += len(vast)
        print(f"\n  CLUB g{c} (n={len(mem)})  recip={recip:.2f}  flow-centr={centr:.2f} (top-in: {king})  H_actie={Hc:.2f}")
        print(f"     mix[{mix}]")
        print(f"     VAST ({len(vast)}): {', '.join(sorted(vast, key=lambda a:-share[idx[a],c]))}")
        for a in sorted(split, key=lambda a:-share[idx[a],c]):
            brk = " ".join(f"g{cc2}:{round(100*share[idx[a],cc2])}" for cc2 in range(K) if share[idx[a],cc2] > 0.05)
            print(f"     split: {a:8s} {brk}")
    print(f"\n  [COHESIE] vast {vast_total}/{n} ({100*vast_total/n:.0f}%) | split {n-vast_total}/{n}")

    # ---- Conflict-laag: take- en arm_other-matrix over de club-partitie ----
    membmap = {agents[i]: int(memb[i]) for i in range(n)}
    takes, arm_oth = [], []
    arm_in = Counter()
    drops, invites = [], []   # (actor, target)
    for d in lines:
        for aid, info in d.get('agents', {}).items():
            a = str(info.get('action', '')); tg = info.get('target')
            ri = info.get('rewire_intent') or {}
            if ri.get('drop'): drops.append((aid, ri['drop']))
            if ri.get('invite'): invites.append((aid, ri['invite']))
            if not tg: continue
            if a.startswith(('take', 'attack')):
                takes.append((aid, tg))
            elif 'strengthen_other' in a or (a.startswith('arm') and 'self' not in a):
                arm_oth.append((aid, tg)); arm_in[tg] += 1
    def clubmatrix(pairs):
        Mx = np.zeros((K, K), int)
        for s, t in pairs:
            if s in membmap and t in membmap: Mx[membmap[s], membmap[t]] += 1
        return Mx
    C = clubmatrix(takes); Rm = clubmatrix(arm_oth)
    tt = int(C.sum()); intra_t = int(np.trace(C))
    print(f"\n  [CONFLICT-LAAG]")
    print(f"  TAKE {tt} | intra=verraad {intra_t} ({100*intra_t/max(tt,1):.0f}%) | inter=predatie {tt-intra_t}")
    if tt:
        colsum = C.sum(axis=0)
        besieged = int(colsum.argmax())
        print(f"     take-matrix (rij=aanvaller, kol=doelwit): kolom-som {[int(x) for x in colsum]} -> beleg-doelwit g{besieged}")
        for i in range(K):
            print(f"       g{i}: " + " ".join(f"{C[i,j]:>3}" for j in range(K)))
    at = int(Rm.sum()); intra_a = int(np.trace(Rm))
    if at:
        prot = arm_in.most_common(3)
        print(f"  ARM_OTHER {at} | intra=eigen-club {intra_a} ({100*intra_a/max(at,1):.0f}%) | inter {at-intra_a} | beschermde whale: {prot}")

    # ---- Rewiring-laag: A=rate, B=grens-sluiting ----
    nr = len(per_round)
    nd, ni = len(drops), len(invites)
    print(f"\n  [REWIRING]")
    print(f"  A-RATE: {nd} drops + {ni} invites = {(nd+ni)/nr:.1f}/ronde | netto {(ni-nd)/nr:+.1f}/ronde ({'groeit netwerk' if ni>nd else 'snoeit netwerk'})")
    # B: grens-sluiting — drops naar buitenstaanders, invites naar insiders?
    def cross_intra(pairs):
        cr = it = 0
        for s, t in pairs:
            if s in membmap and t in membmap:
                if membmap[s] == membmap[t]: it += 1
                else: cr += 1
        return cr, it
    dc, di = cross_intra(drops); ic, ii = cross_intra(invites)
    dtot = dc + di or 1; itot = ic + ii or 1
    print(f"  B-GRENS: drops cross-club {100*dc/dtot:.0f}% / intra {100*di/dtot:.0f}%  |  invites intra-club {100*ii/itot:.0f}% / cross {100*ic/itot:.0f}%")
    closure = (dc/dtot + ii/itot) / 2
    print(f"     grens-sluiting-index {closure:.2f} (hoog = buitenstaanders droppen + insiders inviten = in-group dichttrekken)")

if __name__ == '__main__':
    main()
