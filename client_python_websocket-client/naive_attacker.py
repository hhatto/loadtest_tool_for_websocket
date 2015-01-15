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
    start = datetime.now()
    # send with binary mode
    websocket_connections[ws].send(packed_data, websocket.ABNF.OPCODE_BINARY)
    send_data_size = len(packed_data)
    recv_data_size = 0
    msg_num = 0
    while True:
        opcode, frame = websocket_connections[ws].recv_data_frame(True)
        if opcode == websocket.ABNF.OPCODE_PING:
            websocket_connections[ws].pong("")
            # print(ws, "pong")
        elif opcode == websocket.ABNF.OPCODE_BINARY:
            # print(ws, "data")
            recv_data_size += len(frame.data)
            msg_num += 1
            end = datetime.now()
            break
        else:
            # not support opcode in this tool
            # print(ws, "not support opcode:", opcode)
            break
    tat = end - start
    # print("s: %d, r: %d" % (send_data_size, recv_data_size))
    return send_data_size, recv_data_size, tat.microseconds / 1000., msg_num


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
            print("Message TAT (avg): %.1f [ms]" % (
                testinfo['MsgTATSum']/testinfo['MsgNum']))
            print("Message TAT (min): %.1f [ms]" % testinfo['MsgTATMin'])
            print("Message TAT (max): %.1f [ms]" % testinfo['MsgTATMax'])
        except ZeroDivisionError:
            pass


def _exec(ws_pool_len, end_queue, datasize_queue):
    pool = Pool(2)
    while True:
        ret = pool.map(send_recv, range(ws_pool_len))
        t = [sum([d[0] for d in ret]), sum([d[1] for d in ret]),
             [d[2] for d in ret], sum([d[3] for d in ret])]
        datasize_queue.put(t)
        end = False
        try:
            end = end_queue.get(timeout=random.randint(3, 10))
        except Empty:
            pass
        if end:
            break


def main():
    global websocket_connections, testinfo
    pid = os.getpid()
    end_queue = Queue()
    info_queue = Queue()
    datasize_queue = Queue()
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
        'MsgNum': 0,
        'MsgTATSum': 0,
        'MsgTATMin': 9999999999,
        'MsgTATMax': 0,
    }

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
        else:
            print("connection error")
        time.sleep(conf['interval'] / 1000.)

    # test info proc
    infoproc = Process(target=dump_info, args=(pid, info_queue, ))
    infoproc.start()

    # test execution
    ws_pool_len = len(websocket_connections)
    testproc = Process(target=_exec, args=(ws_pool_len, end_queue, datasize_queue))
    testproc.start()
    print("keep %dsec" % (conf['keep']))
    old_diff = datetime.now() - test_start
    while True:
        diff = datetime.now() - test_start
        if (diff.seconds % 10) == 0 and old_diff.seconds != diff.seconds:
            info_queue.put(testinfo)
        if diff.seconds >= conf['keep']:
            break
        old_diff = diff
        try:
            s, r, tat_list, msg_num = datasize_queue.get(timeout=1)
        except Empty:
            continue
        testinfo['AllSendByteSize'] += s
        testinfo['AllRecvByteSize'] += r
        testinfo['MsgNum'] += msg_num
        testinfo['MsgTATSum'] += sum(tat_list)
        m = min(tat_list)
        if testinfo['MsgTATMin'] > m:
            testinfo['MsgTATMin'] = m
        m = max(tat_list)
        if testinfo['MsgTATMax'] < m:
            testinfo['MsgTATMax'] = m

    # enqueue for proc end & wait proc
    end_queue.put(True)
    info_queue.put(True)
    testproc.join()
    infoproc.join()

    # close sequence
    for con in websocket_connections:
        con.close()
    print("close all websocket connection")


if __name__ == '__main__':
    main()
