import json, re

prs = json.load(open('/root/jxchai/hip-cuCIM-Spy/archive/2026-11-07/cucim_prs.json'))
prs.sort(key=lambda p: p['number'])

KEEP = {
    1087, 843, 844, 845, 846, 847, 848, 1055, 1060, 1061, 1115, 1040, 839, 809,
    782, 516, 485, 517, 521, 540, 482, 828, 838, 770, 836, 842, 813, 967, 764,
    856, 1038, 1142, 1077, 1007, 1028, 1145, 727, 728,
}

RULES = [
    ('CI/构建流水线', r'(?i)\b(ci|gpuci|workflow|workflows|runner|runners|zizmor|pre-commit|sccache|artifact|nightly build|test infra|codecov|telemetry)\b'),
    ('打包/依赖/版本', r'(?i)(conda|rattler|wheel|setuptools|dependency|dependencies|numpy version|cupy version|requirements|cmake|fmt library|version specifier|pinning|cccl|cuda 1\d\.\d|gcc)'),
    ('Forward-merge', r'(?i)forward-merge'),
    ('文档/品牌', r'(?i)(readme|docstring only|docs?\b|documentation|logo|branding|secuirty|security\.md|spdx|copyright|license file)'),
    ('绑定层迁移', r'(?i)(nanobind|pybind11|binding)'),
    ('Python 版本兼容', r'(?i)python 3\.1\d'),
    ('CI测试跳过/网络', r'(?i)(429|ratelimit|rate-limit|xfail|skip (tests|ci))'),
]


def classify(p):
    t = p['title']
    body = (p.get('body') or '')[:400]
    labels = [l['name'].lower() for l in p['labels']['nodes']]
    for name, pat in RULES:
        if re.search(pat, t):
            return name
    if 'doc' in labels or 'maintenance' in labels:
        return '文档/维护'
    return None


buckets = {}
for p in prs:
    if p['number'] in KEEP:
        continue
    c = classify(p)
    if c is None:
        c = '其他(无GPU kernel改动/低复杂度)'
    buckets.setdefault(c, []).append(p['number'])

for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
    print(f'{k} ({len(v)}): {sorted(v)}')
