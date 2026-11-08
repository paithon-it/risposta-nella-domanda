"""Dal testo di una risposta alla lettera scelta e alla confidenza dichiarata."""

from __future__ import annotations

import re

from rnd import LETTERE

_ISOLATA = re.compile(r"(?<![A-Za-zÀ-ÿ])([A-E])(?![A-Za-zÀ-ÿ])")
# La lettera in testa alla risposta («B.», «**D**», «Risposta: C»): vale lei,
# anche se la spiegazione che segue nomina altre lettere («la vitamina C»).
_IN_TESTA = re.compile(r"^[\s*_]*(?:(?i:risposta)\s*:\s*)?[\s*_]*([A-E])(?![A-Za-zÀ-ÿ])")
# …tranne quando la risposta è un'alternativa: «A o B».
_ALTERNATIVA = re.compile(r"^[\s*_).:]*(?:o|oppure|or)\s+[A-E](?![A-Za-zÀ-ÿ])")


def _uniche(riga: str, k: int) -> set[str]:
    return {m for m in _ISOLATA.findall(riga) if m in LETTERE[:k]}


def estrai_lettera(testo: str, k: int) -> int | None:
    """La lettera scelta, come indice; None se manca o se ce n'è più di una.

    Conta la prima riga non vuota (dopo, di solito, viene la spiegazione o la
    confidenza); se lì non c'è nessuna lettera, si guarda tutto il testo.
    """
    righe = [r for r in testo.splitlines() if r.strip()]
    if not righe:
        return None
    m = _IN_TESTA.match(righe[0])
    if m and m.group(1) in LETTERE[:k]:
        if _ALTERNATIVA.match(righe[0][m.end():]):
            return None
        return LETTERE.index(m.group(1))
    trovate = _uniche(righe[0], k)
    if not trovate:
        trovate = _uniche(testo, k)
    if len(trovate) == 1:
        return LETTERE.index(trovate.pop())
    if len(trovate) > 1 and len(righe) > 1:
        # più lettere nominate («nessuna delle opzioni A–D…»): vale una lettera sola sull'ultima riga
        return estrai_lettera_finale(righe[-1], k)
    return None


def estrai_lettera_finale(testo: str, k: int) -> int | None:
    """La lettera dell'ultima riga non vuota, per la variante «ragiona»: prima i passaggi, poi la lettera.

    Il ragionamento può nominare tutte le lettere; conta solo l'ultima riga, e lì una lettera sola.
    """
    righe = [r for r in testo.splitlines() if r.strip()]
    if not righe:
        return None
    ultima = righe[-1]
    m = _IN_TESTA.match(ultima)
    if m and m.group(1) in LETTERE[:k]:
        return None if _ALTERNATIVA.match(ultima[m.end():]) else LETTERE.index(m.group(1))
    trovate = _uniche(ultima, k)
    return LETTERE.index(trovate.pop()) if len(trovate) == 1 else None


def estrai_confidenza(testo: str) -> int | None:
    """Il primo intero dopo la riga della lettera, se sta fra 0 e 100."""
    righe = [r for r in testo.splitlines() if r.strip()]
    for riga in righe[1:]:
        m = re.search(r"\d+", riga)
        if m:
            n = int(m.group())
            return n if 0 <= n <= 100 else None
    return None
