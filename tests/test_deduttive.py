"""Le domande deduttive: la risposta sta tutta nella domanda, e il calcolatore la tira fuori."""

import unittest
from collections import Counter

from rnd import SEME
from rnd.calcolatore import conseguenze, risolvi
from rnd.deduttive import genera
from rnd.domanda import Domanda, valida


def d(testo, opzioni, giusta=0, tipo=None):
    return Domanda("x001", "deduttive", testo, tuple(opzioni), giusta, tipo=tipo)


class TestGenera(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = genera(SEME)

    def test_cento_venti_per_tipo(self):
        self.assertEqual(len(self.ds), 100)
        self.assertEqual(Counter(x.tipo for x in self.ds),
                         {"aritmetica": 20, "cifrario": 20, "sillogismo": 20, "controintuitivo": 20, "ordinamento": 20})
        self.assertEqual(Counter(x.tema for x in self.ds if x.tipo == "cifrario"),
                         {"spostamento-3": 10, "spostamento-2": 10})

    def test_valide_e_uniche(self):
        self.assertEqual([p for x in self.ds for p in valida(x)], [])
        self.assertEqual(len({x.id for x in self.ds}), 100)
        self.assertEqual(len({x.testo for x in self.ds}), 100)

    def test_posizioni_bilanciate(self):
        self.assertEqual(Counter(x.giusta for x in self.ds), {0: 25, 1: 25, 2: 25, 3: 25})

    def test_tipi_mescolati(self):
        # i primi 25 id contengono tutti i tipi, così --limite non ne prende uno solo
        self.assertEqual(len({x.tipo for x in self.ds[:25]}), 5)

    def test_deterministico(self):
        self.assertEqual(genera(SEME), self.ds)

    def test_il_calcolatore_trova_sempre_la_giusta(self):
        sbagliate = [(x.id, risolvi(x), x.giusta) for x in self.ds if risolvi(x) != x.giusta]
        self.assertEqual(sbagliate, [])

    def test_una_sola_conclusione_per_sillogismo(self):
        for x in self.ds:
            if x.tipo in ("sillogismo", "controintuitivo"):
                self.assertEqual(len(conseguenze(x)), 1, x.testo)

    def test_controintuitivo_ha_l_esca_credibile(self):
        for x in self.ds:
            if x.tipo == "controintuitivo":
                giusta = x.opzioni[x.giusta]  # «Tutti i gatti sono verdi»
                soggetto, predicato = giusta.split()[2], giusta.split()[-1]
                self.assertIn(f"Alcuni {soggetto} non sono {predicato}", x.opzioni)

    def test_cifrario_con_parole_della_stessa_lunghezza(self):
        for x in self.ds:
            if x.tipo == "cifrario":
                self.assertEqual(len({len(o) for o in x.opzioni}), 1, x.opzioni)


class TestPrepara(unittest.TestCase):
    def test_main_scrive_le_deduttive(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from rnd import prepara
        from rnd.domanda import carica
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.object(prepara, "CARTELLA", Path(t)):
                prepara.main()
            self.assertEqual(len(carica(Path(t) / "domande" / "deduttive.jsonl")), 100)


class TestCalcolatore(unittest.TestCase):
    def test_aritmetica(self):
        self.assertEqual(risolvi(d("Quanto fa 12 × 34?", ["418", "408", "398", "508"])), 1)

    def test_cifrario(self):
        t = ("Ogni lettera di una parola italiana è stata spostata in avanti di 3 posizioni nell'alfabeto "
             "inglese, ricominciando dalla a dopo la z. La parola cifrata è «fdvd». Qual era la parola?")
        self.assertEqual(risolvi(d(t, ["mare", "casa", "lupo", "pane"])), 1)

    def test_cifrario_che_gira_dopo_la_z(self):
        t = ("Ogni lettera di una parola italiana è stata spostata in avanti di 2 posizioni nell'alfabeto "
             "inglese, ricominciando dalla a dopo la z. La parola cifrata è «bqpg». Qual era la parola?")
        self.assertEqual(risolvi(d(t, ["zone", "mare", "pane", "sole"])), 0)

    def test_ordinamento(self):
        t = "Carla è più alta di Dora. Anna è più alta di Bea. Bea è più alta di Carla. Chi è la seconda più bassa?"
        self.assertEqual(risolvi(d(t, ["Anna", "Bea", "Carla", "Dora"])), 2)
        t2 = t.replace("la seconda più bassa", "la più alta")
        self.assertEqual(risolvi(d(t2, ["Dora", "Carla", "Bea", "Anna"])), 3)

    def test_barbara_neutro(self):
        t = "Tutti i frumi sono tolpi. Tutti i blicchi sono frumi. Che cosa segue necessariamente da queste due premesse?"
        x = d(t, ["Tutti i frumi sono blicchi", "Tutti i blicchi sono tolpi",
                  "Alcuni blicchi non sono tolpi", "Alcuni frumi non sono tolpi"])
        self.assertEqual(conseguenze(x), [1])
        self.assertEqual(risolvi(x), 1)

    def test_articolo_gli(self):
        t = ("Tutti gli uccelli sono quadrati. Tutti i passeri sono uccelli. "
             "Che cosa segue necessariamente da queste due premesse?")
        x = d(t, ["Alcuni passeri non sono quadrati", "Tutti gli uccelli sono passeri",
                  "Tutti i passeri sono quadrati", "Alcuni uccelli non sono quadrati"])
        self.assertEqual(risolvi(x), 2)

    def test_alcuni_non_segue_senza_premessa_esistenziale(self):
        # «Tutti» non dice che i blicchi esistano: «Alcuni blicchi sono tolpi» non segue
        t = "Tutti i frumi sono tolpi. Tutti i blicchi sono frumi. Che cosa segue necessariamente da queste due premesse?"
        self.assertEqual(conseguenze(d(t, ["Alcuni blicchi sono tolpi", "Tutti i tolpi sono blicchi"])), [])

    def test_domanda_che_non_sa_leggere(self):
        self.assertIsNone(risolvi(d("Chi ha scritto I promessi sposi?", ["Manzoni", "Verga", "Foscolo", "Leopardi"])))


if __name__ == "__main__":
    unittest.main()
