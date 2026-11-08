"""Lettura della lettera e della confidenza dalle risposte."""

import unittest

from rnd.lettera import estrai_confidenza, estrai_lettera, estrai_lettera_finale


class TestLettera(unittest.TestCase):
    def test_casi(self):
        for testo, atteso in [("B", 1), ("B)", 1), ("Risposta: C", 2), ("**D**", 3), ("La risposta è A.", 0),
                              ("A o B", None), ("E", None), ("", None), ("b", None), ("Il DNA", None),
                              ("B. Perché la vitamina C non c'entra.", 1), ("B\n85", 1)]:
            with self.subTest(testo=testo):
                self.assertEqual(estrai_lettera(testo, 4), atteso)

    def test_quinta_lettera(self):
        self.assertEqual(estrai_lettera("E", 5), 4)


class TestPrimaRigaAmbigua(unittest.TestCase):
    def test_lettera_sola_in_fondo(self):
        # f057, senza_giusta: la prima riga nomina «A–D», la risposta è la E da sola in fondo
        testo = "Boccaccio (1313–1375) visse nel XIV secolo, quindi nessuna delle opzioni A–D è corretta.\n\nE"
        self.assertEqual(estrai_lettera(testo, 5), 4)
        self.assertEqual(estrai_lettera("Le opzioni A e C sono sbagliate.\n\nD", 4), 3)

    def test_ambigua_anche_in_fondo(self):
        self.assertIsNone(estrai_lettera("Fra A e C.\n\nB o D", 4))
        self.assertIsNone(estrai_lettera("Fra A e C, direi.\nForse.", 4))


class TestLetteraFinale(unittest.TestCase):
    def test_casi(self):
        casi = [
            ("49 × 15: 49 × 10 = 490, 49 × 5 = 245, in tutto 735.\nLa risposta è la B.\nB", 1),
            ("Le premesse dicono che A e C...\n\n**C**", 2),
            ("Calcolo i passaggi.\nRisposta: D", 3),
            ("Il ragionamento nomina A e C.\n\nB", 1),
            ("Non so decidere.\nA o B", None),
            ("Quindi fa 735.", None),
            ("", None),
            ("D", 3),
        ]
        for testo, atteso in casi:
            with self.subTest(testo=testo):
                self.assertEqual(estrai_lettera_finale(testo, 4), atteso)


class TestConfidenza(unittest.TestCase):
    def test_casi(self):
        for testo, atteso in [("B\n85", 85), ("B", None), ("B\n140", None), ("B\nConfidenza: 70%", 70), ("B\n0", 0)]:
            with self.subTest(testo=testo):
                self.assertEqual(estrai_confidenza(testo), atteso)


if __name__ == "__main__":
    unittest.main()
