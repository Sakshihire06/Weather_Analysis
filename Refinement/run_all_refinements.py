import subprocess
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    "1_smoothing_refinement.py",
    "2_anomaly_threshold_refinement.py",
    "3_extreme_event_refinement.py",
]


def main():
    for script in SCRIPTS:
        script_path = CURRENT_DIR / script
        print(f"\nRunning {script}... - run_all_refinements.py:18", flush=True)
        result = subprocess.run([sys.executable, str(script_path)], check=False)

        if result.returncode != 0:
            print(f"{script} failed with exit code {result.returncode} - run_all_refinements.py:22")
            return result.returncode

    print("\nAll refinement scripts completed successfully. - run_all_refinements.py:25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
