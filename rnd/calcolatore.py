"""Il calcolatore: legge una domanda deduttiva e calcola la risposta, senza pesare nessuna parola.

Riconosce quattro forme dal testo, non dal tipo dichiarato: moltiplicazioni, parole cifrate con
uno spostamento noto, sillogismi («Tutti…», «Alcuni…», «Alcuni… non…») e ordinamenti per altezza.
Per i sillogismi controlla ogni opzione su tutti i modelli possibili: le tre classi dividono il
mondo in otto regioni, e un modello dice quali sono abitate (2^8 = 256 modelli).
"""

from __future__ import annotations

import itertools
import re

from rnd.domanda import Domanda

_PRODOTTO = re.compile(r"(\d+)\s*×\s*(\d+)")
_CIFRARIO = re.compile(r"di (\d+) posizioni nell'alfabeto.*«([a-z]+)»", re.S)
_PIU_ALTA = re.compile(r"(\w+) è più alta di (\w+)")
_SILLOGISMO = "Che cosa segue"
_FRASE = re.compile(r"^(?:(Tutti) (?:i|gli) (\w+) sono (\w+)|(Alcuni) (\w+) (non )?sono (\w+))\.?$")
_POSIZIONE = {"la più alta": 0, "la seconda più alta": 1, "la seconda più bassa": -2, "la più bassa": -1}


def _indice(opzioni: tuple[str, ...], valore: str) -> int | None:
    return opzioni.index(valore) if valore in opzioni else None


def decifra(parola: str, k: int) -> str:
    return "".join(chr((ord(c) - 97 - k) % 26 + 97) for c in parola)


def _frase(testo: str) -> tuple[str, str, str] | None:
    """(forma, soggetto, predicato) con forma in A (tutti), I (alcuni sono), O (alcuni non sono)."""
    m = _FRASE.match(testo.strip())
    if not m:
        return None
    if m[1]:
        return "A", m[2], m[3]
    return ("O" if m[6] else "I"), m[5], m[7]


def _vera(f: tuple[str, str, str], abitate: list[frozenset[str]]) -> bool:
    forma, s, p = f
    if forma == "A":
        return all(p in r for r in abitate if s in r)
    if forma == "I":
        return any(s in r and p in r for r in abitate)
    return any(s in r and p not in r for r in abitate)


def conseguenze(d: Domanda) -> list[int]:
    """Gli indici delle opzioni vere in ogni modello in cui sono vere le premesse."""
    premesse_testo = d.testo.split(_SILLOGISMO)[0]
    premesse = [_frase(p) for p in premesse_testo.split(".") if p.strip()]
    opzioni = [_frase(o) for o in d.opzioni]
    if not premesse or None in premesse:
        return []
    termini = sorted({t for f in premesse + [o for o in opzioni if o] for t in f[1:]})
    regioni = [frozenset(c) for n in range(len(termini) + 1) for c in itertools.combinations(termini, n)]
    modelli = []
    for scelta in itertools.product((False, True), repeat=len(regioni)):
        abitate = [r for r, s in zip(regioni, scelta) if s]
        if all(_vera(p, abitate) for p in premesse):
            modelli.append(abitate)
    return [i for i, o in enumerate(opzioni) if o and all(_vera(o, m) for m in modelli)]


def _ordinamento(d: Domanda) -> int | None:
    coppie = _PIU_ALTA.findall(d.testo)
    nomi = {n for c in coppie for n in c}
    sopra = {n: {b for a, b in coppie if a == n} for n in nomi}

    def sotto_di(n: str) -> set[str]:  # tutti quelli più bassi di n, per transitività
        visti, da_fare = set(), list(sopra[n])
        while da_fare:
            x = da_fare.pop()
            if x not in visti:
                visti.add(x)
                da_fare.extend(sopra.get(x, ()))
        return visti

    ordine = sorted(nomi, key=lambda n: -len(sotto_di(n)))  # dalla più alta alla più bassa
    for frase, pos in _POSIZIONE.items():
        if f"Chi è {frase}?" in d.testo:
            return _indice(d.opzioni, ordine[pos])
    return None


def risolvi(d: Domanda) -> int | None:
    """L'indice dell'opzione giusta, o None se la domanda non ha una forma che il calcolatore sa leggere."""
    if m := _PRODOTTO.search(d.testo):
        return _indice(d.opzioni, str(int(m[1]) * int(m[2])))
    if m := _CIFRARIO.search(d.testo):
        return _indice(d.opzioni, decifra(m[2], int(m[1])))
    if _PIU_ALTA.search(d.testo):
        return _ordinamento(d)
    if _SILLOGISMO in d.testo:
        c = conseguenze(d)
        return c[0] if len(c) == 1 else None
    return None
