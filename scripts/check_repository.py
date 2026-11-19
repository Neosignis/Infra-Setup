"""Dependency-free checks for local links and structured reference files."""
import ast
import json
import os
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
errors = []
excluded = {'__pycache__', 'validation-logs', 'node_modules', 'dist', 'build', 'test-results', 'playwright-report'}
# Prune excluded trees before descending into installed dependencies/caches.
# Filtering rglob results still traverses every file in those large folders.
paths = []
for directory, directories, files in os.walk(root):
    directories[:] = [name for name in directories if not name.startswith('.') and name not in excluded]
    paths.extend(Path(directory) / name for name in files if not name.startswith('.') and name not in excluded)
for path in paths:
    if path.suffix == '.json' or path.name.endswith('.json.example'):
        json.loads(path.read_text())
    if path.suffix == '.py':
        ast.parse(path.read_text(), filename=str(path))
    if path.suffix == '.md':
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            if not (path.parent / target.split('#')[0]).exists():
                errors.append(f'{path.relative_to(root)}: missing {target}')
if errors:
    raise SystemExit('\n'.join(errors))
print('Repository JSON, Python syntax and Markdown file links passed')
