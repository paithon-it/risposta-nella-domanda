"""Il modello piccolo in locale e il suo gemello a pesi casuali.

La risposta principale è la scelta vincolata: fra i token delle lettere
A..k, quello più probabile come primo token della risposta. Il gemello a
pesi casuali non sa scrivere una lettera, e con la sola lettura del testo
farebbe circa 0%, non il caso. Il testo libero si registra comunque.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from rnd import LETTERE, SEME
from rnd.lettera import estrai_lettera

MODELLO = "Qwen/Qwen2.5-0.5B-Instruct"


@dataclass
class RispostaLocale:
    testo: str
    lettera_testo: int | None
    lettera_vincolata: int
    probabilita: list[float]


def distribuzione_lettere(logit: torch.Tensor, ids: list[int]) -> list[float]:
    return torch.softmax(logit[ids].float(), dim=-1).tolist()


def ids_lettere(tokenizer, k: int) -> list[int]:
    ids = []
    for lettera in LETTERE[:k]:
        t = tokenizer.encode(lettera, add_special_tokens=False)
        if len(t) != 1:
            raise ValueError(f"la lettera {lettera} non è un token singolo: {t}")
        ids.append(t[0])
    return ids


def testo_chat(tokenizer, prompt: str) -> str:
    """Il prompt nel formato di chat del modello, con il ragionamento spento (Qwen3 e successivi lo hanno
    acceso di serie; per i modelli che non lo prevedono l'argomento in più si ignora)."""
    return tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False)


class ModelloLocale:
    def __init__(self, nome: str = MODELLO, pesi_casuali: bool = False, rispondente: str | None = None):
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

        self.rispondente = rispondente or ("qwen-casuale" if pesi_casuali else "qwen")
        self.tokenizer = AutoTokenizer.from_pretrained(nome)
        gpu = torch.cuda.is_available()
        if pesi_casuali:
            torch.manual_seed(SEME)
            self.modello = AutoModelForCausalLM.from_config(AutoConfig.from_pretrained(nome), dtype=torch.bfloat16)
            if gpu:
                self.modello.to("cuda")
        else:
            dove = {"device_map": "cuda"} if gpu else {}
            try:
                self.modello = AutoModelForCausalLM.from_pretrained(nome, dtype=torch.bfloat16, **dove)
            except ValueError:  # modelli multimodali (Qwen3.8): si usano per il solo testo
                from transformers import AutoModelForImageTextToText
                self.modello = AutoModelForImageTextToText.from_pretrained(nome, dtype=torch.bfloat16, **dove)
        self.modello.eval()
        if self.modello.generation_config.pad_token_id is None:
            self.modello.generation_config.pad_token_id = self.tokenizer.eos_token_id

    def rispondi(self, prompt: str, k: int) -> RispostaLocale:
        ingresso = self.tokenizer(testo_chat(self.tokenizer, prompt), return_tensors="pt").to(self.modello.device)
        with torch.no_grad():
            logit = self.modello(**ingresso).logits[0, -1]
            uscita = self.modello.generate(**ingresso, max_new_tokens=8, do_sample=False)
        probabilita = distribuzione_lettere(logit, ids_lettere(self.tokenizer, k))
        testo = self.tokenizer.decode(uscita[0, ingresso["input_ids"].shape[1]:], skip_special_tokens=True)
        return RispostaLocale(testo, estrai_lettera(testo, k), max(range(k), key=probabilita.__getitem__), probabilita)


class ModelloVLLM:
    """Un modello servito da vLLM, per i pesi quantizzati che transformers non sa usare compressi.

    La scelta vincolata è esatta: per ogni lettera si chiede a vLLM la probabilità di quel token dopo il
    prompt (prompt_logprobs), non le prime proposte del modello; i quattro prompt condividono l'inizio,
    che vLLM calcola una volta sola (prefix caching).
    """

    def __init__(self, nome: str, rispondente: str, llm=None, parametri=None):
        if llm is None:
            import os

            # il campionatore di FlashInfer si compila al volo e vuole nvcc; a noi basta la scelta greedy
            os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
            from vllm import LLM

            # domande corte (al più qualche centinaio di token): poca memoria per la cache, il resto ai pesi
            llm = LLM(model=nome, max_model_len=2048, max_num_seqs=8, max_num_batched_tokens=2048,
                      gpu_memory_utilization=0.92, enable_prefix_caching=True, enforce_eager=True,
                      limit_mm_per_prompt={"image": 0, "video": 0})
        if parametri is None:
            from vllm import SamplingParams as parametri
        self.llm, self._parametri, self.rispondente = llm, parametri, rispondente
        self.tokenizer = llm.get_tokenizer()

    def rispondi(self, prompt: str, k: int) -> RispostaLocale:
        base = self.tokenizer.encode(testo_chat(self.tokenizer, prompt), add_special_tokens=False)
        ids = ids_lettere(self.tokenizer, k)
        uscite = self.llm.generate([{"prompt_token_ids": base + [i]} for i in ids],
                                   self._parametri(max_tokens=1, temperature=0.0, prompt_logprobs=1), use_tqdm=False)
        logp = torch.tensor([u.prompt_logprobs[-1][i].logprob for u, i in zip(uscite, ids)])
        probabilita = torch.softmax(logp, dim=-1).tolist()
        testo = self.llm.generate([{"prompt_token_ids": base}],
                                  self._parametri(max_tokens=8, temperature=0.0, prompt_logprobs=None),
                                  use_tqdm=False)[0].outputs[0].text
        return RispostaLocale(testo, estrai_lettera(testo, k), max(range(k), key=probabilita.__getitem__), probabilita)
