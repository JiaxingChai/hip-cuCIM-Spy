import json, sys

prs = {p['number']: p for p in json.load(open('/root/jxchai/hip-cuCIM-Spy/archive/2026-11-07/cucim_prs.json'))}
ids = [int(x) for x in sys.argv[1:]]
for i in ids:
    p = prs.get(i)
    if not p:
        print(f'### {i} NOT FOUND')
        continue
    body = (p.get('body') or '').replace('\r', '')
    print('=' * 90)
    print(f"### PR #{i} | {p['title']} | merged={p['mergedAt']} | created={p['createdAt']}")
    print('LABELS:', ','.join(l['name'] for l in p['labels']['nodes']))
    print('BODY:')
    print(body[:2600])
