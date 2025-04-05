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

COMMANDS = [
    "activate_next_stage"
]

def make_attribute_store():
    store = {}

    for name in ATTRIBUTES:
        store[name] = { "value": None, "dirty": False, "undefined": True }

    return store

def make_command_store():
    store = {}

    for name in COMMANDS:
        store[name] = False

    return store

class Bridge:
    def __init__(self, doze:kec.util.Doze):
        self._attributes = make_attribute_store()
        self._commands = make_command_store()
        self._coordinator = doze
        self._lock = threading.Lock()

    def _clear_commands(self):
        for name in self._commands:
            self._commands[name] = False

    def sync(self, control:krpc.services.spacecenter.Control):
        # A new vessel should not take old commands - that could certainly lead to
        # surprises such as stage having been commanded while no vessel was active
        # so it would stage as soon as it became active
        self._clear_commands()

        self.update(control, everything=True)

    # A control object is passed in as needed to ensure a stale instance is not
    # held and interacted with when set() is called
    def update(self, control:krpc.services.spacecenter.Control, everything:bool=False):
        with self._lock:
            for name in self._attributes:
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

            for name in self._commands:
                if not self._commands[name]:
                    continue

                method = getattr(control, name)

                method()

                self._commands[name] = False

    def set(self, name:str, value):
        print(f"Bridge setting {name} = {value}")

        with self._lock:
            if name not in self._attributes:
                raise KeyError(name)

            attribute = self._attributes[name]

            attribute["value"] = value
            attribute["dirty"] = True
            attribute["undefined"] = False

        self._coordinator.wakeup()

    def command(self, name:str):
        print(f"Bridge enque command: {name}")

        with self._lock:
            if name not in self._commands:
                raise KeyError(name)

            self._commands[name] = True

        self._coordinator.wakeup()
