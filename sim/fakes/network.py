STA_IF = 1


class WLAN:
    def __init__(self, mode):
        pass

    def active(self, active):
        return True

    def scan(self):
        return []

    def connect(self, ssid, key=None):
        pass

    def isconnected(self):
        return True
