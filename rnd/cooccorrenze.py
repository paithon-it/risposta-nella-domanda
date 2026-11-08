"""Il solutore che pesa le parole, alla maniera dei solutori PMI di ARC (2018).

Per ogni opzione si misura quanto le sue parole stanno vicine alle parole
della domanda in un grande archivio di testi, con la PMI positiva:

    PPMI(q, o) = max(0, log(c(q, o) · N / (c(q) · c(o))))

dove c(q, o) conta le volte in cui q e o compaiono entro `finestra` parole
piene (stopword tolte) nella stessa riga, e N è il numero di parole piene
lette. Il punteggio di un'opzione è la media sulle coppie (parola della
domanda, parola dell'opzione). Niente stemming: «pianta» e «piante» sono
parole diverse, ed è un limite dichiarato.
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from rnd.domanda import Domanda
from rnd.varianti import NESSUNA

STOPWORDS = Path(__file__).resolve().parent.parent / "stopwords"
_PAROLA = re.compile(r"[a-zà-ÿ]+")


def carica_stop(lingua: str) -> frozenset[str]:
    return frozenset((STOPWORDS / f"{lingua}.txt").read_text(encoding="utf-8").split())


def parole(testo: str, stop: frozenset[str]) -> list[str]:
    return [w for w in _PAROLA.findall(testo.lower()) if len(w) >= 2 and w not in stop]


def _opzioni_vere(d: Domanda) -> list[str]:
    return [o for o in (*d.opzioni, *( [d.extra] if d.extra else [])) if o != NESSUNA]


def coppie_rilevanti(ds: list[Domanda], stop: frozenset[str]) -> tuple[frozenset[str], frozenset[tuple[str, str]]]:
    vocabolario: set[str] = set()
    coppie: set[tuple[str, str]] = set()
    for d in ds:
        qw = parole(d.testo, stop)
        vocabolario.update(qw)
        for o in _opzioni_vere(d):
            ow = parole(o, stop)
            vocabolario.update(ow)
            coppie.update((q, w) for q in qw for w in ow if q != w)
    return frozenset(vocabolario), frozenset(coppie)


@dataclass
class Conteggi:
    posizioni: int = 0
    singole: dict[str, int] = field(default_factory=dict)
    coppie: dict[tuple[str, str], int] = field(default_factory=dict)

    def unisci(self, altro: "Conteggi") -> "Conteggi":
        singole, coppie = dict(self.singole), dict(self.coppie)
        for k, v in altro.singole.items():
            singole[k] = singole.get(k, 0) + v
        for k, v in altro.coppie.items():
            coppie[k] = coppie.get(k, 0) + v
        return Conteggi(self.posizioni + altro.posizioni, singole, coppie)

    def salva(self, p: Path) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"posizioni": self.posizioni, "singole": self.singole,
                                 "coppie": {f"{q}|{o}": n for (q, o), n in self.coppie.items()}},
                                ensure_ascii=False), encoding="utf-8")

    @classmethod
    def carica(cls, p: Path) -> "Conteggi":
        v = json.loads(p.read_text(encoding="utf-8"))
        return cls(v["posizioni"], v["singole"], {tuple(k.split("|", 1)): n for k, n in v["coppie"].items()})


def conta(righe: Iterable[str], vocabolario: frozenset[str], coppie: frozenset[tuple[str, str]],
          stop: frozenset[str], finestra: int = 10) -> Conteggi:
    c = Conteggi()
    for riga in righe:
        toks = parole(riga, stop)
        c.posizioni += len(toks)
        for i, t in enumerate(toks):
            if t not in vocabolario:
                continue
            c.singole[t] = c.singole.get(t, 0) + 1
            for u in toks[i + 1:i + 1 + finestra]:
                if u not in vocabolario or u == t:
                    continue
                for coppia in ((t, u), (u, t)):
                    if coppia in coppie:
                        c.coppie[coppia] = c.coppie.get(coppia, 0) + 1
    return c


def _ppmi(q: str, o: str, c: Conteggi) -> float:
    n_qo, n_q, n_o = c.coppie.get((q, o), 0), c.singole.get(q, 0), c.singole.get(o, 0)
    if not (n_qo and n_q and n_o):
        return 0.0
    return max(0.0, math.log(n_qo * c.posizioni / (n_q * n_o)))


def punteggi(d: Domanda, c: Conteggi, stop: frozenset[str]) -> list[float]:
    qw = parole(d.testo, stop)
    risultato = []
    for o in d.opzioni:
        ow = parole(o, stop) if o != NESSUNA else []
        coppie = [(q, w) for q in qw for w in ow if q != w]
        risultato.append(sum(_ppmi(q, w, c) for q, w in coppie) / len(coppie) if coppie else 0.0)
    return risultato


def punteggi_solo_opzioni(d: Domanda, c: Conteggi, stop: frozenset[str]) -> list[float]:
    """Senza la domanda resta solo la frequenza: la media di log((c(o)+1)/N)."""
    n = max(c.posizioni, 1)
    risultato = []
    for o in d.opzioni:
        ow = parole(o, stop) if o != NESSUNA else []
        risultato.append(sum(math.log((c.singole.get(w, 0) + 1) / n) for w in ow) / len(ow) if ow else math.log(1 / n))
    return risultato


def scegli(punteggi: list[float], rng: random.Random) -> int:
    """L'opzione col punteggio più alto; i pareggi si rompono a caso, mai a favore della A."""
    massimo = max(punteggi)
    return rng.choice([i for i, p in enumerate(punteggi) if p == massimo])


def coperta(d: Domanda, c: Conteggi, stop: frozenset[str]) -> bool:
    """Il corpus ha visto almeno una volta la risposta giusta vicino a una parola della domanda."""
    if d.giusta is None:
        return False
    qw, gw = parole(d.testo, stop), parole(d.opzioni[d.giusta], stop)
    return any(c.coppie.get((q, w), 0) > 0 for q in qw for w in gw)
