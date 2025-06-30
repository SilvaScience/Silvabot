from PyQt5 import QtCore
from collections import defaultdict
import time

class PI863():

    name = 'PI863'

    def __init__(self):
        super(PI863, self).__init__()

        # setting up the parameter dict
        self.parameter_dict = defaultdict()