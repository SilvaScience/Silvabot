"""
Smoke test for drivers.Spectrograph, using the demo camera and demo monochromator so it runs
with no hardware attached. Checks the three things composition is responsible for: merging the
two parameter dicts, routing a parameter change to the right sub-device, and producing a
wavelength axis from the monochromator's live position.
"""

from pathlib import Path
import sys
import tempfile
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT / 'src'))
from PyQt5 import QtWidgets
from drivers.Spectrograph import Spectrograph

app = QtWidgets.QApplication(sys.argv)

reference = yaml.safe_load(open(ROOT / 'src' / 'calibrations' / 'pixis_sp2300i.yaml'))
reference.update(camera='Spectrometer', monochromator='SpectraPro2300iDemo', num_pixels=2048)
calib_file = Path(tempfile.gettempdir()) / 'demo_pairing.yaml'
calib_file.write_text(yaml.dump(reference), encoding='utf-8')

spec = Spectrograph(
    camera={'driver': 'drivers.SpectrometerDemo_advanced.SpectrometerDemo'},
    monochromator={'driver': 'drivers.SpectraPro2300iDemo.SpectraPro2300iDemo'},
    calibration=str(calib_file))

failures = []

# 1. both devices' parameters are visible under one dict
for param in ('central_wave', 'grating', 'mirror', 'int_time', 'avg_scan'):
    if param not in spec.parameter_dict:
        failures.append(f'parametre absent du dict fusionne: {param}')
print(f'  parametres fusionnes : {sorted(spec.parameter_dict)}')

# 2. a change reaches the device that declared it, and neither the other one nor a stale copy
spec.set_parameter('central_wave', 512.5)
spec.set_parameter('int_time', 250)
if spec.monochromator.center_wl != 512.5:
    failures.append('central_wave n a pas atteint le monochromateur')
if spec.camera.parameter_dict['int_time'] != 250:
    failures.append('int_time n a pas atteint la camera')
if spec.parameter_dict['central_wave'] != 512.5:
    failures.append('le dict du Spectrograph n a pas suivi')
print(f'  routage : central_wave -> {spec.monochromator.name}, int_time -> {spec.camera.name}')

# 3. the wavelength axis follows the monochromator, and only the monochromator
wls_a = spec.get_wavelength()
spec.set_parameter('central_wave', 700.0)
wls_b = spec.get_wavelength()
if len(wls_a) != spec.num_pixels:
    failures.append(f'axe de longueur {len(wls_a)}, attendu {spec.num_pixels}')
if np.allclose(wls_a, wls_b):
    failures.append('l axe n a pas bouge quand le monochromateur a bouge')
print(f'  axe @512.5nm : {wls_a[0]:.2f} -> {wls_a[-1]:.2f} nm')
print(f'  axe @700.0nm : {wls_b[0]:.2f} -> {wls_b[-1]:.2f} nm')

# 4. the detector surface stays reachable through the composite
if not hasattr(spec, 'get_intensities') or not hasattr(spec, 'spec_length'):
    failures.append('surface detecteur non deleguee')
print(f'  delegation camera : spec_length={spec.spec_length}, binning={spec.parameter_dict.get("binning")}')

# 5. the merged dict is a live view, not a snapshot taken at construction
spec.camera.parameter_dict['int_time'] = 999          # as the camera's own worker would
if spec.parameter_dict['int_time'] != 999:
    failures.append('lecture traversante: une valeur ecrite par la camera n est pas vue')
spec.parameter_dict['int_time'] = 123                 # as the session restore would
if spec.camera.parameter_dict['int_time'] != 123:
    failures.append('ecriture traversante: la valeur n atteint pas la camera')
print(f'  vue vivante : camera->composite ok, composite->camera ok')

# 6. a calibration fit for other hardware is reported rather than computed silently
mismatched = dict(reference, camera='SomeOtherCamera')
bad_file = Path(tempfile.gettempdir()) / 'mismatched_pairing.yaml'
bad_file.write_text(yaml.dump(mismatched), encoding='utf-8')
print('  garde-fou appariement (un WARNING doit suivre) :')
Spectrograph(camera={'driver': 'drivers.SpectrometerDemo_advanced.SpectrometerDemo'},
             monochromator={'driver': 'drivers.SpectraPro2300iDemo.SpectraPro2300iDemo'},
             calibration=str(bad_file))

print()
if failures:
    for f in failures:
        print(f'  ECHEC: {f}')
print(f'{len(failures)} echec(s).')
sys.exit(1 if failures else 0)
