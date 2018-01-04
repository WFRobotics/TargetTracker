import logging
from queue import Queue
from threading import Event, Thread
from time import time

import cv2
from tracker.circular_buffer import CircularBuffer

from tracker.grip_pipeline import Pipeline


class PipelineBuilder:
    @staticmethod
    def build(config=None):
        # create the base Pipeline
        pipeline = Pipeline()

        # then configure it if given values
        if config is not None:
            if "pipeline" in config:
                config_pipe = config["pipeline"]
                for stage_name, stage in config_pipe.items():
                    for setting_name, setting in stage.items():
                        # todo make this set variables based on the input strings if possible
                        if stage_name == 'hsv_threshold':
                            if setting_name == 'hue':
                                pipeline.__hsv_threshold_hue = setting
                            elif setting_name == 'saturation':
                                pipeline.__hsv_saturation_hue = setting
                            elif setting_name == 'value':
                                pipeline.__hsv_value_hue = setting
                        if stage_name == 'hsl_threshold':
                            if setting_name == 'hue':
                                pipeline.__hsl_threshold_hue = setting
                            elif setting_name == 'saturation':
                                pipeline.__hsl_saturation_hue = setting
                            elif setting_name == 'luminosity':
                                pipeline.__hsl_luminosity_hue = setting
                        elif stage_name == 'filter_contours':
                            if setting_name == 'min_area':
                                pipeline.__filter_contours_min_area = setting
                            elif setting_name == 'max_area':
                                pipeline.__filter_contours_max_area = setting
                            elif setting_name == 'min_perimeter':
                                pipeline.__filter_contours_min_perimeter = setting
                            elif setting_name == 'max_perimeter':
                                pipeline.__filter_contours_max_perimeter = setting
                            elif setting_name == 'min_width':
                                pipeline.__filter_contours_min_width = setting
                            elif setting_name == 'max_width':
                                pipeline.__filter_contours_max_width = setting
                            elif setting_name == 'min_height':
                                pipeline.__filter_contours_min_height = setting
                            elif setting_name == 'max_height':
                                pipeline.__filter_contours_max_height = setting
                            elif setting_name == 'solidarity':
                                pipeline.__filter_contours_solidity = setting
                            elif setting_name == 'min_vertices':
                                pipeline.__filter_contours_min_vertices = setting
                            elif setting_name == 'max_vertices':
                                pipeline.__filter_contours_max_vertices = setting
                            elif setting_name == 'min_ratio':
                                pipeline.__filter_contours_min_ratio = setting
                            elif setting_name == 'max_ratio':
                                pipeline.__filter_contours_max_ratio = setting
        return pipeline


class Processing(Thread):
    """Image process each frame, detects targets, push to consumer(s)"""

    def __interprocess(self, pipe, queue, rx_handle):
        """Helper thread - Grab frames, ensures camera process never blocked"""
        # Note: A few FPS faster as class method + local thread varaibles - DRL
        while True:
            try:
                queue.put(pipe.recv())
                rx_handle.set()
            except EOFError:
                break  # Camera process pipe EOF signaled its close()

    def __init__(self, config=None):
        super(Processing, self).__init__(daemon=True)
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        self.rx_queue = Queue()
        self.rx_handle = Event()
        self.rx_pipe = None
        self.listeners = []
        
        self.pipeline = PipelineBuilder.build(config)
        self.grip_enable = True
        if (config is not None) and ("disable" in config):
            self.grip_enable = not config["disable"]
        self.network = False
        self.streamer = False

        self.fps = CircularBuffer(25)
        self.delay = CircularBuffer(25)
        self.time_last = time()
        
    def register_listener(self, callback):
        """Connect to recipient of processed data"""
        self.listeners.append(callback)

    def register_source(self, pipe, src):
        """Connect to source of frames"""
        self.rx_pipe = pipe
        self.src = src

        dequeuer = Thread(
            target=self.__interprocess,
            args=(self.rx_pipe, self.rx_queue, self.rx_handle,),
            name='Dequeuer',
        )
        dequeuer.daemon = True
        dequeuer.start()

    def set_grip_enable(self, grip_enable):
        self.grip_enable = grip_enable

    def set_destination(self, network, streamer):
        self.network = network
        self.streamer = streamer

    def run(self):
        """Image process frames, give to listener"""
        self.log.info("Starting")
        while True:
            if self.rx_queue.empty():
                self.rx_handle.wait(.5)  # Don't run until a frame gets queued
            if self.rx_handle.is_set():
                self.rx_handle.clear()
            else:
                continue
            data = self.process_frame()
            for listener in self.listeners:
                listener(data, self.src)
        self.log.info("Stopping")

    def process_frame(self):
        """Process frame"""
        frame, start = self.rx_queue.get()

        contours = []
        if self.grip_enable:
            self.pipeline.process(frame)

            # TODO rotation? See 7b at
            # http://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
            # Get the bounding rectangles
            if self.pipeline.filter_contours_output is not None:
                for contour in self.pipeline.filter_contours_output:
                    contours.append(cv2.boundingRect(contour))

        # get some timing metrics
        now = time()
        duration = now - self.time_last
        fps = 1 / duration if duration else 1  # TODO consider lock to fix?
        self.fps.append(fps)
        self.delay.append(1000 * (now - start))
        self.time_last = now

        if self.streamer:  # check streamer first as both
            return self.src, frame, frame.shape, contours, self.fps.get_average(1), self.delay.get_average(1), start
        if self.network:
            return self.src, None, frame.shape, contours, self.fps.get_average(1), self.delay.get_average(1), start
