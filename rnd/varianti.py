"""Le varianti di una domanda e il prompt che la presenta.

`applica` trasforma la domanda (opzioni, giusta), `prompt` decide la forma
del messaggio. Chi corre l'esperimento chiama prima l'una e poi l'altro.
"""

from __future__ import annotations

import random
from dataclasses import replace

from rnd import LETTERE, SEME
from rnd.domanda import Domanda

VARIANTI = ("intera", "solo_opzioni", "mescolata", "con_nessuna", "senza_giusta", "confidenza", "lettera_a", "ragiona")
NESSUNA = "Nessuna delle precedenti"

SOLO_LETTERA = "Rispondi solo con la lettera."
CHIUSE = {
    "confidenza": "Rispondi con la lettera e poi, sulla riga dopo, un numero da 0 a 100: quanto sei sicuro.",
    "lettera_a": "Rispondi con la lettera e poi spiega in una frase perché.",
    "ragiona": "Ragiona passo per passo, poi scrivi solo la lettera sull'ultima riga.",
}
SENZA_DOMANDA = "Non vedi la domanda, solo le opzioni. Quale è più probabilmente quella giusta?"


def _rimappa(i: int | None, perm: list[int]) -> int | None:
    return None if i is None else perm.index(i)


def applica(d: Domanda, variante: str, seme: int = SEME) -> Domanda:
    if variante in ("intera", "confidenza", "lettera_a", "ragiona"):
        return d
    if variante == "solo_opzioni":
        return replace(d, testo="")
    if variante == "mescolata":
        perm = list(range(len(d.opzioni)))
        random.Random(f"{seme}:mescola:{d.id}").shuffle(perm)
        if perm == sorted(perm):
            perm = perm[1:] + perm[:1]
        return replace(d, opzioni=tuple(d.opzioni[i] for i in perm),
                       giusta=_rimappa(d.giusta, perm), indice_familiare=_rimappa(d.indice_familiare, perm))
    if variante == "con_nessuna":
        return replace(d, opzioni=d.opzioni + (NESSUNA,))
    if variante == "senza_giusta":
        if d.extra is None or d.giusta is None:
            raise ValueError(f"{d.id}: senza_giusta vuole una giusta e un extra")
        opzioni = list(d.opzioni)
        opzioni[d.giusta] = d.extra
        return replace(d, opzioni=tuple(opzioni) + (NESSUNA,), giusta=len(opzioni))
    raise ValueError(f"variante sconosciuta: {variante!r}")


def _blocco(testo: str, opzioni: tuple[str, ...]) -> list[str]:
    righe = [f"Domanda: {testo}" if testo else SENZA_DOMANDA]
    righe += [f"{LETTERE[i]}) {o}" for i, o in enumerate(opzioni)]
    return righe


def _esempio_in_a(e: Domanda) -> list[str]:
    altre = [o for i, o in enumerate(e.opzioni) if i != e.giusta]
    return _blocco(e.testo, (e.opzioni[e.giusta], *altre)) + ["Risposta: A", ""]


def prompt(d: Domanda, variante: str, esempi: list[Domanda] | None = None) -> str:
    righe: list[str] = []
    if variante == "lettera_a":
        if not esempi:
            raise ValueError("lettera_a vuole gli esempi")
        for e in esempi:
            righe += _esempio_in_a(e)
    righe += _blocco(d.testo, d.opzioni)
    righe.append(CHIUSE.get(variante, SOLO_LETTERA))
    return "\n".join(righe)
