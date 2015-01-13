import argparse
import json
import os
import psutil


def _humanize_bytes(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def get_stats(pid=os.getpid()):
    proc = psutil.Process(pid)
    mem = proc.get_memory_info()
    fds = proc.get_num_fds()
    cpu = proc.cpu_percent()
    conns = proc.get_connections()
    net_established = len([c for c in conns if c.status == 'ESTABLISHED'])
    net_listen = len([c for c in conns if c.status == 'LISTEN'])
    net_time_wait = len([c for c in conns if c.status == 'TIME_WAIT'])
    stats = {
        "pid": pid,
        "fds": fds,
        "cpu": cpu,
        "net.established": net_established,
        "net.listen": net_listen,
        "net.time_wait": net_time_wait,
        "mem.rss": mem.rss,
        "mem.rss_human": _humanize_bytes(mem.rss),
        "mem.vss": mem.vms,
        "mem.vss_human": _humanize_bytes(mem.vms)
    }
    ret = json.dumps(stats)
    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='stress test tool for websocket servers')
    parser.add_argument('-p', '--pid', dest='pid', help='pid')
    args = parser.parse_args()
    pid = args.pid
    print(get_stats(int(pid)))
