# -*- coding: utf-8 -*-
"""
Created on Fri Aug  1 11:23:17 2025

@author: bviscogliosi
"""
A = 79.9641 *1E4
B = 79.9641 *1E4
C = 80.0586 *1E4

f = A - (2*B) + C
print(f)
print(B-A, C-A, C-B)

# %%
A = 79.9641 *1E4
B = 79.989 *1E4
C = 80.0586 *1E4

f = A - (2*B) + C
print(f)
print(B-A, C-A, C-B)

# %%
A = 79.9641 *1E4
B = 79.9901 *1E4
C = 80.0191 *1E4
D = 80.0481 *1E4

f = A - (2*B) + C
f2 = A - B - C + D
print(f)
print(f2)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# %% Standard BF 4 beam config. 
A = 78.729 *1E3
B = 78.8606 *1E3# 79.0835*1E4 #   78.8606
C = 79.453 *1E3
D = 79.5995 *1E3


f = + A - 2*B + C
f2 =  + A - B - C + D
f3 =  -(+ A - B) - C + D
BA = B-A
DC = D-C
print(f)
print(f2)
print(BA-DC)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# %%
A = 78.729 *1E4
B = 79.232 *1E4# 79.0835*1E4 #   78.8606
C = 79.75 *1E4
D = 79.5995 *1E4


f = + A - 2*B + C
f2 =  + A - B - C + D
print(f)
print(f2)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# %%
A = 78.712 *1E4
B = 78.8606 *1E4# 79.0835*1E4 #   78.8606
C = 79.0242 *1E4
D = 79.5995 *1E4


f = + A - 2*B + C
f2 =  + A - B - C + D
print(f)
print(f2)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# This frequency leads to 213.3/2=106.65 stable signal. This requires N = 100 
# It can also be divided by 4, 213.3 = 53.325. This requires N = 20

# %% frequency for 71.53kHz sideband
A = 78.712 *1E4
B = 78.8606 *1E4# 79.0835*1E4 #   78.8606
C = 79.335 *1E4
D = 0 *1E4


f = + A - 2*B + C
f2 =  + A - B + C # + D
print(f)
print(f2)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# This frequency leads to 213.3/2=106.65 stable signal. This requires N = 100 
# It can also be divided by 4, 213.3 = 53.325. This requires N = 20




# %% frequency for kHz modulation
A = 78.729 *1E3 #frequency in M
B = 78.8606 *1E3# 79.0835*1E4 #   78.8606
C = 0.1466 *1E3
D = 0 #79.5995 *1E4


f = + A - 2*B + C
f2 =  + (A - B) + C + D
print(f)
print(f2)
print(f'B-A={B-A}, C-A={C-A}, C-B={C-B}, D-C={D-C}')

# This frequency leads to 213.3/2=106.65 stable signal. This requires N = 100 
# It can also be divided by 4, 213.3 = 53.325. This requires N = 20

# %% BF 4 beam config. with 25kH
A = 78.729 *1E3
B = 78.8606 *1E3# 79.0835*1E4 #   78.8606
C = 79.4554 *1E3
D = 79.5995 *1E3


f = + A - 2*B + C
f2 =  + A - B - C + D
f3 =  -(+ A - B) - C + D
BA = B-A
DC = D-C
print(f)
print(f2)
print(BA-DC)
print(f'B-A={B-A}, D-C={D-C}')
