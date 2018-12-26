#!/usr/bin/env python

import csv


class MessageConfig:

    def __init__(self, RawMessage):
        # Message is formatted as comma separated list of
        # MsgLength,Version,CameraSource,Width,Height,Exposure,Brightness,Saturation

        self.Valid = False

        # check if we actually received a message
        if RawMessage is not None:
            # Weird garbage to handle when we get more than one 'message' per receive
            reader = list([row for row in csv.reader(RawMessage.splitlines())])

            row = reader[0]

            i = 0

            self.Length = int(row[i])
            i += 1
            self.Version = int(row[i])
            i += 1
            self.Source = int(row[i])
            i += 1
            self.Width = int(row[i])
            i += 1
            self.Height = int(row[i])
            i += 1
            self.Exposure = int(row[i])
            i += 1
            self.Brightness = int(row[i])
            i += 1
            self.Saturation = int(row[i])
            i += 1
            self.Valid = True

        else:
            self.Length = 0
            self.Version = 0
            self.Source = 0
            self.Width = 640
            self.Height = 480
            self.Exposure = -8
            self.Brightness = 40
            self.Saturation = 200

    def getValid(self):
        return self.Valid

    def getVersion(self):
        return self.Version

    def getSource(self):
        return self.Source

    def getWidth(self):
        return self.Width

    def getHeight(self):
        return self.Height

    def getExposure(self):
        return self.Exposure

    def getBrightness(self):
        return self.Brightness

    def getSaturation(self):
        return self.Saturation
