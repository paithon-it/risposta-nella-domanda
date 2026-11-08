"""Sintesi: intervalli di Wilson, trappole, caso in testa alla scala, stabilità, calibrazione."""

import unittest

from rnd.corsa import Esito
from dataclasses import replace

from rnd.domanda import Domanda
from rnd.statistiche import affidabilita, brier, cifre_solutore, riassumi, sintesi_da, wilson


def esito(rispondente="finto", famiglia="fresche", variante="intera", id="f001", ripetizione=0,
          lettera=1, giusta=1, k=4, indice_familiare=None, confidenza=None, probabilita=None):
    corretta = None if lettera is None or giusta is None else lettera == giusta
    return Esito(rispondente, famiglia, variante, id, ripetizione, lettera, None, probabilita, confidenza, None,
                 giusta, corretta, k, indice_familiare, 0.0)


class TestWilson(unittest.TestCase):
    def test_valori_noti(self):
        lo, hi = wilson(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3); self.assertAlmostEqual(hi, 0.5962, places=3)

    def test_vuoto(self):
        self.assertEqual(wilson(0, 0), (0.0, 1.0))


class TestRiassumi(unittest.TestCase):
    def test_conti(self):
        r = riassumi([esito(lettera=1), esito(lettera=2), esito(lettera=None)])
        self.assertEqual((r["n"], r["valide"], r["corrette"]), (3, 2, 1))
        self.assertAlmostEqual(r["accuratezza"], 1 / 3)


class TestSintesi(unittest.TestCase):
    def test_caso_in_testa_alla_scala(self):
        s = sintesi_da([esito()], {})
        self.assertEqual(s["scala"][0]["rispondente"], "caso")
        self.assertAlmostEqual(s["scala"][0]["accuratezza"], 0.25)

    def test_trappola_quota_familiare(self):
        es = [esito(famiglia="trappola", id="t01-c", lettera=0, giusta=1, indice_familiare=0),
              esito(famiglia="trappola", id="t02-c", lettera=1, giusta=1, indice_familiare=3),
              esito(famiglia="trappola", id="t01-f", lettera=2, giusta=2)]
        t = sintesi_da(es, {})["trappola"]["finto"]
        self.assertEqual(t["quota_familiare"], 0.5)
        self.assertEqual(t["cambiata"]["n"], 2); self.assertEqual(t["familiare"]["corrette"], 1)

    def test_stabilita(self):
        es = [esito(id="f001", ripetizione=r, lettera=1) for r in range(3)] + \
             [esito(id="f002", ripetizione=r, lettera=r % 2) for r in range(3)]
        self.assertEqual(sintesi_da(es, {})["stabilita"]["finto"]["quota_stabili"], 0.5)

    def test_lettera_a(self):
        es = [esito(variante="lettera_a", id="f001", lettera=0, giusta=2),
              esito(variante="lettera_a", id="f002", lettera=1, giusta=1),
              esito(variante="lettera_a", id="f003", lettera=0, giusta=0),  # esclusa: la giusta è già A
              esito(variante="intera", id="f001", lettera=2, giusta=2),
              esito(variante="intera", id="f002", lettera=1, giusta=1)]
        la = sintesi_da(es, {})["epistemologia"]["finto"]["lettera_a"]
        self.assertEqual((la["quota_a"], la["quota_a_intera"], la["n"]), (0.5, 0.0, 2))

    def test_nessuna(self):
        es = [esito(variante="con_nessuna", lettera=4, giusta=1, k=5), esito(variante="con_nessuna", id="f002", lettera=1, giusta=1, k=5),
              esito(variante="senza_giusta", lettera=4, giusta=4, k=5)]
        ep = sintesi_da(es, {})["epistemologia"]["finto"]
        self.assertEqual(ep["con_nessuna"]["quota_nessuna"], 0.5)
        self.assertEqual(ep["senza_giusta"]["accuratezza"], 1.0)


class TestRegimeDeduttive(unittest.TestCase):
    def test_divide_secondo_come_ha_risposto_l_oracolo(self):
        ded = dict(famiglia="deduttive", giusta=1)
        es = [replace(esito(rispondente="sonnet", id="d1", lettera=1, **ded), testo="B"),
              replace(esito(rispondente="sonnet", id="d2", lettera=1, **ded), testo="49 × 15 = 735\nB"),
              replace(esito(rispondente="sonnet", id="d3", lettera=0, **ded), testo="A)"),
              replace(esito(rispondente="sonnet", id="d4", lettera=1, **ded), testo="B"),
              esito(rispondente="qwen3.8-27b", id="d1", lettera=1, **ded),
              esito(rispondente="qwen3.8-27b", id="d2", lettera=0, **ded),
              esito(rispondente="qwen3.8-27b", id="d3", lettera=1, **ded),
              esito(rispondente="qwen3.8-27b", id="d4", lettera=0, **ded)]
        tipi = {"d1": "aritmetica", "d2": "aritmetica", "d3": "sillogismo", "d4": "cifrario-2"}
        r = sintesi_da(es, {}, tipi)["regime_deduttive"]
        self.assertEqual(r["sola_lettera"], {"n": 2, "sonnet": 1, "qwen3.8-27b": 2})
        self.assertEqual(r["sola_lettera_cifrari"], {"n": 1, "sonnet": 1, "qwen3.8-27b": 0})
        self.assertEqual(r["conto_scritto"], {"n": 1, "sonnet": 1, "qwen3.8-27b": 0})

    def test_senza_entrambi_niente(self):
        self.assertEqual(sintesi_da([esito()], {})["regime_deduttive"], {})


class TestCifreSolutore(unittest.TestCase):
    def test_conta_le_domande_con_sole_cifre(self):
        def dom(i, tipo, opzioni):
            return Domanda(id=i, famiglia="fresche", testo="Quando?", opzioni=opzioni, giusta=0, tipo=tipo)
        ds = [dom("f1", "due_passi", ("1930", "1920", "1945", "1969")),
              dom("f2", "associativa", ("Manzoni", "Verga", "Foscolo", "Leopardi")),
              dom("f3", "associativa", ("1930", "Verga", "Foscolo", "Leopardi"))]  # una parola c'è: non è un sorteggio
        es = [esito(rispondente="pmi", id="f1", lettera=0, giusta=0),
              esito(rispondente="pmi", id="f2", lettera=1, giusta=0),
              esito(rispondente="pmi", id="f3", lettera=0, giusta=0)]
        self.assertEqual(cifre_solutore(es, ds, frozenset()),
                         {"numeriche": 1, "giuste_numeriche": 1, "altre": 2, "giuste_altre": 1, "per_tipo": {"due_passi": 1}})


class TestSondaToken(unittest.TestCase):
    def test_prende_solo_le_risposte_a_sola_lettera(self):
        from rnd.sonda_token import da_provare

        def dom(i, tipo):
            return Domanda(id=i, famiglia="deduttive", testo="?", opzioni=("a", "b", "c", "d"), giusta=0, tipo=tipo)
        ds = [dom("d1", "aritmetica"), dom("d2", "aritmetica"), dom("d3", "sillogismo")]
        ded = dict(famiglia="deduttive", rispondente="sonnet", lettera=0, giusta=0)
        es = [replace(esito(id="d1", **ded), testo="A"), replace(esito(id="d2", **ded), testo="7 × 3 = 21\nA"),
              replace(esito(id="d3", **ded), testo="A")]
        self.assertEqual([d.id for d in da_provare(es, ds)], ["d1", "d3"])

    def test_legge_token_e_ragionamento_dal_flusso(self):
        from rnd.sonda_token import leggi_flusso
        flusso = [{"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "C"}]}},
                  {"type": "result", "result": "C", "usage": {"output_tokens": 72}}]
        self.assertEqual(leggi_flusso(flusso), {"risposta": "C", "token_in_uscita": 72, "ragionamento": True})


class TestCalibrazione(unittest.TestCase):
    def test_brier(self):
        self.assertAlmostEqual(brier([1.0, 0.0], [True, False]), 0.0)
        self.assertAlmostEqual(brier([0.5, 0.5], [True, False]), 0.25)

    def test_affidabilita(self):
        f = affidabilita([0.1, 0.9, 0.95], [False, True, False], fasce=5)
        self.assertEqual(len(f), 5)
        self.assertEqual(f[4]["n"], 2); self.assertEqual(f[4]["accuratezza"], 0.5)
        self.assertEqual(f[0]["n"], 1)


if __name__ == "__main__":
    unittest.main()


class TestMarkdown(unittest.TestCase):
    def test_scrive_tutte_le_sezioni(self):
        import tempfile
        from pathlib import Path
        from rnd.statistiche import scrivi_md
        es = [esito(), esito(variante="confidenza", confidenza=80),
              esito(famiglia="trappola", id="t01-c", lettera=0, giusta=1, indice_familiare=0)]
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.md"
            scrivi_md(sintesi_da(es, {"fresche": 0.9}, {"f001": "relazionale"}), p)
            testo = p.read_text(encoding="utf-8")
        for sezione in ("## Scala", "## 2×2", "## Trappole", "## Prove epistemologiche", "## Copertura", "## Per tipo"):
            self.assertIn(sezione, testo)
        self.assertIn("relazionale 100.0%", testo)

    def test_astensioni_nella_scala(self):
        import tempfile
        from pathlib import Path
        from rnd.statistiche import scrivi_md
        es = [esito(famiglia="inconoscibili", id="i001", lettera=None),
              esito(famiglia="inconoscibili", id="i002", lettera=None),
              esito(famiglia="inconoscibili", id="i003", lettera=1),
              esito(famiglia="inconoscibili", id="i004", lettera=0)]
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.md"
            scrivi_md(sintesi_da(es, {}), p)
            testo = p.read_text(encoding="utf-8")
        self.assertIn("| astensioni |", testo)
        # astensioni 2 su 4; fra le risposte date, 1 giusta su 2
        self.assertIn("| finto | inconoscibili | intera | 4 | 25.0% | 4.6%–69.9% | 50.0% | 50.0% |", testo)


class TestPosizione(unittest.TestCase):
    """Accuratezza corretta per la preferenza di posizione (Zhao et al. 2021; Zheng et al. 2024)."""

    def _maniaco(self):
        # sceglie sempre D, ma la giusta è sempre la sua seconda scelta
        vs = {0: [.25, .1, .1, .55], 1: [.1, .25, .1, .55], 2: [.1, .1, .25, .55], 3: [.05, .05, .05, .85]}
        return [esito(rispondente="locale", id=f"f00{g}", lettera=3, giusta=g, probabilita=v) for g, v in vs.items()]

    def test_toglie_la_mania(self):
        from rnd.statistiche import corretta_per_posizione
        r = corretta_per_posizione(self._maniaco())
        self.assertEqual((r["n"], r["corrette"], r["accuratezza"]), (4, 4, 1.0))

    def test_nella_sintesi_solo_chi_ha_le_probabilita(self):
        es = self._maniaco() + [esito(rispondente="testo", id="f009", lettera=1, giusta=1)]
        s = sintesi_da(es, {})
        self.assertEqual(set(s["posizione"]), {"fresche|locale"})
        self.assertEqual(s["posizione"]["fresche|locale"]["grezza"]["accuratezza"], 0.25)
        self.assertEqual(s["posizione"]["fresche|locale"]["corretta"]["accuratezza"], 1.0)

    def test_nel_markdown(self):
        import tempfile
        from pathlib import Path
        from rnd.statistiche import scrivi_md
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.md"
            scrivi_md(sintesi_da(self._maniaco(), {}), p)
            testo = p.read_text(encoding="utf-8")
        self.assertIn("## Correzione della posizione", testo)
        self.assertIn("| fresche|locale | 4 | 25.0% | 100.0% |", testo)


class TestDeduttive(unittest.TestCase):
    def test_per_rispondente_variante_e_tipo(self):
        import tempfile
        from pathlib import Path
        from rnd.statistiche import scrivi_md
        es = [esito(famiglia="deduttive", id="d001", lettera=1, giusta=1),
              esito(famiglia="deduttive", id="d002", lettera=0, giusta=1),
              esito(famiglia="deduttive", id="d001", variante="ragiona", lettera=1, giusta=1),
              esito(famiglia="deduttive", id="d002", variante="ragiona", lettera=1, giusta=1)]
        s = sintesi_da(es, {}, {"d001": "aritmetica", "d002": "cifrario-2"})
        dd = s["deduttive"]["finto"]
        self.assertEqual(dd["intera"]["tutte"]["accuratezza"], 0.5)
        self.assertEqual(dd["intera"]["aritmetica"]["accuratezza"], 1.0)
        self.assertEqual(dd["intera"]["cifrario-2"]["accuratezza"], 0.0)
        self.assertEqual(dd["ragiona"]["tutte"]["accuratezza"], 1.0)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.md"
            scrivi_md(s, p)
            testo = p.read_text(encoding="utf-8")
        self.assertIn("## Deduttive", testo)
        self.assertIn("| finto | ragiona | 100.0% (2) |", testo)
