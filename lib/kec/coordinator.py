from enum import Enum
import threading

import krpc.client
import krpc.service

import kec.bridge
import kec.util

def make_state():
    return {
        "flying": False,
        "vessel": None,
    }

def make_queue():
    queue = {}

    for name in make_state():
        queue[name] = { "value": None, "dirty": False }

    return queue

class Coordinator:
    def __init__(self, ksp:krpc.client.Client):
        self._doze = kec.util.Doze()
        self._thread = threading.Thread(group=None, target=self)
        self._state = make_state()
        self._queue = make_queue()
        self._ksp = ksp
        self._active_vessel_stream = None

        self.bridge = kec.bridge.Bridge(self._doze)

        self._thread.daemon = True
        self._thread.start()

    def __call__(self):
        with self._doze:
            while True:
                need_sync = False

                self._doze.sleep()

                print("Checking for flight status change")
                if self._is_ready("flying"):
                    new_flying = self._consume("flying")

                    if self._state["flying"] != new_flying:
                        self._state["flying"] = new_flying

                        if self._state["flying"]:
                            self._start_flight()
                        else:
                            self._end_flight()

                print("Checking for vessel change")
                if self._state["flying"] and self._is_ready("vessel"):
                    print("Consume vessel from queue")
                    vessel = self._consume("vessel")

                    if type(vessel) == ValueError:
                        vessel = None

                    if vessel != self._state["vessel"]:
                        if vessel == None:
                            print("Vessel is gone")
                        else:
                            print(f"New vessel: {vessel}")

                        need_sync = True
                        self._state["vessel"] = vessel

                print("Checking for vesel update needed")
                if self._state["vessel"] != None:
                    if need_sync:
                        self.bridge.sync(self._state["vessel"].control)
                    else:
                        self.bridge.update(self._state["vessel"].control)

    # The condition variable must be locked upon entry to this method
    def _is_ready(self, name:str):
        return self._queue[name]["dirty"]

    # The condition variable must be locked upon entry to this method
    def _consume(self, name:str):
        self._queue[name]["dirty"] = False

        return self._queue[name]["value"]

    # The condition variable must be locked upon entry to this method
    def _start_flight(self):
        print("Flight started")

        # The stream management must be done in a thread seperate from the thread that delivered the
        # game scene change notification or a dead lock happens inside kRPC
        self._active_vessel_stream = self._ksp.add_stream(getattr, self._ksp.space_center, "active_vessel")
        self._active_vessel_stream.add_callback(lambda vessel : self.enqueue("vessel", vessel))
        self._active_vessel_stream.start()

        print("Done handling flight start")

    # The condition variable must be locked upon entry to this method
    def _end_flight(self):
        print("Flight ended")

        self._state["vessel"] = None
        self._active_vessel_stream = None

    def enqueue(self, name:str, value):
        with self._doze:
            self._queue[name]["value"] = value
            self._queue[name]["dirty"] = True

            self._doze.wakeup()
