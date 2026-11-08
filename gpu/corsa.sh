#!/usr/bin/env bash
# La corsa del modello grande sulla GPU: tutte le famiglie, le varianti che girano anche sui modelli locali.
# Uso, sulla macchina con la GPU, dalla cartella dell'esperimento:  bash gpu/corsa.sh
# Riprende da dove si è fermata, come la corsa sulla CPU.
set -uo pipefail
RND="${RND:-$HOME/rnd}"
RISPONDENTE="${RISPONDENTE:-qwen3.8-27b}"
OUT="${OUT:-$RND/risultati-gpu}"
. "$RND/venv/bin/activate"
# tutte le cache dentro $RND (vLLM, FlashInfer e Triton scrivono altrimenti nella home), statistiche di vLLM spente
export HF_HOME="$RND/hf" XDG_CACHE_HOME="$RND/cache" XDG_CONFIG_HOME="$RND/config" TRITON_CACHE_DIR="$RND/triton" \
       VLLM_CACHE_ROOT="$RND/vllm" VLLM_CONFIG_ROOT="$RND/vllm-config" VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export HF_HUB_OFFLINE=1
EPI=intera,solo_opzioni,mescolata,con_nessuna,senza_giusta,lettera_a
if [ "${1:-}" = "--solo-prova" ]; then python3 gpu/prova.py "$RISPONDENTE"; exit; fi
for f in fresche inconoscibili trappola deduttive; do
  v=intera,solo_opzioni
  [ "$f" = fresche ] && v=$EPI
  inizio=$(date +%s)
  python3 -m rnd.corsa --rispondente "$RISPONDENTE" --famiglie "$f" --varianti "$v" --cartella "$OUT"
  echo "TEMPO $f $(( $(date +%s) - inizio )) s"
done
echo FINE
