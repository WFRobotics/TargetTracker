from setuptools import setup, find_packages


# Install Target Tracker for development:
#     See README.md
#     If that fails, try:
#         - running command line as admin
#         - python -m pip install --upgrade pip

setup(
    name='Target Tracker',
    version='0.1',
    description='Vision Coprocessor',
    long_description='Kangaroo coprocessor vision target tracking',
    author='Team 4818 WFRobotics',
    author_email='wfrobotics@gmail.com',
    packages=find_packages(),
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'track = tracker.vision:main',
            'track_local = tracker.vision:main_local',
            ]
    },
    install_requires=[
        'opencv-python>=3.3.0.10',
        'jsonschema>=2.6.0'
    ],
    extras_require={
        'dev': [
            'flake8',
        ],
    },
)
