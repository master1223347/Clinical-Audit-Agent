"""Shared pytest configuration for tests/eval/.

Sets up sys.path so all eval tests can import:
  - app.*   (from the worktree root)
  - run_eval (from tests/eval/, where the harness lives)
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
_EVAL_DIR = Path(__file__).parent

for _p in (_ROOT, _EVAL_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
