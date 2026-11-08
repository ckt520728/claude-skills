"""Start the dashboard at http://127.0.0.1:8090/. It only listens on this computer."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_agent.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="RSI knowledge dashboard")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    print(f"Dashboard: http://127.0.0.1:{args.port}/  (keep this window open)")
    create_app().run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
