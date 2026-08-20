"""
Exercises SpectrometerPlot's four-ROI maths and the plot binning without any hardware.

Both only run when the spectrum handed to set_data() is 2D (set_data branches on spec.ndim), so
this feeds a synthetic frame whose rows are constant inside each default ROI band. That makes the
expected ROI averages exact, and any indexing mistake shows up as a wrong number rather than as a
curve that looks plausible.
"""

from pathlib import Path
import sys
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from PyQt5 import QtWidgets
from GUI.SpectrometerPlot import SpectrometerPlot

app = QtWidgets.QApplication(sys.argv)
plot = SpectrometerPlot()

NUM_PIXELS = 100
LEVELS = [10.0, 20.0, 30.0, 40.0]        # one constant level per ROI band
failures = []

# Build a frame that is zero everywhere except inside each ROI's own row range.
rows = max(hi.value() for _, hi in plot.roi_controls) + 10
frame = np.zeros((rows, NUM_PIXELS))
for i, (lo_spin, hi_spin) in enumerate(plot.roi_controls):
    frame[lo_spin.value():hi_spin.value(), :] = LEVELS[i]
    print(f'  ROI{i}: rows {lo_spin.value()}-{hi_spin.value()} remplies a {LEVELS[i]}')

wls = np.linspace(500.0, 600.0, NUM_PIXELS)
plot.checkbox_image.setChecked(True)      # 'Sum mode': plot the ROI curves instead of the image
plot.input_line.setText('y[0]-y[1]')
plot.set_data(wls, frame)

# 1. each ROI averages only its own rows
for i in range(4):
    got = float(np.mean(plot.y[i]))
    if not np.isclose(got, LEVELS[i]):
        failures.append(f'ROI{i} vaut {got}, attendu {LEVELS[i]}')
print(f'  moyennes ROI : {[float(np.mean(plot.y[i])) for i in range(4)]}')

# 2. the expression is evaluated over those curves
expected = LEVELS[0] - LEVELS[1]
got = float(np.mean(plot.y[4]))
if not np.isclose(got, expected):
    failures.append(f"expression 'y[0]-y[1]' vaut {got}, attendu {expected}")
print(f"  expression y[0]-y[1] : {got}")

# 3. a different expression reaches the same path
plot.input_line.setText('y[2]/y[3]')
plot.set_data(wls, frame)
expected = LEVELS[2] / LEVELS[3]
got = float(np.mean(plot.y[4]))
if not np.isclose(got, expected):
    failures.append(f"expression 'y[2]/y[3]' vaut {got}, attendu {expected}")
print(f'  expression y[2]/y[3] : {got:.4f}')

# 4. binning is a running mean: flat input must come back flat, a spike must spread
plot.spinbox_bin.setValue(5)
flat = plot.do_binning(np.full(NUM_PIXELS, 7.0))
if not np.isclose(np.mean(flat[10:-10]), 7.0):
    failures.append(f'binning d un signal plat donne {np.mean(flat[10:-10])}, attendu 7.0')
spike = np.zeros(NUM_PIXELS)
spike[50] = 9.0
binned_spike = plot.do_binning(spike)
width = int(np.count_nonzero(binned_spike))
if width <= 1:
    failures.append(f'binning=5 n etale pas le pic (largeur {width})')
print(f'  binning=5 : plat -> {np.mean(flat[10:-10]):.3f}, pic etale sur {width} points')

# 5. a 1D spectrum must not touch the ROI path at all
before = {i: np.array(plot.y[i]) for i in range(5)}
plot.set_data(wls, np.ones(NUM_PIXELS))
if any(not np.array_equal(before[i], plot.y[i]) for i in range(5)):
    failures.append('un spectre 1D a modifie les courbes ROI')
print('  spectre 1D : courbes ROI inchangees (chemin non emprunte)')

print()
for f in failures:
    print(f'  ECHEC: {f}')
print(f'{len(failures)} echec(s).')
sys.exit(1 if failures else 0)
