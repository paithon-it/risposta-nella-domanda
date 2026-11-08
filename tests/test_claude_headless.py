"""L'oracolo via Claude Code headless: comando, ambiente ridotto, cartella vuota, sonda."""

import json
import os
import subprocess
import unittest
from unittest import mock

from rnd.claude_headless import SISTEMA, ambiente, comando, esegui, problemi_sonda


class TestComando(unittest.TestCase):
    def test_ambiente_ridotto(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-x", "PAITHON_X": "y"}):
            a = ambiente()
        self.assertEqual(set(a), {"HOME", "USER", "PATH", "LANG"})
        self.assertEqual(a["LANG"], "C.UTF-8")

    def test_comando(self):
        c = comando("ciao")
        self.assertEqual(c[:3], ["claude", "-p", "ciao"])
        self.assertNotIn("--bare", c)
        self.assertEqual(c[c.index("--tools") + 1], "")
        self.assertEqual(c[c.index("--setting-sources") + 1], "")
        self.assertEqual(c[c.index("--system-prompt") + 1], SISTEMA)
        self.assertEqual(c[c.index("--mcp-config") + 1], '{"mcpServers":{}}')
        for opzione in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
            self.assertIn(opzione, c)
        self.assertEqual(c[c.index("--model") + 1], "sonnet")
        self.assertNotIn("--verbose", c)
        self.assertIn("--verbose", comando("ciao", formato="stream-json"))


class TestEsegui(unittest.TestCase):
    def test_cartella_vuota_e_ambiente(self):
        visto = {}

        def registra(args, **kw):
            visto["contenuto_cwd"] = os.listdir(kw["cwd"])
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps({"type": "result", "result": "B", "is_error": False}), stderr="")

        with mock.patch("subprocess.run", side_effect=registra) as run:
            self.assertEqual(esegui("ciao"), "B")
        self.assertEqual(visto["contenuto_cwd"], [])
        self.assertEqual(run.call_args.kwargs["env"], ambiente())
        self.assertEqual(run.call_args.args[0], comando("ciao"))

    def test_errore(self):
        fallito = subprocess.CompletedProcess([], 1, stdout="", stderr="limite raggiunto")
        with mock.patch("subprocess.run", return_value=fallito):
            with self.assertRaisesRegex(RuntimeError, "limite raggiunto"):
                esegui("ciao")


class TestSonda(unittest.TestCase):
    def test_pulita(self):
        self.assertEqual(problemi_sonda({"init": {"tools": [], "mcp_servers": []}, "risposta": "Solo il messaggio di sistema."}), [])

    def test_strumenti(self):
        self.assertTrue(problemi_sonda({"init": {"tools": ["WebSearch"], "mcp_servers": []}, "risposta": ""}))

    def test_nessuna_memoria_non_e_un_problema(self):
        # la domanda della sonda chiede delle memorie: dire che non ce ne sono è la risposta pulita
        r = "Documenti: nessuno. Nessuna memoria salvata fra le conversazioni. Strumenti: nessuno."
        self.assertEqual(problemi_sonda({"init": {"tools": [], "mcp_servers": []}, "risposta": r}), [])

    def test_memoria_dell_utente_ereditata(self):
        r = "Ho ricevuto il file MEMORY.md con le memorie dell'utente."
        self.assertTrue(problemi_sonda({"init": {"tools": [], "mcp_servers": []}, "risposta": r}))

    def test_contesto_ereditato(self):
        self.assertTrue(problemi_sonda({"init": {"tools": [], "mcp_servers": []}, "risposta": "Ho le istruzioni di CLAUDE.md"}))


if __name__ == "__main__":
    unittest.main()


class TestSondaVera(unittest.TestCase):
    """L'evento init registrato dalla prima sonda vera (8/11/2026): i nomi dei campi sono quelli."""

    def test_evento_registrato_pulito(self):
        from pathlib import Path
        init = json.loads((Path(__file__).parent / "fixtures" / "stream-init.json").read_text(encoding="utf-8"))
        self.assertIn("tools", init); self.assertIn("mcp_servers", init)
        self.assertEqual(problemi_sonda({"init": init, "risposta": ""}), [])
        self.assertEqual(init["apiKeySource"], "none")  # il piano di Claude Code, non l'API
