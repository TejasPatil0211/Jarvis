"""
Jarvis — package bootstrap.

Adding the project folder to sys.path lets every module use flat imports
(`from brain import Brain`) in BOTH invocation styles:

    python main.py            # script mode
    python -m jarvis.main     # package mode

Without this, `python -m jarvis.main` would fail because the project folder
is not on sys.path when the package is imported from its parent directory.
"""

import os
import sys

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)
