import argparse
import json
import os
import random
import time
from datetime import datetime
from Queue import Empty
from multiprocessing import Pool, Process, Queue
import humanize
import msgpack
import websocket

websocket_connections = []
testinfo = None


def connect(url):
    try:
        # timeout is 3sec
        ws = websocket.create_connection(url, timeout=3)
    except Exception as e:
        print('websocket access error [{}]: {}'.format(url, e))
        return
    return ws


def send_recv(ws):
    global websocket_connections, testinfo
    packed_data = msgpack.packb([{'a': 1}, ])
    websocket_connections[ws].send(packed_data, websocket.ABNF.OPCODE_BINARY)  # send with binary mode
    testinfo['AllSendByteSize'] += len(packed_data)
    testinfo['AllRecvByteSize'] += len(websocket_connections[ws].recv())


def dump_info(pid, info_queue):
    global testinfo
    while True:
        end = False
        try:
            end = info_queue.get(timeout=10)
        except Empty:
            continue
        if end is True:
            break
        testinfo.update(end)
        now =  datetime.now()
        print("======= %s (elapsed: %s)" % (now, now - testinfo['StartTime']))
        print("tool's pid: %d" % pid)
        print("target url: %s" % testinfo['TargetURL'])
        print("Send Byte Size   : %s [byte] (%s)" % (
            humanize.intcomma(testinfo['AllSendByteSize']), humanize.naturalsize(testinfo['AllSendByteSize'])))
        print("Recive Byte Size : %s [byte] (%s)" % (
            humanize.intcomma(testinfo['AllRecvByteSize']), humanize.naturalsize(testinfo['AllRecvByteSize'])))
        print("Connection       : %d [conn]" % testinfo['ConnectionNum'])
        print("Connect Time(avg): %.1f [ms]" % (testinfo['ConnExecTimeSum']/testinfo['ConnectionNum']))
        print("Connect Time(min): %.1f [ms]" % testinfo['ConnExecTimeMin'])
        print("Connect Time(max): %.1f [ms]" % testinfo['ConnExecTimeMax'])


def _exec(ws_pool_len, end_queue):
    pool = Pool(10)
    while True:
        a = pool.map(send_recv, range(ws_pool_len))
        end = False
        try:
            end = end_queue.get(timeout=random.randint(1, 10))
        except Empty:
            pass
        if end:
            break


def main():
    global websocket_connections, testinfo
    # FIXME: unable multi-process
    pid = os.getpid()
    que = Queue()
    info_queue = Queue()
    test_start = datetime.now()
    parser = argparse.ArgumentParser(description='stress test tool for websocket servers')
    parser.add_argument('--config', dest='config_file', required=True, help='config file')
    optargs = parser.parse_args()
    conf = json.load(open(optargs.config_file))
    testinfo = {
        'TargetURL': conf['url'] + 'ws',
        'StartTime': datetime.now(),
        'AllSendByteSize': 0,
        'AllRecvByteSize': 0,
        'ConnectionNum': 0,
        'ConnExecTimeSum': 0,
        'ConnExecTimeMin': 9999999999,
        'ConnExecTimeMax': 0,
    }

    # test info proc
    infoproc = Process(target=dump_info, args=(pid, info_queue, ))
    infoproc.start()

    # connect websocket
    for cnt in range(conf['loops']):
        start = datetime.now()
        ws = connect(conf['url'] + "ws")
        if ws:
            end = datetime.now()
            diff = end - start
            diff = diff.microseconds / 1000.     # milliseconds
            websocket_connections.append(ws)
            testinfo['ConnectionNum'] += 1
            testinfo['ConnExecTimeSum'] += diff
            if testinfo['ConnExecTimeMin'] > diff:
                testinfo['ConnExecTimeMin'] = diff
            if testinfo['ConnExecTimeMax'] < diff:
                testinfo['ConnExecTimeMax'] = diff
            time.sleep(conf['interval'] / 1000.)

    # test execution
    ws_pool_len = len(websocket_connections)
    testproc = Process(target=_exec, args=(ws_pool_len, que))
    testproc.start()
    print("keep %dsec" % (conf['keep']))
    num = 0
    while True:
        if (num % 10) == 1:
            info_queue.put(testinfo)
        diff = datetime.now() - test_start
        if diff.seconds >= conf['keep']:
            break
        num += 1
        time.sleep(1)

    # enqueue for proc end & wait proc
    que.put(True)
    info_queue.put(True)
    testproc.join()
    infoproc.join()

    # close sequence
    for con in websocket_connections:
        con.close()
    print("close all websocket connection")


if __name__ == '__main__':
    main()
