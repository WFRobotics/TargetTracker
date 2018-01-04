#!/usr/bin/env python

import csv


class MessageConfig:

    def __init__(self, raw_message):
        # Message is formatted as comma separated list of
        # MsgLength,Version,CameraSource,Width,Height,Exposure,Brightness,Saturation

        self.valid = False

        # check if we actually received a message
        if raw_message is not None:
            # Weird garbage to handle when we get more than one 'message'
            # per receive
            reader = list([row for row in csv.reader(raw_message.decode().splitlines())])

            row = reader[0]
            i = 0

            self.length = int(row[i])
            i += 1
            self.version = int(row[i])
            i += 1
            self.network_source = int(row[i])
            i += 1
            self.streamer_source = int(row[i])
            i += 1
            self.camera_count = int(row[i])
            i += 1
            self.processor_enable = []
            if self.camera_count > 0:
                for x in range(self.camera_count):
                    self.processor_enable.append(row[i] == '1')
                    i += 1
            self.valid = True

        else:
            self.length = 0
            self.version = 0
            self.network_source = 0
            self.streamer_source = 0
            self.camera_count = 0
            self.processor_enable = []

    def get_valid(self):
        """Was the message valid?"""
        return self.valid

    def get_version(self):
        """Version of the message"""
        return self.version

    def get_network_source(self):
        """Camera/Processing source for the network client messages"""
        return self.network_source

    def get_streamer_source(self):
        """Camera/Processing source for the video streamer"""
        return self.streamer_source

    def get_camera_count(self):
        """Count of cameras used for the array of GRIP processing enable flags"""
        return self.camera_count

    def get_processor_enable(self):
        """Array of GRIP processing enable flags"""
        return self.processor_enable
