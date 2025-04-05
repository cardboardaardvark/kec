import threading

class Doze:
    def __init__(self):
        self._condition = threading.Condition()
        self._sleep = True

    def __enter__(self):
        self._condition.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._condition.release()

    def sleep(self):
        while self._sleep:
            print("Starting to doze")

            self._condition.wait()

        print("Woke up from doze")
        self._sleep = True

    def wakeup(self):
        with self._condition:
            self._sleep = False
            self._condition.notify_all()
