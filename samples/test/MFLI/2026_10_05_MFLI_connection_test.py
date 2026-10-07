from zhinst.toolkit import Session
import zhinst
from importlib.metadata import version

session = Session("192.168.1.116")
session.connect_device("DEV7797", interface="1GbE")

print("zhinst version:", version("zhinst"))
print(zhinst.toolkit.__version__)
print(session)