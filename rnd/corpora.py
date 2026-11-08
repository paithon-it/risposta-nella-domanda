"""Lettura dei corpora, una riga (paragrafo o frase) alla volta."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Iterator


def righe_parquet(p: Path) -> Iterator[str]:
    """I paragrafi della colonna `text` di un parquet di Wikipedia (wikimedia/wikipedia)."""
    import pyarrow.parquet as pq

    for lotto in pq.ParquetFile(p).iter_batches(columns=["text"], batch_size=512):
        for testo in lotto.column(0).to_pylist():
            for riga in (testo or "").split("\n"):
                if riga.strip():
                    yield riga.strip()


def righe_testo(p: Path) -> Iterator[str]:
    apri = gzip.open if p.suffix == ".gz" else open
    with apri(p, "rt", encoding="utf-8", errors="replace") as f:
        for riga in f:
            if riga.strip():
                yield riga.strip()
