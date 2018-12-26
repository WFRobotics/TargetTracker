# TargetTracker
STEM Alliance vision coprocessor

Python script to run GRIP generated code on a Kangaroo. Detected vision targets are reported to the robot. 

# Setup
Install the latest [python 3](https://www.python.org/downloads/). Put it **and the python scripts directory** in your PATH:
```bat
C:\Python37;C:\Python37\Scripts\
```
**afterwards** open a command line and **install Target Tracker + dependencies** with python's package manager:
```bat
pip install -e .[dev]
```

# Run
**At competition**, the Kangeroo will run Target Tracker from a startup script, which calls:
```bat
track
```
you can also run on your **own PC for testing**:
```bat
track_local
```
which **sends data locally to the java test app** stored in the Reuse repo

# Hardware
- Kangaroo PC
- USB Camera
