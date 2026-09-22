from setuptools import setup, find_packages

setup(
    name="asus-dearmour",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "dearmour=asus_driver_extractor.cli:main",
            "dearmour-gui=asus_driver_extractor.gui:launch_gui",
            "asus-unpack=asus_driver_extractor.cli:main",
            "ade=asus_driver_extractor.cli:main",
            "ade-gui=asus_driver_extractor.gui:launch_gui",
        ],
    },
)
