"""
Setup script for Mars Load Cell Calibration application.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Mars Load Cell & IMU Calibration System"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="mars-loadcell-calibration",
    version="1.0.0",
    author="Mars Robotics Team",
    author_email="your-email@example.com",
    description="Load Cell & IMU Calibration System with GUI",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mars-loadcell-calibration",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "pyinstaller>=5.13.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "mars-loadcell-calibration=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.ino", "*.toml", "*.txt", "*.md"],
    },
    data_files=[
        ("arduino_sketches/calibration", ["calibration/calibration.ino"]),
        ("arduino_sketches/firmware", ["firmware/firmware.ino"]),
        ("arduino_sketches/imu_program", ["imu_program/imu_program.ino"]),
    ],
    keywords="arduino, calibration, load-cell, imu, gui, automation",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/mars-loadcell-calibration/issues",
        "Source": "https://github.com/yourusername/mars-loadcell-calibration",
        "Documentation": "https://github.com/yourusername/mars-loadcell-calibration/wiki",
    },
)