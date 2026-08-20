"""
Checks drivers.SpectraPro.parse_turret against the ?GRATINGS response shapes the units produce,
including the one that defeated the previous digit-extraction parser: a blaze given in microns,
whose decimal point splits into two tokens and shifts every offset after it.
"""

from pathlib import Path
import sys
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from drivers.SpectraPro import parse_turret

CASES = [
    ('SP2150, 2 gratings, 6 empty slots',
     '1  600 g/mm BLZ=  1200NM \r\n2  300 g/mm BLZ=  1200NM \r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n ok',
     [600.0, 300.0], [1200.0, 1200.0]),
    ('SP2300i, blaze in UM, last slot',
     '1  1200 g/mm BLZ=  300NM \r\n2  1200 g/mm BLZ=  750NM \r\n3   300 g/mm BLZ=  2.0UM \r\n ok',
     [1200.0, 1200.0, 300.0], [300.0, 750.0, 2000.0]),
    ('SP2300i, blaze in UM plus empty slots',
     '1  1200 g/mm BLZ=  300NM \r\n2  1200 g/mm BLZ=  750NM \r\n3   300 g/mm BLZ=  2.0UM \r\n4\r\n5\r\n6\r\n ok',
     [1200.0, 1200.0, 300.0], [300.0, 750.0, 2000.0]),
    ('SP2300i, blaze in UM first, offsets would shift',
     '1   300 g/mm BLZ=  2.0UM \r\n2  1200 g/mm BLZ=  300NM \r\n3  1200 g/mm BLZ=  750NM \r\n4\r\n5\r\n ok',
     [300.0, 1200.0, 1200.0], [2000.0, 300.0, 750.0]),
]

failures = 0
for name, response, densities, blazes in CASES:
    n, d, b = parse_turret(response)
    ok = n == len(densities) and np.allclose(d, densities) and np.allclose(b, blazes)
    failures += not ok
    print(f'  {name:<44} n={n} densites={list(d)} blazes={list(b)}  {"ok" if ok else "ECHEC"}')

try:
    parse_turret('1\r\n2\r\n3\r\n ok')
    print('  ECHEC: une reponse sans reseau aurait du lever')
    failures += 1
except ValueError:
    print(f'  {"reponse sans reseau lisible -> ValueError":<44} ok')

print(f'\n{len(CASES) + 1} cas, {failures} echec(s).')
sys.exit(1 if failures else 0)
