from tornado import gen
from tornado.ioloop import PeriodicCallback, IOLoop
from tornado.websocket import websocket_connect
import msgpack


@gen.engine
def run():
    uri = "ws://localhost:9000/ws"
    ws = yield websocket_connect(uri)

    def send_msg():
        packed_data = msgpack.packb([{'a': 1}, ])
        ws.write_message(packed_data, True)

    task = PeriodicCallback(send_msg, 5000)
    task.start()
    while True:
        msg = yield ws.read_message()
    IOLoop.instance.stop()


def main():
    for cnt in range(100):
        IOLoop.instance().add_callback(run)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
