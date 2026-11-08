"""I file di domande scritti davvero: conteggi, indizi di lunghezza, doppioni, validità."""

import json
import unittest
from collections import Counter
from pathlib import Path

from rnd.domanda import carica, valida
from rnd.varianti import NESSUNA

CARTELLA = Path(__file__).resolve().parent.parent


def _jsonl(p):
    with p.open(encoding="utf-8") as f:
        return [json.loads(r) for r in f if r.strip()]


FRESCHE = _jsonl(CARTELLA / "sorgente" / "fresche.jsonl")
TRAPPOLE = _jsonl(CARTELLA / "sorgente" / "trappola.jsonl")
ESEMPI = _jsonl(CARTELLA / "sorgente" / "esempi.jsonl")
GENERATI = [CARTELLA / "domande" / f"{f}.jsonl" for f in ("fresche", "trappola", "inconoscibili")]


class TestSorgenti(unittest.TestCase):
    def test_conteggi(self):
        self.assertEqual((len(FRESCHE), len(TRAPPOLE), len(ESEMPI)), (200, 50, 3))
        self.assertEqual(Counter(s["tipo"] for s in FRESCHE), {"associativa": 80, "relazionale": 60, "negazione": 30, "due_passi": 30})

    def test_giusta_non_sempre_la_piu_lunga(self):  # Review Focus 1
        piu_lunga = sum(len(s["giusta"]) > max(len(x) for x in s["sbagliate"]) for s in FRESCHE)
        self.assertLessEqual(piu_lunga / len(FRESCHE), 0.35)

    def test_niente_doppioni(self):
        testi = [s["testo"] for s in FRESCHE] + [c[v]["testo"] for c in TRAPPOLE for v in ("familiare", "cambiata")] + [s["testo"] for s in ESEMPI]
        self.assertEqual(len(testi), len(set(testi)))

    def test_extra_diverso_dalle_opzioni(self):
        for s in FRESCHE:
            self.assertNotIn(s["extra"], [s["giusta"], *s["sbagliate"]], s["id"])
            self.assertNotEqual(s["extra"], NESSUNA)

    def test_niente_trattini_lunghi(self):
        for s in FRESCHE:
            self.assertNotIn("—", json.dumps(s, ensure_ascii=False))

    def test_domande_generate_valide(self):
        for f in GENERATI:
            for d in carica(f):
                self.assertEqual(valida(d), [], d.id)

    def test_posizioni_bilanciate(self):
        self.assertEqual(Counter(d.giusta for d in carica(GENERATI[0])), {0: 50, 1: 50, 2: 50, 3: 50})


if __name__ == "__main__":
    unittest.main()
