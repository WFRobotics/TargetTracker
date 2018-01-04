import logging
import socket
import time

import cv2

from os import curdir, sep
from queue import Queue
from threading import Thread

try:
    # Python 3
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs
    from socketserver import ThreadingMixIn
except ModuleNotFoundError:
    # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from urlparse import parse_qs
    from SocketServer import ThreadingMixIn


# todo find better ways to share these between the threads
stop_response = False
processed_frames = None
quality = 80


DEERE_GREEN = (43, 124, 54)
DEERE_YELLOW = (23, 225, 251)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (0, 255, 255)


class MjpgHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        self.log.info("%s - - [%s] %s\n" % (self.address_string(),
                                            self.log_date_time_string(),
                                            format % args))

    def handle(self):
        """Handles a request ignoring dropped connections."""

        try:
            return BaseHTTPRequestHandler.handle(self)
        except (socket.error, socket.timeout):
            self.connected = False

    def do_GET(self):
        """Handle a GET request"""

        global stop_response
        global processed_frames
        global quality

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        self.connected = True

        if self.path.endswith('mjpg'):
            # stream the actual mjpg image

            self.send_response(200)
            self.send_header(
                'Content-type',
                'multipart/x-mixed-replace; boundary=--jpgboundary',
                )
            self.end_headers()

            jpg = None
            frame = None

            # continue running until externally cancelled
            while not stop_response:

                # grab frames if they're available
                if processed_frames.empty():
                    time.sleep(.01)
                    continue

                frame, targets, fps, delay = processed_frames.get(block=False)

                if frame is None:
                    continue

                ret, jpg = cv2.imencode('.jpg', frame,
                                        [int(cv2.IMWRITE_JPEG_QUALITY), quality])

                if jpg is None:
                    continue

                self.wfile.write('--jpgboundary'.encode())
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Content-length', str(jpg.size))
                self.end_headers()
                if self.connected:
                    self.wfile.write(jpg.tostring())
        else:
            #
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            if self.connected:
                f = open(curdir + sep + 'streamer' + sep + 'index.html', 'rb')
                self.wfile.write(f.read())
                f.close()

    # def parse_POST(self):
    #     ctype, pdict = parse_header(self.headers['content-type'])
    #     if ctype == 'multipart/form-data':
    #         postvars = parse_multipart(self.rfile, pdict)
    #     elif ctype == 'application/x-www-form-urlencoded':
    #         length = int(self.headers['content-length'])
    #         postvars = parse_qs(
    #                 self.rfile.read(length),
    #                 keep_blank_values=1)
    #     else:
    #         postvars = {}
    #     return postvars
    #
    # def do_POST(self):
    #     # todo get this working
    #     #global rootnode, cameraQuality
    #     self.connected = True
    #     self.log = logging.getLogger(self.__class__.__name__)
    #     self.log.setLevel(logging.INFO)
    #
    #     try:
    #         postvars = self.parse_POST()
    #         self.log.info(postvars[0])
    #         value = int(postvars[0])
    #         cameraQuality = max(2, min(99, value))
    #         self.wfile.write("<HTML>POST OK. Camera Set to<BR><BR>");
    #         self.wfile.write(str(cameraQuality));
    #
    #     except:
    #         pass


class StreamMjpgServer(Thread):

    def __init__(self, host, port):
        Thread.__init__(self, name=self.__class__.__name__)
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        # TODO consider making this threaded to allow multiple stream
        # connections currently, threading makes it lag bad, so only one
        # connection at a time
        self.server = HTTPServer((host, port), MjpgHandler)

    def run(self):
        try:
            self.log.info('Starting')
            # Start the server
            # Note: This blocks, hence why it needs to be started from a thread
            self.server.serve_forever()

        except KeyboardInterrupt:
            pass

        finally:
            self.log.info('Stopping')
            self.server.server_close()

    def stop(self):
        global stop_response

        # tell the Request Handler to stop serving frames
        stop_response = True

        # tell the HTTPServer to stop handling requests
        self.server.stop_flag = True

        # finally shut the server down
        self.server.shutdown()


class StreamMjpg(Thread):
    def processor_callback(self, data):
        """Receive processed data tuple from processing thread"""
        global processed_frames
        src, frame, shape, contours, fps, delay, start = data

        # todo handle switching cameras and post-processing image
        # and do this in a better spot
        # todo get the connection status from the network client
        frame = create_image(frame, contours, fps, delay, False)

        # todo able to do this with only one queue?
        if self.show_local:
            # prevent the queue from adding additional frames if it's full
            if self.show_frames.full():
                self.show_frames.get(block=False)
            self.show_frames.put((frame, contours, fps, delay))

        if self.send:
            # prevent the queue from adding additional frames if it's full
            if processed_frames.full():
                processed_frames.get(block=False)
            processed_frames.put((frame, contours, fps, delay))

    def __init__(self, config, show_local):
        super(StreamMjpg, self).__init__()
        global processed_frames
        global quality
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        self.send = True
        if "stream" in config:
            self.send = config["stream"]
        if "quality" in config:
            quality = config["quality"]

        if self.send:
            processed_frames = Queue(maxsize=10)
            self.stream = StreamMjpgServer('localhost', config["port"])

        self.show_frames = Queue(maxsize=10)
        self.show_local = show_local

        self.running = True

    def shutdown(self):
        """Stop thread - TODO what this means"""
        self.running = False

    def run(self):
        """Thread main - Show frames in local app window"""
        window_name = '4818 Target Tracker'
        if self.show_local:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        if self.send:
            self.stream.start()

        while self.running:
            if not self.show_local or self.show_frames.empty():
                time.sleep(.01)
                continue

            frame, targets, fps, delay = self.show_frames.get(block=False)
            if frame is not None:
                cv2.imshow(window_name, frame)
                cv2.waitKey(1)
        self.stream.stop()
        self.stream.join()


def create_image(frame, targets, fps, delay, connected):
    h, w, c = frame.shape

    if connected:
        cv2.rectangle(frame, (2, 2), (15, 15), GREEN, -1)
    else:
        cv2.rectangle(frame, (2, 2), (15, 15), RED, -1)

    # put the FPS info on the image
    put_text_shadow(frame,
                    "{:3.0f} fps".format(fps),
                    w - 80,
                    15)
    put_text_shadow(frame,
                    "{:3.0f} ms".format(delay),
                    w - 80,
                    30)

    if targets is not None:
        put_text_shadow(frame,
                        "{:3.0f} found".format(len(targets)),
                        w - 80,
                        45)

        # draw the contour rectangles
        for contour in targets:
            x, y, w, h = contour
            cv2.rectangle(frame, (x, y), (x + w, y + h),
                          DEERE_YELLOW, 3)

    return frame


def put_text_shadow(frame, text, x, y,
                    font=cv2.FONT_HERSHEY_SIMPLEX,
                    scale=0.5,
                    back=BLACK,
                    fore=WHITE,
                    thickness=1):
    # draw shadow
    cv2.putText(frame,
                text,
                (x - 1, y - 1),
                font,
                scale,
                back,
                thickness,
                cv2.LINE_AA)
    cv2.putText(frame,
                text,
                (x + 1, y + 1),
                font,
                scale,
                back,
                thickness,
                cv2.LINE_AA)
    # draw foreground
    cv2.putText(frame,
                text,
                (x, y),
                font,
                scale,
                fore,
                thickness,
                cv2.LINE_AA)
