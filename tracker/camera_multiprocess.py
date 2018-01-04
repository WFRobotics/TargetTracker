import logging
import multiprocessing

import cv2
from time import time


def camera_process(config, pipe_out):
    """Process main - Camera"""
    log = multiprocessing.log_to_stderr()
    log.setLevel(logging.INFO)
    config, disconnected, stream = connect(config)

    log.info("Starting")
    try:
        while True:
            if disconnected:
                config, disconnected, stream = connect(config)
                continue

            start = time()
            retval, frame = stream.read()
            if not retval:
                disconnected = True
                log.warning("Disconnected")
                continue

            if config['rotate']:
                if config['rotate'] == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif config['rotate'] == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif config['rotate'] == -90 or config['rotate'] == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            pipe_out.send((frame, start))
    except KeyboardInterrupt:
        log.debug("Stopping")
    pipe_out.close()
    stream.release()
    log.debug("Exiting")
    cv2.destroyAllWindows()


def connect(config):
    """Try to connect to hardware"""
    config, stream = make_camera(config)
    disconnected = not stream.isOpened()
    return config, disconnected, stream


# TODO Instead configure with camera builder
def make_camera(config_new):
    """Configure camera"""
    # set default values
    config = dict()
    config['width'] = 640
    config['height'] = 480
    config['rotate'] = 0
    config['exposure'] = -8
    config['brightness'] = 40
    config['saturation'] = 200

    if config is not None:
        # but then overwrite any that were passed in
        config.update(config_new)

    stream = cv2.VideoCapture(config['src'])
    stream.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
    stream.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
    stream.set(cv2.CAP_PROP_EXPOSURE, config['exposure'])
    stream.set(cv2.CAP_PROP_BRIGHTNESS, config['brightness'])
    stream.set(cv2.CAP_PROP_SATURATION, config['saturation'])

    return config, stream
