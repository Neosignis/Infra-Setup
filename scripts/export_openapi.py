"""Export without starting the service or requiring configured credentials."""
import json
import sys
from pathlib import Path

from neosignis.api import app

target = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"
content = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
if "--check" in sys.argv:
    if not target.exists() or target.read_text() != content:
        raise SystemExit("OpenAPI is stale; run scripts/export_openapi.py")
    print("OpenAPI matches the executable API")
else:
    target.write_text(content)
