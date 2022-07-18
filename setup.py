from setuptools import setup

setup(
    name='lemon',
    packages=['lemon'],
    entry_points={'console_scripts': ['lemon=lemon.actions:cli']},
    install_requires=[
        "cerberus>=1.3.4",
        "click>=8.1.3",
        "prettytable>=3.3.0",
        "psutil>=5.9.1",
        "pyyaml>=6.0",
        "redis>=4.3.4",
        "pybind11"
    ],
    version="1.0.0"
)
