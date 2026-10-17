# classifier

Emitter detector and signal classifier for the Maia /waterfall spectrum. Replaces the template-matching classifier.

Once per interval (default 1 s) it averages the received frames, reads fc / sample rate / RF bandwidth from /api/ad9361, and

1. finds wide blocks (LTE, DVB-T, DAB, Wi-Fi): median filter, cut at sharp edges, keep plateaus clearly above a neighbour;
2. finds narrow emitters (FM, GSM, carriers, bursts): prominent peaks that also stand out from the local ripple, with bandwidth limited by the valley to the next emitter;
3. measures each in Hz (occupied bandwidth, SNR, flatness, burstiness) and names it from bandwidth, shape, burstiness, frequency band, channel raster (FM 100 kHz, GSM 200 kHz) and known board clock harmonics (reported as spurs);
4. clusters bursty narrow peaks in the ISM bands into one Wi-Fi activity emitter;
5. tracks emitters across intervals and publishes the best one.

MQTT (state/classifier/): label, confidence, freq_offset, bandwidth_bins, frame_bins, template_id and feature_* as before (the Dashboard reads these), plus
emitters (JSON list, up to 16), emitter_count, noise_floor_db, center_hz and sample_rate_hz.

Options: -H host -p port -P path, -c confidence floor for the primary label (default 0.40), -i interval in seconds (default 1.0),
-A 0|1 Wi-Fi clustering, -v verbose, -t FILE offline test (needs -F fc -S fs -B rfbw -N floats_per_frame). -f and -m are accepted and ignored.

## Tests and reference implementation

`test/` holds a Python reference implementation of the same algorithm (`detect4.py`, `classify.py`), 16 real captures from a Fishball 7010 (`captures/`:
FM, GSM, LTE, DVB-T, DAB, UMTS, Wi-Fi, ISM, ADS-B, quiet bands) and a synthetic signal test (`synth.py`, `synth_test.py`).

```sh
pip install numpy scipy                 # for the Python side
make host-test                          # builds test/classifier-native with the host compiler
make test                               # C output must equal the Python reference on every capture, then the synthetic checks
```

Last result: 16 of 16 captures identical (with Wi-Fi clustering off, which only the C code has), 9 of 9 synthetic checks (FM, GSM, LTE, DVB-T, DAB, LoRa-like
bursts, Wi-Fi, CW; noise-only false alarms 0 of 40, and 0 of 20 with a tilted noise floor). Live on a Fishball 7010: 12 of 12 FM stations at 98 MHz identified. The synthetic
signals are models, not over-the-air recordings. Known weak spots: weak DAB ensembles, and contiguous GSM or UMTS carriers can read as an "LTE 5 MHz" block.

Offline run on one capture: `test/classifier-native -t test/captures/fm98.bin -F <fc_Hz> -S <fs_Hz> -B <rfbw_Hz> -N <floats_per_frame>` (the values are in `test/captures/fm98.json`).

## Tools

`tools/` has helpers for working with a live radio (`radio.py` talks to the Maia API and `/waterfall`, `capture.py` records captures like the ones in `test/captures`,
`iio_attr.py` reads and writes IIO attributes over libiio, `mqtt_watch.py` prints MQTT topics, `overlay.py` plots results) and the clock-spur tools:
`sweep_spurs.py`, `analyse_spurs.py` and `spurmask.py` (the Python prototype of the mask in `maia-httpd`). See [doc/fishball7010](../../doc/fishball7010/README.md#clock-spurs-and-the-lo-spike).
They default to a radio at 192.168.2.1 (edit `radio.py` for another address).
