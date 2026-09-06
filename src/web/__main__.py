"""`python -m src.web` — espelha `python -m src.graph`, que é como o resto do projeto se roda."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "8000")),
        # `reload=False` de propósito: o `GRAFO` é montado no import e o recarregador o
        # remontaria a cada salvamento, no meio de um run de 3m30.
        reload=False,
        log_level="info",
    )
