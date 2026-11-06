from __future__ import annotations

import sys

from .base import run as _run


def run(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if "--model" not in argv:
        argv = ["--model", "RAS"] + argv
    return _run(argv)


def main(argv=None):
    run(argv)


if __name__ == "__main__":
    main()
