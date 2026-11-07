"""Build step: train and cache the on-device classifier so the web service starts instantly.

    uv run python -m pauseline.prepare
"""

from __future__ import annotations

import time

from pauseline.risk.classifier import get_classifier


def main() -> None:
    t = time.time()
    clf = get_classifier()
    print(f"classifier ready in {time.time() - t:.1f}s: {clf.meta}")


if __name__ == "__main__":
    main()
