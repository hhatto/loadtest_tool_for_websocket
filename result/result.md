## Machine
### cpu
```
$ cat /proc/cpuinfo     # 8core
processor   : 7
vendor_id   : GenuineIntel
cpu family  : 6
model       : 26
model name  : Intel(R) Core(TM) i7 CPU         960  @ 3.20GHz
stepping    : 5
cpu MHz     : 1600.000
cache size  : 8192 KB
physical id : 0
siblings    : 8
core id     : 3
cpu cores   : 4
apicid      : 7
initial apicid  : 7
fpu     : yes
fpu_exception   : yes
cpuid level : 11
wp      : yes
flags       : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good xtopology nonstop_tsc aperfmperf pni dtes64 monitor ds_cpl vmx est tm2 ssse3 cx16 xtpr pdcm sse4_1 sse4_2 popcnt lahf_lm ida dts tpr_shadow vnmi flexpriority ept vpid
bogomips    : 6383.46
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:
```

### memory
```
$ free
             total       used       free     shared    buffers     cached
Mem:       5981148    2545964    3435184          0     260224    1159768
-/+ buffers/cache:    1125972    4855176
Swap:      6127612     380896    5746716
```

### versions
* Python2.7.8
* Go1.4


## Results

### Go (gorilla/websocket)
```
{"mem.vss_human": "140.5 MB", "fds": 4101, "net.established": 4096, "net.time_wait": 0, "mem.vss": 147288064, "net.listen": 0, "mem.rss_human": "135.1 MB", "pid": 31880, "cpu": 34.8, "mem.rss": 141627392}

jenkins  31880 24.4  2.3 143836 138308 pts/1   Sl+  16:38   1:01 ./attacker.linux.nonwait -config ../test.conf.json

======= 2015-01-22 16:45:10.637969399 +0900 JST (elapsed: 6m20.007773097s)
tool's pid       : 31880
Target URL       : ws://localhost:9000/
Send Byte Size   : 1,161,425 [byte] (1.2MB)
Recive Byte Size : 1,161,420 [byte] (1.2MB)
Connection       : 4096 [conn]
Connect Time(avg): 0.8 [ms]
Connect Time(min): 0.4 [ms]
Connect Time(max): 159.9 [ms]
Message RTT (avg): 0.1 [ms]
Message RTT (min): 0.2 [ms]
Message RTT (max): 3.4 [ms]
```

### Python (websocket-client)
```
{"mem.vss_human": "220.5 MB", "fds": 4109, "net.established": 4096, "net.time_wait": 0, "mem.vss": 231243776, "net.listen": 0, "mem.rss_human": "19.4 MB", "pid": 32641, "cpu": 12.2, "mem.rss": 20353024}
{"mem.vss_human": "220.5 MB", "fds": 4109, "net.established": 4096, "net.time_wait": 0, "mem.vss": 231243776, "net.listen": 0, "mem.rss_human": "19.4 MB", "pid": 32642, "cpu": 12.4, "mem.rss": 20365312}
{"mem.vss_human": "516.1 MB", "fds": 4111, "net.established": 4096, "net.time_wait": 0, "mem.vss": 541212672, "net.listen": 0, "mem.rss_human": "20.9 MB", "pid": 32640, "cpu": 0.4, "mem.rss": 21950464}
{"mem.vss_human": "293.5 MB", "fds": 4106, "net.established": 4096, "net.time_wait": 0, "mem.vss": 307773440, "net.listen": 0, "mem.rss_human": "22.4 MB", "pid": 32534, "cpu": 0.2, "mem.rss": 23502848}
{"mem.vss_human": "219.2 MB", "fds": 4107, "net.established": 4096, "net.time_wait": 0, "mem.vss": 229883904, "net.listen": 0, "mem.rss_human": "19.3 MB", "pid": 32639, "cpu": 0.0, "mem.rss": 20262912}

jenkins  32534  1.3  0.3 300560 22952 pts/1    Sl+  16:53   0:04 python naive_attacker.py --config ../test.conf.json
jenkins  32639  0.0  0.3 224496 19788 pts/1    S+   16:55   0:00 python naive_attacker.py --config ../test.conf.json
jenkins  32640  0.1  0.3 528528 21436 pts/1    Sl+  16:55   0:00 python naive_attacker.py --config ../test.conf.json
jenkins  32641  8.8  0.3 225824 19876 pts/1    S+   16:55   0:21 python naive_attacker.py --config ../test.conf.json
jenkins  32642  8.5  0.3 225824 19888 pts/1    S+   16:55   0:20 python naive_attacker.py --config ../test.conf.json

======= 2015-01-22 17:00:24.221677 (elapsed: 0:06:29.614849)
tool's pid: 32534
target url: ws://localhost:9000/ws
Send Byte Size   : 634,880 [byte] (634.9 kB)
Recive Byte Size : 634,880 [byte] (634.9 kB)
Connection       : 4096 [conn]
Connect Time(avg): 1.7 [ms]
Connect Time(min): 1.0 [ms]
Connect Time(max): 160.4 [ms]
Message RTT (avg): 1.3 [ms]
Message RTT (min): 0.3 [ms]
Message RTT (max): 168.5 [ms]
```
