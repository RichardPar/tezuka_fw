"""Spur mask prototype (reference for the Rust version in maia-httpd). Works on one spectrum as served on /waterfall:
z[0] is metadata, z[1:] are 4095 power bins centred on the LO (bin index 2047 of z[1:], i.e. z[2048])."""
import numpy as np
CLOCKS_HZ = (25e6, 100e6 / 3)       # board clocks whose harmonics leak into the receiver (measured on a Fishball 7010)
PPM = 50e-6                          # search window around each nominal harmonic (the real lines sit +5 to +20 ppm off)
RATIO_DB = 8.0                       # a line must stand this far above its surroundings (power dB) to be masked
MAX_WIDTH = 5                        # ... and be at most this many bins wide at half height (in dB)

def _ref(b, p):
    lo, hi = max(0, p - 24), min(len(b), p + 25)
    r = np.concatenate([b[lo:max(lo, p - 6)], b[min(hi, p + 7):hi]])
    return float(np.median(r)) if len(r) >= 8 else None

def _mask_line(b, p):
    ref = _ref(b, p)
    if ref is None or ref <= 0: return None
    peak = b[p]
    if peak < ref * 10 ** (RATIO_DB / 10): return None
    half = max(ref * np.sqrt(peak / ref), peak * 0.1)      # half the excess in dB, but never more than 10 dB below the peak
    l = r = p
    while l > 0 and b[l - 1] >= half: l -= 1
    while r < len(b) - 1 and b[r + 1] >= half: r += 1
    if r - l + 1 > MAX_WIDTH: return None                 # too wide: a real signal, not a spur
    thr = ref * 2.5
    while l > p - 6 and l > 0 and b[l - 1] > thr: l -= 1
    while r < p + 6 and r < len(b) - 1 and b[r + 1] > thr: r += 1
    return max(0, l - 1), min(len(b) - 1, r + 1), ref

def mask(z, fc, fs, centre=True, clocks=CLOCKS_HZ):
    """Returns (masked copy of z, list of masked (frequency_Hz, bins))."""
    z = np.array(z, dtype=np.float64); b = z[1:]; n = len(b); c = n // 2; hz = fs / 4096.0
    done = []
    cand = []
    if centre: cand.append((c, 2, fc))
    for f0 in clocks:
        k0, k1 = int(np.ceil((fc - 0.48 * fs) / f0)), int(np.floor((fc + 0.48 * fs) / f0))
        for k in range(max(1, k0), k1 + 1):
            f = k * f0; idx = c + int(round((f - fc) / hz)); w = int(np.ceil(PPM * f / hz)) + 1
            if w < 2: w = 2
            if idx - w - 24 < 0 or idx + w + 24 >= n: continue
            p = idx - w + int(np.argmax(b[idx - w:idx + w + 1]))
            cand.append((p, 0, f))
    for p, fixed, f in cand:
        if fixed:                                         # centre: always interpolate, the LO leaks here
            ref = _ref(b, p)
            if ref is not None: b[p - fixed:p + fixed + 1] = ref; done.append((f, 2 * fixed + 1))
            continue
        m = _mask_line(b, p)
        if m: l, r, ref = m; b[l:r + 1] = ref; done.append((f, r - l + 1))
    z[1:] = b
    return z, done
