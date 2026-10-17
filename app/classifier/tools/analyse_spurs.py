"""Separate the LO (centre) peaks from the off-centre spurs in a sweep made with sweep_spurs.py and show which board clock each
off-centre line is a harmonic of. usage: analyse_spurs.py [spur_sweep.json]"""
import json, sys
import numpy as np

data = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'spur_sweep.json'))
centre = [x for x in data if abs(x['f'] - x['fc']) < 40e3]
spurs = [x for x in data if abs(x['f'] - x['fc']) >= 40e3]
tunings = len({x['fc'] for x in data})
if centre:
    pr = [x['prom'] for x in centre]
    print('centre (LO) peaks: %d, prominence %.0f-%.0f dB (median %.0f)' % (len(centre), min(pr), max(pr), np.median(pr)))
bases = {'25 MHz': 25.0, '100/3 MHz': 100 / 3}
print('off-centre spurs: %d in %d tunings\n  %-10s %5s %5s  %-10s %4s %9s' % (len(spurs), tunings, 'MHz', 'prom', 'bins', 'base', 'k', 'ppm'))
for x in sorted(spurs, key=lambda x: x['f']):
    f = x['f'] / 1e6
    name, b = min(bases.items(), key=lambda kv: abs(f - round(f / kv[1]) * kv[1]))
    k = round(f / b); ppm = (f - k * b) / f * 1e6
    print('  %-10.3f %5.0f %5d  %-10s %4d %+8.1f%s' % (f, x['prom'], x['bins'], name, k, ppm, '' if abs(ppm) < 50 else '   not a harmonic'))
