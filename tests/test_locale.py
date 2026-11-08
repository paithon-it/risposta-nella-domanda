"""Modello locale: scelta vincolata fra le lettere, gemello a pesi casuali."""

import os
import unittest

import torch

from rnd.domanda import Domanda
from rnd.locale import ModelloLocale, distribuzione_lettere, ids_lettere
from rnd.varianti import prompt

D_FACILE = Domanda("x", "fresche", "Qual è la capitale d'Italia?", ("Milano", "Roma", "Napoli", "Torino"), 1)


class TokenizerFinto:
    """Una lettera = un token, tranne la E che ne vale due."""

    def encode(self, testo, add_special_tokens=False):
        return [ord(testo)] if testo != "E" else [69, 70]


class TestVincolata(unittest.TestCase):
    def test_distribuzione(self):
        logit = torch.full((50,), -1e9)
        logit[[7, 9, 11, 13]] = torch.tensor([0.0, 2.0, 0.0, 0.0])
        p = distribuzione_lettere(logit, [7, 9, 11, 13])
        self.assertAlmostEqual(sum(p), 1.0, places=5)
        self.assertEqual(max(range(4), key=p.__getitem__), 1)

    def test_logit_piatti(self):  # pesi casuali: sempre una distribuzione valida su k lettere
        p = distribuzione_lettere(torch.zeros(50), [1, 2, 3, 4])
        self.assertEqual(len(p), 4); self.assertAlmostEqual(sum(p), 1.0, places=5)

    def test_ids_lettere(self):
        self.assertEqual(ids_lettere(TokenizerFinto(), 4), [65, 66, 67, 68])
        with self.assertRaises(ValueError):
            ids_lettere(TokenizerFinto(), 5)


@unittest.skipUnless(os.environ.get("RND_INTEGRAZIONE"), "scarica il modello (RND_INTEGRAZIONE=1)")
class TestIntegrazione(unittest.TestCase):
    def test_qwen_risponde(self):
        m = ModelloLocale()
        r = m.rispondi(prompt(D_FACILE, "intera"), 4)
        self.assertEqual(m.rispondente, "qwen")
        self.assertEqual(r.lettera_vincolata, 1)
        self.assertIsNotNone(r.lettera_testo)

    def test_gemello_casuale(self):
        m = ModelloLocale(pesi_casuali=True)
        r = m.rispondi(prompt(D_FACILE, "intera"), 4)
        self.assertEqual(m.rispondente, "qwen-casuale")
        self.assertIn(r.lettera_vincolata, range(4))
        self.assertAlmostEqual(sum(r.probabilita), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
