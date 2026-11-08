"""Varianti delle domande e forma dei prompt."""

import unittest
from dataclasses import replace

from rnd.domanda import Domanda
from rnd.varianti import NESSUNA, VARIANTI, applica, prompt

D = Domanda("f001", "fresche", "Quale gas rilasciano le piante?",
            ("anidride carbonica", "ossigeno", "azoto", "metano"), 1, extra="elio")
ESEMPI = [
    Domanda("e1", "fresche", "Di che colore è il cielo sereno?", ("verde", "azzurro", "rosso", "nero"), 1),
    Domanda("e2", "fresche", "Quante zampe ha un ragno?", ("sei", "quattro", "otto", "dieci"), 2),
    Domanda("e3", "fresche", "Qual è la capitale della Francia?", ("Lione", "Nizza", "Marsiglia", "Parigi"), 3),
]


class TestApplica(unittest.TestCase):
    def test_otto_varianti(self):
        self.assertEqual(VARIANTI, ("intera", "solo_opzioni", "mescolata", "con_nessuna", "senza_giusta", "confidenza",
                                    "lettera_a", "ragiona"))

    def test_ragiona_chiede_i_passaggi_e_la_lettera_in_fondo(self):
        p = prompt(D, "ragiona")
        self.assertTrue(p.endswith("Ragiona passo per passo, poi scrivi solo la lettera sull'ultima riga."))
        self.assertIn("Domanda: Quale gas rilasciano le piante?", p)

    def test_identita(self):
        for v in ("intera", "confidenza", "lettera_a", "ragiona"):
            self.assertEqual(applica(D, v), D)

    def test_solo_opzioni(self):
        v = applica(D, "solo_opzioni")
        self.assertEqual(v.testo, ""); self.assertEqual((v.opzioni, v.giusta), (D.opzioni, D.giusta))

    def test_mescolata_rimappa(self):
        v = applica(D, "mescolata")
        self.assertNotEqual(v.opzioni, D.opzioni)
        self.assertEqual(sorted(v.opzioni), sorted(D.opzioni))
        self.assertEqual(v.opzioni[v.giusta], D.opzioni[D.giusta])
        self.assertEqual(applica(D, "mescolata"), v)

    def test_mescolata_rimappa_familiare(self):
        c = replace(D, famiglia="trappola", coppia="t1", versione="cambiata", indice_familiare=0)
        v = applica(c, "mescolata")
        self.assertEqual(v.opzioni[v.indice_familiare], "anidride carbonica")

    def test_con_nessuna(self):
        v = applica(D, "con_nessuna")
        self.assertEqual(v.opzioni, D.opzioni + (NESSUNA,)); self.assertEqual(v.giusta, 1)

    def test_senza_giusta(self):
        v = applica(D, "senza_giusta")
        self.assertNotIn("ossigeno", v.opzioni); self.assertIn("elio", v.opzioni)
        self.assertEqual(v.opzioni[v.giusta], NESSUNA); self.assertEqual(len(v.opzioni), 5)

    def test_senza_giusta_vuole_extra(self):
        with self.assertRaises(ValueError):
            applica(replace(D, extra=None), "senza_giusta")

    def test_variante_sconosciuta(self):
        with self.assertRaises(ValueError):
            applica(D, "boh")


class TestPrompt(unittest.TestCase):
    def test_intera_esatto(self):
        self.assertEqual(prompt(D, "intera"),
                         "Domanda: Quale gas rilasciano le piante?\nA) anidride carbonica\nB) ossigeno\nC) azoto\nD) metano\nRispondi solo con la lettera.")

    def test_solo_opzioni(self):
        p = prompt(applica(D, "solo_opzioni"), "solo_opzioni")
        self.assertTrue(p.startswith("Non vedi la domanda, solo le opzioni. Quale è più probabilmente quella giusta?\nA) "))
        self.assertNotIn("Quale gas", p)

    def test_confidenza(self):
        self.assertTrue(prompt(D, "confidenza").endswith("un numero da 0 a 100: quanto sei sicuro."))

    def test_lettera_a_esempi_in_a(self):
        p = prompt(D, "lettera_a", esempi=ESEMPI)
        self.assertEqual(p.count("Risposta: A"), 3)
        for e in ESEMPI:
            self.assertIn(f"A) {e.opzioni[e.giusta]}", p)
        self.assertTrue(p.endswith("Rispondi con la lettera e poi spiega in una frase perché."))
        self.assertIn("Domanda: Quale gas rilasciano le piante?\nA) anidride carbonica", p)

    def test_lettera_a_vuole_esempi(self):
        with self.assertRaises(ValueError):
            prompt(D, "lettera_a")


if __name__ == "__main__":
    unittest.main()
