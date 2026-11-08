"""La corsa: ripresa senza doppioni, righe troncate, risposte fuori formato, varianti per famiglia."""

import json
import tempfile
import unittest
from pathlib import Path

from rnd.corsa import Esito, carica_esiti, corri, fatti, varianti_per
from rnd.domanda import Domanda
from rnd.statistiche import riassumi
from rnd.varianti import NESSUNA

DS = [Domanda(f"f00{i}", "fresche", f"Domanda {i}?", ("uno", "due", "tre", "quattro"), i % 4, extra="cinque")
      for i in range(1, 4)]


def sempre_b(d, variante, testo):
    return "B"


class TestCorsa(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.out = Path(self.t.name) / "finto.jsonl"

    def tearDown(self):
        self.t.cleanup()

    def test_ripresa_senza_doppioni(self):
        self.assertEqual(corri("finto", DS, ["intera"], self.out, _rispondi=sempre_b), 3)
        self.assertEqual(corri("finto", DS, ["intera"], self.out, _rispondi=sempre_b), 0)
        self.assertEqual(len(carica_esiti(self.out)), 3)

    def test_ripetizioni_aggiunte_dopo(self):
        corri("finto", DS, ["intera"], self.out, _rispondi=sempre_b)
        self.assertEqual(corri("finto", DS, ["intera"], self.out, ripetizioni=3, _rispondi=sempre_b), 6)

    def test_riga_troncata(self):
        corri("finto", DS[:2], ["intera"], self.out, _rispondi=sempre_b)
        righe = self.out.read_text(encoding="utf-8").splitlines()
        self.out.write_text(righe[0] + "\n" + righe[1][:20], encoding="utf-8")
        self.assertEqual(fatti(self.out), {("fresche", "intera", "f001", 0)})
        self.assertEqual(corri("finto", DS[:2], ["intera"], self.out, _rispondi=sempre_b), 1)
        self.assertEqual([e.id for e in carica_esiti(self.out)], ["f001", "f002"])

    def test_fuori_formato_non_valida(self):
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=lambda *a: "A o B")
        e = carica_esiti(self.out)[0]
        self.assertIsNone(e.lettera); self.assertIsNone(e.corretta)
        r = riassumi([e])
        self.assertEqual((r["n"], r["valide"], r["corrette"]), (1, 0, 0))

    def test_corretta_e_k(self):
        corri("finto", DS[:1], ["intera", "senza_giusta"], self.out, _rispondi=lambda d, v, t: "E" if v == "senza_giusta" else "B")
        intera, senza = carica_esiti(self.out)
        self.assertEqual((intera.lettera, intera.giusta, intera.corretta, intera.k), (1, 1, True, 4))
        self.assertEqual((senza.k, senza.corretta), (5, True))  # E = «Nessuna delle precedenti»

    def test_confidenza_letta(self):
        corri("finto", DS[:1], ["confidenza"], self.out, _rispondi=lambda *a: "B\n80")
        self.assertEqual(carica_esiti(self.out)[0].confidenza, 80)

    def test_lettera_vincolata_dai_locali(self):
        from rnd.locale import RispostaLocale
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=lambda *a: RispostaLocale("zzz", None, 2, [0.1, 0.2, 0.6, 0.1]))
        e = carica_esiti(self.out)[0]
        self.assertEqual((e.lettera, e.lettera_testo, e.probabilita), (2, None, [0.1, 0.2, 0.6, 0.1]))

    def test_solutore_restituisce_un_indice(self):
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=lambda *a: 3)
        self.assertEqual(carica_esiti(self.out)[0].lettera, 3)

    def test_testo_conservato(self):
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=lambda *a: "Non posso saperlo.")
        e = carica_esiti(self.out)[0]
        self.assertEqual((e.testo, e.lettera), ("Non posso saperlo.", None))

    def test_testo_dei_locali_e_del_solutore(self):
        from rnd.locale import RispostaLocale
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=lambda *a: RispostaLocale("zzz", None, 2, [0.25] * 4))
        corri("pmi", DS[1:2], ["intera"], self.out, _rispondi=lambda *a: 3)
        self.assertEqual([e.testo for e in carica_esiti(self.out)], ["zzz", None])

    def test_righe_vecchie_senza_testo(self):
        corri("finto", DS[:1], ["intera"], self.out, _rispondi=sempre_b)
        riga = json.loads(self.out.read_text(encoding="utf-8"))
        del riga["testo"]
        self.out.write_text(json.dumps(riga) + "\n", encoding="utf-8")
        self.assertIsNone(carica_esiti(self.out)[0].testo)

    def test_ragiona_legge_l_ultima_riga(self):
        corri("finto", DS[:1], ["ragiona"], self.out, _rispondi=lambda *a: "A no, B nemmeno.\nC")
        e = carica_esiti(self.out)[0]
        self.assertEqual((e.lettera, e.variante), (2, "ragiona"))

    def test_il_calcolatore_che_non_sa_leggere_si_astiene(self):
        corri("calcolatore", DS[:1], ["solo_opzioni"], self.out, _rispondi=lambda *a: None)
        e = carica_esiti(self.out)[0]
        self.assertEqual((e.lettera, e.corretta), (None, None))

    def test_pareggio_dei_locali_a_caso(self):
        # logit in bfloat16: pareggi esatti frequenti; non devono andare sempre alla lettera più bassa
        from rnd.locale import RispostaLocale
        ds = [Domanda(f"f{i:03d}", "fresche", f"D{i}?", ("a", "b", "c", "d"), 0) for i in range(40)]
        corri("finto", ds, ["intera"], self.out, _rispondi=lambda *a: RispostaLocale("", None, 0, [0.4, 0.1, 0.4, 0.1]))
        scelte = {e.lettera for e in carica_esiti(self.out)}
        self.assertEqual(scelte, {0, 2})

    def test_rileggi_corregge_lettera_e_pareggi(self):
        from rnd.corsa import rileggi
        from rnd.locale import RispostaLocale
        d5 = Domanda("f057", "fresche", "Chi?", ("a", "b", "c", "d"), 1, extra="e")  # senza_giusta: E è «Nessuna»
        testo = "Boccaccio visse nel XIV secolo, quindi nessuna delle opzioni A–D è corretta.\n\nE"
        corri("sonnet", [d5], ["senza_giusta"], self.out, _rispondi=lambda *a: testo)
        righe = [json.loads(r) for r in self.out.read_text(encoding="utf-8").splitlines()]
        righe[0].update(lettera=None, lettera_testo=None, corretta=None)  # com'era prima della correzione
        locali = [Domanda(f"f{i:03d}", "fresche", f"D{i}?", ("a", "b", "c", "d"), 2) for i in range(20)]
        altro = Path(self.t.name) / "qwen.jsonl"
        corri("qwen", locali, ["intera"], altro, _rispondi=lambda *a: RispostaLocale("", None, 0, [0.4, 0.1, 0.4, 0.1]))
        loc = [json.loads(r) for r in altro.read_text(encoding="utf-8").splitlines()]
        for r in loc:
            r.update(lettera=0, corretta=False)  # com'era: sempre la prima del pareggio
        self.out.write_text("".join(json.dumps(r) + "\n" for r in righe + loc), encoding="utf-8")
        cambiate = rileggi(self.out)
        es = carica_esiti(self.out)
        self.assertEqual((es[0].lettera, es[0].corretta), (4, True))
        self.assertEqual({e.lettera for e in es[1:]}, {0, 2})
        self.assertGreater(cambiate, 1)
        self.assertEqual(rileggi(self.out), 0)  # rileggere due volte non cambia niente

    def test_varianti_per_le_deduttive(self):
        tutte = ["intera", "solo_opzioni", "mescolata", "ragiona"]
        self.assertEqual(varianti_per("deduttive", tutte), ["intera", "solo_opzioni", "ragiona"])
        self.assertEqual(varianti_per("trappola", tutte), ["intera", "solo_opzioni"])

    def test_varianti_per_famiglia(self):
        tutte = ["intera", "solo_opzioni", "mescolata", "senza_giusta"]
        self.assertEqual(varianti_per("fresche", tutte), tutte)
        self.assertEqual(varianti_per("trappola", tutte), ["intera", "solo_opzioni"])


if __name__ == "__main__":
    unittest.main()
