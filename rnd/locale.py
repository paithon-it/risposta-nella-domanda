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


class ModelloLocale:
    def __init__(self, nome: str = MODELLO, pesi_casuali: bool = False):
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

        self.rispondente = "qwen-casuale" if pesi_casuali else "qwen"
        self.tokenizer = AutoTokenizer.from_pretrained(nome)
        if pesi_casuali:
            torch.manual_seed(SEME)
            self.modello = AutoModelForCausalLM.from_config(AutoConfig.from_pretrained(nome), dtype=torch.bfloat16)
        else:
            self.modello = AutoModelForCausalLM.from_pretrained(nome, dtype=torch.bfloat16)
        self.modello.eval()
        if self.modello.generation_config.pad_token_id is None:
            self.modello.generation_config.pad_token_id = self.tokenizer.eos_token_id

    def rispondi(self, prompt: str, k: int) -> RispostaLocale:
        testo_chat = self.tokenizer.apply_chat_template([{"role": "user", "content": prompt}],
                                                        tokenize=False, add_generation_prompt=True)
        ingresso = self.tokenizer(testo_chat, return_tensors="pt")
        with torch.no_grad():
            logit = self.modello(**ingresso).logits[0, -1]
            uscita = self.modello.generate(**ingresso, max_new_tokens=8, do_sample=False)
        probabilita = distribuzione_lettere(logit, ids_lettere(self.tokenizer, k))
        testo = self.tokenizer.decode(uscita[0, ingresso["input_ids"].shape[1]:], skip_special_tokens=True)
        return RispostaLocale(testo, estrai_lettera(testo, k), max(range(k), key=probabilita.__getitem__), probabilita)
