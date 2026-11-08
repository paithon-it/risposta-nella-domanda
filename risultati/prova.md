# Prova sul campione

25 fresche, 10 inconoscibili, 10 coppie trappola, 25 + 25 ARC; Claude con 5 s di pausa fra le chiamate.
Numeri piccoli: servono a vedere che tutto funziona e quanto costa, non a concludere.

## Che cosa dice la prova

**Controlli dello spec: superati, nessun guasto tecnico.**
- `qwen` sulle fresche sta sopra il caso: 52% (IC 33,5–70%).
- Il solutore di parole copre il 92,5% delle fresche.
- La sonda di Claude è pulita a ogni giro: nessuno strumento, nessun server MCP.

**Una lacuna corretta.** La corsa non conservava il testo delle risposte. Ora lo
conserva (campo `testo`). Le 11 risposte di Claude senza lettera sono state
rifatte per poterle leggere.

**Costo di Claude.** Una chiamata vale circa 700 token in ingresso e 3 in uscita
(0,003 dollari a prezzo di API; sul piano non si paga a parte), senza
ragionamento esteso. La corsa completa sono 1660 chiamate, circa 3,4 ore e 1,2
milioni di token in ingresso: basta una sessione, non serve dividerla su più giorni.

**Osservazioni.** Sono risultati, non guasti, e su numeri piccoli.
1. **Claude si astiene sulle inconoscibili.** In 7 casi su 10 risponde «non ho
   modo di saperlo, qualsiasi lettera sarebbe una scelta a caso». In 2 tira a
   indovinare e lo dice, in 1 scrive solo «B». La sintesi ora ha la colonna
   «astensioni».
2. **Claude fa il 100% su fresche e trappole.** Per lui queste domande sono
   facili, quindi l'informazione utile è quanto gli resta senza la domanda:
   con le sole opzioni arriva al **56%**, molto sopra il caso. Le opzioni da
   sole dicono parecchio. È un dato per l'articolo e un limite delle domande
   da dichiarare.
3. **Il gemello a pesi casuali sceglie quasi sempre la stessa lettera** (E nel
   94% dei casi con cinque opzioni). Il suo 88% su «senza la giusta» viene
   dalla posizione, non da un'abilità.
4. **`qwen` non sceglie quasi mai la D** (1%). E se gli esempi hanno sempre la
   giusta in A, risponde A nel 100% dei casi (11% senza esempi). Claude, con
   gli stessi esempi, non cede (0%).
5. **Trappole.** Il solutore di parole segue la risposta familiare nel 40%
   delle versioni cambiate, `qwen` nel 50%, Claude mai.

**Proposta per la corsa completa.** Matrice invariata. Claude in una sessione
sola, con 5 s di pausa. Per i modelli locali, accanto all'accuratezza grezza,
un'accuratezza corretta per la preferenza di posizione, calcolata dalle
probabilità già salvate: nessuna chiamata in più.

## Esiti raccolti e formato delle risposte

| rispondente | esiti | lettera nel testo | nessuna lettera |
|---|---|---|---|
| pmi-arc | 50 | (sceglie per indice) | 0 |
| pmi | 110 | (sceglie per indice) | 0 |
| qwen-casuale | 210 | 0 (0.0%) | 0 |
| qwen | 210 | 200 (95.2%) | 0 |
| sonnet | 225 | 218 (96.9%) | 7 |

Per `qwen` e `qwen-casuale` conta la scelta vincolata fra le lettere; la colonna del testo dice
solo quante volte il testo libero conteneva anche una lettera leggibile.

## Quale lettera sceglie

Quota di ogni lettera fra le risposte, per numero di opzioni. Le posizioni giuste sono bilanciate:
chi non ha preferenze di posizione sta vicino al 25% con quattro opzioni e al 20% con cinque.

| rispondente | opzioni | n | A | B | C | D | E |
|---|---|---|---|---|---|---|---|
| pmi-arc | 4 | 50 | 12% | 22% | 36% | 30% |  |
| pmi | 4 | 110 | 24% | 25% | 30% | 22% |  |
| qwen-casuale | 4 | 160 | 27% | 24% | 2% | 48% |  |
| qwen-casuale | 5 | 50 | 4% | 0% | 0% | 2% | 94% |
| qwen | 4 | 160 | 38% | 21% | 40% | 1% |  |
| qwen | 5 | 50 | 20% | 26% | 52% | 0% | 2% |
| sonnet | 4 | 168 | 26% | 30% | 27% | 17% |  |
| sonnet | 5 | 50 | 14% | 14% | 18% | 6% | 48% |

## Claude: tempi e stima della corsa completa

- 225 chiamate: mediana **2.3 s**, media 2.5 s, minimo 2.1 s, massimo 4.8 s (pausa esclusa).
- Chiamate della corsa completa: fresche × 7 varianti 1400, inconoscibili 100, trappola 100, ripetute (30 id × 2 in più) 60, in tutto **1660**.
- Con 5 s di pausa: circa **3.4 ore** di orologio in serie.

| variante | chiamate | mediana s |
|---|---|---|
| con_nessuna | 25 | 2.2 |
| confidenza | 25 | 2.3 |
| intera | 75 | 2.3 |
| lettera_a | 25 | 2.6 |
| mescolata | 25 | 2.2 |
| senza_giusta | 25 | 2.3 |
| solo_opzioni | 25 | 2.3 |

## Tempi e memoria per invocazione

| giro | secondi | memoria max | uscita |
|---|---|---|---|
| pmi-fresche | 0 | 18 MB | 0 |
| pmi-inconoscibili | 0 | 18 MB | 0 |
| pmi-trappola | 0 | 18 MB | 0 |
| qwen-fresche | 114 | 1866 MB | 0 |
| qwen-inconoscibili | 19 | 1688 MB | 0 |
| qwen-trappola | 32 | 1724 MB | 0 |
| qwen-casuale-fresche | 198 | 1866 MB | 0 |
| qwen-casuale-inconoscibili | 30 | 1834 MB | 0 |
| qwen-casuale-trappola | 39 | 1834 MB | 0 |
| pmi-arc | 0 | 26 MB | 0 |
| sonnet-fresche | 1300 | 334 MB | 0 |
| sonnet-inconoscibili | 99 | 326 MB | 0 |
| sonnet-trappola | 156 | 328 MB | 0 |
| sonnet-ripetute | 152 | 328 MB | 0 |

- `qwen`: mediana 0.59 s a domanda su 210.
- `qwen-casuale`: mediana 0.72 s a domanda su 210.

## Sintesi della prova

### Scala

| rispondente | famiglia | variante | n | accuratezza | IC 95% | astensioni | acc. fra le risposte |
|---|---|---|---|---|---|---|---|
| caso | fresche | intera | – | 25.0% | 25.0%–25.0% | – | – |
| pmi | fresche | intera | 25 | 64.0% | 44.5%–79.8% | 0.0% | 64.0% |
| pmi | fresche | solo_opzioni | 25 | 24.0% | 11.5%–43.4% | 0.0% | 24.0% |
| pmi | inconoscibili | intera | 10 | 10.0% | 1.8%–40.4% | 0.0% | 10.0% |
| pmi | inconoscibili | solo_opzioni | 10 | 10.0% | 1.8%–40.4% | 0.0% | 10.0% |
| pmi | trappola | intera | 20 | 30.0% | 14.5%–51.9% | 0.0% | 30.0% |
| pmi | trappola | solo_opzioni | 20 | 35.0% | 18.1%–56.7% | 0.0% | 35.0% |
| pmi-arc | arc_challenge | intera | 25 | 36.0% | 20.2%–55.5% | 0.0% | 36.0% |
| pmi-arc | arc_easy | intera | 25 | 60.0% | 40.7%–76.6% | 0.0% | 60.0% |
| qwen-casuale | fresche | intera | 25 | 16.0% | 6.4%–34.7% | 0.0% | 16.0% |
| qwen-casuale | fresche | solo_opzioni | 25 | 32.0% | 17.2%–51.6% | 0.0% | 32.0% |
| qwen-casuale | inconoscibili | intera | 10 | 20.0% | 5.7%–51.0% | 0.0% | 20.0% |
| qwen-casuale | inconoscibili | solo_opzioni | 10 | 20.0% | 5.7%–51.0% | 0.0% | 20.0% |
| qwen-casuale | trappola | intera | 20 | 25.0% | 11.2%–46.9% | 0.0% | 25.0% |
| qwen-casuale | trappola | solo_opzioni | 20 | 25.0% | 11.2%–46.9% | 0.0% | 25.0% |
| qwen | fresche | intera | 25 | 52.0% | 33.5%–70.0% | 0.0% | 52.0% |
| qwen | fresche | solo_opzioni | 25 | 28.0% | 14.3%–47.6% | 0.0% | 28.0% |
| qwen | inconoscibili | intera | 10 | 0.0% | 0.0%–27.8% | 0.0% | 0.0% |
| qwen | inconoscibili | solo_opzioni | 10 | 30.0% | 10.8%–60.3% | 0.0% | 30.0% |
| qwen | trappola | intera | 20 | 20.0% | 8.1%–41.6% | 0.0% | 20.0% |
| qwen | trappola | solo_opzioni | 20 | 25.0% | 11.2%–46.9% | 0.0% | 25.0% |
| sonnet | fresche | intera | 25 | 100.0% | 86.7%–100.0% | 0.0% | 100.0% |
| sonnet | fresche | solo_opzioni | 25 | 56.0% | 37.1%–73.3% | 0.0% | 56.0% |
| sonnet | inconoscibili | intera | 10 | 10.0% | 1.8%–40.4% | 70.0% | 33.3% |
| sonnet | trappola | intera | 20 | 100.0% | 83.9%–100.0% | 0.0% | 100.0% |

### 2×2 (variante intera)

| famiglia · rispondente | n | accuratezza | IC 95% |
|---|---|---|---|
| fresche|pmi | 25 | 64.0% | 44.5%–79.8% |
| fresche|qwen | 25 | 52.0% | 33.5%–70.0% |
| fresche|qwen-casuale | 25 | 16.0% | 6.4%–34.7% |
| fresche|sonnet | 25 | 100.0% | 86.7%–100.0% |
| inconoscibili|pmi | 10 | 10.0% | 1.8%–40.4% |
| inconoscibili|qwen | 10 | 0.0% | 0.0%–27.8% |
| inconoscibili|qwen-casuale | 10 | 20.0% | 5.7%–51.0% |
| inconoscibili|sonnet | 10 | 10.0% | 1.8%–40.4% |

### Trappole

| rispondente | segue la familiare | IC 95% | n | acc. familiare | acc. cambiata |
|---|---|---|---|---|---|
| pmi | 40.0% | 16.8%–68.7% | 10 | 40.0% | 20.0% |
| qwen-casuale | 20.0% | 5.7%–51.0% | 10 | 30.0% | 20.0% |
| qwen | 50.0% | 23.7%–76.3% | 10 | 30.0% | 10.0% |
| sonnet | 0.0% | 0.0%–27.8% | 10 | 100.0% | 100.0% |

### Prove epistemologiche (fresche)

### pmi
- intera: 64.0% (44.5%–79.8%, n=25)

### qwen-casuale
- intera: 16.0% (6.4%–34.7%, n=25)
- mescolata: 24.0% (11.5%–43.4%, n=25)
- senza_giusta: 88.0% (70.0%–95.8%, n=25)
- con_nessuna: sceglie «Nessuna» a torto 100.0% (86.7%–100.0%, n=25)
- lettera_a: risponde A 0.0% (0.0%–17.6%, n=18) contro 44.4% senza esempi
- calibrazione (probabilità massima): Brier 0.165 su 25

### qwen
- intera: 52.0% (33.5%–70.0%, n=25)
- mescolata: 32.0% (17.2%–51.6%, n=25)
- senza_giusta: 0.0% (0.0%–13.3%, n=25)
- con_nessuna: sceglie «Nessuna» a torto 4.0% (0.7%–19.5%, n=25)
- lettera_a: risponde A 100.0% (82.4%–100.0%, n=18) contro 11.1% senza esempi
- calibrazione (probabilità massima): Brier 0.218 su 25

### sonnet
- intera: 100.0% (86.7%–100.0%, n=25)
- mescolata: 100.0% (86.7%–100.0%, n=25)
- senza_giusta: 96.0% (80.5%–99.3%, n=25)
- con_nessuna: sceglie «Nessuna» a torto 0.0% (0.0%–13.3%, n=25)
- lettera_a: risponde A 0.0% (0.0%–17.6%, n=18) contro 0.0% senza esempi
- calibrazione (dichiarata): Brier 0.000 su 25

### Stabilità (ripetizioni)

- sonnet: 100.0% di 10 domande con la stessa lettera

### Copertura del corpus

- fresche: 92.5%
- arc_easy: 99.5%
- arc_challenge: 96.5%

### Per tipo (fresche, intera)

- pmi: associativa 77.8% (n=9), due_passi 50.0% (n=4), negazione 0.0% (n=1), relazionale 63.6% (n=11)
- qwen-casuale: associativa 22.2% (n=9), due_passi 0.0% (n=4), negazione 0.0% (n=1), relazionale 18.2% (n=11)
- qwen: associativa 77.8% (n=9), due_passi 50.0% (n=4), negazione 0.0% (n=1), relazionale 36.4% (n=11)
- sonnet: associativa 100.0% (n=9), due_passi 100.0% (n=4), negazione 100.0% (n=1), relazionale 100.0% (n=11)
