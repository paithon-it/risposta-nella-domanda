"""Scaricare i corpora e contare le co-occorrenze.

    python3 -m rnd.scarica arc        # archivio ARC di AI2: domande di test e ARC Corpus
    python3 -m rnd.scarica conta-arc  # conteggi sull'ARC Corpus  -> risultati/conteggi-arc.json
    python3 -m rnd.scarica conta-it   # conteggi su Wikipedia in italiano -> risultati/conteggi-it.json

I conteggi dipendono dalle domande (il vocabolario e le coppie da contare):
ogni blocco del corpus lascia un parziale firmato con l'impronta del
vocabolario, e se le domande cambiano i parziali vecchi non si riusano.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
import zipfile
from multiprocessing import Pool
from pathlib import Path

from rnd import SEME
from rnd.cooccorrenze import Conteggi, carica_stop, conta, coppie_rilevanti
from rnd.corpora import righe_parquet, righe_testo
from rnd.domanda import carica, salva
from rnd.prepara import arc

CARTELLA = Path(__file__).resolve().parent.parent
DATI = CARTELLA / "dati"
URL_ARC = "https://ai2-public-datasets.s3.amazonaws.com/arc/ARC-V1-Feb2018.zip"
WIKIPEDIA = ("wikimedia/wikipedia", "20231101.it", 10)


def firma(vocabolario: frozenset[str], coppie: frozenset[tuple[str, str]]) -> str:
    dati = json.dumps([sorted(vocabolario), sorted(coppie)], ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(dati).hexdigest()[:12]


def trova(nomi: list[str], suffisso: str) -> str:
    for n in nomi:
        if n.endswith(suffisso):
            return n
    raise FileNotFoundError(suffisso)


def _conta_una(lavoro: tuple) -> Conteggi:
    fonte, tipo, vocabolario, coppie, stop, parziale = lavoro
    if parziale.exists():
        return Conteggi.carica(parziale)
    righe = righe_parquet(fonte) if tipo == "parquet" else righe_testo(fonte)
    c = conta(righe, vocabolario, coppie, stop)
    c.salva(parziale)
    return c


def conta_fonti(fonti: list[Path], tipo: str, vocabolario, coppie, stop, parziali: Path, processi: int = 4) -> Conteggi:
    parziali.mkdir(parents=True, exist_ok=True)
    f = firma(vocabolario, coppie)
    lavori = [(p, tipo, vocabolario, coppie, stop, parziali / f"{p.stem}-{f}.json") for p in fonti]
    if processi == 1:
        risultati = [_conta_una(x) for x in lavori]
    else:
        with Pool(processi) as pool:
            risultati = pool.map(_conta_una, lavori)
    totale = Conteggi()
    for c in risultati:
        totale = totale.unisci(c)
    return totale


def _dividi(p: Path, n: int, cartella: Path) -> list[Path]:
    """Divide un testo in n blocchi di righe consecutive, per contarli in parallelo."""
    blocchi = [cartella / f"{p.stem}-{i:02d}.txt" for i in range(n)]
    if all(b.exists() for b in blocchi):
        return blocchi
    dimensione = p.stat().st_size
    uscite = [b.open("w", encoding="utf-8") for b in blocchi]
    letti = 0
    with p.open(encoding="utf-8", errors="replace") as f:
        for riga in f:
            letti += len(riga.encode("utf-8", errors="replace"))
            uscite[min(n - 1, letti * n // dimensione)].write(riga)
    for u in uscite:
        u.close()
    return blocchi


def scarica_arc() -> None:
    cartella = DATI / "arc"
    cartella.mkdir(parents=True, exist_ok=True)
    archivio = cartella / "ARC-V1-Feb2018.zip"
    if not archivio.exists():
        urllib.request.urlretrieve(URL_ARC, archivio)
    with zipfile.ZipFile(archivio) as z:
        nomi = z.namelist()
        for suffisso in ("ARC-Easy-Test.jsonl", "ARC-Challenge-Test.jsonl", "ARC_Corpus.txt"):
            destinazione = cartella / suffisso
            if not destinazione.exists():
                destinazione.write_bytes(z.read(trova(nomi, suffisso)))
    salva(arc(cartella / "ARC-Easy-Test.jsonl", "arc_easy", 200, SEME), CARTELLA / "domande" / "arc_easy.jsonl")
    salva(arc(cartella / "ARC-Challenge-Test.jsonl", "arc_challenge", 200, SEME), CARTELLA / "domande" / "arc_challenge.jsonl")


def conta_arc() -> Conteggi:
    ds = carica(CARTELLA / "domande" / "arc_easy.jsonl") + carica(CARTELLA / "domande" / "arc_challenge.jsonl")
    stop = carica_stop("en")
    voc, cop = coppie_rilevanti(ds, stop)
    blocchi = _dividi(DATI / "arc" / "ARC_Corpus.txt", 8, DATI / "arc")
    c = conta_fonti(blocchi, "testo", voc, cop, stop, DATI / "parziali-arc")
    c.salva(CARTELLA / "risultati" / "conteggi-arc.json")
    return c


FAMIGLIE_IT = ("fresche", "trappola", "inconoscibili", "deduttive")


def conta_it() -> Conteggi:
    from huggingface_hub import hf_hub_download

    repo, config, n = WIKIPEDIA
    blocchi = [Path(hf_hub_download(repo, f"{config}/train-{i:05d}-of-{n:05d}.parquet", repo_type="dataset",
                                    local_dir=DATI / "wikipedia-it")) for i in range(n)]
    ds = [d for f in FAMIGLIE_IT for d in carica(CARTELLA / "domande" / f"{f}.jsonl")]
    stop = carica_stop("it")
    voc, cop = coppie_rilevanti(ds, stop)
    c = conta_fonti(blocchi, "parquet", voc, cop, stop, DATI / "parziali-it")
    c.salva(CARTELLA / "risultati" / "conteggi-it.json")
    return c


def main(argv: list[str]) -> int:
    comandi = {"arc": scarica_arc, "conta-arc": conta_arc, "conta-it": conta_it}
    if len(argv) != 1 or argv[0] not in comandi:
        print(__doc__)
        return 2
    inizio = time.monotonic()
    comandi[argv[0]]()
    print(f"{argv[0]}: fatto in {time.monotonic() - inizio:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
