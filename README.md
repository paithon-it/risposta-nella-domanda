# La risposta è nella domanda?

Codice, domande e risposte dell'esperimento dietro l'articolo di paithon.it
[«La risposta è nella domanda?»](https://paithon.it/la-risposta-e-nella-domanda/):
quando un modello linguistico risponde giusto a un quiz a risposta multipla
che non ha mai visto, da dove arriva la risposta? Dalla domanda, dai pesi del
modello o dal calcolo?

Una scala di rispondenti sulle stesse domande: il caso; un solutore che pesa
le parole (PMI su Wikipedia in italiano); Qwen2.5-0.5B con i pesi a caso e
addestrato; Qwen3.8 27B quantizzato a 4 bit, su una GPU; Claude Sonnet 5.5
senza strumenti né memoria; per le domande deduttive, un calcolatore che fa il
conto. Domande: 200 nuove in italiano, 50 coppie trappola, 100 inconoscibili,
100 deduttive, più 400 di ARC.

*English summary: code, questions and all model answers for paithon.it's
article on whether the answer to a multiple-choice question is "in the
question". A word co-occurrence solver, Qwen models from 0.5B (with random and
trained weights) to 27B, Claude Sonnet 5.5 and a symbolic calculator answer the
same fresh Italian questions; see `risultati/sintesi.md`.*

## Come citare

paithon.it (2026). *La risposta è nella domanda?* Esperimento e dati.
https://github.com/paithon-it/risposta-nella-domanda

## Test

```bash
python3 -m unittest discover -s tests -v
```

I test di unità non usano la rete; quelli che scaricano modelli partono solo
con `RND_INTEGRAZIONE=1`.

## Il modello piccolo (Qwen2.5 0,5B)

`Qwen/Qwen2.5-0.5B-Instruct` in bfloat16 su CPU (4 core): circa 10 s per
caricarlo, 2,8 s a domanda (scelta vincolata più 8 token di testo libero),
1,7 GB di memoria al massimo. Il gemello a pesi casuali (stessa
configurazione, `torch.manual_seed(20261107)`) va a 1,4 s a domanda e scrive
testo senza senso: per questo la risposta dei modelli locali è la scelta
vincolata fra le lettere, non il testo (misurato l'8/11/2026).

## Il modello grande (Qwen3.8 27B)

Il gradino fra Qwen 0,5B e Claude è **Qwen3.8 27B**, l'8/11/2026 su una GPU
NVIDIA L4 da 24 GB. I pesi originali (`Qwen/Qwen3.8-27B`, 56 GB in bf16, 31 in
FP8) non ci stanno: si usa la quantizzazione a 4 bit
`cyankiwi/Qwen3.8-27B-AWQ-INT4` (21 GB, formato compressed-tensors), fatta da
terzi. La legge compressa vLLM (`ModelloVLLM` in `rnd/locale.py`); transformers
proverebbe a decomprimerla in bf16.

Risponde come gli altri modelli open: scelta vincolata fra le lettere, con la
probabilità esatta di ciascuna lettera dopo il prompt (`prompt_logprobs` di
vLLM), più 8 token di testo libero. Il ragionamento che Qwen3.8 ha acceso di
serie è spento (`enable_thinking=False`). Caricamento in circa 100 s, poi meno
di un secondo a domanda: 1800 risposte in 26 minuti. Passi e script in `gpu/`.

Risultati principali (`risultati/sintesi.md`): 95,5% sulle domande fresche,
40,5% con le sole opzioni, 79% sulle deduttive (100% sui sillogismi, 75% sulle
moltiplicazioni, 50% sul cifrario con spostamento 3 e 10% con spostamento 2),
6% di risposte familiari nelle versioni cambiate delle trappole.

## L'oracolo (Claude via Claude Code)

`rnd/claude_headless.py` lancia `claude -p` senza strumenti, senza server
MCP, senza impostazioni ereditate, in una cartella vuota e con un ambiente di
quattro variabili. La sonda dell'8/11/2026 (`risultati/sonda.json`, email
dell'utente oscurata) mostra: nessuno strumento, nessuna skill, nessun
comando, solo i plugin interni di Claude Code, autenticazione dal piano
(`apiKeySource: none`), modello `claude-sonnet-5-5`. Il modello dichiara di
aver ricevuto solo il system prompt, l'ambiente (cartella, data, modello) e
l'email dell'utente che Claude Code allega da sé: niente che riguardi
l'articolo. La corsa rifà la sonda ogni volta e si ferma se compaiono strumenti, server MCP o parole sospette nella risposta.

Claude Code non spegne il ragionamento nascosto del modello.
`python3 -m rnd.sonda_token` rifà le 66 deduttive a cui Claude aveva risposto
con la sola lettera e registra token e blocchi di ragionamento
(`risultati/sonda-token.json`): 57 risposte da tre token, due cifrari con un
blocco di ragionamento (54 e 72 token), sette volte il conto scritto. I gruppi
sono in `risultati/sintesi.md`, «Deduttive secondo come ha risposto Claude».

## Corpora e conteggi

- **ARC** (AI2 Reasoning Challenge, Clark et al. 2018): archivio originale di
  AI2, `https://ai2-public-datasets.s3.amazonaws.com/arc/ARC-V1-Feb2018.zip`
  (680 MB), licenza CC BY-SA 4.0. Si usano le domande di test a quattro
  opzioni (campione di 200 Easy e 200 Challenge, seme 20261107) e l'ARC
  Corpus (14 milioni di frasi di argomento scientifico, 137 milioni di parole
  piene). I file in `domande/arc_*.jsonl` restano sotto CC BY-SA 4.0.
  `python3 -m rnd.scarica arc` (48 s) e `conta-arc` (49 s, 4 processi).
  Copertura: 99,5% delle Easy e 96,5% delle Challenge hanno almeno una volta
  la risposta giusta vicino a una parola della domanda. Il solutore di
  co-occorrenze rifà la divisione del 2018: **61%** sulle Easy, **22,5%**
  sulle Challenge (come il caso: le Challenge sono proprio le domande che i
  solutori di questo tipo sbagliavano).
- **Wikipedia in italiano**: `wikimedia/wikipedia`, configurazione
  `20231101.it`, 10 file parquet (2,8 GB), licenza CC BY-SA 4.0.
  `python3 -m rnd.scarica conta-it` (97 s, 435 milioni di parole piene).
  Copertura delle domande fresche: 92,5%. Le inconoscibili risultano
  «coperte» al 35%: le parole d'ordine casuali a volte sono parole vere, e il
  solutore trova legami anche dove non ce ne sono.

I file scaricati stanno in `dati/` (non versionata); i conteggi, piccoli, in
`risultati/conteggi-*.json`.

## Come si rifà tutto

Requisiti: Python 3.12, le librerie di `requirements.txt`, e per l'oracolo
Claude Code con un abbonamento (`claude -p`; mai `--bare`, che passa
all'API a consumo). In ordine:

```bash
python3 -m rnd.prepara                 # domande da sorgente/, inconoscibili generate col seme
python3 -m rnd.scarica arc             # ARC: domande e corpus (680 MB)
python3 -m rnd.scarica conta-arc       # conteggi sul corpus di ARC
python3 -m rnd.scarica conta-it        # Wikipedia in italiano (2,8 GB) e conteggi
```

Poi la corsa, un rispondente alla volta (ogni comando riprende da dove si è
fermato, senza rifare niente):

```bash
EPI=intera,solo_opzioni,mescolata,con_nessuna,senza_giusta,lettera_a
python3 -m rnd.corsa --rispondente pmi --famiglie fresche,inconoscibili,trappola --varianti intera,solo_opzioni
python3 -m rnd.corsa --rispondente pmi-arc --famiglie arc_easy,arc_challenge --varianti intera
python3 -m rnd.corsa --rispondente qwen --famiglie fresche,inconoscibili,trappola --varianti $EPI
python3 -m rnd.corsa --rispondente qwen-casuale --famiglie fresche,inconoscibili,trappola --varianti $EPI
python3 -m rnd.corsa --rispondente sonnet --famiglie fresche --varianti $EPI,confidenza --pausa 5
python3 -m rnd.corsa --rispondente sonnet --famiglie inconoscibili,trappola --varianti intera --pausa 5
python3 -m rnd.corsa --rispondente sonnet --famiglie fresche --varianti intera --limite 30 --ripetizioni 3 --pausa 5
# le deduttive
python3 -m rnd.corsa --rispondente pmi --famiglie deduttive --varianti intera,solo_opzioni
python3 -m rnd.corsa --rispondente calcolatore --famiglie deduttive --varianti intera,solo_opzioni
python3 -m rnd.corsa --rispondente sonnet --famiglie deduttive --varianti intera,solo_opzioni,ragiona --pausa 5
python3 -m rnd.corsa --rispondente qwen --famiglie deduttive --varianti intera,solo_opzioni
python3 -m rnd.corsa --rispondente qwen-casuale --famiglie deduttive --varianti intera,solo_opzioni
# il modello grande, sulla GPU: gpu/README.md (gpu/prepara.sh, poi gpu/corsa.sh)
python3 -m rnd.statistiche             # risultati/sintesi.json e sintesi.md
```

Il modello grande (Qwen3.8 27B) gira su una GPU a ore: passi e script in
`gpu/README.md`.

Sulle famiglie diverse dalle fresche girano solo `intera` e `solo_opzioni`, più
`ragiona` sulle deduttive. Se cambiano le regole di lettura della lettera, le
risposte salvate si rileggono senza nuove chiamate:
`python3 -c "from rnd.corsa import rileggi; from pathlib import Path; [print(p, rileggi(p)) for p in Path('risultati').glob('*.jsonl')]"`.

## La corsa dell'8/11/2026

Su una VPS da 4 core e 8 GB, senza GPU, con la memoria quasi piena (il
modello locale andava in swap, i tempi sono quindi pessimistici):

| Giro | Risposte | Tempo |
|---|---|---|
| `pmi`, tutte le famiglie | 800 | meno di un secondo |
| `pmi-arc` | 400 | meno di un secondo |
| `qwen` | 1600 | 58 minuti |
| `qwen-casuale` | 1600 | circa 25 minuti |
| `sonnet` | 1660 | 3 ore e mezza (5 s di pausa fra le chiamate) |
| `qwen3.8-27b` | 1800 | 26 minuti su una GPU L4 (vedi `gpu/README.md`) |

Una chiamata di Claude costa circa 700 token in ingresso e 3 in uscita, senza
ragionamento esteso. I due rami (modelli locali e Claude) sono girati in
parallelo; il sistema ha fermato una volta il ramo locale per la memoria, e la
corsa ha ripreso da dove si era fermata. Ogni casella della matrice ha il
numero di risposte atteso, senza doppioni.

Le deduttive sono girate dopo, lo stesso giorno: 100 domande per rispondente e
variante, Claude in 40 minuti (300 chiamate), i due Qwen in 2 minuti ciascuno.
La revisione finale del codice ha trovato due difetti, corretti prima di
pubblicare i numeri: una risposta di Claude con la lettera sull'ultima riga
(f057) contata come astensione, e i pareggi esatti delle probabilità dei Qwen
(logit in bfloat16) assegnati sempre alla lettera più bassa invece che a caso.
Le risposte sono state rilette con `rileggi`, senza nuove chiamate.

Quota di risposte con una lettera leggibile nel testo, deduttive comprese:
`qwen` 96,3% su 1800, `sonnet` 96,6% su 1960 (le 66 senza lettera sono tutte
astensioni sulle domande inconoscibili), `qwen-casuale` 0,2% (scrive testo
senza senso: per i modelli locali conta la scelta vincolata).

## Le domande

Le 200 domande fresche, le 50 coppie trappola e i 3 esempi li ha scritti
Claude Opus 5.5 nella notte fra il 7 e l'8/11/2026; l'autore li ha approvati senza correzioni l'8/11
(`revisione.md`). Le 100 domande inconoscibili e le 100 deduttive le genera
`rnd.prepara` con il seme 20261107. Le deduttive sono cinque tipi da 20
(`rnd/deduttive.py`): moltiplicazioni a due cifre, parole cifrate con
spostamento 3 o 2, sillogismi con parole inventate, gli stessi con parole vere
e conclusione contraria al mondo, ordinamenti. Il calcolatore
(`rnd/calcolatore.py`) le risolve tutte leggendo il testo. Limite noto: nelle
moltiplicazioni i distrattori stanno attorno al risultato (±10, ±100, o un
fattore aumentato di uno), e in 18 casi su 20 la giusta sta fra i due numeri
di mezzo.

## Licenze

- Codice (`rnd/`, `tests/`, `gpu/`): licenza MIT, vedi `LICENSE`.
- Dati (domande, risposte, conteggi in `domande/`, `sorgente/`, `risultati/`):
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.it), la
  licenza di ARC e di Wikipedia da cui derivano in parte.
- Il testo dell'articolo, su paithon.it: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.it).
