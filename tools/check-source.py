"""Parse every tracked Python source without importing the bot or writing bytecode."""
import ast
import subprocess
from pathlib import Path

paths = subprocess.check_output(["git", "ls-files", "-z", "--", "*.py"]).decode().split("\0")
sources = [Path(path) for path in paths if path]
if not sources:
    raise SystemExit("No tracked Python sources found")
for source in sources:
    ast.parse(source.read_bytes(), filename=str(source))
print(f"Parsed {len(sources)} tracked Python sources")
