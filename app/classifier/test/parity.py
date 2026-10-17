"""Run the C classifier and the Python reference on every capture in captures/ and compare their output line by line
(Wi-Fi clustering is off for the comparison: it is only in the C code). Run from this directory after `make host-test`."""
import glob, json, os, subprocess, sys
ok = 0; names = sorted(os.path.basename(f)[:-5] for f in glob.glob('captures/*.json'))
for nm in names:
    m = json.load(open('captures/%s.json' % nm))
    c = subprocess.run(['./classifier-native', '-A', '0', '-t', 'captures/%s.bin' % nm, '-F', str(m['fc_hz']), '-S', str(m['fs_hz']),
                        '-B', str(m['rf_bw_hz']), '-N', str(m['floats_per_frame'])], capture_output=True, text=True).stdout
    p = subprocess.run([sys.executable, 'spec_dump.py', nm], capture_output=True, text=True).stdout
    same = c == p; ok += same
    print('%-10s %s' % (nm, 'identical' if same else 'DIFFERENT'))
print('%d / %d captures identical' % (ok, len(names)))
sys.exit(0 if ok == len(names) else 1)
