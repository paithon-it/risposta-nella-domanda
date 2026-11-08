"""Conteggio in parallelo con parziali riprendibili."""

import tempfile
import unittest
from pathlib import Path

from rnd.cooccorrenze import carica_stop, conta, coppie_rilevanti
from rnd.corpora import righe_testo
from rnd.domanda import Domanda
from rnd.scarica import conta_fonti, firma, trova

STOP = carica_stop("it")
D = Domanda("x", "fresche", "Quale pigmento serve alla fotosintesi?", ("granito", "clorofilla", "sale", "ferro"), 1)
TESTI = ["La fotosintesi usa la clorofilla.\nIl granito è duro.\n", "La clorofilla è verde.\nIl sale e il ferro.\n", "Fotosintesi e clorofilla.\n"]


class TestScarica(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.base = Path(self.t.name)
        self.fonti = []
        for i, testo in enumerate(TESTI):
            p = self.base / f"c{i}.txt"; p.write_text(testo, encoding="utf-8"); self.fonti.append(p)
        self.voc, self.cop = coppie_rilevanti([D], STOP)

    def tearDown(self):
        self.t.cleanup()

    def test_parallelo_uguale_a_seriale(self):
        seriale = conta([r for p in self.fonti for r in righe_testo(p)], self.voc, self.cop, STOP)
        self.assertEqual(conta_fonti(self.fonti, "testo", self.voc, self.cop, STOP, self.base / "parziali", processi=2), seriale)

    def test_parziali_riusati_solo_con_la_stessa_firma(self):
        parziali = self.base / "parziali"
        conta_fonti(self.fonti, "testo", self.voc, self.cop, STOP, parziali, processi=1)
        self.assertEqual(len(list(parziali.glob(f"*-{firma(self.voc, self.cop)}.json"))), 3)
        self.fonti[0].write_text("niente di utile\n", encoding="utf-8")  # se rilegge, il risultato cambia
        c = conta_fonti(self.fonti, "testo", self.voc, self.cop, STOP, parziali, processi=1)
        self.assertGreater(c.coppie.get(("fotosintesi", "clorofilla"), 0), 1)  # ha riusato il parziale vecchio

    def test_trova(self):
        nomi = ["ARC-V1-Feb2018-2/ARC-Easy/ARC-Easy-Test.jsonl", "ARC-V1-Feb2018-2/ARC-Easy/ARC-Easy-Train.jsonl"]
        self.assertEqual(trova(nomi, "ARC-Easy-Test.jsonl"), nomi[0])
        with self.assertRaises(FileNotFoundError):
            trova(nomi, "ARC_Corpus.txt")


if __name__ == "__main__":
    unittest.main()


class TestFamiglieIt(unittest.TestCase):
    def test_conta_anche_le_deduttive(self):
        from rnd.scarica import FAMIGLIE_IT
        self.assertEqual(FAMIGLIE_IT, ("fresche", "trappola", "inconoscibili", "deduttive"))
