"""De runset — één definitie van welke runs meetellen, voor alle measures.

Waarom dit bestaat: de oude analysescripts hielden er ieder hun eigen idee van
de dataset op na. Sommige lazen `~/Desktop/thesis-runs`, andere
`~/origins/simulation/data/runs`, en drie droegen een inline manifest met
Slurm-job-ID's mee. Die bronnen liepen uiteen — de bureaubladkopie miste de
opruiming van afgekeurde runs en telde vier fallback-vervuilde runs mee als
geldig, wat in de T4-tabel 66,6% opleverde waar 64,4% hoorde te staan.

Hier is de waarheid `_INDEX.csv` in `data/thesis_final/`: 188 runs, per cel
doorgenummerd, elk met zijn seed als onherleidbare marker.

Twee harde regels, allebei geleerd op 12-13 aug:

1. **Een onleesbare bron telt nooit als lege bron.** Ontbreekt de index, of is
   een cel niet te lezen, dan is dat een fout en geen n=0. Drie keer op één dag
   telde iets stil als leeg: iCloud gooide 72 van de 157 logs weg en liet
   placeholders achter die als b'' lezen; macOS trok de schijftoegang in toen
   Claude Code zichzelf bijwerkte, waarna glob niets meer teruggaf; en de
   bureaubladkopie miste de opruiming op Snellius.
2. **Wie runs overslaat, zegt het.** `skipped` hoort in de uitvoer van elke
   measure, zodat een uitsluiting in de tekst kan landen in plaats van in een
   README.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

# _shared/ ligt twee niveaus onder simulation/, vandaar parents[2].
WORTEL = Path(__file__).resolve().parents[2] / "data" / "thesis_final"
INDEX = WORTEL / "_INDEX.csv"

RUNGS = ("L1", "L2", "L3", "L4")
PAYOFFS = ("scar", "knife", "abund")
PRODUCTION = [f"prod_{r}_{p}" for r in RUNGS for p in PAYOFFS]
NOCOMM = [f"prod_{r}_knife_nocomm" for r in RUNGS]
QWEN = [f"robust_qwen_{r}_knife" for r in ("L2", "L3", "L4")]
DEEPSEEK = [f"robust_deepseek_{r}_knife" for r in ("L2", "L3", "L4")]


class RunsetError(RuntimeError):
    """Onleesbaar of ontbrekend — nooit stilzwijgend als leeg behandelen."""


def _index() -> list[dict]:
    if not INDEX.exists():
        raise RunsetError(
            f"{INDEX} ontbreekt. De measures draaien op de geconsolideerde set;\n"
            f"bouw die eerst of wijs WORTEL aan de juiste map toe.")
    with INDEX.open() as fh:
        rijen = list(csv.DictReader(fh))
    if not rijen:
        raise RunsetError(f"{INDEX} is leeg.")
    return rijen


_RIJEN = None


def rijen() -> list[dict]:
    global _RIJEN
    if _RIJEN is None:
        _RIJEN = _index()
    return _RIJEN


def cel(naam: str) -> list[Path]:
    """Alle reasoning_live-paths van één cel, op nummer gesorteerd.

    Faalt hard als de cel niet in de index staat of de map niet leesbaar is.
    Een typefout in een celnaam moet een fout geven, geen lege lijst — anders
    rapporteert een measure keurig n=0 over een cel die gewoon bestaat.
    """
    hoort = [r for r in rijen() if r["cel"] == naam]
    if not hoort:
        raise RunsetError(
            f"cel '{naam}' staat niet in _INDEX.csv. Bekend: "
            f"{sorted({r['cel'] for r in rijen()})}")
    map_ = WORTEL / naam
    try:
        os.listdir(map_)
    except OSError as e:
        raise RunsetError(f"cel '{naam}' bestaat maar is niet te lezen: {e}") from e
    paths = []
    for r in sorted(hoort, key=lambda r: r["nieuw_id"]):
        p = map_ / r["bestand"]
        if not p.exists():
            raise RunsetError(f"{p} staat in de index maar niet op schijf.")
        paths.append(p)
    return paths


def cells(namen) -> dict[str, list[Path]]:
    return {n: cel(n) for n in namen}


# --- welke serving-stack een run draaide -----------------------------------
#
# Dertig van de 150 productieruns liepen via OpenRouter in plaats van de
# clusterengine, op hetzelfde model en dezelfde configuratie, om cellen af te
# maken waar de allocatie tekortschoot. De appendix meldde dat, en meldde ook
# dat drie figuren tussen de armen verder uiteenlopen dan de spreiding binnen
# een cel — zonder te zeggen wélke drie. Een externe audit vroeg daarnaar op
# 17 augustus. Zonder deze functie was dat niet te beantwoorden: de bron stond
# in de index en nergens in de code.

def arm_van(p: Path) -> str:
    """`cluster`, `openrouter`, `resumed` of `onbekend` voor één run-path."""
    for r in rijen():
        if r["bestand"] == p.name:
            b = (r.get("bron") or "").strip().lower()
            if b.startswith("openrouter"):
                return "openrouter"
            if b.startswith("resumed"):
                return "resumed"
            if b.startswith("job"):
                return "cluster"
            return "onbekend"
    raise RunsetError(f"{p.name} staat niet in _INDEX.csv.")


def per_arm(naam: str) -> dict[str, list[Path]]:
    """De runs van een cel, gegroepeerd op serving-stack.

    `resumed` telt hier als cluster: die runs zijn op Snellius begonnen en na een
    onderbreking daar hervat, dus ze deelden de engine met de clusterruns. Wat
    hier gescheiden wordt is de stack, niet de onderbreking; die staat apart in
    de index en heeft zijn eigen voetnoot in de appendix.
    """
    uit: dict[str, list[Path]] = {}
    for p in cel(naam):
        a = arm_van(p)
        uit.setdefault("cluster" if a in ("cluster", "resumed") else a, []).append(p)
    return uit


def log_path(p: Path) -> Path:
    """Het goedkoopste bestand met acties en resources voor deze run.

    Bij voorkeur het compacte `_log.jsonl`: dezelfde velden als de
    `reasoning_live`, zonder de redeneertekst, en tien keer kleiner.

    21 van de 188 runs hebben er geen — precies de runs die op Snellius zijn
    hervat, waar alleen het volle bestand bewaard bleef. Die vallen terug op de
    `reasoning_live`, wat geen concessie is: `action`, `resources`, `target` en
    `breakdown` staan daar identiek in. Het kost alleen leestijd.

    De terugval is niet stil: `source_count()` laat zien welke runs welk bestand
    gebruikten, zodat een measure kan verantwoorden waar hij uit las.
    """
    q = p.with_name(p.name.replace("_reasoning_live.jsonl", "_log.jsonl"))
    if q.exists():
        return q
    if p.exists():
        return p
    raise RunsetError(f"noch log noch reasoning_live voor {p.name}")


def source_count(paths) -> dict[str, int]:
    """Hoeveel runs uit een `_log.jsonl` lazen en hoeveel uit de volle trace."""
    uit = {"log": 0, "reasoning_live": 0}
    for p in paths:
        uit["log" if log_path(p).name.endswith("_log.jsonl") else "reasoning_live"] += 1
    return uit


def clean(namen=None) -> dict[str, list[Path]]:
    """Alleen runs zonder fallbacks.

    Acht van de 188 runs bevatten er wel, alle acht op T2, ten hoogste 0,50%
    geforceerd. Dat is ruim onder de 1,0% waarop een run is afgekeurd, dus ze
    horen in de hoofdanalyse thuis. Deze ingang bestaat om te kunnen tóetsen of
    een bevinding erop leunt — niet om ze standaard weg te laten.
    """
    namen = namen or PRODUCTION
    uit = {}
    for n in namen:
        houd = []
        for r in sorted((r for r in rijen() if r["cel"] == n),
                        key=lambda r: r["nieuw_id"]):
            if int(r["forced"]) == 0 and int(r["hersteld"]) == 0:
                houd.append(WORTEL / n / r["bestand"])
        uit[n] = houd
    return uit


def count() -> dict[str, int]:
    uit: dict[str, int] = {}
    for r in rijen():
        uit[r["cel"]] = uit.get(r["cel"], 0) + 1
    return uit


if __name__ == "__main__":
    t = count()
    print(f"{sum(t.values())} runs in {len(t)} cells\n")
    for groep, namen in (("productie", PRODUCTION), ("no-channel", NOCOMM),
                         ("Qwen", QWEN), ("DeepSeek", DEEPSEEK)):
        n = sum(t.get(c, 0) for c in namen)
        print(f"  {groep:12} {n:3}  ({', '.join(f'{c.split(chr(95))[-1]}={t.get(c,0)}' for c in namen)})")
    dirty = [r for r in rijen() if int(r["forced"]) or int(r["hersteld"])]
    print(f"\n  runs met fallbacks: {len(dirty)}")
    for r in dirty:
        print(f"    {r['cel']}/{r['nieuw_id']}  forced={r['forced']} hersteld={r['hersteld']}")
