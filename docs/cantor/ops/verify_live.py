"""Verify both live Cantor manifests exactly match the reviewed registration."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--base-url', default='https://relay.cantorfm.com')
args = parser.parse_args()
records = {}
for kind, collection in [('catalog', 'models'), ('backends', 'engines')]:
    url = f"{args.base_url.rstrip('/')}/{kind}/v1.json"
    expected = json.loads((args.repo / f'relay/public/{kind}/v1.json').read_text())
    for attempt in range(6):
        request = Request(url, headers={'User-Agent': 'cantor/0.2.10', 'Cache-Control': 'no-cache'})
        with urlopen(request, timeout=30) as response:
            actual = json.loads(response.read())
        if actual == expected:
            break
        if attempt == 5:
            raise RuntimeError(f'Live {kind} does not match the reviewed manifest')
        time.sleep(10)
    assert any(entry['name'] == 'yue2' for entry in actual[collection])
    records[kind] = {'url': url, 'matches_reviewed_manifest': True, 'entries': len(actual[collection])}
records['checked_utc'] = datetime.now(timezone.utc).isoformat()
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(records))
