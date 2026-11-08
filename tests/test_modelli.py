"""I modelli locali della scala: nomi, pesi, ordine nella sintesi, ragionamento spento."""

import unittest
from unittest import mock

from rnd import corsa
from rnd.locale import testo_chat
from rnd.statistiche import ORDINE


class TokenizerCheRicorda:
    def apply_chat_template(self, messaggi, **kw):
        self.kw = kw
        return messaggi[0]["content"]


class TestModelli(unittest.TestCase):
    def test_qwen38_27b_quantizzato_con_vllm(self):
        self.assertEqual(corsa.MODELLI_VLLM["qwen3.8-27b"], "cyankiwi/Qwen3.8-27B-AWQ-INT4")
        self.assertEqual(corsa.MODELLI_LOCALI["qwen"], ("Qwen/Qwen2.5-0.5B-Instruct", False))
        self.assertEqual(corsa.MODELLI_LOCALI["qwen-casuale"], ("Qwen/Qwen2.5-0.5B-Instruct", True))
        self.assertIn("qwen3.8-27b", corsa.RISPONDENTI)

    def test_crea_rispondente_passa_nome_e_rispondente(self):
        with mock.patch("rnd.locale.ModelloVLLM") as M:
            corsa.crea_rispondente("qwen3.8-27b")
        M.assert_called_once_with("cyankiwi/Qwen3.8-27B-AWQ-INT4", rispondente="qwen3.8-27b")
        with mock.patch("rnd.locale.ModelloLocale") as M:
            corsa.crea_rispondente("qwen-casuale")
        M.assert_called_once_with("Qwen/Qwen2.5-0.5B-Instruct", pesi_casuali=True, rispondente="qwen-casuale")

    def test_ordine_nella_sintesi(self):
        self.assertLess(ORDINE.index("qwen"), ORDINE.index("qwen3.8-27b"))
        self.assertLess(ORDINE.index("qwen3.8-27b"), ORDINE.index("sonnet"))

    def test_ragionamento_spento(self):
        t = TokenizerCheRicorda()
        self.assertEqual(testo_chat(t, "Domanda?"), "Domanda?")
        self.assertEqual(t.kw, {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False})


class _Lp:
    def __init__(self, v):
        self.logprob = v


class _Uscita:
    def __init__(self, prompt_logprobs=None, testo=""):
        self.prompt_logprobs = prompt_logprobs
        self.outputs = [type("G", (), {"text": testo})()]


class _TokenizerLettere:
    def apply_chat_template(self, messaggi, **kw):
        return "<chat>" + messaggi[0]["content"]

    def encode(self, testo, add_special_tokens=False):
        return [ord(c) for c in testo]


class _MotoreFinto:
    """Logprob di ogni lettera dopo il prompt: A -2, B -0.5, C -3, D -4; testo libero «B»."""
    VALORI = {ord("A"): -2.0, ord("B"): -0.5, ord("C"): -3.0, ord("D"): -4.0}

    def __init__(self):
        self.richieste = []

    def get_tokenizer(self):
        return _TokenizerLettere()

    def generate(self, prompts, parametri, use_tqdm=False):
        self.richieste.append((prompts, parametri))
        if parametri["prompt_logprobs"] is not None:
            return [_Uscita(prompt_logprobs=[None] * (len(p["prompt_token_ids"]) - 1)
                            + [{p["prompt_token_ids"][-1]: _Lp(self.VALORI[p["prompt_token_ids"][-1]])}]) for p in prompts]
        return [_Uscita(testo="B") for _ in prompts]


class TestModelloVLLM(unittest.TestCase):
    def test_probabilita_esatte_delle_lettere(self):
        import math
        from rnd.locale import ModelloVLLM
        motore = _MotoreFinto()
        m = ModelloVLLM("finto", rispondente="finto", llm=motore, parametri=lambda **kw: kw)
        r = m.rispondi("Domanda?", 4)
        attese = [math.exp(v) for v in (-2.0, -0.5, -3.0, -4.0)]
        attese = [x / sum(attese) for x in attese]
        for a, b in zip(r.probabilita, attese):
            self.assertAlmostEqual(a, b, places=6)
        self.assertEqual((r.testo, r.lettera_testo, r.lettera_vincolata), ("B", 1, 1))
        # quattro prompt, uno per lettera, tutti con lo stesso inizio
        prompt_lettere = motore.richieste[0][0]
        self.assertEqual([p["prompt_token_ids"][-1] for p in prompt_lettere], [65, 66, 67, 68])
        self.assertEqual(len({tuple(p["prompt_token_ids"][:-1]) for p in prompt_lettere}), 1)


if __name__ == "__main__":
    unittest.main()
