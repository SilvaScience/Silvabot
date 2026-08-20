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
