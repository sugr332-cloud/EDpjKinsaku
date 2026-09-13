"""Standalone entry point for the PyInstaller-bundled C-CORE binary EliteIntel invokes directly.

Distinct from `app.cli.__main__` (the full `edpj` CLI, registered as the `edpj` console script):
this module imports only `app.cli.bio`'s Typer app, not the sibling CLI submodules
(`backfill`/`collector`/`calibration`/`state`) that `app.cli.__main__` eagerly imports and that pull
in sqlalchemy/psycopg/alembic/fastapi/uvicorn/pyzmq - none of which `bio evaluate` itself needs (see
EliteIntel's docs/ELITEINTEL_INTEGRATION_PLAN.md Phase 8-A investigation, which measured this as a
460ms -> 125ms startup difference and roughly half the bundle size in a real PyInstaller `--onedir`
build).

`bio_app` has exactly one command, so Typer collapses it away when run standalone: the resulting
binary takes no subcommand arguments and reads/writes the same request/response JSON as
`edpj bio evaluate` directly on stdin/stdout. Built by scripts/build_ccore_binary.ps1.
"""
from __future__ import annotations

from app.cli.bio import bio_app

if __name__ == "__main__":
    bio_app()
