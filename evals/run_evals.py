"""Evaluation harness stub for COCO COLORS pipeline."""
import argparse
import sys


def main():
    """Run evaluation suite."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--threshold-groundedness", type=float, default=0.8)
    parser.add_argument("--threshold-task-completion", type=float, default=0.9)
    parser.add_argument("--threshold-relevance", type=float, default=0.8)
    parser.add_argument("--fail-on-breach", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    print(f"Eval stub passed | dataset={args.dataset}")
    sys.exit(0)


if __name__ == "__main__":
    main()
