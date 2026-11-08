"""Preparazione dei file di domande: posizioni bilanciate, trappole, inconoscibili, ARC."""

import re
import unittest
from collections import Counter
from pathlib import Path

from rnd import SEME
from rnd.domanda import valida
from rnd.prepara import arc, bilancia, coppie_trappola, inconoscibili

FIXTURE = Path(__file__).parent / "fixtures" / "arc-mini.jsonl"
TIPI = ("associativa", "relazionale", "negazione", "due_passi")


def sorgenti_finte(n):
    return [
        {"id": f"f{i:03d}", "testo": f"Domanda numero {i}?", "giusta": f"giusta {i}",
         "sbagliate": [f"sbagliata {i}a", f"sbagliata {i}b", f"sbagliata {i}c"],
         "extra": f"extra {i}", "tipo": TIPI[i % 4], "tema": "scienze"}
        for i in range(n)
    ]


def coppia_finta(sbagliate_cambiata=("sette", "otto", "cinque")):
    return {
        "coppia": "t01",
        "familiare": {"testo": "Quanti sono i nani di Biancaneve?", "giusta": "sette", "sbagliate": ["sei", "otto", "cinque"]},
        "cambiata": {"testo": "Se uno dei nani di Biancaneve se ne va, quanti ne restano?", "giusta": "sei", "sbagliate": list(sbagliate_cambiata)},
    }


class TestBilancia(unittest.TestCase):
    def test_equidistribuisce(self):
        ds = bilancia(sorgenti_finte(200), "fresche", SEME)
        self.assertEqual(Counter(d.giusta for d in ds), {0: 50, 1: 50, 2: 50, 3: 50})

    def test_la_giusta_resta_la_giusta(self):
        ds = bilancia(sorgenti_finte(200), "fresche", SEME)
        for d, s in zip(ds, sorgenti_finte(200)):
            self.assertEqual(d.opzioni[d.giusta], s["giusta"])
            self.assertEqual(set(d.opzioni), {s["giusta"], *s["sbagliate"]})
            self.assertEqual((d.extra, d.tipo), (s["extra"], s["tipo"]))
            self.assertEqual(valida(d), [])

    def test_deterministico(self):
        self.assertEqual(bilancia(sorgenti_finte(200), "fresche", SEME), bilancia(sorgenti_finte(200), "fresche", SEME))


class TestTrappola(unittest.TestCase):
    def test_indice_familiare(self):
        f, c = coppie_trappola([coppia_finta()], SEME)
        self.assertEqual((f.id, c.id), ("t01-f", "t01-c"))
        self.assertEqual((f.versione, c.versione), ("familiare", "cambiata"))
        self.assertEqual(c.opzioni[c.indice_familiare], "sette")
        self.assertEqual(c.opzioni[c.giusta], "sei")
        self.assertEqual(valida(f), []); self.assertEqual(valida(c), [])

    def test_rifiuta_familiare_assente(self):
        with self.assertRaises(ValueError):
            coppie_trappola([coppia_finta(("nove", "otto", "cinque"))], SEME)


class TestInconoscibili(unittest.TestCase):
    def test_cento_valide_e_bilanciate(self):
        ds = inconoscibili(100, SEME)
        self.assertEqual(len(ds), 100)
        self.assertEqual(len({d.id for d in ds}), 100)
        self.assertTrue(all(valida(d) == [] for d in ds))
        self.assertTrue(all(d.famiglia == "inconoscibili" and d.extra and d.extra not in d.opzioni for d in ds))
        self.assertLessEqual(max(Counter(d.giusta for d in ds).values()), 35)

    def test_niente_nomi_propri(self):
        for d in inconoscibili(100, SEME):
            self.assertIsNone(re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", d.testo), d.testo)

    def test_deterministico(self):
        self.assertEqual(inconoscibili(100, SEME), inconoscibili(100, SEME))


class TestArc(unittest.TestCase):
    def test_solo_quattro_opzioni(self):
        ds = arc(FIXTURE, "arc_easy", 10, SEME)
        self.assertEqual(len(ds), 4)
        self.assertTrue(all(len(d.opzioni) == 4 and d.famiglia == "arc_easy" for d in ds))

    def test_etichette_numeriche(self):
        d = {x.id: x for x in arc(FIXTURE, "arc_easy", 10, SEME)}["NYSEDREGENTS_3"]
        self.assertEqual(d.opzioni[d.giusta], "whale")

    def test_campione(self):
        self.assertEqual(len(arc(FIXTURE, "arc_challenge", 2, SEME)), 2)


if __name__ == "__main__":
    unittest.main()
