#!/bin/sh
# Where is the CPU going? Samples /proc twice, WIN seconds apart (default 20), and prints per-process and per-thread CPU,
# the system split (user/system/irq/softirq/iowait), forks and context switches per second, and the busiest interrupts.
# Plain POSIX sh and awk (BusyBox is fine); two awk passes, so the probe itself costs next to nothing.
# On the radio:  ssh root@192.168.2.1 'sh -s' < tools/cpu_profile.sh | tee /tmp/cpu_profile.txt
WIN=${WIN:-20}
T=/tmp/cpuprof.$$; mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
NCPU=$(grep -c '^cpu[0-9]' /proc/stat)
HZ=100   # clock ticks per second (USER_HZ is 100 on Linux/ARM)

snap() {   # <prefix>: per-process and per-thread tick counts, system counters, interrupts
  awk '{
    n = length($0); open = index($0, "(")
    for (i = n; i > 0; i--) if (substr($0, i, 1) == ")") break
    comm = substr($0, open + 1, i - open - 1); split(substr($0, i + 2), f, " ")
    print $1, comm, f[12] + f[13], f[14] + f[15]
  }' /proc/[0-9]*/stat > "$T/$1.proc" 2>/dev/null
  for d in /proc/[0-9]*; do p=${d#/proc/}; case $(cat "$d/comm" 2>/dev/null) in maia-httpd|classifier|mosquitto|api_controller*|iiod|mqtt_pubd) ;; *) continue;; esac
    awk -v p="$p" '{ n = length($0); open = index($0, "("); for (i = n; i > 0; i--) if (substr($0, i, 1) == ")") break
      split(substr($0, i + 2), f, " "); print p, $1, substr($0, open + 1, i - open - 1), f[12] + f[13] }' "$d"/task/[0-9]*/stat 2>/dev/null
  done > "$T/$1.thr"
  grep -E '^(cpu |cpu[0-9]|ctxt|processes|procs_running)' /proc/stat > "$T/$1.stat"
  awk '{ s = 0; for (i = 2; i <= NF; i++) if ($i ~ /^[0-9]+$/) s += $i; print s, $1, $NF, $(NF-1) }' /proc/interrupts > "$T/$1.irq"
}

echo "== $(cat /proc/loadavg) | uptime $(cut -d. -f1 /proc/uptime) s | $NCPU cpus | window $WIN s"
snap a; sleep "$WIN"; snap b

echo; echo "== system CPU split over the window (percent of all cpus)"
awk -v hz=$HZ -v win=$WIN 'FNR == NR { if ($1 ~ /^cpu/) for (i = 2; i <= 9; i++) a[$1, i] = $i; next }
  $1 ~ /^cpu/ { tot = 0; for (i = 2; i <= 9; i++) tot += $i - a[$1, i]
    if (tot > 0) printf "%-5s user %5.1f  nice %4.1f  system %5.1f  idle %5.1f  iowait %4.1f  irq %4.1f  softirq %4.1f\n", $1,
      100*($2-a[$1,2])/tot, 100*($3-a[$1,3])/tot, 100*($4-a[$1,4])/tot, 100*($5-a[$1,5])/tot, 100*($6-a[$1,6])/tot, 100*($7-a[$1,7])/tot, 100*($8-a[$1,8])/tot }' "$T/a.stat" "$T/b.stat"
awk -v win=$WIN 'FNR == NR { a[$1] = $2; next } $1 == "ctxt" || $1 == "processes" { printf "%s per second: %.1f\n", ($1 == "ctxt" ? "context switches" : "new processes (forks)"), ($2 - a[$1]) / win }' "$T/a.stat" "$T/b.stat"

echo; echo "== CPU by process: percent of ONE cpu (own = utime+stime; children = time of children that exited in the window, i.e. short-lived forks)"
awk -v hz=$HZ -v win=$WIN 'FNR == NR { own[$1] = $3; kid[$1] = $4; next }
  { d = $3 - own[$1]; k = $4 - kid[$1]; if ($1 in own || 1) { dd[$1] = d; kk[$1] = k; name[$1] = $2 } }
  END { for (p in dd) if (dd[p] > 0 || kk[p] > 0) printf "%6.1f %6.1f  %-6s %s\n", 100 * dd[p] / (hz * win), 100 * kk[p] / (hz * win), p, name[p] }' "$T/a.proc" "$T/b.proc" | sort -rn | head -14 | awk 'BEGIN { print "   own  child  pid    command" } { print }'

echo; echo "== busiest threads of the main services (percent of one cpu)"
awk -v hz=$HZ -v win=$WIN 'FNR == NR { a[$1 " " $2] = $4; next } { d = $4 - a[$1 " " $2]; if (d > 0) printf "%6.1f  pid %-5s tid %-5s %s\n", 100 * d / (hz * win), $1, $2, $3 }' "$T/a.thr" "$T/b.thr" | sort -rn | head -10

echo; echo "== busiest interrupts (per second, summed over cpus)"
awk -v win=$WIN 'FNR == NR { a[$2 " " $3 " " $4] = $1; next } { k = $2 " " $3 " " $4; d = $1 - a[k]; if (d > 0) printf "%8.1f  %s\n", d / win, k }' "$T/a.irq" "$T/b.irq" | sort -rn | head -8

echo; echo "== snapshot (BusyBox top, one iteration)"
top -bn1 2>/dev/null | head -16
echo; echo "== memory"; grep -E 'MemTotal|MemFree|MemAvailable|Buffers|^Cached|SwapTotal' /proc/meminfo
