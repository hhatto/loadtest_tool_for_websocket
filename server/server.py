import msgpack
from tornado.ioloop import IOLoop
from tornado.ioloop import PeriodicCallback
from tornado.web import Application
from tornado.websocket import WebSocketHandler

LISTEN_PORT = 9000


class EchoBinaryMessageWebSocket(WebSocketHandler):

    def open(self):
        self.cb = PeriodicCallback(self._send_ping, 5000)
        self.cb.start()

    def _send_ping(self):
        self.ping("ping")

    def on_message(self, msg):
        unpack_data = msgpack.unpackb(msg)
        packed_msg = msgpack.packb(unpack_data)
        self.write_message(packed_msg, binary=True)

    def on_close(self):
        self.cb.stop()


application = Application([
    (r"/ws", EchoBinaryMessageWebSocket),
])

if __name__ == '__main__':
    application.listen(LISTEN_PORT)
    print("listen on port:{}".format(LISTEN_PORT))
    IOLoop.instance().start()
