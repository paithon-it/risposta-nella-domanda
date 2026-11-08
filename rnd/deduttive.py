"""Le domande deduttive: la risposta è contenuta per intero nella domanda.

Cinque tipi da 20, generati con il seme: moltiplicazioni a due cifre; parole cifrate con uno
spostamento di 3 (il cifrario di Cesare, frequente nei testi) o di 2 (raro); sillogismi con
parole inventate; gli stessi sillogismi con parole vere e una conclusione contraria al mondo;
ordinamenti per altezza. I sillogismi hanno tutti la stessa forma (Barbara: tutti gli M sono P,
tutti gli S sono M, quindi tutti gli S sono P) e gli stessi distrattori, così neutri e
controintuitivi differiscono solo per il contenuto.
"""

from __future__ import annotations

import random

from rnd.domanda import Domanda
from rnd.prepara import bilancia

N = 20

PAROLE = ("casa", "lupo", "mare", "pane", "sole", "luna", "vino", "neve", "lago", "rete",
          "vento", "fiore", "libro", "notte", "porta", "carta", "gatto", "treno", "monte", "fiume",
          "campo", "bosco", "barca", "ponte", "torre", "sedia", "penna", "tazza", "prato", "fuoco",
          "strada", "albero", "giorno", "scuola", "piazza", "stella", "chiave", "nuvola", "tavolo")

INVENTATE = ("blicchi", "frumi", "tolpi", "mendi", "garbi", "dorvi", "nafti", "ribbi", "cravi", "voddi",
             "melchi", "tarvi", "bonfi", "pelsi", "guddi", "ferni", "lombi", "puvvi", "nercoli", "brami")

# (S, M, P): gli S sono davvero M, e nessuno S è davvero P
CONTRARI = (("gatti", "mammiferi", "verdi"), ("cani", "mammiferi", "trasparenti"), ("salmoni", "pesci", "pelosi"),
            ("passeri", "uccelli", "quadrati"), ("pini", "alberi", "liquidi"), ("limoni", "frutti", "metallici"),
            ("martelli", "attrezzi", "morbidi"), ("violini", "strumenti", "invisibili"), ("tavoli", "mobili", "gassosi"),
            ("treni", "veicoli", "commestibili"), ("cavalli", "quadrupedi", "alati"), ("tulipani", "fiori", "salati"),
            ("diamanti", "minerali", "elastici"), ("squali", "pesci", "vegetariani"), ("delfini", "mammiferi", "terrestri"),
            ("carciofi", "ortaggi", "dolci"), ("coltelli", "utensili", "rotondi"), ("aerei", "veicoli", "subacquei"),
            ("vulcani", "monti", "freddi"), ("orologi", "oggetti", "vivi"))

NOMI = ("Anna", "Bea", "Carla", "Dora", "Elena", "Fiora", "Giulia", "Ilaria", "Laura", "Marta",
        "Nora", "Olga", "Paola", "Rita", "Sara", "Tina")
DOMANDE_ORDINE = ("la più alta", "la seconda più alta", "la seconda più bassa", "la più bassa")
SEGUE = "Che cosa segue necessariamente da queste due premesse?"


def articolo(parola: str) -> str:
    """«i» o «gli» davanti a un nome maschile plurale."""
    s = parola.lower()
    if s[0] in "aeiouxyz" or s[:2] in ("gn", "ps") or (s[0] == "s" and s[1] not in "aeiou"):
        return "gli"
    return "i"


def tutti(s: str, p: str) -> str:
    return f"Tutti {articolo(s)} {s} sono {p}"


def cifra(parola: str, k: int) -> str:
    return "".join(chr((ord(c) - 97 + k) % 26 + 97) for c in parola)


def _aritmetica(i: int, rng: random.Random) -> dict:
    a, b = (rng.choice([n for n in range(13, 98) if n % 10]) for _ in range(2))
    p = a * b
    candidati = [x for x in (p + 10, p - 10, p + 100, p - 100, a * (b + 1), (a + 1) * b) if x > 0 and x != p]
    sbagliate = rng.sample(sorted(set(candidati)), 3)
    return {"testo": f"Quanto fa {a} × {b}?", "giusta": str(p), "sbagliate": [str(x) for x in sbagliate],
            "tipo": "aritmetica"}


def _cifrario(i: int, rng: random.Random, k: int, usate: set[str]) -> dict:
    parola = rng.choice([w for w in PAROLE if w not in usate])
    usate.add(parola)
    sbagliate = rng.sample([w for w in PAROLE if len(w) == len(parola) and w != parola], 3)
    testo = (f"Ogni lettera di una parola italiana è stata spostata in avanti di {k} posizioni nell'alfabeto "
             f"inglese, ricominciando dalla a dopo la z. La parola cifrata è «{cifra(parola, k)}». Qual era la parola?")
    return {"testo": testo, "giusta": parola, "sbagliate": sbagliate, "tipo": "cifrario", "tema": f"spostamento-{k}"}


def _barbara(s: str, m: str, p: str, tipo: str) -> dict:
    testo = f"{tutti(m, p)}. {tutti(s, m)}. {SEGUE}"
    return {"testo": testo, "giusta": tutti(s, p),
            "sbagliate": [f"Alcuni {s} non sono {p}", tutti(m, s), f"Alcuni {m} non sono {p}"], "tipo": tipo}


def _ordinamento(i: int, rng: random.Random) -> dict:
    nomi = rng.sample(NOMI, 4)  # dalla più alta alla più bassa
    frasi = [f"{a} è più alta di {b}." for a, b in zip(nomi, nomi[1:])]
    rng.shuffle(frasi)
    domanda = DOMANDE_ORDINE[i % 4]
    giusta = nomi[DOMANDE_ORDINE.index(domanda)]
    return {"testo": " ".join(frasi) + f" Chi è {domanda}?", "giusta": giusta,
            "sbagliate": [n for n in nomi if n != giusta], "tipo": "ordinamento"}


def genera(seme: int) -> list[Domanda]:
    rng = random.Random(f"{seme}:deduttive")
    usate: set[str] = set()
    fonti = [_aritmetica(i, rng) for i in range(N)]
    fonti += [_cifrario(i, rng, 3 if i < N // 2 else 2, usate) for i in range(N)]
    for i in range(N):
        s, m, p = rng.sample(INVENTATE, 3)
        fonti.append(_barbara(s, m, p, "sillogismo"))
    fonti += [_barbara(s, m, p, "controintuitivo") for s, m, p in CONTRARI[:N]]
    fonti += [_ordinamento(i, rng) for i in range(N)]
    random.Random(f"{seme}:ordine:deduttive").shuffle(fonti)
    for i, f in enumerate(fonti):
        f["id"] = f"d{i + 1:03d}"
    return bilancia(fonti, "deduttive", seme)
