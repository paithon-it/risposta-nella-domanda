"""Modello della domanda: giro in JSONL e validazione."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from rnd.domanda import Domanda, carica, salva, valida

D_BUONA = Domanda(
    "f001", "fresche", "Quale gas rilasciano le piante con la fotosintesi?",
    ("anidride carbonica", "ossigeno", "azoto", "metano"), 1,
    extra="elio", tipo="relazionale", tema="scienze",
)


class TestDomanda(unittest.TestCase):
    def test_giro_jsonl(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "d.jsonl"
            salva([D_BUONA, replace(D_BUONA, id="f002", testo="Perché città è accentata?")], p)
            self.assertEqual(carica(p), [D_BUONA, replace(D_BUONA, id="f002", testo="Perché città è accentata?")])
            self.assertIn("città", p.read_text(encoding="utf-8"))

    def test_valida_buona(self):
        self.assertEqual(valida(D_BUONA), [])

    def test_valida_errori(self):
        casi = [
            replace(D_BUONA, opzioni=("x",)),
            replace(D_BUONA, opzioni=("a", "a", "b", "c")),
            replace(D_BUONA, giusta=4),
            replace(D_BUONA, famiglia="altro"),
            replace(D_BUONA, tipo="strano"),
            replace(D_BUONA, famiglia="trappola", coppia="t01", versione="cambiata", indice_familiare=None),
            replace(D_BUONA, famiglia="trappola", coppia="t01", versione="cambiata", indice_familiare=1),
        ]
        for d in casi:
            with self.subTest(d=d):
                self.assertTrue(valida(d))


if __name__ == "__main__":
    unittest.main()
