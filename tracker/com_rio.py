import logging
import multiprocessing
import socket

from threading import Lock, Thread
from time import sleep, time


class NetworkClient(Thread):
    """Communicates with RoboRIO server socket"""
    def __init__(self, config):
        super(NetworkClient, self).__init__(name='COM')
        self.log = logging.getLogger('COM') 
        self.log.setLevel(logging.INFO)
        self.address = (config['host'], config['port'])
        self.lock = Lock() # Reduce latency by locking vs enqueuing
        self.connected = False
        self.running = True
        self.connect()
        self.log.info("Timeout for COM operations: {}s".format(self.sock.gettimeout()))

    def shutdown(self):
        """Stop thread - Allow RIO socket to disconnect gracefully"""
        self.running = False

    def run(self):
        """Thread main - Service Connecting, transmit is done from calling thread"""
        self.log.info("Starting")
        while self.running:
            if not self.connected:
                self.connect()
            sleep(0.1) # Yield: Between servicing connection
        self.log.info("Stopping")
        self.sock.close()

    def transmit(self, coprocessor_data):
        """Send message over the socket to RIO"""
        self.lock.acquire()
        if self.connected:
            try:
                self.sock.sendall(coprocessor_data.encode())
            except (ConnectionResetError, socket.error) as e:
                self.log.error(e)
                self.connected = False
        self.lock.release()

    def connect(self):
        """Init socket"""
        self.lock.acquire()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(.25)  # So socket connect() fails fast
        try:
            self.sock.connect(self.address)
            self.connected = True
            self.log.info('Connected to {}'.format(self.address))
        except socket.error as e:
            self.sock.close()
            self.connected = False
        self.lock.release()
