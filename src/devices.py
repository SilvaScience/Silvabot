"""
Device construction from the project-defined driver paths used in config.yaml.

Kept out of main.py so a composite device (see drivers.Spectrograph) can build its own
sub-devices without importing the interface it is loaded by.
"""

import importlib


def load_class(path):
    # loads a class from a project-defined path. Returns the class
    module_name, class_name = path.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), class_name)


def create_device(path, init_args=None):
    # Initializes a class from project-defined path. Returns the called class
    cls = load_class(path)
    return cls(**(init_args or {}))


def caps(device):
    """
        What a device can do, as declared by the driver rather than guessed from which attributes
        happen to exist.
        input:
            - device: any loaded device, or None
        output:
            - frozenset: capability names, empty for a device that declares none

        Names in use:
            'acquisition'  reads must be bracketed by start_acquisition/stop_acquisition
            'roi'          the sensor readout region can be set, and a full frame read for alignment
            'frame'        frame_shape() reports the shape of what get_intensities() returns
            'shutter_mode' the physical shutter can be forced open or closed
            'stitch'       a monochromator can be moved between grating positions
    """
    return getattr(device, 'caps', frozenset())
