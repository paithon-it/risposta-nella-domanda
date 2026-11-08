# Il modello grande sulla GPU

Qwen3.8 27B non gira sulla CPU di una macchina da 8 GB: si usa una GPU a ore.
Per l'8/11/2026: una NVIDIA L4 da 24 GB, 31 GB di RAM, Ubuntu 24.04.

**Il modello.** I pesi originali di `Qwen/Qwen3.8-27B` sono 56 GB in bf16 e 31
in FP8: non stanno nei 24 GB della L4. Si usa una quantizzazione a 4 bit fatta
da terzi, `cyankiwi/Qwen3.8-27B-AWQ-INT4` (21 GB di file, formato
compressed-tensors). transformers non la sa usare compressa (prova a
decomprimerla in bf16), vLLM sì: per questo il modello grande passa da
`ModelloVLLM` in `rnd/locale.py`, che chiede a vLLM la probabilità esatta di
ciascuna lettera dopo il prompt. Il ragionamento di serie di Qwen3.8 è spento
(`enable_thinking=False`), come per la scelta vincolata degli altri modelli.

**I passi.** Dalla macchina dove sta l'esperimento, con `GPU` uguale a
`utente@indirizzo` della macchina con la GPU:

```bash
rsync -az --exclude __pycache__ --exclude risultati --exclude dati ./ "$GPU:rnd/esperimento/"
ssh "$GPU" 'cd rnd/esperimento && bash gpu/prepara.sh'
ssh "$GPU" 'cd rnd/esperimento && RND=~/rnd RISPONDENTE=qwen3.8-27b bash gpu/corsa.sh --solo-prova'
ssh "$GPU" 'cd rnd/esperimento && nohup bash gpu/corsa.sh > ~/rnd/corsa.log 2>&1 &'
rsync -az "$GPU:rnd/risultati-gpu/" risultati/
ssh "$GPU" 'rm -rf ~/rnd'        # alla fine non resta niente
```

Tutto sta in `~/rnd` sulla macchina con la GPU: ambiente Python, modello,
cache di vLLM, FlashInfer e Triton, risultati. Gli script lo impongono con le
variabili d'ambiente (`XDG_CACHE_HOME`, `TRITON_CACHE_DIR`, `VLLM_CACHE_ROOT` e
le altre) e spengono le statistiche d'uso di vLLM (`VLLM_NO_USAGE_STATS=1`,
`DO_NOT_TRACK=1`). Cancellata quella cartella, della corsa non resta traccia.
Per controllare, prima di cancellarla:
`find ~ -maxdepth 3 -newer ~/rnd/venv -not -path '*/rnd*'`.

La prima volta, l'8/11/2026, queste variabili non c'erano: vLLM ha scritto le
sue cache nella home e ha registrato un file di statistiche d'uso anonime
(hardware e versioni, nessun dato delle domande). Cache e file sono stati
cancellati a mano dopo la corsa.
