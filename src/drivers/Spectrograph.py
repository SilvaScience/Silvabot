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

        self.camera = create_device(camera['driver'], camera.get('init_args'))
        self.monochromator = create_device(monochromator['driver'], monochromator.get('init_args'))
        self.calibration = load_calibration(calibration)
        self._check_pairing()

        self.num_pixels = int(self.calibration.get('num_pixels', getattr(self.camera, 'spec_length', 1024)))
        self.pixels = np.linspace(1, self.num_pixels, self.num_pixels)
        self.spec_length = self.num_pixels
        self.wavelengths = np.zeros(self.num_pixels)

        self._build_parameters()

    def _check_pairing(self):
        """ Warns when the calibration names hardware other than what was actually loaded. The
            constants are fit for one triple; on a different one they still compute, silently. """
        for role, device in (('camera', self.camera), ('monochromator', self.monochromator)):
            expected = self.calibration.get(role)
            actual = getattr(device, 'name', None)
            if expected and actual and expected != actual:
                print(f'WARNING Spectrograph: calibration {self.calibration["source"]} was fit for '
                      f'{role} {expected!r} but {actual!r} was loaded. Wavelengths will be wrong.')

    def _build_parameters(self):
        """ Merges both sub-devices' parameter dicts into one, and records which device owns each
            name so set_parameter can route. A name declared by both is refused here rather than
            silently driving whichever device is reached first. """
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_dict = {}
        self._owner = {}
        for device in (self.monochromator, self.camera):
            for param, properties in getattr(device, 'parameter_display_dict', {}).items():
                if param in self._owner:
                    raise ValueError(
                        f'Spectrograph: {param!r} is declared by both {self.monochromator.name} and '
                        f'{self.camera.name}; rename it in one of the two drivers.')
                self.parameter_display_dict[param] = properties
                self.parameter_dict[param] = device.parameter_dict[param]
                self._owner[param] = device

    def set_parameter(self, parameter, value):
        """REQUIRED. Routes a parameter change to whichever sub-device declared it."""
        device = self._owner.get(parameter)
        if device is None:
            return
        device.set_parameter(parameter, value)
        self.parameter_dict[parameter] = device.parameter_dict.get(parameter, value)

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
            return self.wavelengths

        grating = str(int(round(self.monochromator.grating)))
        if grating not in self.calibration['gratings']:
            raise RuntimeError(
                f'Spectrograph: no calibration for grating {grating} in '
                f'{self.calibration["source"]}. Calibrated: {sorted(self.calibration["gratings"])}.')
        self.wavelengths = pixel_to_wavelength(self.pixels, center_wl,
                                               self.calibration['gratings'][grating])
        return self.wavelengths

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
