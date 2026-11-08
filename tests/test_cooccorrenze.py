"""Il solutore che pesa le parole: conteggi, PPMI, pareggi, copertura, lettura dei corpora."""

import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from rnd import SEME
from rnd.cooccorrenze import (Conteggi, carica_stop, conta, coperta, coppie_rilevanti, parole,
                              punteggi, punteggi_solo_opzioni, scegli)
from rnd.corpora import righe_parquet, righe_testo
from rnd.domanda import Domanda
from rnd.varianti import NESSUNA

STOP = carica_stop("it")
CORPUS = [
    "La fotosintesi avviene nelle foglie grazie alla clorofilla.",
    "La clorofilla assorbe la luce e rende possibile la fotosintesi.",
    "Nella fotosintesi le piante liberano ossigeno.",
    "Durante la fotosintesi la pianta usa anidride carbonica e acqua.",
    "Il granito è una roccia molto dura usata nelle costruzioni.",
    "Il sale da cucina si scioglie nell'acqua.",
    "Il ferro arrugginisce con l'umidità.",
    "Le foglie verdi devono il colore alla clorofilla.",
    "Il granito contiene quarzo e feldspato.",
    "La pianta cresce verso la luce.",
]
D_ASSOC = Domanda("x1", "fresche", "Quale pigmento serve alla fotosintesi?", ("granito", "clorofilla", "sale", "ferro"), 1)
D_INCON = Domanda("i1", "inconoscibili", "Qual è il codice di sblocco della cassaforte K-4821?", ("4821", "1203", "9981", "0042"), 2)


def conteggi(righe=CORPUS, ds=(D_ASSOC, D_INCON)):
    voc, cop = coppie_rilevanti(list(ds), STOP)
    return conta(righe, voc, cop, STOP)


class TestParole(unittest.TestCase):
    def test_minuscole_senza_stopword(self):
        self.assertEqual(parole("La fotosintesi avviene nell'acqua, è VITALE.", STOP), ["fotosintesi", "avviene", "acqua", "vitale"])


class TestCoppie(unittest.TestCase):
    def test_nessuna_esclusa(self):
        d = Domanda("x2", "fresche", "Quale pigmento?", ("clorofilla", NESSUNA), 0)
        voc, cop = coppie_rilevanti([d], STOP)
        self.assertIn(("pigmento", "clorofilla"), cop)
        self.assertFalse(any("precedenti" in c for c in cop))


class TestSolutore(unittest.TestCase):
    def test_associativa_vince(self):
        self.assertEqual(scegli(punteggi(D_ASSOC, conteggi(), STOP), random.Random(0)), 1)

    def test_pareggio_casuale(self):
        scelte = Counter(scegli([0.0] * 4, random.Random(f"{SEME}:{i}")) for i in range(400))
        self.assertEqual(set(scelte), {0, 1, 2, 3})
        self.assertLess(max(scelte.values()), 150)

    def test_inconoscibile_tutti_zero(self):
        self.assertEqual(punteggi(D_INCON, conteggi(), STOP), [0.0] * 4)

    def test_solo_opzioni_preferisce_la_parola_frequente(self):
        p = punteggi_solo_opzioni(D_ASSOC, conteggi(), STOP)
        self.assertEqual(max(range(4), key=p.__getitem__), 1)  # «clorofilla» compare tre volte, le altre meno

    def test_coperta(self):
        c = conteggi()
        self.assertTrue(coperta(D_ASSOC, c, STOP)); self.assertFalse(coperta(D_INCON, c, STOP))


class TestConteggi(unittest.TestCase):
    def test_unisci(self):
        voc, cop = coppie_rilevanti([D_ASSOC, D_INCON], STOP)
        meta = conta(CORPUS[:5], voc, cop, STOP).unisci(conta(CORPUS[5:], voc, cop, STOP))
        self.assertEqual(meta, conta(CORPUS, voc, cop, STOP))

    def test_salva_carica(self):
        c = conteggi()
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.json"; c.salva(p)
            self.assertEqual(Conteggi.carica(p), c)


class TestCorpora(unittest.TestCase):
    def test_parquet(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "w.parquet"
            pq.write_table(pa.table({"id": ["1", "2"], "text": ["Prima riga.\n\nSeconda riga.", "Terza."]}), p)
            self.assertEqual(list(righe_parquet(p)), ["Prima riga.", "Seconda riga.", "Terza."])

    def test_testo(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.txt"; p.write_text("uno\n\n due \n", encoding="utf-8")
            self.assertEqual(list(righe_testo(p)), ["uno", "due"])


if __name__ == "__main__":
    unittest.main()
