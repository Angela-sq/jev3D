#!/usr/bin/env python3
"""Record SHA-256 hashes of the prompt, schedule, datapack and controller before scoring."""
import hashlib,json
from config import OUT,REPO,TOOLS
files=[OUT/'ACTOR_PROMPT.md',OUT/'schedule.json',*sorted((OUT/'datapack').rglob('*.*')),*sorted(TOOLS.glob('*.py')),TOOLS/'deploy.sh']
digests={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'frozen-sha256.json').write_text(json.dumps(digests,indent=2)+'\n')
print(len(digests),'files frozen')
