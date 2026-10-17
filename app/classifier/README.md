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

Test data, the Python reference implementation and the synthetic signal tests are in https://github.com/RichardPar/fishball7010-open-fw (classifier/).
Validated against that reference on 16 real captures and on synthetic FM, GSM, LTE, DVB-T, DAB, LoRa-like, Wi-Fi and CW signals; weak spots are listed there.
