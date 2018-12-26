import cv2
import logging

from queue import Empty
from threading import Thread
from time import sleep, time

from tracker.com_rio import NetworkClient
from tracker.com_video import CamHandler, stream_queue, ThreadedHTTPServer
from tracker.pipeline import Pipeline
from tracker.util import CircularBuffer


def processing_process(config, queue):
    """Process main - Vision Processing via GRIP Pipeline"""
    log = logging.getLogger('Processing')
    log.setLevel(logging.INFO)
    video = config['video'] == 1

    com = NetworkClient(config)
    processor = TargetProcessor(queue)
    processor.register(com, stream_queue)
    com.start()
    processor.start()

    if video:
        stream = ThreadedHTTPServer(('localhost', 8080), CamHandler)
        stream.queue = stream_queue

    try:
        if video:
            stream.serve_forever()
        while True:
            sleep(100)
    except KeyboardInterrupt:
        log.info("Shutting down")
        if video:
            stream.shutdown()
    finally:
        queue.close()
        queue.join_thread()
        com.shutdown()
        com.join()

        processor.shutdown()
        processor.join()
        if video:
            stream.server_close()

class TargetProcessor(Thread):
    """Image process each frame, detects targets, push to consumer(s)"""
    def __init__(self, queue):
        Thread.__init__(self)
        self.daemon = True
        self.rx_queue = queue
        self.pipeline = Pipeline() # Grip pipeline
        self.fps = CircularBuffer(15)
        self.time_last = time() - .001
        self.running = True

    def register(self, com, queue_stream):
        """Communication object to receive output data"""
        self.com = com
        self.stream = queue_stream

    def shutdown(self):
        self.running = False

    def run(self):
        """Process frame for targets"""
        while self.running:
            if self.rx_queue.empty():
                sleep(0) # Yield: Ahead of camera
                continue

            targets = ''
            num_targets = 0
            frame, t_taken = self.rx_queue.get(True, timeout=.1) # Throws Empty: Disconnected

            now = time()
            delta = now - self.time_last
            self.fps.append(1.0 / delta)
            self.time_last = now

            self.pipeline.process(frame)
            frame_h, frame_w, _ = frame.shape
            center_x = frame_w / 2.0
            center_y = frame_h / 2.0

            # Calculate the dimensions of the bounding rectangles
            # http://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html

            # Concatenation reasoning - https://waymoot.org/home/python_string/
            for index, contour in enumerate(self.pipeline.filter_contours_output):
                pixel_x, pixel_y, pixel_w, pixel_h = cv2.boundingRect(contour)
                percent_x = (pixel_x - center_x) / center_x  # -1 to 1
                percent_y = (pixel_y - center_y) / center_y  # -1 to 1
                targets += "{},{},{},{},".format( percent_x, percent_y, pixel_w, pixel_h)
                num_targets += 1

            coprocessor_data = "{},{},{},{},{},{}\n".format(
                (time() - t_taken) * 1000.0,
                frame_w,
                frame_h,
                self.fps.get_average(1),
                num_targets,
                targets,
            )
            self.com.transmit(coprocessor_data)
            if not self.stream.full():
                self.stream.put(frame)
