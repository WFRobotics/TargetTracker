#!python3.6

import argparse
import json
import logging
import os

from multiprocessing import Queue, Process
from threading import Thread
from time import sleep

from tracker.camera import camera_process
from tracker.processor import processing_process


def load_config(path_rel, grip, show_local):
    """Read JSON, update with arparse args, return dict"""
    if path_rel is None:
        path_rel = 'config\\robot.json'
    pwd = os.path.dirname(__file__)
    path_abs = os.path.join(pwd, path_rel)
    with open(path_abs, 'r') as f:
        s = f.read()
        config = json.loads(s)
        config.update({'grip': grip, 'show': show_local})
        for key, val in config.items():
            print(key, val)
    return config


def start_target_tracker(config):
    """STEM Alliance of Fargo Moorhead Vision Coprocessor Application"""
    queue = Queue(1)  # Camera to Processor frames, size of 1: Camera blocked until pop
    args = (config, queue)
    camera = Process(target=camera_process, args=args, name='Camera', daemon=True)
    processor = Thread(target=processing_process, args=args, name='Processing', daemon=True)

    processor.start()
    camera.start()


# Entry Point
def main(path='config\\robot.json', grip=True, show_local=False):
    """Team 4818 WFRobotics Vision Coprocessor"""
    logging.basicConfig()

    config = load_config(path, grip, show_local) 
    start_target_tracker(config)
    print('\n--- Press Ctrl + C to exit ---\n')

    while True:
        try:
            sleep(0.1)  # Yield: Periodically wake so Ctrl + C can kill app
        except KeyboardInterrupt:
            break  # Exit app


# Entry Point
def main_local():
    """Test with sockets on this computer"""
    path = 'config\\test_local.json'
    main(path, grip=True, show_local=False) 


if __name__ == '__main__':
    arg_parse = argparse.ArgumentParser()

    # TODO Just pass the config path?
    arg_parse.add_argument('--local',
                           help='Connect to the Java test app',
                           action='store_true')

    arg_parse.add_argument('--no_grip',
                           help='Prevent the GRIP Pipeline from running',
                           action='store_true')

    arg_parse.add_argument('--show_local',
                           help='Pop up a video stream window',
                           action='store_true')
    args = arg_parse.parse_args()

    if args.local:
        path = 'config\\test_local.json'
    else:
        path = 'config\\robot.json'

    main(path, grip=not args.no_grip, show_local=args.show_local)
