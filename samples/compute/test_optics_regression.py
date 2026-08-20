"""
Regression check for compute.optics.pixel_to_wavelength.

The dispersion equation used to be copied in every camera driver. This compares the shared
function against that original inline form, over every calibration set the repo carries, so
the extraction can be shown to change no wavelength anywhere. Run it directly; no hardware
needed.
"""

from pathlib import Path
import sys
import numpy as np
import yaml

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from compute.optics import pixel_to_wavelength


def original_formula(px, wl_center, constants, m_order=1):
    # Verbatim from the drivers before the extraction, kept here as the reference.
    f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = constants
    n = px - (n0 + offset_adjust * wl_center)
    psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
    eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))
    return ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))
            ) + curvature * n ** 2


# Every calibration in the repo: (name, pixel count, constants in the original tuple order)
CASES = [
    ('Pixis.py / SP2150',      1024, [330605663.74965495, -0.20488367116307532, 2.021864300924973,
                                      508.0, 0, 6666.666666666667, 26000.0, 3.1224154313329654e-06]),
    ('Alize.py grating 1',      640, [382456483.7755453, 6.3514446357904335, 1.9092120540448625,
                                      273.6666666666667, 0, 6666.666666666667, 15000.0, 1.1640095515828127e-06]),
    ('Heliotis.py grating 2',   512, [1197096958.9926493, -18.68106438263782, -1.6871589585359328,
                                      238.25, 0, 4926.108374384236, 24000.0, -6.663483223202162e-06]),
    ('Heliotis.py grating 3',   512, [24739656.496170387, 4.763915731068521, 1.4300129817768625,
                                      243.0, 0, 4926.108374384236, 24000.0, -0.0001681610550643024]),
]

# Plus every calibration file shipped for a camera/monochromator pairing.
for path in sorted((Path(__file__).resolve().parent.parent.parent / 'src' / 'calibrations').glob('*.yaml')):
    calib = yaml.safe_load(open(path))
    for key, c in sorted(calib.get('gratings', {}).items()):
        CASES.append((f'{path.stem} grating {key}', calib.get('num_pixels', 1024),
                      [c['f'], c['delta'], c['gamma'], c['n0'], c['offset_adjust'],
                       c['d_grating'], c['x_pixel'], c['curvature']]))

CENTER_WAVELENGTHS = np.arange(350.0, 901.0, 25.0)

failures = 0
for name, num_pixels, constants in CASES:
    px = np.linspace(1, num_pixels, num_pixels)
    calib = dict(zip(('f', 'delta', 'gamma', 'n0', 'offset_adjust',
                      'd_grating', 'x_pixel', 'curvature'), constants))
    worst = 0.0
    exact = True
    for wl in CENTER_WAVELENGTHS:
        old = original_formula(px, wl, constants)
        new = pixel_to_wavelength(px, wl, calib)
        if not np.array_equal(old, new):
            exact = False
            worst = max(worst, float(np.max(np.abs(old - new))))
    status = 'identique au bit' if exact else f'ECART max {worst:.3e} nm'
    if not exact:
        failures += 1
    print(f'  {name:<28} {num_pixels:>5} px x {len(CENTER_WAVELENGTHS)} lambda   {status}')

print()
print(f'{len(CASES)} calibrations testees, {failures} ecart(s).')
sys.exit(1 if failures else 0)
