"""La corsa: ogni rispondente risponde a ogni domanda in ogni variante, una riga JSONL per esito.

    python3 -m rnd.corsa --rispondente sonnet --famiglie fresche --varianti intera,solo_opzioni --pausa 5

La corsa riprende da sola: le risposte già scritte non si rifanno, e
un'ultima riga troncata (corsa interrotta a metà scrittura) si scarta.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

from rnd import SEME
from rnd.cooccorrenze import scegli
from rnd.domanda import Domanda, carica
from rnd.lettera import estrai_confidenza, estrai_lettera, estrai_lettera_finale
from rnd.varianti import VARIANTI, applica, prompt

CARTELLA = Path(__file__).resolve().parent.parent
VARIANTI_BASE = ("intera", "solo_opzioni")
MODELLI_LOCALI = {  # rispondente: (modello su Hugging Face, pesi a caso)
    "qwen": ("Qwen/Qwen2.5-0.5B-Instruct", False),
    "qwen-casuale": ("Qwen/Qwen2.5-0.5B-Instruct", True),
}
MODELLI_VLLM = {
    # 27B quantizzato a 4 bit da terzi: i pesi originali (56 GB in bf16, 31 in FP8) non stanno su una L4 da 24 GB,
    # e il formato (compressed-tensors) lo legge compresso solo vLLM
    "qwen3.8-27b": "cyankiwi/Qwen3.8-27B-AWQ-INT4",
}
RISPONDENTI = ("pmi", "pmi-arc", "calcolatore", *MODELLI_LOCALI, *MODELLI_VLLM, "sonnet", "haiku", "opus")


@dataclass
class Esito:
    rispondente: str
    famiglia: str
    variante: str
    id: str
    ripetizione: int
    lettera: int | None
    lettera_testo: int | None
    probabilita: list[float] | None
    confidenza: int | None
    spiegazione: str | None
    giusta: int | None
    corretta: bool | None
    k: int
    indice_familiare: int | None
    durata_s: float
    testo: str | None = None  # la risposta com'è arrivata (assente nelle righe della prova prima dell'8/11)


def carica_esiti(p: Path) -> list[Esito]:
    esiti = []
    if not p.exists():
        return esiti
    with p.open(encoding="utf-8") as f:
        for riga in f:
            try:
                esiti.append(Esito(**json.loads(riga)))
            except (json.JSONDecodeError, TypeError):
                continue
    return esiti


def fatti(p: Path) -> set[tuple[str, str, str, int]]:
    return {(e.famiglia, e.variante, e.id, e.ripetizione) for e in carica_esiti(p)}


def varianti_per(famiglia: str, varianti: list[str]) -> list[str]:
    """Le varianti epistemologiche girano solo sulle fresche (ruling del pre-flight); «ragiona» anche sulle deduttive."""
    if famiglia == "fresche":
        return list(varianti)
    ammesse = VARIANTI_BASE + ("ragiona",) if famiglia == "deduttive" else VARIANTI_BASE
    return [v for v in varianti if v in ammesse]


def _ripara(p: Path) -> None:
    """Toglie un'ultima riga troncata, così la prossima scrittura comincia a capo."""
    if not p.exists():
        return
    dati = p.read_bytes()
    if dati and not dati.endswith(b"\n"):
        p.write_bytes(dati[:dati.rfind(b"\n") + 1])


def _esito(rispondente: str, d: Domanda, variante: str, rip: int, risposta, durata: float) -> Esito:
    k = len(d.opzioni)
    prob = conf = spieg = lettera_testo = testo = None
    if risposta is None:  # il calcolatore che non sa leggere la domanda si astiene
        lettera = None
    elif isinstance(risposta, str):
        testo = risposta
        leggi = estrai_lettera_finale if variante == "ragiona" else estrai_lettera
        lettera = lettera_testo = leggi(risposta, k)
        conf = estrai_confidenza(risposta) if variante == "confidenza" else None
        spieg = risposta if variante == "lettera_a" else None
    elif isinstance(risposta, int):
        lettera = risposta
    else:  # RispostaLocale: conta la scelta vincolata, con i pareggi rotti a caso (logit in bfloat16)
        lettera_testo, prob = risposta.lettera_testo, risposta.probabilita
        lettera = scegli(prob, _rng_pareggio(d.id, variante, rip))
        testo = risposta.testo
    corretta = None if lettera is None or d.giusta is None else lettera == d.giusta
    return Esito(rispondente, d.famiglia, variante, d.id, rip, lettera, lettera_testo, prob, conf, spieg,
                 d.giusta, corretta, k, d.indice_familiare, round(durata, 3), testo)


def _rng_pareggio(id_: str, variante: str, rip: int) -> random.Random:
    return random.Random(f"{SEME}:pareggio:{id_}:{variante}:{rip}")


def _rilettura(e: Esito) -> Esito:
    """L'esito con la lettera ricalcolata dal testo o dalle probabilità salvati, con le regole di oggi."""
    if e.probabilita:
        lettera = scegli(e.probabilita, _rng_pareggio(e.id, e.variante, e.ripetizione))
        lettera_testo = estrai_lettera(e.testo, e.k) if e.testo is not None else e.lettera_testo
        confidenza = e.confidenza
    elif e.testo is not None:
        leggi = estrai_lettera_finale if e.variante == "ragiona" else estrai_lettera
        lettera = lettera_testo = leggi(e.testo, e.k)
        confidenza = estrai_confidenza(e.testo) if e.variante == "confidenza" else e.confidenza
    else:
        return e
    corretta = None if lettera is None or e.giusta is None else lettera == e.giusta
    return replace(e, lettera=lettera, lettera_testo=lettera_testo, confidenza=confidenza, corretta=corretta)


def rileggi(p: Path) -> int:
    """Riscrive il file con le lettere rilette; restituisce quante righe sono cambiate."""
    righe = [r for r in p.read_text(encoding="utf-8").splitlines() if r.strip()]
    esiti = carica_esiti(p)
    if len(esiti) != len(righe):
        raise ValueError(f"{p}: {len(righe) - len(esiti)} righe illeggibili, non riscrivo")
    nuovi = [_rilettura(e) for e in esiti]
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(asdict(e), ensure_ascii=False) + "\n" for e in nuovi), encoding="utf-8")
    tmp.replace(p)
    return sum(a != b for a, b in zip(esiti, nuovi))


def corri(rispondente: str, domande: list[Domanda], varianti: list[str], uscita: Path, ripetizioni: int = 1,
          pausa_s: float = 0.0, limite: int | None = None, _rispondi: Callable | None = None,
          esempi: list[Domanda] | None = None) -> int:
    uscita.parent.mkdir(parents=True, exist_ok=True)
    _ripara(uscita)
    gia = fatti(uscita)
    nuovi = 0
    with uscita.open("a", encoding="utf-8") as f:
        for variante in varianti:
            for d in domande[:limite] if limite else domande:
                dv = applica(d, variante)
                testo = prompt(dv, variante, esempi=esempi)
                for rip in range(ripetizioni):
                    if (d.famiglia, variante, d.id, rip) in gia:
                        continue
                    inizio = time.monotonic()
                    risposta = _rispondi(dv, variante, testo)
                    e = _esito(rispondente, dv, variante, rip, risposta, time.monotonic() - inizio)
                    f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
                    f.flush()
                    nuovi += 1
                    if pausa_s:
                        time.sleep(pausa_s)
    return nuovi


def esempi_da(p: Path) -> list[Domanda]:
    with p.open(encoding="utf-8") as f:
        sorgenti = [json.loads(r) for r in f if r.strip()]
    return [Domanda(s["id"], "fresche", s["testo"], (s["giusta"], *s["sbagliate"]), 0) for s in sorgenti]


def crea_rispondente(nome: str) -> Callable:
    if nome in ("pmi", "pmi-arc"):
        from rnd.cooccorrenze import Conteggi, carica_stop, punteggi, punteggi_solo_opzioni, scegli

        c = Conteggi.carica(CARTELLA / "risultati" / ("conteggi-it.json" if nome == "pmi" else "conteggi-arc.json"))
        stop = carica_stop("it" if nome == "pmi" else "en")

        def pmi(d, variante, testo):
            pt = punteggi_solo_opzioni(d, c, stop) if variante == "solo_opzioni" else punteggi(d, c, stop)
            return scegli(pt, random.Random(f"{SEME}:{d.id}:{variante}"))
        return pmi
    if nome == "calcolatore":
        from rnd.calcolatore import risolvi

        return lambda d, variante, testo: risolvi(d)
    if nome in MODELLI_LOCALI or nome in MODELLI_VLLM:
        from rnd import locale

        if nome in MODELLI_VLLM:
            m = locale.ModelloVLLM(MODELLI_VLLM[nome], rispondente=nome)
        else:
            hf, casuali = MODELLI_LOCALI[nome]
            m = locale.ModelloLocale(hf, pesi_casuali=casuali, rispondente=nome)
        return lambda d, variante, testo: m.rispondi(testo, len(d.opzioni))
    if nome in ("sonnet", "haiku", "opus"):
        from rnd.claude_headless import esegui, problemi_sonda, sonda

        problemi = problemi_sonda(sonda(nome))
        if problemi:
            raise SystemExit(f"sonda non pulita, niente corsa: {problemi}")
        return lambda d, variante, testo: esegui(testo, nome)
    raise SystemExit(f"rispondente sconosciuto: {nome}")


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--rispondente", required=True, choices=RISPONDENTI)
    a.add_argument("--famiglie", required=True)
    a.add_argument("--varianti", required=True)
    a.add_argument("--ripetizioni", type=int, default=1)
    a.add_argument("--pausa", type=float, default=0.0)
    a.add_argument("--limite", type=int)
    a.add_argument("--solo-id")
    a.add_argument("--cartella", type=Path, default=CARTELLA / "risultati")
    o = a.parse_args(argv)
    varianti = o.varianti.split(",")
    sconosciute = set(varianti) - set(VARIANTI)
    if sconosciute:
        raise SystemExit(f"varianti sconosciute: {sorted(sconosciute)}")
    esempi = esempi_da(CARTELLA / "sorgente" / "esempi.jsonl") if "lettera_a" in varianti else None
    rispondi = crea_rispondente(o.rispondente)
    uscita = o.cartella / f"{o.rispondente}.jsonl"
    totale = 0
    try:
        for famiglia in o.famiglie.split(","):
            ds = carica(CARTELLA / "domande" / f"{famiglia}.jsonl")
            if o.solo_id:
                ds = [d for d in ds if d.id in set(o.solo_id.split(","))]
            totale += corri(o.rispondente, ds, varianti_per(famiglia, varianti), uscita, o.ripetizioni, o.pausa,
                            o.limite, _rispondi=rispondi, esempi=esempi)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"corsa interrotta dopo {totale} esiti nuovi: {e}\nlo stesso comando riprende da qui", file=sys.stderr)
        return 2
    print(f"{totale} esiti nuovi in {uscita}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
