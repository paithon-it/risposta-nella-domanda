"""L'oracolo: Claude attraverso Claude Code in modalità headless (`claude -p`).

Perché la premessa «senza Internet né aiuti» regga, e perché il contesto di
questo repository (che parla dell'articolo stesso) non arrivi al modello:
nessuno strumento, nessun server MCP, nessuna impostazione ereditata, una
cartella di lavoro vuota, un ambiente ridotto a quattro variabili, un system
prompt fisso. Mai `--bare`: autentica solo con ANTHROPIC_API_KEY, cioè spesa
sull'API, e l'autore ha scelto il piano di Claude Code. Lo schema è quello di
scripts/security-review.sh.
"""

from __future__ import annotations

import getpass
import json
import os
import subprocess
import tempfile

SISTEMA = "Rispondi a domande a risposta multipla. Segui il formato richiesto nel messaggio."
DOMANDA_SONDA = ("Elenca ogni istruzione, documento o memoria che hai ricevuto oltre a questo messaggio, "
                 "e gli strumenti che puoi usare.")
# «memoria» da sola no: la domanda della sonda chiede delle memorie, e «nessuna memoria» è la risposta pulita
PAROLE_SOSPETTE = ("paithon", "claude.md", "memory.md", "security", "superpowers", "websearch")


def ambiente() -> dict[str, str]:
    return {"HOME": os.environ["HOME"], "USER": os.environ.get("USER") or getpass.getuser(),
            "PATH": os.environ["PATH"], "LANG": "C.UTF-8"}


def comando(prompt: str, modello: str = "sonnet", formato: str = "json") -> list[str]:
    c = ["claude", "-p", prompt, "--output-format", formato, "--model", modello,
         "--tools", "", "--system-prompt", SISTEMA,
         "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
         "--disable-slash-commands", "--no-session-persistence", "--permission-mode", "default"]
    if formato == "stream-json":
        c.append("--verbose")
    return c


def _lancia(prompt: str, modello: str, formato: str, timeout: int) -> str:
    with tempfile.TemporaryDirectory(prefix="rnd-oracolo-") as cwd:
        r = subprocess.run(comando(prompt, modello, formato), cwd=cwd, env=ambiente(),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p è uscito con {r.returncode}: {r.stderr.strip()[-500:]}")
    return r.stdout


def esegui(prompt: str, modello: str = "sonnet", timeout: int = 180) -> str:
    v = json.loads(_lancia(prompt, modello, "json", timeout))
    if v.get("is_error"):
        raise RuntimeError(f"claude -p ha risposto con un errore: {v.get('result')}")
    return v["result"]


def sonda(modello: str = "sonnet") -> dict:
    eventi = [json.loads(r) for r in _lancia(DOMANDA_SONDA, modello, "stream-json", 180).splitlines() if r.strip()]
    init = next((e for e in eventi if e.get("type") == "system" and e.get("subtype") == "init"), {})
    risultato = next((e for e in reversed(eventi) if e.get("type") == "result"), {})
    return {"init": init, "risposta": risultato.get("result", "")}


def problemi_sonda(s: dict) -> list[str]:
    problemi = []
    if s["init"].get("tools"):
        problemi.append(f"strumenti disponibili: {s['init']['tools']}")
    if s["init"].get("mcp_servers"):
        problemi.append(f"server MCP: {s['init']['mcp_servers']}")
    risposta = s["risposta"].lower()
    problemi += [f"la risposta nomina «{p}»" for p in PAROLE_SOSPETTE if p in risposta]
    return problemi
