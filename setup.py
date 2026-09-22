from setuptools import setup, find_packages

setup(
    name="asus-driver-extractor",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "asus-unpack=asus_driver_extractor.cli:main",
            "ade=asus_driver_extractor.cli:main",
            "ade-gui=asus_driver_extractor.gui:launch_gui",
        ],
    },
)
