# ablations/_bootstrap.py
import os
import sys

def add_repo_root_to_path() -> None:
    """Ensure we can import project modules when running from ablations/."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)