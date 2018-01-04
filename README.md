# TargetTracker
Python script to run GRIP generated code on a Kangaroo that detects and reports tracked targets.

# Prerequisites
- Kangaroo PC
- Python 3.6+
- OpenCV 3.x/GRIP

# Main Features
- 1 or 2 cameras
- Custom configurations of cameras, processing settings, ports, etc
- MJPG streamer (for webpage/Smartdashboard)
- Socket connection for reporting target data to RoboRIO

# Issues
- OpenCV/GRIP processing multiple camera streams at once cannot keep up with 30fps, and will continuously increase the frame delay and decrease FPS until it is unusable. It is recommended to only have one camera stream being processed at a time.

# Install & Run
```bat
pip install -e .
```

```bat
track
```

# Develop & Test
```bat
pip install -e .[dev]
```

```bat
flake8
```

# Help
For help, run
```bat
    py vision.py --help
```
