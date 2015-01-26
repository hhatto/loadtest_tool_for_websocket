import argparse
import json
import os
import random
import threading
import time
from datetime import datetime
import humanize
import msgpack
from tornado import gen
from tornado.ioloop import PeriodicCallback, IOLoop
from tornado.websocket import websocket_connect

Sem = threading.Semaphore()
rtt_info = {
    'TargetID': None,
    'MsgNum': 0,
    'Sum': 0,
    'Min': 9999999999,
    'Max': 0,
}
testinfo = {
    'TargetURL': '',
    'StartTime': datetime.now(),
    'AllSendByteSize': 0,
    'AllRecvByteSize': 0,
    'ConnectionNum': 0,
    'ConnExecTimeSum': 0,
    'ConnExecTimeMin': 9999999999,
    'ConnExecTimeMax': 0,
}
conf = None


@gen.engine
def run():
    global testinfo, rtt_info, conf
    uri = testinfo['TargetURL']

    start = datetime.now()
    ws = yield websocket_connect(uri)
    end = datetime.now()

    # for RTT info
    if not rtt_info['TargetID']:
        rtt_info['TargetID'] = id(ws)

    connect_end_time = datetime.now()
    diff = end - start
    diff = diff.microseconds / 1000.    # msec
    testinfo['ConnectionNum'] += 1
    testinfo['ConnExecTimeSum'] += diff
    if testinfo['ConnExecTimeMin'] > diff:
        testinfo['ConnExecTimeMin'] = diff
    if testinfo['ConnExecTimeMax'] < diff:
        testinfo['ConnExecTimeMax'] = diff

    is_maxcon = False
    if testinfo['ConnectionNum'] >= conf['loops']:
        print("keep %d sec" % conf['keep'])
        is_maxcon = True

    def send_msg():
        packed_data = msgpack.packb([{'a': 1}, ])
        start = datetime.now()
        ws.write_message(packed_data, True)
        testinfo['AllSendByteSize'] += len(packed_data)
        if rtt_info['TargetID'] == id(ws):
            rtt_info['Start'] = start

    def wrap_send_msg():
        offset = random.randint(2, 7)
        IOLoop.instance().call_later(offset, send_msg)

    task = PeriodicCallback(wrap_send_msg, 3000)
    task.start()
    while True:
        msg = yield ws.read_message()
        end = datetime.now()
        testinfo['AllRecvByteSize'] += len(msg)
        if rtt_info['TargetID'] == id(ws):
            diff = end - rtt_info['Start']
            rtt_info['MsgNum'] += 1
            _tmp = diff.microseconds / 1000.
            rtt_info['Sum'] += _tmp
            if rtt_info['Min'] > _tmp:
                rtt_info['Min'] = _tmp
            if rtt_info['Max'] < _tmp:
                rtt_info['Max'] = _tmp
        diff = end - connect_end_time
        if diff.seconds > conf['keep'] and is_maxcon:
            break
    IOLoop.instance().stop()


def wrap_dump_info():
    global testinfo, rtt_info
    pid = os.getpid()

    def dump_info(pid):
        now = datetime.now()
        try:
            print("======= %s (elapsed: %s)" % (now, now - testinfo['StartTime']))
            print("tool's pid: %d" % pid)
            print("target url: %s" % testinfo['TargetURL'])
            print("Send Byte Size   : %s [byte] (%s)" % (
                humanize.intcomma(testinfo['AllSendByteSize']),
                humanize.naturalsize(testinfo['AllSendByteSize'])))
            print("Recive Byte Size : %s [byte] (%s)" % (
                humanize.intcomma(testinfo['AllRecvByteSize']),
                humanize.naturalsize(testinfo['AllRecvByteSize'])))
            print("Connection       : %d [conn]" % testinfo['ConnectionNum'])
            print("Connect Time(avg): %.1f [ms]" % (
                testinfo['ConnExecTimeSum']/testinfo['ConnectionNum']))
            print("Connect Time(min): %.1f [ms]" % testinfo['ConnExecTimeMin'])
            print("Connect Time(max): %.1f [ms]" % testinfo['ConnExecTimeMax'])
            print("Message RTT (avg): %.1f [ms]" % (
                rtt_info['Sum']/rtt_info['MsgNum']))
            print("Message RTT (min): %.1f [ms]" % rtt_info['Min'])
            print("Message RTT (max): %.1f [ms]" % rtt_info['Max'])
        except ZeroDivisionError:
            pass

    IOLoop.instance().call_later(0.1, dump_info, pid)


def main():
    global testinfo, conf
    parser = argparse.ArgumentParser(description='stress test tool for websocket servers')
    parser.add_argument('--config', dest='config_file', required=True, help='config file')
    optargs = parser.parse_args()
    conf = json.load(open(optargs.config_file))

    testinfo['StartTime'] = datetime.now()
    testinfo['TargetURL'] = conf['url'] + 'ws'
    for offset, cnt in enumerate(range(conf['loops'])):
        IOLoop.instance().call_later(offset * conf['interval'] / 1000., run)

    info_task = PeriodicCallback(wrap_dump_info, 10 * 1000)
    info_task.start()

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
