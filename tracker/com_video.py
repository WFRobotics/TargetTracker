import cv2

from queue import Empty, Queue
from time import sleep

from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn

stream_queue = Queue(1)


class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                try:
                    if stream_queue.empty():
                        sleep(0)
                        continue
                    img = stream_queue.get()
                    retval, jpg = cv2.imencode('.jpg', img)
                    jpg_bytes = jpg.tobytes()
                    self.wfile.write(b"\r\n--jpgboundary\r\n")
                    self.send_header('Content-type','image/jpeg')
                    self.send_header('Content-length', len(jpg_bytes))
                    self.end_headers()
                    self.wfile.write(jpg_bytes)
                except KeyboardInterrupt:
                    break
            return
        if self.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(b'<html><head></head><body>')
            self.wfile.write(b'<img src="http://127.0.0.1:8080/cam.mjpg"/>')
            self.wfile.write(b'</body></html>')
            return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
