import logging
import threading

import krpc
import krpc.services
import krpc.services.spacecenter

import kec.util

ATTRIBUTES = [
    "brakes",
    "gear",
    "pitch",
    "roll",
    "sas",
    "sas_mode",
    "throttle",
    "yaw"
]

def make_attribute_store():
    store = {}

    for name in ATTRIBUTES:
        store[name] = { "value": None, "dirty": False, "undefined": True }

    return store

class Bridge:
    def __init__(self, doze:kec.util.Doze):
        self._attributes = make_attribute_store()
        self._coordinator = doze
        self._lock = threading.Lock()

    def sync(self, control:krpc.services.spacecenter.Control):
        self.update(control, everything=True)

    # A control object is passed in as needed to ensure a stale instance is not
    # held and interacted with when set() is called
    def update(self, control:krpc.services.spacecenter.Control, everything:bool=False):
        with self._lock:
            for name in ATTRIBUTES:
                attribute = self._attributes[name]
                value = attribute["value"]

                if attribute["undefined"]:
                    continue

                if not attribute["dirty"] and not everything:
                    continue

                try:
                    setattr(control, name, value)
                    print(f"Updated vessel with {name} = {value}")
                except:
                    logging.exception(f"Could not set kRPC vessel control attribute: {name}")

                attribute["dirty"] = False

    def set(self, name:str, value):
        print(f"Bridge setting {name} = {value}")

        with self._lock:
            attribute = self._attributes[name]

            attribute["value"] = value
            attribute["dirty"] = True
            attribute["undefined"] = False

        self._coordinator.wakeup()
