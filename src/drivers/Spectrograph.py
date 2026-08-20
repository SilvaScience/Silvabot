"""
A camera and a monochromator presented to the interface as one spectrometer.

The application asks a spectrometer for get_wavelength() and get_intensities(); it has no
reason to know the instrument is made of two boxes. This class holds that pairing, so the
camera drivers stay pure detectors and the monochromator driver stays reusable across tables.

The pairing is fixed at construction: there is no attach step and no window during which a
camera exists without its monochromator.

The optical calibration belongs to the (camera, monochromator, grating) triple, not to the
camera, so it is a named file under calibrations/ rather than init_args on the detector.
Moving any of the three means refitting it.
"""

import numpy as np
import yaml
from pathlib import Path
from PyQt5 import QtCore
from collections import defaultdict
from collections.abc import MutableMapping

from devices import create_device
from compute.optics import pixel_to_wavelength, linear_wavelengths


def load_calibration(path):
    """
        Reads a calibration file describing one camera/monochromator pairing.
        input:
            - path (str): path to the YAML file, absolute or relative to the src folder
        output:
            - dict: the calibration, with its 'gratings' keys normalised to strings
    """
    path = Path(path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    if not path.exists():
        raise FileNotFoundError(f'Spectrograph: calibration file not found: {path}')
    calibration = yaml.safe_load(open(path)) or {}
    calibration['gratings'] = {str(k): v for k, v in calibration.get('gratings', {}).items()}
    calibration.setdefault('source', str(path))
    return calibration


class MergedParameters(MutableMapping):
    """
        Live view over the sub-devices' parameter_dict, keyed by parameter name.
        input:
            - owners (dict): parameter name -> the device that declared it

        Reads and writes both reach the owning device rather than a copy. A value the device
        updates on its own -- a worker publishing sensor_T -- is therefore seen here, and a value
        written here -- a session parameter restored at startup -- reaches the device.
    """

    def __init__(self, owners):
        self._owners = owners

    def __getitem__(self, key):
        return self._owners[key].parameter_dict[key]

    def __setitem__(self, key, value):
        self._owners[key].parameter_dict[key] = value

    def __delitem__(self, key):
        raise TypeError('Spectrograph parameters are fixed by its sub-devices')

    def __iter__(self):
        return iter(self._owners)

    def __len__(self):
        return len(self._owners)


class Spectrograph(QtCore.QThread):

    name = 'Spectrograph'
    type = 'Spectrometer'

    def __init__(self, camera, monochromator, calibration):
        """
            input:
                - camera (dict): {'driver': path, 'init_args': {...}} for the detector
                - monochromator (dict): {'driver': path, 'init_args': {...}} for the monochromator
                - calibration (str): path to the calibration file for this pairing
        """
        super(Spectrograph, self).__init__()

        self.camera = self._build('camera', camera)
        self.monochromator = self._build('monochromator', monochromator)
        self.calibration = load_calibration(calibration)
        self._check_pairing()

        self.num_pixels = int(self.calibration.get('num_pixels', getattr(self.camera, 'spec_length', 1024)))
        self.pixels = np.linspace(1, self.num_pixels, self.num_pixels)
        self.spec_length = self.num_pixels
        self.wavelengths = np.zeros(self.num_pixels)

        # Whatever the detector can do, plus the one thing pairing it with a monochromator adds.
        self.caps = frozenset(getattr(self.camera, 'caps', frozenset())) | {'stitch'}

        self._build_parameters()

    @staticmethod
    def _build(role, spec):
        """ Builds one sub-device, honouring the same 'fallback' key config.yaml uses at top level
            so a missing instrument degrades to its demo instead of taking the whole pairing down. """
        try:
            return create_device(spec['driver'], spec.get('init_args'))
        except Exception as e:
            print(f"Spectrograph {role}: {spec['driver'].split('.')[-1]} failed ({e})")
            if not spec.get('fallback'):
                raise
            device = create_device(spec['fallback'], spec.get('init_args'))
            print(f"Spectrograph {role}: {spec['fallback'].split('.')[-1]} (fallback) connected")
            return device

    def _check_pairing(self):
        """ Warns when the calibration names hardware other than what was actually loaded. The
            constants are fit for one triple; on a different one they still compute, silently. """
        for role, device in (('camera', self.camera), ('monochromator', self.monochromator)):
            expected = self.calibration.get(role)
            actual = getattr(device, 'name', None)
            # Tested on the class, not on name: SpectrometerDemo reports name 'Spectrometer'.
            if type(device).__name__.endswith('Demo'):
                continue  # a demo stand-in is not the hardware the fit was made on, and says so
            if expected and actual and expected != actual:
                print(f'WARNING Spectrograph: calibration {self.calibration["source"]} was fit for '
                      f'{role} {expected!r} but {actual!r} was loaded. Wavelengths will be wrong.')

        declared = self.calibration.get('num_pixels')
        readout = getattr(self.camera, 'spec_length', None)
        if declared and isinstance(readout, int) and declared != readout:
            print(f'WARNING Spectrograph: calibration declares {declared} pixels but '
                  f'{self.camera.name} reads out {readout}. The axis will not line up with the data.')

    def _build_parameters(self):
        """ Records which device owns each parameter name, and exposes the two dicts as one. The
            values are read through to the owning device rather than copied: a copy taken here
            stops tracking whatever the device updates on its own, which froze sensor_T on screen
            at its startup value. A name declared by both devices is refused rather than silently
            driving whichever is reached first. """
        self.parameter_display_dict = defaultdict(dict)
        self._owner = {}
        for device in (self.monochromator, self.camera):
            for param, properties in getattr(device, 'parameter_display_dict', {}).items():
                if param in self._owner:
                    raise ValueError(
                        f'Spectrograph: {param!r} is declared by both {self.monochromator.name} and '
                        f'{self.camera.name}; rename it in one of the two drivers.')
                self.parameter_display_dict[param] = dict(properties)  # copy: not shared state
                self._owner[param] = device
        self.parameter_dict = MergedParameters(self._owner)

    def set_parameter(self, parameter, value):
        """REQUIRED. Routes a parameter change to whichever sub-device declared it."""
        device = self._owner.get(parameter)
        if device is None:
            return
        device.set_parameter(parameter, value)  # its own dict is the one parameter_dict reads

    def get_wavelength(self):
        """
            Wavelength axis for the current monochromator position.
            output:
                - np.ndarray: wavelength in nm at each sensor pixel
        """
        center_wl, lines_per_mm = self.monochromator.get_monochromator_parameters()
        if not self.calibration.get('calibrated', True):
            self.wavelengths = linear_wavelengths(
                center_wl, lines_per_mm, self.calibration['focal_length_mm'],
                self.calibration['pixel_size_mm'], self.num_pixels)
            self._publish_axis()
            return self.wavelengths

        grating = str(int(round(self.monochromator.grating)))
        if grating not in self.calibration['gratings']:
            raise RuntimeError(
                f'Spectrograph: no calibration for grating {grating} in '
                f'{self.calibration["source"]}. Calibrated: {sorted(self.calibration["gratings"])}.')
        self.wavelengths = pixel_to_wavelength(self.pixels, center_wl,
                                               self.calibration['gratings'][grating])
        self._publish_axis()
        return self.wavelengths

    def _publish_axis(self):
        """ Hands the axis to cameras that already carry a `wavelength` attribute, because they
            save it themselves alongside their raw frames (HeliotisCamera). """
        if hasattr(self.camera, 'wavelength'):
            self.camera.wavelength = self.wavelengths

    def get_intensities(self):
        """REQUIRED. The detector reads; the monochromator is not involved."""
        return self.camera.get_intensities()

    def close_device(self):
        for device in (self.camera, self.monochromator):
            if hasattr(device, 'close_device'):
                device.close_device()

    def __getattr__(self, item):
        """ Forwards anything not defined here to the camera: shutter handling, readout region,
            frame_shape and the rest of the detector-specific surface the GUI and the measurement
            classes reach for. Only called for attributes normal lookup did not find. """
        if item.startswith('_'):
            raise AttributeError(item)
        try:
            camera = self.__dict__['camera']
        except KeyError:
            raise AttributeError(item)
        return getattr(camera, item)
