from setuptools import find_packages, setup

setup(
    name="assayer",
    version="0.0.1",
    description="Redis queue watchdog to automatically evaluate ML model checkpoints offline during training",
    author="Abhinav Moudgil",
    author_email="abhinavmoudgil95@gmail.com",
    packages=find_packages(),
)