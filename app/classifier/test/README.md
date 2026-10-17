# Classifier tests

Run from this directory (or use `make test` one level up). Needs python3 with numpy and scipy and a host C compiler.

* `captures/` - 16 recordings of the `/waterfall` feed from a Fishball 7010 (`*.bin` float32 frames, `*.json` centre frequency, sample rate, bandwidth, gain).
* `detect4.py`, `classify.py` - Python reference implementation of the detector and the classification rules.
* `spec_dump.py <name>` - prints the reference result for one capture in the format the C program uses for `-t`.
* `parity.py` - runs both on every capture and compares the output line by line.
* `synth.py`, `synth_test.py` - synthetic spectra (FM, GSM, LTE, DVB-T, DAB, LoRa-like bursts, Wi-Fi, CW, noise) and the checks on them, including noise-only false alarms.
* `captures_overview.png`, `detect4_overlay.png` - plots of the captures and of what the detector found.

`classifier-native` is built by `make host-test` and is not committed.
