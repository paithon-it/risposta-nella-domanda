"""La domanda a risposta multipla, il suo file JSONL e la validazione."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

FAMIGLIE = ("fresche", "trappola", "inconoscibili", "arc_easy", "arc_challenge", "deduttive")
TIPI = ("associativa", "relazionale", "negazione", "due_passi",
        "aritmetica", "cifrario", "sillogismo", "controintuitivo", "ordinamento")
VERSIONI = ("familiare", "cambiata")


@dataclass(frozen=True)
class Domanda:
    id: str
    famiglia: str
    testo: str
    opzioni: tuple[str, ...]
    giusta: int | None
    extra: str | None = None
    tipo: str | None = None
    tema: str | None = None
    coppia: str | None = None
    versione: str | None = None
    indice_familiare: int | None = None


def salva(ds: Iterable[Domanda], p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for d in ds:
            f.write(json.dumps(asdict(d), ensure_ascii=False) + "\n")


def carica(p: Path) -> list[Domanda]:
    ds = []
    with p.open(encoding="utf-8") as f:
        for riga in f:
            if riga.strip():
                v = json.loads(riga)
                v["opzioni"] = tuple(v["opzioni"])
                ds.append(Domanda(**v))
    return ds


def valida(d: Domanda) -> list[str]:
    """I problemi della domanda; lista vuota se va bene."""
    problemi = []
    k = len(d.opzioni)
    if not 2 <= k <= 5:
        problemi.append(f"{d.id}: {k} opzioni (servono da 2 a 5)")
    if len(set(d.opzioni)) != k:
        problemi.append(f"{d.id}: opzioni ripetute")
    if d.giusta is not None and not 0 <= d.giusta < k:
        problemi.append(f"{d.id}: giusta {d.giusta} fuori intervallo")
    if d.famiglia not in FAMIGLIE:
        problemi.append(f"{d.id}: famiglia {d.famiglia!r} sconosciuta")
    if d.tipo is not None and d.tipo not in TIPI:
        problemi.append(f"{d.id}: tipo {d.tipo!r} sconosciuto")
    if d.versione is not None and d.versione not in VERSIONI:
        problemi.append(f"{d.id}: versione {d.versione!r} sconosciuta")
    if d.versione == "cambiata":
        if d.indice_familiare is None:
            problemi.append(f"{d.id}: cambiata senza indice_familiare")
        elif d.indice_familiare == d.giusta:
            problemi.append(f"{d.id}: la risposta familiare coincide con la giusta")
        elif not 0 <= d.indice_familiare < k:
            problemi.append(f"{d.id}: indice_familiare fuori intervallo")
    return problemi
