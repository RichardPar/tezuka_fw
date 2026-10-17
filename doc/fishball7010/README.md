# Fishball 7010 (TZT 70 MHz-6 GHz, Zynq-7010 + AD9363)

![The board: TZT 70 MHz-6 GHz Zynq-7010 + AD9363 SDR](board.png)

*The board these changes were made on, as sold by TZT (product photo from the AliExpress listing; the image remains the seller's).*

## Why this exists

The seller of this board did not release the source for the firmware it ships, although that firmware includes GPL software (Linux, U-Boot,
Buildroot). So the shipped firmware was analysed instead: the boot files were extracted from the vendor SD card, the U-Boot and device tree
were matched against public sources, and the board was identified as a **Fishball 7010 clone** (its first-stage boot loader sets up the
MIO pins and DDR exactly like Tezuka's `fishball7010` target, on all 46 MIO registers). With that known, Tezuka's `fishball7010` target
can be used directly. Only the vendor FSBL and bitstream remain closed binaries on the vendor card, and the Tezuka build does not use them.

This branch is Tezuka plus the fixes that were needed to make it work well on this board.

## What differs from upstream Tezuka

Kernel, Maia SDR, the Buildroot root file system and the Dashboard are stock Tezuka v0.3.23 (Linux 6.12, `fishball7010`). The branch changes:

| Change | Where |
|---|---|
| **Signal classifier v2**: a template-free emitter detector replaces the template matcher, which pinned one core on the Zynq-7010. See [app/classifier](../../app/classifier/README.md). | `app/classifier`, `package/classifier`, `S61classifier` |
| **Status scripts without forks**: `api_controller.sh` publishes only changed values and reads sysfs/proc with shell builtins, `watchconsoletx.sh` and `update.sh` no longer fork every second. All state topics are kept; `state/main/forks_per_s` is new. | `board/tezuka/common/overlay_*` |
| **Tickless idle, 250 Hz kernel tick** (Fishball 7010 only): the default periodic 1000 Hz tick woke each core 1000 times a second even when idle. Timer interrupts went from 2152 to 137-190 per second. | `board/tezuka/fishball7010/kernel/fragment/frag1.config` |
| **Status poll only while someone listens**: `api_controller.sh` polls fully only while a remote MQTT client is connected (Dashboard, Home Assistant, ...) or `/tmp/always_poll` exists; otherwise one cheap poll a minute. New topic `state/main/polling` (`active` or `idle`). The U-Boot environment is read once per refresh instead of once per variable (seven forks and seven flash reads every 30 s before). | `board/tezuka/common/overlay_tezuka/root/api_controller.sh` |
| **Part names from the board model**: the Dashboard no longer hard-codes Zynq-7020 / AD9361; it reads them from `state/main/hw_model`. | `Dashboard/data.jsx` (`hwParts`), `pages1-3.jsx` |
| **AD9363 label** for this board: device tree model and `S23udc` (which rewrote the model to AD9361). The driver stays in `ad9361` mode (70 MHz-6 GHz). **Specific to boards fitted with an AD9363**: drop these two commits for AD9361 boards. | `board/tezuka/fishball7010/kernel-dts`, `.../dts`, `.../u-boot-dts`, `S23udc` |
| **Spur mask in `maia-httpd`**: masks the LO leakage bin and harmonics of the board's 25 MHz and 100/3 MHz clocks in the spectrum sent on `/waterfall`. See [Clock spurs](#clock-spurs-and-the-lo-spike). | `package/maia-httpd/0002-spur-mask.patch` |
| **`package-lock.json`** completed (esbuild platform packages), so `npm ci` works with npm 11. | `Dashboard/package-lock.json` |

Measured on a Fishball 7010 over MQTT (CPU metric: one busy core reads 100). The tick and polling changes were measured separately with `tools/cpu_profile.sh` (below); the last version of the client check (awk) was built but its idle profile was not taken, so the saving from the polling change is expected, not measured:

| | stock Tezuka v0.3.23 | this branch |
|---|---|---|
| CPU metric | 97 (pinned) | 12-17 |
| forks per second | not measured | 3-8 |
| chip / FPGA temperature | 47-48 / 57-59 C | 41-42 / 49-50 C at 3 minutes of uptime (still warming) |
| `hw_model` | `FISHBall-PlutoSky (Z7010-AD9361)` | `FISHBall-PlutoSky (Z7010-AD9363)` |

## Build

```sh
# Debian / Ubuntu host. Besides the packages in the top-level README you need:
sudo apt install jq nodejs npm libclang-dev libgmp-dev libmpc-dev libmpfr-dev

git clone https://github.com/RichardPar/tezuka_fw && cd tezuka_fw
git checkout fishball7010-fixes
./getbuildroot.sh                  # downloads Buildroot (pinned in buildroot.version)
./build.sh fishball                # full SD image plus the flash-only mini image; first build takes hours
```

Output: `output/fishball/images/sdimg/` (the files for the SD card) and `build/fishball.zip`.

Things that went wrong on the first build here, so you do not have to find out:
* `maia-httpd` needs **libclang** on the host (a bindgen step in `aws-lc-sys`). Without `libclang-dev` the Rust build stops. If libclang is not in a standard place, set `LIBCLANG_PATH`.
* The Dashboard step runs `npm ci`; it needs **Node** and a completed lock file (this branch has one).
* The kernel's gcc plugin needs the **gmp/mpc/mpfr headers**. They were supplied through `CPATH` here; installing the `-dev` packages above does the same. The build was not tried without them.
* `build.sh` needs **jq**.

## Write the SD card

The card needs one FAT32 partition with the contents of `output/fishball/images/sdimg/` at its root: `BOOT.bin`, `uImage`,
`devicetree.dtb`, `uramdisk.image.xz`, `uEnv.txt`, `system_top.bin`, `tezuka_top.bin` and the `overclock/` folder.

```sh
# Option A: format and write (erases the card; asks you to type YES; only accepts whole mmcblk devices of 64 GB or less)
lsblk                                         # find the card, e.g. /dev/mmcblk0, and check its size
sudo tools/fishball7010-write-sdcard.sh /dev/mmcblk0 output/fishball/images/sdimg

# Option B: copy onto a card that is already FAT32
cp -r output/fishball/images/sdimg/. /media/$USER/<card label>/ && sync
```

Set the boot-mode switch to SD, power on and open `https://192.168.2.1` (use `http://` to see the temperature readouts). After a boot the
network can take a few minutes to answer. If it does not boot, put the stock Tezuka release `sdimg/` on the card; that boots on this board.

## Where the CPU goes

`tools/cpu_profile.sh` samples `/proc` twice and prints the CPU split, forks and context switches per second, CPU by process (own time and
the time of short-lived children), the busiest threads of the main services, the busiest interrupts and the remote MQTT clients:
`ssh root@192.168.2.1 'WIN=60 sh -s' < tools/cpu_profile.sh`. On an idle radio (no Dashboard open, 60 second window) with the tick change
and the polling gate: CPU 94.5% idle, 4.3 forks per second, 137 timer interrupts per second, `api_controller.sh` 3.6% of one core (it was
7.4%); the classifier used 2.5% and `maia-httpd` 1.5%. Lessons from getting there: parsing `/proc/net/tcp` in bash costs 58 ms per call on this
CPU (66 lines), so the client check uses one awk (17 ms); and reading seven U-Boot variables one by one read the whole flash seven times.

## Checking a build on the radio

* `state/main/hw_model` reads `FISHBall-PlutoSky (Z7010-AD9363)`; the Dashboard's Architecture page says Zynq-7010 and AD9363.
* `state/main/cpu` settles at 12-17 and `state/main/forks_per_s` at about 4.
* Helpers: `app/classifier/tools/mqtt_watch.py 10 'state/classifier/#'` prints the classifier topics (plain Python, no packages), and
  `tools/cpio-diff.py a.cpio b.cpio` compares two root file systems file by file.
* The classifier only runs if `classifier_enabled` is 1 in the U-Boot environment (the Dashboard's Signal Classifier page toggles it).

## Clock spurs and the LO spike

The two big spikes either side of centre at 869 MHz were not DC. They stay at the same absolute frequency when the radio is retuned, so
they are harmonics of the board's own clocks. A sweep over 47 tunings with a 50 ohm terminator on RX-A (everything strong and narrow then
comes from the board) gave:

| Line | Source | Offset from nominal |
|---|---|---|
| centre bin | LO leakage | peak of 10-30 dB in all 37 usable tunings (median 11 dB) |
| 625.012, 875.018, 1625.032, 1875.033 MHz | 25 MHz x 25, 35, 65, 75 | +18 to +21 ppm |
| 666.671, 866.671, 1066.671 MHz | 100/3 MHz x 20, 26, 32 | +4.5 to +7 ppm |
| 706.656 MHz | not explained | one-off, not masked |

With the antenna on, the 875 MHz line is about 40 dB tall. `0002-spur-mask.patch` adds `src/spurmask.rs` to `maia-httpd` and calls it
where the FPGA's spectrum buffer becomes the `/waterfall` frame, so the Maia UI, the Dashboard and the classifier all see masked data:

* the centre bins are replaced with the level around them;
* a narrow line within 50 ppm of a harmonic of 25 MHz or 100/3 MHz, at least 8 dB above its surroundings and at most 5 bins wide (measured at
  half its height in dB, never more than 10 dB below the peak), is replaced with the level around it;
* IQ samples, recordings and libiio are **not** touched; only the AD9361 input is masked (not the DDC);
* a real narrow carrier exactly on a harmonic would be hidden too; creating `/mnt/jffs2/no-spur-mask` on the radio turns the mask off.

Checked on the live radio with the antenna on, 40 frames each: centre masked in 40 of 40 frames; the three strongest spurs above 10 dB in
0 of 40 frames; all 12 FM stations at 98 MHz still present. The Rust code has unit tests and masks the same bins as the Python prototype
(`app/classifier/tools/spurmask.py`) on the 16 recorded captures. Run the Rust tests with the Buildroot host compiler once `maia-httpd` has been
extracted (`output/fishball/build/maia-httpd-*/maia-httpd/src/spurmask.rs`):
`output/fishball/host/bin/rustc --edition 2024 --test spurmask.rs -o t && ./t`.

Re-measuring on another board: `app/classifier/tools/sweep_spurs.py` (terminator on RX-A) writes the lines it finds and
`analyse_spurs.py` shows which clock each is a harmonic of. The data from this board is `spur_sweep.json` here.

## Status

* Works: boot from SD (stock and this branch), USB and network, Maia SDR and Dashboard, RX-A (869 MHz, 800-900 MHz survey, 98 MHz FM, 2.4 GHz Wi-Fi).
* Partly checked: TX1-A at low power (the tone could be on-board coupling).
* Not tested: RX-B, TX2, gigabit Ethernet, the SD slot inside the radio, above 3.8 GHz, flashing to QSPI.
* Dashboard pages built from this branch were not opened in a browser (the bundle compiles; the values were checked over MQTT).

## What is in this directory

| Path | What |
|---|---|
| `history.md` | Project log of the first route (vendor boot files): findings, pitfalls, measurements |
| `results/` | RF test plots (869 MHz capture, TX tone test, 800-900 MHz sweep) |
| `vendor-devicetree.dts` | Decompiled device tree from the vendor SD card |
| `spur_sweep.json` | Spur sweep data (terminated input, 20.72 MS/s, gain 50) |
| `legacy/` | The first route: keep the vendor `BOOT.bin` and pack the kernel and Maia bitstream into a FIT image by hand. Not needed any more; kept because the vendor U-Boot has no LZMA support and ignores `setenv bootargs`, which is why the scripts look the way they do. The scripts expect to sit in a `scripts/` folder next to a `patches/` folder. |

Related: [app/classifier](../../app/classifier/README.md) (classifier source, reference implementation, 16 real captures, synthetic tests, radio helper tools).
