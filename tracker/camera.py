import logging
import multiprocessing

from queue import Full
from time import sleep, time

import cv2


def camera_process(config, queue):
    """Process main - Camera"""
    log = multiprocessing.log_to_stderr()
    log.setLevel(logging.INFO)

    log.info("Starting")
    disconnected = True
    try:
        while True:
            if disconnected:
                disconnected, stream, rotate = connect(config)
                if not disconnected:
                    log.info("Connected")
                continue
            if queue.full():
                log.debug("Full")
                sleep(.01) # Ahead of processor
                continue

            retval, frame = stream.read()
            if not retval:
                disconnected = True
                log.warning("Disconnected")
                continue

            if rotate is None:
                queue.put((frame, time()))
            else:
                queue.put((cv2.rotate(frame, rotate), time()))
    except KeyboardInterrupt:
        log.info("Stopping")
    finally:
        queue.close()
        queue.join_thread()
        if stream.isOpened():
            stream.release()
    log.info("Exiting")


def connect(config):
    """Try to connect to hardware"""
    stream, rotate = make_camera(config)
    disconnected = not stream.isOpened()
    return disconnected, stream, rotate


def make_camera(config):
    """Returns configured camera stream"""
    rotate_options = {
        0 : None,
        90 : cv2.ROTATE_90_CLOCKWISE,
        180 : cv2.ROTATE_180,
        -90 : cv2.ROTATE_90_COUNTERCLOCKWISE,
    }

    stream = cv2.VideoCapture(config['src'])
    stream.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
    stream.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
    stream.set(cv2.CAP_PROP_EXPOSURE, config['exposure'])
    stream.set(cv2.CAP_PROP_BRIGHTNESS, config['brightness'])
    stream.set(cv2.CAP_PROP_SATURATION, config['saturation'])
    rotate = rotate_options[config['rotate']]

    return stream, rotate 
