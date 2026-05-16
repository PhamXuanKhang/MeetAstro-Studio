from pathlib import Path
import runpy

root_hook = Path(__file__).resolve().parents[2] / "scripts" / "log_hook.py"
runpy.run_path(str(root_hook), run_name="__main__")
