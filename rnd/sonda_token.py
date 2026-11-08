"""Dietro la sola lettera c'è un ragionamento nascosto?

Si richiedono a Claude le deduttive a cui aveva risposto con la sola lettera, e
si legge quanti token ha prodotto e se c'è un blocco di ragionamento. Non è una
seconda corsa: il modello può rispondere diversamente, e ciò che interessa è
il conteggio dei token.

    python3 -m rnd.sonda_token
"""

from __future__ import annotations

import json

from rnd.claude_headless import _lancia
from rnd.corsa import CARTELLA, carica_esiti
from rnd.domanda import carica
from rnd.statistiche import _SOLA_LETTERA
from rnd.varianti import prompt


def da_provare(esiti, domande) -> list:
    per_id = {d.id: d for d in domande}
    return [per_id[e.id] for e in esiti
            if e.famiglia == "deduttive" and e.variante == "intera" and e.ripetizione == 0
            and e.id in per_id and e.testo is not None and _SOLA_LETTERA.fullmatch(e.testo)]


def leggi_flusso(eventi: list[dict]) -> dict:
    blocchi = [b.get("type") for e in eventi if e.get("type") == "assistant" for b in e["message"].get("content", [])]
    fine = [e for e in eventi if e.get("type") == "result"][-1]
    return {"risposta": fine.get("result"), "token_in_uscita": fine["usage"]["output_tokens"], "ragionamento": "thinking" in blocchi}


if __name__ == "__main__":
    esiti = carica_esiti(CARTELLA / "risultati" / "sonnet.jsonl")
    righe = []
    for d in da_provare(esiti, carica(CARTELLA / "domande" / "deduttive.jsonl")):
        testo = _lancia(prompt(d, "intera"), "sonnet", "stream-json", 180)
        righe.append({"id": d.id, "tipo": d.tipo, **leggi_flusso([json.loads(r) for r in testo.splitlines() if r.strip()])})
    (CARTELLA / "risultati" / "sonda-token.json").write_text(json.dumps(righe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
