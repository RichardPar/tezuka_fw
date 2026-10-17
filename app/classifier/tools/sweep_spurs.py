"""Sweep the RX LO over a range and record every strong narrow line in the spectrum (the spurs of the board itself when RX-A has a
50 ohm terminator on it). Writes JSON for analyse_spurs.py. usage: sweep_spurs.py [start_MHz stop_MHz step_MHz] [out.json]
Needs the radio at 192.168.2.1 (edit radio.py for another address). Leaves the radio on the last tuning."""
import json, sys, time
import numpy as np
from scipy.signal import find_peaks
import radio

args = sys.argv[1:]
out_file = args.pop() if args and args[-1].endswith('.json') else 'spur_sweep.json'
start, stop, step = (int(float(a)) for a in args[:3]) if len(args) >= 3 else (150, 2000, 40)
found, tunings, skipped = [], 0, 0
for lo in range(start, stop + 1, step):
    try:
        radio.api('PATCH', 'ad9361', {'rx_lo_frequency': int(lo * 1e6)}); time.sleep(1.6)
        st = radio.api('GET', 'ad9361'); frames = radio.frames(8, timeout=8); st2 = radio.api('GET', 'ad9361')
    except Exception:
        skipped += 1; continue
    a = np.array([np.frombuffer(f, dtype='<f4') for f in frames if len(f) == 4096 * 4])
    if len(a) < 4 or (st2['rx_lo_frequency'], st2['sampling_frequency']) != (st['rx_lo_frequency'], st['sampling_frequency']):
        skipped += 1; continue          # the radio was retuned by someone else during the capture
    tunings += 1
    m = 10 * np.log10(a[:, 1:].mean(0) + 1e-30); hz = st['sampling_frequency'] / 4096; c = len(m) // 2; fc = st['rx_lo_frequency']
    lo_i, hi_i = int(c - 0.45 * 4096), int(c + 0.45 * 4096)
    pk, pr = find_peaks(m[lo_i:hi_i], prominence=10); pk = pk + lo_i
    for k, p in zip(pk, pr['prominences']):
        found.append(dict(fc=fc, f=fc + (k - c) * hz, prom=float(p), level=float(m[k]), hz=hz, gain=st['rx_gain'],
                          bins=int(np.sum(m[max(0, k - 8):k + 9] >= m[k] - 6))))
json.dump(found, open(out_file, 'w'))
print('%d peaks of at least 10 dB in %d tunings (%d skipped); wrote %s' % (len(found), tunings, skipped, out_file))
