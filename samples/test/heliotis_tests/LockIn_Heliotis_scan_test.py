import zhinst.core
import time
import numpy as np
import csv
import urllib.request


url = "http://127.0.0.1:8006/netlink?id=c0p1t8p1cfm0p0&ziSessionId=0"
webpage = urllib.request.urlopen(url)
datareader = csv.reader(webpage.read().decode().splitlines())
data = []
