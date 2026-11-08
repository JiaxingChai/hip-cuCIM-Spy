import json, re, sys

prs = json.load(open('/root/jxchai/hip-cuCIM-Spy/archive/2026-11-07/cucim_prs.json'))
kw = re.compile(
    r'(kernel|rawkernel|gpu|watershed|regionprops|deconv|morpholog|resize|rotate|'
    r'median|rank|texture|stain|tile|cache|atomic|warp|shared|int64|large image|'
    r'64-bit|fft|convolve|separable|pyramid|interpolat|hessian|radon|hough|peak|'
    r'skeleton|blob|downscale|lab2rgb|rgba|colormap|sobel|scharr|prewitt|laplacian|'
    r'label|cucim\.skimage|measure|segmentation)',
    re.I)

rows = []
for p in prs:
    labels = [l['name'].lower() for l in p['labels']['nodes']]
    if 'doc' in labels:
        continue
    t = p['title']
    b = p.get('body') or ''
    if kw.search(t) or kw.search(b[:3000]):
        rows.append((p['number'], p['mergedAt'] is not None, t, labels))

print(len(rows))
for n, m, t, l in sorted(rows):
    print(n, 'M' if m else '-', t[:115], '|', ','.join(l))
