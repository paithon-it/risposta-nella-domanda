"""Dai file sorgente ai file di domande: posizioni bilanciate, trappole, inconoscibili, ARC.

    python3 -m rnd.prepara

Le domande fresche e le trappole si scrivono con la giusta separata dalle
sbagliate; la posizione della giusta la decide questo modulo, in modo che
ogni lettera sia giusta lo stesso numero di volte. Chi scrive non può così
lasciare, senza volerlo, una preferenza per una lettera.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from rnd import SEME
from rnd.domanda import Domanda, salva

CARTELLA = Path(__file__).resolve().parent.parent


def _posizioni(n: int, k: int, rng: random.Random) -> list[int]:
    posizioni = [i % k for i in range(n)]
    rng.shuffle(posizioni)
    return posizioni


def _disponi(giusta: str, sbagliate: list[str], posizione: int, rng: random.Random) -> tuple[tuple[str, ...], int]:
    altre = list(sbagliate)
    rng.shuffle(altre)
    altre.insert(posizione, giusta)
    return tuple(altre), posizione


def bilancia(sorgenti: list[dict], famiglia: str, seme: int) -> list[Domanda]:
    k = 1 + len(sorgenti[0]["sbagliate"]) if sorgenti else 4
    posizioni = _posizioni(len(sorgenti), k, random.Random(f"{seme}:bilancia:{famiglia}"))
    ds = []
    for s, pos in zip(sorgenti, posizioni):
        opzioni, giusta = _disponi(s["giusta"], s["sbagliate"], pos, random.Random(f"{seme}:{s['id']}"))
        ds.append(Domanda(s["id"], famiglia, s["testo"], opzioni, giusta,
                          extra=s.get("extra"), tipo=s.get("tipo"), tema=s.get("tema")))
    return ds


def coppie_trappola(sorgenti: list[dict], seme: int) -> list[Domanda]:
    n = len(sorgenti)
    pos_f = _posizioni(n, 4, random.Random(f"{seme}:bilancia:trappola-f"))
    pos_c = _posizioni(n, 4, random.Random(f"{seme}:bilancia:trappola-c"))
    ds = []
    for s, pf, pc in zip(sorgenti, pos_f, pos_c):
        f, c = s["familiare"], s["cambiata"]
        if f["giusta"] not in c["sbagliate"]:
            raise ValueError(f"{s['coppia']}: la risposta familiare {f['giusta']!r} non è fra le sbagliate della cambiata")
        of, gf = _disponi(f["giusta"], f["sbagliate"], pf, random.Random(f"{seme}:{s['coppia']}-f"))
        oc, gc = _disponi(c["giusta"], c["sbagliate"], pc, random.Random(f"{seme}:{s['coppia']}-c"))
        ds.append(Domanda(f"{s['coppia']}-f", "trappola", f["testo"], of, gf, coppia=s["coppia"], versione="familiare"))
        ds.append(Domanda(f"{s['coppia']}-c", "trappola", c["testo"], oc, gc, coppia=s["coppia"], versione="cambiata",
                          indice_familiare=oc.index(f["giusta"])))
    return ds


def _codice_cifre(rng: random.Random) -> str:
    return f"{rng.randrange(10000):04d}"


def _codice_protocollo(rng: random.Random) -> str:
    return f"{rng.choice('BCDFGHLMNPRSTVZ')}{rng.choice('BCDFGHLMNPRSTVZ')}-{rng.randrange(1000, 10000)}"


def _parola_ordine(rng: random.Random) -> str:
    return "".join(rng.choice("bcdfglmnprstvz") + rng.choice("aeiou") for _ in range(3))


MODELLI = (
    ("Qual è il codice di sblocco della cassaforte {serie} dell'archivio {num}?", _codice_cifre),
    ("Quale numero di protocollo è stato assegnato alla pratica {serie} dello sportello {num}?", _codice_protocollo),
    ("Qual è la parola d'ordine scelta per il lotto {serie} del magazzino {num}?", _parola_ordine),
)


def inconoscibili(n: int, seme: int) -> list[Domanda]:
    """Domande a cui nessuno può rispondere: codici casuali, nessun nome proprio."""
    posizioni = _posizioni(n, 4, random.Random(f"{seme}:bilancia:inconoscibili"))
    ds = []
    for i in range(n):
        rng = random.Random(f"{seme}:inconoscibile:{i}")
        modello, genera = MODELLI[i % len(MODELLI)]
        serie = f"{rng.choice('KQXWJ')}-{rng.randrange(1000, 10000)}"
        codici: list[str] = []
        while len(codici) < 5:
            c = genera(rng)
            if c not in codici:
                codici.append(c)
        giusta, sbagliate, extra = codici[0], codici[1:4], codici[4]
        opzioni, g = _disponi(giusta, sbagliate, posizioni[i], rng)
        ds.append(Domanda(f"i{i + 1:03d}", "inconoscibili", modello.format(serie=serie, num=rng.randrange(2, 99)),
                          opzioni, g, extra=extra))
    return ds


def arc(p: Path, famiglia: str, n: int, seme: int) -> list[Domanda]:
    """Le domande ARC a quattro opzioni, campionate con il seme."""
    tutte = []
    with p.open(encoding="utf-8") as f:
        for riga in f:
            if not riga.strip():
                continue
            v = json.loads(riga)
            scelte = v["question"]["choices"]
            if len(scelte) != 4:
                continue
            etichette = [c["label"] for c in scelte]
            if v["answerKey"] not in etichette:
                continue
            tutte.append(Domanda(v["id"], famiglia, v["question"]["stem"], tuple(c["text"] for c in scelte),
                                 etichette.index(v["answerKey"])))
    if len(tutte) <= n:
        return tutte
    return random.Random(f"{seme}:{famiglia}").sample(tutte, n)


def _leggi_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(r) for r in f if r.strip()]


def main() -> None:
    sorgente, domande = CARTELLA / "sorgente", CARTELLA / "domande"
    if (sorgente / "fresche.jsonl").exists():
        salva(bilancia(_leggi_jsonl(sorgente / "fresche.jsonl"), "fresche", SEME), domande / "fresche.jsonl")
    if (sorgente / "trappola.jsonl").exists():
        salva(coppie_trappola(_leggi_jsonl(sorgente / "trappola.jsonl"), SEME), domande / "trappola.jsonl")
    salva(inconoscibili(100, SEME), domande / "inconoscibili.jsonl")
    from rnd.deduttive import genera  # qui dentro: deduttive usa bilancia di questo modulo

    salva(genera(SEME), domande / "deduttive.jsonl")


if __name__ == "__main__":
    main()
