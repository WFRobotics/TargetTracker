import logging
import socket

from queue import Queue
from threading import Thread
from time import sleep


def build(data):
    src, frame, shape, contours, fps, delay, start_time = data
    targets = []

    height, width, _ = shape

    # Concatenation reasoning - https://waymoot.org/home/python_string/
    for index, contour in enumerate(contours):
        x, y, w, h = contour
        # use the map + str here to remove the extra parentheses from the tuple
        targets.append(",".join(map(str, (index,
                                          x + w / 2,  # center x
                                          y + h / 2,  # center y
                                          w,  # width
                                          h)  # height
                                    )))

    message_body = ",".join(str(val) for val in (
        1,  # version
        src,  # camera source
        width,  # image width
        height,  # image height
        fps,  # average fps
        start_time,  # when the frame was captured
        len(targets),  # number of targets found
        ",".join(str(val) for val in targets)  # list of targets
    )
                            )
    return "".join((str(len(message_body)), ",", message_body, "\n"))


class NetworkClient(Thread):
    """Communicates with RoboRIO server socket"""

    def processor_callback(self, data):
        """Receive message to send from another thread"""
        if self.connected:
            self.rx_queue.put(data)

    def register_listener(self, listener):
        self.listeners.append(listener)

    def __init__(self, host, port):
        super(NetworkClient, self).__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)
        self.rx_queue = Queue()
        self.connected = False
        self.running = True
        self.address = (host, port)
        self.listeners = []

    def shutdown(self):
        """Stop thread - Allow RIO socket to disconnect gracefully"""
        self.running = False

    def run(self):
        """Thread main - Sends messages"""
        self.log.info("Starting")
        while self.running:
            if not self.connected:
                self.connect()
                continue
            if self.rx_queue.empty():
                sleep(.01)  # 1/3 of 30 FPS, allow processing to run
                continue

            data = self.rx_queue.get(timeout=.01)
            try:
                message = build(data)
                self.sock.sendall(message.encode())

                response = self.sock.recv(1024)
                if response:
                    for listener in self.listeners:
                        listener(response)
            except (ConnectionResetError, socket.error) as e:
                self.log.error(e)
                self.connected = False
                self.sock.shutdown(socket.SHUT_RDWR)  # Faster reconnect
        self.log.info("Stopping")
        self.sock.close()

    def connect(self):
        """Init socket"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(.01)  # So socket connect() fails fast
        try:
            self.sock.connect(self.address)
            self.connected = True
            self.log.info('Connected to {}'.format(self.address))
        except socket.error as e:
            self.sock.close()
