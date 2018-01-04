#!python3.6

import argparse
import json
import logging
import msvcrt
import os.path
from multiprocessing import Pipe, Process
from time import sleep

import jsonschema
from cv2 import destroyAllWindows

from tracker.camera_multiprocess import camera_process
from tracker.message_config import MessageConfig
from tracker.network_client import NetworkClient
from tracker.process_pipeline import Processing
from tracker.stream_mjpg import StreamMjpg


class ComRouter:
    def __init__(self, network_callback, network_src, streamer_callback, streamer_src):
        self.network_callback = network_callback
        self.network_src = network_src
        self.streamer_callback = streamer_callback
        self.streamer_src = streamer_src

    def set_network_src(self, network_src):
        self.network_src = network_src

    def set_streamer_src(self, streamer_src):
        self.streamer_src = streamer_src

    def get_network_src(self):
        return self.network_src

    def get_streamer_src(self):
        return self.streamer_src

    def callback(self, data, src):
        if self.network_src == src:
            self.network_callback(data)
        if self.streamer_src == src:
            self.streamer_callback(data)


class TargetTracker:
    """
    Team 4818 WFRobotics Vision Coprocessor Application

    - Provides high-level operations to start/stop image processing, similar
      to a GUI's main form
    - Other operations are preferably self-contained by each stage of the
      image processing pipeline
    """

    default_camera = 0

    def __init__(self, config, show_local):
        logging.basicConfig()

        self.network = NetworkClient(config['network']['host'], config['network']['port'])
        self.streamer = StreamMjpg(config=config["streamer"], show_local=show_local)

        self.com_router = ComRouter(self.network.processor_callback,
                                    config['routes']['network'],
                                    self.streamer.processor_callback,
                                    config['routes']['streamer'])

        self.network.register_listener(self.config_message_listener)

        self.processors = []

        for index, config_cam in enumerate(config['cameras']):
            pipe_camera_output, pipe_processing_input = Pipe()
            name = "Camera process " + str(index)

            processor = Processing(config_cam["processor"])

            camera = Process(target=camera_process, args=(config_cam["camera"], pipe_camera_output), name=name)

            processor.register_listener(self.com_router.callback)
            processor.register_source(pipe_processing_input, index)

            processor.start()
            camera.start()
            pipe_camera_output.close()  # Must close main process reference

            self.processors.append(processor)

        self.set_processor_destinations(config['routes']['network'],
                                        config['routes']['streamer'])

        self.network.start()
        self.streamer.start()

    def set_processor_destinations(self, network_index, streamer_index):
        """Notify the Processors of which destination to use, between the network client and the streamer"""
        # since a camera/processor can be used to source the network and the streamer at the same time,
        # these cannot be mutually exclusive
        network_destinations = []
        streamer_destinations = []

        for i in self.processors:  # initialize them all to False so they can get disabled
            network_destinations.append(False)
            streamer_destinations.append(False)

        if 0 <= network_index < len(self.processors):
            network_destinations[network_index] = True

        if 0 <= streamer_index < len(self.processors):
            streamer_destinations[streamer_index] = True

        for i, _ in enumerate(self.processors):  # tell the processors which destination to use
            self.processors[i].set_destination(network_destinations[i], streamer_destinations[i])

    def config_message_listener(self, message):
        """Callback for when a configuration message is received to handle changing the settings"""
        # todo combine this with the ComRouter
        config_message = None
        if message:
            try:
                config_message = MessageConfig(message)
            except Exception as e:
                # todo print("failed to parse config")
                return

        if config_message and config_message.get_valid():
            # if is a valid message, set the network and stream sources
            self.com_router.set_network_src(config_message.get_network_source())
            self.com_router.set_streamer_src(config_message.get_streamer_source())

            # tell the processors which destination to use
            self.set_processor_destinations(config_message.get_network_source(),
                                            config_message.get_streamer_source())

            # and set the grip processor enables
            enables = config_message.get_processor_enable()
            if len(enables) == len(self.processors):
                for i, _ in enumerate(self.processors):
                    self.processors[i].set_grip_enable(enables[i])

    def __del__(self):
        self.network.shutdown()
        self.network.join()
        self.streamer.shutdown()
        self.streamer.join()

        destroyAllWindows()


def load_configs(host, user_config):
    """Load configuration files and validate them"""
    config = dict()

    schema_file = 'config.json_schema'

    # list of config files to try and load, latest file takes priority
    config_files = ['config_default.json', 'config_team.json']
    if user_config is not None:
        config_files.append(user_config)

    config_files_loaded = []
    for config_file in config_files:
        if os.path.isfile(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_new = json.load(f)
                config.update(config_new)
                config_files_loaded.append(config_file)
            except:
                print('Failed to load ', config_file)
                pass

    if config:
        print('Config files loaded, lowest priority first:')
        for config_file in config_files_loaded:
            print('  ', config_file)
    else:
        print('No config files loaded')
        raise Exception

    # only way host is not None here is if localhost was requested
    if host is None:
        # load the base value for the network here, but only set it
        if "network" in config:
            if "host" in config["network"]:
                host = config["network"]["host"]
    if host is None:
        # else ensure it gets set to a default value
        host = 'roborio-4818-frc.local'
    config["network"]["host"] = host  # write it back to ensure it has a value

    port = 5801
    if "network" in config:
        if "port" in config["network"]:
            port = config["network"]["port"]
    config["network"]["port"] = port  # write it back to ensure it has a value

    port_stream = 5802
    if "streamer" in config:
        if "port" in config["streamer"]:
            port_stream = config["streamer"]["port"]
    config["streamer"]["port"] = port_stream  # write it back to ensure it has a value

    # validate the config
    if os.path.isfile(schema_file):  # validate the json files themselves
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
                jsonschema.validate(config, schema)
        except jsonschema.exceptions.ValidationError as ve:
            print('Config failed validation: ' + str(ve))
            raise Exception
        except jsonschema.exceptions.SchemaError as se:
            print('Config Schema is not valid: ' + str(se))
            print('Continuing...')

    # prevent duplicate camera sources
    unique = []
    for cam in config['cameras']:
        if cam['camera']['src'] not in unique:
            unique.append(cam['camera']['src'])
        else:
            print('Config Error: Multiple cameras with the same source')
            raise Exception

    # TODO limit to 2 cameras only for now
    if len(config['cameras']) > 2:
        print('Config Error: Currently, only 2 cameras are supported')
        raise Exception

    # print some quick info
    print('Starting Configuration:')
    for cam in config['cameras']:
        print('   Camera \'{}\' - [{}] {} - {}'.format(
            cam['camera']['name'],
            cam['camera']['type'],
            str(cam['camera']['src']),
            'GRIP processing enabled' if not cam['processor']['disable'] else 'GRIP processing disabled'
        ))

    index = config['routes']['network']
    valid_cam = 0 <= index < len(config['cameras'])
    print('   Sending targets to {}:{} from \'{}\' camera'.format(
        config['network']['host'],
        str(config['network']['port']),
        config['cameras'][index]['camera']['name'] if valid_cam else '__NOT_ACTIVE__'
    ))

    if config['streamer']['stream']:
        index = config['routes']['streamer']
        valid_cam = 0 <= index < len(config['cameras'])
        print('   Streaming on port {} with quality of {}% from \'{}\' camera'.format(
            str(config['streamer']['port']),
            str(config['streamer']['quality']),
            config['cameras'][index]['camera']['name'] if valid_cam else '__NOT_ACTIVE__'
        ))
    else:
        print('  Streaming disabled')

    return config


# Entry Point
def main(host=None, show_local=False, user_config=None):
    """Team 4818 WFRobotics Vision Coprocessor"""

    config = load_configs(host, user_config)

    tracker = TargetTracker(config, show_local)

    sleep(1)

    print('\n--- Press escape or enter to exit ---\n')
    while True:
        try:
            sleep(1)  # Yield, periodically wake to allow exception

            if msvcrt.kbhit():
                key = ord(msvcrt.getch())
                if key is 27 or key is ord('\r'):
                    # catch escape or enter
                    break

        except KeyboardInterrupt:
            # catch ctrl-c
            break  # Exit app


# Entry Point
def main_local(show_local=False, user_config=None):
    """Test with sockets on this computer"""
    main(host='localhost', show_local=show_local, user_config=user_config)


def is_valid_file(parser, arg):
    """Used by arg parser to validate the specified configuration file is an actual file"""
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return arg


def parse_args():
    arg_parse = argparse.ArgumentParser()

    arg_parse.add_argument('--local',
                           help='Run the tracker in local mode for testing',
                           action='store_true')

    arg_parse.add_argument('--show_local',
                           help='Show the image locally',
                           action='store_true')

    arg_parse.add_argument('--config',
                           help="User config file",
                           metavar="FILE",
                           type=lambda x: is_valid_file(arg_parse, x))

    return arg_parse.parse_args()


if __name__ == '__main__':
    args = parse_args()

    if args.local:
        main_local(show_local=args.show_local,
                   user_config=args.config)
    else:
        main(show_local=args.show_local,
             user_config=args.config)
