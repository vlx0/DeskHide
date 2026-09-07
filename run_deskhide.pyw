import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from deskhide.instance import claim_or_exit
from deskhide.ui import run

if __name__ == "__main__":
    claim_or_exit()
    run(start_hidden="--tray" in sys.argv)
