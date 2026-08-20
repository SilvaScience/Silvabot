"""
Grating spectrograph optics: turns sensor pixel indices into wavelengths.

Shared by every camera that sits on a monochromator (Pixis, Stresing, Alize, Heliotis).
Kept out of the drivers so a correction to the dispersion model lands once instead of once
per camera. The constants are fit per (camera, monochromator, grating) triple: groove density
and blaze angle change the optical path enough that one grating's fit does not describe
another's.
"""

import numpy as np

CALIBRATION_KEYS = ('f', 'delta', 'gamma', 'n0', 'offset_adjust',
                    'd_grating', 'x_pixel', 'curvature')


def pixel_to_wavelength(pixels, center_wl, calib, m_order=1):
    """
        Wavelength seen by each sensor pixel, from the fitted dispersion equation.
        input:
            - pixels (np.ndarray): sensor pixel indices, 1-based as the fits were made
            - center_wl (float): monochromator central wavelength in nm
            - calib (dict): fit constants for one camera/monochromator/grating triple,
              keys as in CALIBRATION_KEYS
            - m_order (int): diffraction order
        output:
            - np.ndarray: wavelength in nm at each pixel
    """
    missing = [k for k in CALIBRATION_KEYS if k not in calib]
    if missing:
        raise KeyError(f'calibration is missing {missing}, expected {list(CALIBRATION_KEYS)}')

    f, delta, gamma = calib['f'], calib['delta'], calib['gamma']
    d_grating, x_pixel, curvature = calib['d_grating'], calib['x_pixel'], calib['curvature']

    n = np.asarray(pixels) - (calib['n0'] + calib['offset_adjust'] * center_wl)
    psi = np.arcsin(m_order * center_wl / (2 * d_grating * np.cos(gamma / 2)))
    eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))
    return ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))
            + curvature * n ** 2)


def linear_wavelengths(center_wl, grating_lines_per_mm, focal_length_mm, pixel_size_mm, num_pixels):
    """
        Wavelength axis from the spectrograph's nominal linear dispersion, for a setup with no
        fitted calibration.
        input:
            - center_wl (float): monochromator central wavelength in nm
            - grating_lines_per_mm (float): groove density of the selected grating
            - focal_length_mm (float): spectrograph focal length
            - pixel_size_mm (float): sensor pixel pitch
            - num_pixels (int): number of pixels along the wavelength axis
        output:
            - np.ndarray: wavelength in nm at each pixel

        Coarse next to pixel_to_wavelength: it ignores the grating angles the fit accounts for.
    """
    dispersion = 1e6 / (focal_length_mm * grating_lines_per_mm)  # nm/mm
    pixel_indices = np.arange(num_pixels)
    return center_wl + (pixel_indices - num_pixels // 2) * dispersion * pixel_size_mm
