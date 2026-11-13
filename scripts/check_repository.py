"""Dependency-free checks for local links and structured reference files."""
import ast
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
errors = []
paths = [p for p in root.rglob('*') if not any(part.startswith('.') or part in {'__pycache__', 'validation-logs'} for part in p.relative_to(root).parts)]
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
