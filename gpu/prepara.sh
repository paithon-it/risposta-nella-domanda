#!/usr/bin/env bash
# Prepara la macchina con la GPU: ambiente Python con vLLM e modello scaricato.
# Tutto sta dentro $RND (di serie ~/rnd), così alla fine si cancella una cartella sola.
# Uso, sulla macchina con la GPU, dalla cartella dell'esperimento:  bash gpu/prepara.sh
set -euo pipefail
RND="${RND:-$HOME/rnd}"
MODELLO="${MODELLO:-cyankiwi/Qwen3.8-27B-AWQ-INT4}"
mkdir -p "$RND"
# tutte le cache dentro $RND (vLLM, FlashInfer e Triton scrivono altrimenti nella home), statistiche di vLLM spente
export HF_HOME="$RND/hf" XDG_CACHE_HOME="$RND/cache" XDG_CONFIG_HOME="$RND/config" TRITON_CACHE_DIR="$RND/triton" \
       VLLM_CACHE_ROOT="$RND/vllm" VLLM_CONFIG_ROOT="$RND/vllm-config" VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
python3 -m venv "$RND/venv"
. "$RND/venv/bin/activate"
pip install -q --no-cache-dir --upgrade pip
pip install -q --no-cache-dir vllm   # porta con sé torch e transformers compatibili
python -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__, 'cuda', torch.cuda.is_available())"
hf download "$MODELLO" > /dev/null
du -sh "$RND/hf"
