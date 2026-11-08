"""La sintesi dei risultati: accuratezze con intervallo di Wilson, il 2×2, le trappole, le prove epistemologiche."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from rnd.corsa import CARTELLA, Esito, carica_esiti

ORDINE = ("pmi", "pmi-arc", "calcolatore", "qwen-casuale", "qwen", "qwen3.8-27b", "haiku", "sonnet", "opus")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margine = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - margine), min(1.0, centro + margine))


def riassumi(esiti: list[Esito]) -> dict:
    n = len(esiti)
    corrette = sum(1 for e in esiti if e.corretta)
    return {"n": n, "valide": sum(1 for e in esiti if e.lettera is not None), "corrette": corrette,
            "accuratezza": corrette / n if n else 0.0, "ic95": list(wilson(corrette, n))}


def _quota(sì: int, n: int) -> dict:
    return {"n": n, "quota": sì / n if n else 0.0, "ic95": list(wilson(sì, n))}


def brier(p: list[float], esatte: list[bool]) -> float:
    return sum((pi - float(e)) ** 2 for pi, e in zip(p, esatte)) / len(p) if p else 0.0


def affidabilita(conf: list[float], esatte: list[bool], fasce: int = 5) -> list[dict]:
    gruppi: list[list[tuple[float, bool]]] = [[] for _ in range(fasce)]
    for c, e in zip(conf, esatte):
        gruppi[min(int(c * fasce), fasce - 1)].append((c, e))
    return [{"da": i / fasce, "a": (i + 1) / fasce, "n": len(g),
             "conf_media": sum(c for c, _ in g) / len(g) if g else None,
             "accuratezza": sum(e for _, e in g) / len(g) if g else None} for i, g in enumerate(gruppi)]


def corretta_per_posizione(esiti: list[Esito]) -> dict:
    """Accuratezza dopo aver tolto la preferenza di posizione: per ogni numero di opzioni si stima la
    preferenza media del rispondente per ogni lettera (media delle sue probabilità, senza guardare le
    risposte giuste) e si sceglie la lettera con il rapporto più alto fra probabilità e preferenza.
    Funziona perché le posizioni giuste sono bilanciate (Zhao et al. 2021; Zheng et al. 2024)."""
    per_k = defaultdict(list)
    for e in esiti:
        per_k[e.k].append(e)
    corrette = n = 0
    for k, es in per_k.items():
        media = [sum(e.probabilita[i] for e in es) / len(es) for i in range(k)]
        for e in es:
            if e.giusta is None:
                continue
            n += 1
            scelta = max(range(k), key=lambda i: e.probabilita[i] / media[i] if media[i] else 0.0)
            corrette += scelta == e.giusta
    return {"n": n, "corrette": corrette, "accuratezza": corrette / n if n else 0.0, "ic95": list(wilson(corrette, n))}


def _ordinati(nomi) -> list[str]:
    return sorted(nomi, key=lambda r: (ORDINE.index(r) if r in ORDINE else len(ORDINE), r))


def _calibrazione(conf: list[float], esatte: list[bool], fonte: str) -> dict:
    return {"fonte": fonte, "n": len(conf), "brier": brier(conf, esatte), "fasce": affidabilita(conf, esatte)}


def _epistemologia(es: list[Esito]) -> dict:
    per = defaultdict(list)
    for e in es:
        if e.famiglia == "fresche" and e.ripetizione == 0:
            per[e.variante].append(e)
    ep: dict = {}
    for v in ("intera", "mescolata", "senza_giusta"):
        if per[v]:
            ep[v] = riassumi(per[v])
    valide = [e for e in per["con_nessuna"] if e.lettera is not None]
    if per["con_nessuna"]:
        q = _quota(sum(1 for e in valide if e.lettera == e.k - 1), len(valide))
        ep["con_nessuna"] = {"n": q["n"], "quota_nessuna": q["quota"], "ic95": q["ic95"]}
    la = [e for e in per["lettera_a"] if e.giusta != 0 and e.lettera is not None]
    if la:
        ids = {e.id for e in la}
        base = [e for e in per["intera"] if e.id in ids and e.lettera is not None]
        ep["lettera_a"] = {"n": len(la), "quota_a": sum(1 for e in la if e.lettera == 0) / len(la),
                           "ic95": list(wilson(sum(1 for e in la if e.lettera == 0), len(la))),
                           "quota_a_intera": sum(1 for e in base if e.lettera == 0) / len(base) if base else 0.0}
    dichiarate = [e for e in per["confidenza"] if e.confidenza is not None and e.corretta is not None]
    if dichiarate:
        ep["calibrazione"] = _calibrazione([e.confidenza / 100 for e in dichiarate], [e.corretta for e in dichiarate], "dichiarata")
    else:
        prob = [e for e in per["intera"] if e.probabilita and e.corretta is not None]
        if prob:
            ep["calibrazione"] = _calibrazione([max(e.probabilita) for e in prob], [e.corretta for e in prob], "probabilità massima")
    return ep


def sintesi_da(esiti: list[Esito], copertura: dict[str, float], tipi: dict[str, str] | None = None) -> dict:
    per_risp = defaultdict(list)
    for e in esiti:
        per_risp[e.rispondente].append(e)
    nomi = _ordinati(per_risp)
    primi = [e for e in esiti if e.ripetizione == 0]

    scala = [{"rispondente": "caso", "famiglia": "fresche", "variante": "intera", "n": None,
              "accuratezza": 0.25, "ic95": [0.25, 0.25]}]
    gruppi = defaultdict(list)
    for e in primi:
        if e.variante in ("intera", "solo_opzioni"):
            gruppi[(e.rispondente, e.famiglia, e.variante)].append(e)
    for (r, f, v) in sorted(gruppi, key=lambda c: (nomi.index(c[0]), c[1], c[2])):
        scala.append({"rispondente": r, "famiglia": f, "variante": v, **riassumi(gruppi[(r, f, v)])})

    due_per_due = {f"{f}|{r}": riassumi(g) for (r, f, v), g in gruppi.items()
                   if v == "intera" and f in ("fresche", "inconoscibili")}

    trappola = {}
    for r in nomi:
        tr = [e for e in per_risp[r] if e.famiglia == "trappola" and e.variante == "intera" and e.ripetizione == 0]
        if not tr:
            continue
        cambiate = [e for e in tr if e.id.endswith("-c")]
        valide = [e for e in cambiate if e.lettera is not None]
        q = _quota(sum(1 for e in valide if e.lettera == e.indice_familiare), len(valide))
        trappola[r] = {"quota_familiare": q["quota"], "ic95": q["ic95"], "n_valide": q["n"],
                       "familiare": riassumi([e for e in tr if e.id.endswith("-f")]), "cambiata": riassumi(cambiate)}

    stabilita = {}
    for r in nomi:
        rip = defaultdict(dict)
        for e in per_risp[r]:
            rip[(e.famiglia, e.variante, e.id)][e.ripetizione] = e.lettera
        ripetute = [v for v in rip.values() if len(v) > 1]
        if ripetute:
            stabili = sum(1 for v in ripetute if len(set(v.values())) == 1)
            stabilita[r] = {"domande": len(ripetute), "quota_stabili": stabili / len(ripetute)}

    per_tipo = {}
    if tipi:
        for r in nomi:
            g = defaultdict(list)
            for e in per_risp[r]:
                if e.famiglia == "fresche" and e.variante == "intera" and e.ripetizione == 0 and e.id in tipi:
                    g[tipi[e.id]].append(e)
            if g:
                per_tipo[r] = {t: riassumi(v) for t, v in sorted(g.items())}

    deduttive = {}
    for r in nomi:
        g = defaultdict(lambda: defaultdict(list))
        for e in per_risp[r]:
            if e.famiglia == "deduttive" and e.ripetizione == 0:
                g[e.variante]["tutte"].append(e)
                if tipi and e.id in tipi:
                    g[e.variante][tipi[e.id]].append(e)
        if g:
            deduttive[r] = {v: {t: riassumi(gv[t]) for t in ["tutte"] + sorted(set(gv) - {"tutte"})}
                            for v, gv in g.items()}

    epistemologia = {r: ep for r in nomi if (ep := _epistemologia(per_risp[r]))}
    posizione = {f"{f}|{r}": {"grezza": riassumi(g), "corretta": corretta_per_posizione(g)}
                 for (r, f, v), g in sorted(gruppi.items()) if v == "intera" and all(e.probabilita for e in g)}

    return {"scala": scala, "due_per_due": due_per_due, "trappola": trappola, "epistemologia": epistemologia,
            "stabilita": stabilita, "copertura": copertura, "per_tipo": per_tipo, "posizione": posizione,
            "deduttive": deduttive}


def _copertura() -> dict[str, float]:
    from rnd.cooccorrenze import Conteggi, carica_stop, coperta
    from rnd.domanda import carica

    risultato = {}
    for file_conteggi, lingua, famiglie in (("conteggi-it.json", "it", ("fresche",)),
                                            ("conteggi-arc.json", "en", ("arc_easy", "arc_challenge"))):
        p = CARTELLA / "risultati" / file_conteggi
        if not p.exists():
            continue
        c, stop = Conteggi.carica(p), carica_stop(lingua)
        for f in famiglie:
            q = CARTELLA / "domande" / f"{f}.jsonl"
            if q.exists():
                ds = carica(q)
                risultato[f] = sum(coperta(d, c, stop) for d in ds) / len(ds)
    return risultato


def sintesi(cartella: Path) -> dict:
    esiti = [e for p in sorted(cartella.glob("*.jsonl")) for e in carica_esiti(p)]
    tipi = None
    from rnd.domanda import carica
    fresche, deduttive = CARTELLA / "domande" / "fresche.jsonl", CARTELLA / "domande" / "deduttive.jsonl"
    if fresche.exists():
        tipi = {d.id: d.tipo for d in carica(fresche) if d.tipo}
    if deduttive.exists():  # il cifrario si divide per spostamento: 3 (frequente) e 2 (raro)
        tipi = (tipi or {}) | {d.id: f"cifrario-{d.tema.split('-')[1]}" if d.tipo == "cifrario" else d.tipo
                               for d in carica(deduttive) if d.tipo}
    return sintesi_da(esiti, _copertura(), tipi)


TIPI_DEDUTTIVE = ("aritmetica", "cifrario-3", "cifrario-2", "sillogismo", "controintuitivo", "ordinamento")


def _pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def _ic(ic) -> str:
    return f"{_pct(ic[0])}–{_pct(ic[1])}"


def _astensioni(x: dict) -> str:
    """Quota senza lettera e accuratezza fra le risposte date: chi si astiene non sbaglia per forza."""
    if not x.get("n"):
        return "– | –"
    valide = x["valide"]
    return f"{_pct((x['n'] - valide) / x['n'])} | {_pct(x['corrette'] / valide) if valide else '–'}"


def scrivi_md(s: dict, p: Path) -> None:
    r = ["# Sintesi", "", "## Scala", "",
         "| rispondente | famiglia | variante | n | accuratezza | IC 95% | astensioni | acc. fra le risposte |",
         "|---|---|---|---|---|---|---|---|"]
    r += [f"| {x['rispondente']} | {x['famiglia']} | {x['variante']} | {x['n'] if x['n'] is not None else '–'} | "
          f"{_pct(x['accuratezza'])} | {_ic(x['ic95'])} | {_astensioni(x)} |" for x in s["scala"]]
    r += ["", "## 2×2 (variante intera)", "", "| famiglia · rispondente | n | accuratezza | IC 95% |", "|---|---|---|---|"]
    r += [f"| {k} | {v['n']} | {_pct(v['accuratezza'])} | {_ic(v['ic95'])} |" for k, v in sorted(s["due_per_due"].items())]
    r += ["", "## Trappole", "", "| rispondente | segue la familiare | IC 95% | n | acc. familiare | acc. cambiata |", "|---|---|---|---|---|---|"]
    r += [f"| {k} | {_pct(v['quota_familiare'])} | {_ic(v['ic95'])} | {v['n_valide']} | {_pct(v['familiare']['accuratezza'])} | "
          f"{_pct(v['cambiata']['accuratezza'])} |" for k, v in s["trappola"].items()]
    r += ["", "## Prove epistemologiche (fresche)", ""]
    for k, ep in s["epistemologia"].items():
        r.append(f"### {k}")
        for nome, v in ep.items():
            if nome == "calibrazione":
                r.append(f"- calibrazione ({v['fonte']}): Brier {v['brier']:.3f} su {v['n']}")
            elif "quota_nessuna" in v:
                r.append(f"- con_nessuna: sceglie «Nessuna» a torto {_pct(v['quota_nessuna'])} ({_ic(v['ic95'])}, n={v['n']})")
            elif "quota_a" in v:
                r.append(f"- lettera_a: risponde A {_pct(v['quota_a'])} ({_ic(v['ic95'])}, n={v['n']}) contro {_pct(v['quota_a_intera'])} senza esempi")
            else:
                r.append(f"- {nome}: {_pct(v['accuratezza'])} ({_ic(v['ic95'])}, n={v['n']})")
        r.append("")
    r += ["## Stabilità (ripetizioni)", ""]
    r += [f"- {k}: {_pct(v['quota_stabili'])} di {v['domande']} domande con la stessa lettera" for k, v in s["stabilita"].items()]
    r += ["", "## Correzione della posizione (modelli locali, variante intera)", "",
          "| famiglia · rispondente | n | grezza | corretta | IC 95% corretta |", "|---|---|---|---|---|"]
    r += [f"| {k} | {v['grezza']['n']} | {_pct(v['grezza']['accuratezza'])} | {_pct(v['corretta']['accuratezza'])} | "
          f"{_ic(v['corretta']['ic95'])} |" for k, v in s.get("posizione", {}).items()]
    r += ["", "## Copertura del corpus", ""]
    r += [f"- {k}: {_pct(v)}" for k, v in s["copertura"].items()]
    r += ["", "## Per tipo (fresche, intera)", ""]
    for k, v in s["per_tipo"].items():
        r.append(f"- {k}: " + ", ".join(f"{t} {_pct(x['accuratezza'])} (n={x['n']})" for t, x in v.items()))
    r += ["", "## Deduttive", "", "accuratezza (n) per rispondente, variante e tipo", "",
          "| rispondente | variante | tutte | " + " | ".join(TIPI_DEDUTTIVE) + " |",
          "|---|---|---|" + "---|" * len(TIPI_DEDUTTIVE)]
    for rispondente, vv in s.get("deduttive", {}).items():
        for v in sorted(vv, key=lambda v: ("intera", "solo_opzioni", "ragiona").index(v) if v in ("intera", "solo_opzioni", "ragiona") else 9):
            celle = [f"{_pct(vv[v][t]['accuratezza'])} ({vv[v][t]['n']})" if t in vv[v] else "–" for t in ("tutte",) + TIPI_DEDUTTIVE]
            r.append(f"| {rispondente} | {v} | " + " | ".join(celle) + " |")
    p.write_text("\n".join(r) + "\n", encoding="utf-8")


if __name__ == "__main__":
    s = sintesi(CARTELLA / "risultati")
    (CARTELLA / "risultati" / "sintesi.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    scrivi_md(s, CARTELLA / "risultati" / "sintesi.md")
