#!/usr/bin/env python3
import sys

from continuity import main_default

if __name__ == "__main__":
    raise SystemExit(main_default("bootstrap", sys.argv[1:]))
