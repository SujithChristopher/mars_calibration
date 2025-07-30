"""
Version information for Mars Calibration application.
"""

__version__ = "0.1.3"
__build_date__ = "2025-07-30"
__build_commit__ = "main"

# Application metadata
APP_NAME = "Mars Calibration"
APP_DESCRIPTION = "Load Cell & IMU Calibration System"
APP_AUTHOR = "Mars Calibration Team"
APP_URL = "https://github.com/SujithChristopher/mars_calibration"

def get_version_info():
    """Get formatted version information."""
    return {
        "version": __version__,
        "build_date": __build_date__,
        "build_commit": __build_commit__,
        "app_name": APP_NAME,
        "description": APP_DESCRIPTION,
        "author": APP_AUTHOR,
        "url": APP_URL
    }

def get_version_string():
    """Get version as a string."""
    return __version__