#!/usr/bin/env python3
"""
Muse.ai OpenAI-Compatible Bridge Server Runner
"""

import sys
import os

# Add package directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muse.server import run_server

if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
