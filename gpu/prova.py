"""Prova su tre domande prima della corsa: tempo di caricamento, memoria della GPU, scelta vincolata.

Uso, sulla macchina con la GPU, dalla cartella dell'esperimento:
    HF_HOME=~/rnd/hf HF_HUB_OFFLINE=1 python3 gpu/prova.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rnd.corsa import crea_rispondente  # noqa: E402
from rnd.domanda import carica  # noqa: E402
from rnd.varianti import prompt  # noqa: E402


def main() -> None:  # vLLM avvia un processo separato: il codice deve stare sotto __main__
    RISPONDENTE = sys.argv[1] if len(sys.argv) > 1 else "qwen3.8-27b"
    t0 = time.time()
    r = crea_rispondente(RISPONDENTE)
    print("caricato in", round(time.time() - t0, 1), "s")
    for f in ("fresche", "deduttive", "inconoscibili"):
        d = carica(Path("domande") / f"{f}.jsonl")[0]
        t = time.time()
        x = r(d, "intera", prompt(d, "intera"))
        scelta = max(range(len(d.opzioni)), key=x.probabilita.__getitem__)
        print(f"{f}: giusta {d.giusta}, scelta {scelta}, probabilità {[round(p, 3) for p in x.probabilita]}, "
              f"testo {x.testo!r}, {time.time() - t:.2f} s")


if __name__ == "__main__":
    main()
