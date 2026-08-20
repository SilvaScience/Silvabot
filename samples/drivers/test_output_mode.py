"""
Checks the 1D/2D readout mode without hardware, using a stand-in camera that behaves like a
PIXIS readout: it returns roi_height/roi_binning rows, and flattens them only in 1D.

What matters is that the two modes agree numerically -- 2D with roi_binning set to the full
region height must give exactly what 1D gives -- and that the frame shape a measurement declares
follows the mode, since DataHandling is preallocated from it.
"""

from pathlib import Path
import sys
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from measurements.MeasurementClasses import frame_spec_length


class FakeCamera:
    """ Same output contract as PixisCamera: on-chip groups, flattened in 1D. """
    name = 'Fake'
    caps = frozenset({'output_mode', 'frame', 'acquisition'})

    def __init__(self, sensor_rows=54, pixels=8):
        self.sensor_rows, self.spec_length = sensor_rows, pixels
        self.roi_height, self.roi_binning, self.output_mode = sensor_rows, sensor_rows, '1D'
        # each sensor row carries its own index, so a summed group has a predictable value
        self.sensor = np.tile(np.arange(sensor_rows, dtype=float)[:, None], (1, pixels))

    def set_output_mode(self, mode):
        self.output_mode = mode
        self.roi_binning = self.roi_height if mode == '1D' else self.roi_binning
        return mode

    def get_output_mode(self):
        return self.output_mode

    def frame_shape(self):
        return (max(self.roi_height // self.roi_binning, 1), self.spec_length)

    def get_intensities(self):
        groups = self.sensor.reshape(self.roi_height // self.roi_binning, self.roi_binning, -1).sum(axis=1)
        return groups.sum(axis=0) if self.output_mode == '1D' else groups


cam = FakeCamera()
failures = []

one_d = cam.get_intensities()
if one_d.ndim != 1:
    failures.append(f'le mode 1D rend {one_d.ndim} dimensions')
if frame_spec_length(cam) is not None:
    failures.append('le mode 1D declare une forme de trame')
print(f'  1D : forme {one_d.shape}, somme {one_d[0]:.0f}, aucune forme declaree')

cam.set_output_mode('2D')
cam.roi_binning = 6
two_d = cam.get_intensities()
if two_d.shape != (9, 8):
    failures.append(f'2D binning 6 rend {two_d.shape}, attendu (9, 8)')
if frame_spec_length(cam) != (9, 8):
    failures.append(f'forme declaree {frame_spec_length(cam)}, attendu (9, 8)')
print(f'  2D binning=6 : forme {two_d.shape}, forme declaree {frame_spec_length(cam)}')

# the two modes must not disagree about the total signal
if not np.allclose(two_d.sum(axis=0), one_d):
    failures.append('la somme des groupes 2D ne redonne pas le spectre 1D')
print(f'  somme des 9 groupes == spectre 1D : {np.allclose(two_d.sum(axis=0), one_d)}')

# binning at the full region height is the 1D result, one row instead of none
cam.roi_binning = cam.roi_height
full = cam.get_intensities()
if full.shape != (1, 8) or not np.allclose(full[0], one_d):
    failures.append('2D avec binning = roi_height ne redonne pas le resultat 1D')
print(f'  2D binning=roi_height : forme {full.shape}, identique au 1D')

cam.set_output_mode('1D')
if frame_spec_length(cam) is not None or cam.get_intensities().ndim != 1:
    failures.append('le retour en 1D ne restaure pas le comportement')
print('  retour en 1D : restaure')

# roi_binning is the user's setting and must survive a spell in 1D: apply_readout_region used to
# write the full region height back over it, so the next switch to 2D delivered a single row.
class ModeCamera(FakeCamera):
    """ Mirrors PixisCamera's apply_readout_region well enough to catch that write-back. """
    def apply_readout_region(self):
        self.applied_binning = self.roi_height if self.output_mode == '1D' else self.roi_binning
        if self.output_mode == '2D':
            self.roi_binning = self.applied_binning

    def set_output_mode(self, mode):
        self.output_mode = mode
        self.apply_readout_region()
        return mode


mc = ModeCamera()
mc.roi_binning = 6                 # chosen under Hardware
mc.set_output_mode('1D')           # a spell in 1D, as at startup
mc.apply_readout_region()          # as adjusting roi_y0 would trigger
if mc.roi_binning != 6:
    failures.append(f'roi_binning vaut {mc.roi_binning} apres un passage en 1D, attendu 6')
mc.set_output_mode('2D')
if mc.roi_height // mc.roi_binning != 9:
    failures.append(f'retour en 2D rend {mc.roi_height // mc.roi_binning} ligne(s), attendu 9')
print(f'  roi_binning survit au 1D : {mc.roi_binning}, retour en 2D -> '
      f'{mc.roi_height // mc.roi_binning} lignes')

print()
for f in failures:
    print(f'  ECHEC: {f}')
print(f'{len(failures)} echec(s).')
sys.exit(1 if failures else 0)
