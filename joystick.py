import sys
import time

import krpc
import pygame

ACTIVE_VESSEL = None

DEAD_BAND = 0.02
# Calibration values: min, max, center
CALIBRATION = {
    0: [-0.6, 0.6, 0.01174962614825892],
    1: [-0.55, 0.55, -0.003936887722403638],
    2: [-0.55, 0.55, 0.027436140018921477],
    3: [-0.98, 0.98, 0],
    4: [-0.6, 0.6, 0.01174962614825892]
}
CALIBRATION_MIN = 0
CALIBRATION_MAX = 1
CALIBRATION_CENTER = 2

AXIS_LAST_POSITION = {}
EVENT_HANDLERS = {}

AXIS_HANDLERS = {}
AXIS_ROLL = 0
AXIS_PITCH = 1
AXIS_THROTTLE = 2
AXIS_YAW = 4

BUTTON_HANDLERS = {}
BUTTON_DUAL_RATES = 0
BUTTON_GEAR = 1
BUTTON_RESET = 2
BUTTON_MODE_DOWN = 3
BUTTON_MODE_UP = 4

def enumerate_joysticks():
    devices = {}

    for x in range(pygame.joystick.get_count()):
        device = pygame.joystick.Joystick(x)

        devices[device.get_name()] = device.get_guid()

    return devices

def get_joystick(name:str):
    for x in range(pygame.joystick.get_count()):
        device = pygame.joystick.Joystick(x)

        if device.get_name() == name:
            return device

    raise RuntimeError(f"Joystick not found: {name}")

def button_event_handler(number:int, pressed:bool):
    if number not in BUTTON_HANDLERS:
        return

    handler = BUTTON_HANDLERS[number]

    handler(pressed)

def axis_event_handler(number:int, position:float):
    if number not in AXIS_HANDLERS:
        return

    if number in AXIS_LAST_POSITION and abs(AXIS_LAST_POSITION[number] - position) < DEAD_BAND:
        return

    AXIS_LAST_POSITION[number] = position
    adjustment = 1

    if number in CALIBRATION:
        position = position - CALIBRATION[number][CALIBRATION_CENTER]

    if abs(position) < DEAD_BAND * 2:
        position = 0
    elif number in CALIBRATION:
        if position > 0:
            adjustment = 1 / CALIBRATION[number][CALIBRATION_MAX]
        else:
            adjustment = abs(1 / CALIBRATION[number][CALIBRATION_MIN])

    adjusted = position * adjustment

    if adjusted > 1:
        adjusted = 1
    elif adjusted < -1:
        adjusted = -1

    handler = AXIS_HANDLERS[number]

    handler(adjusted)

def gear_switch_handler(pressed:bool):
    state = "retracted"

    if pressed:
        state = "extended"

    print(f"Gear: {state}")
    ACTIVE_VESSEL.control.gear = pressed

def dual_rates_switch_handler(pressed:bool):
    state = "disengaged"

    if pressed:
        state = "engaged"

    print(f"Brakes: {state}")
    ACTIVE_VESSEL.control.brakes = pressed

def mode_switch_handler(switch_down:bool):
    state = "on"

    if switch_down:
        state = "off"

    print(f"SAS stability: {state}")

    try:
        if state == "on":
            ACTIVE_VESSEL.control.sas = True
            ACTIVE_VESSEL.control.sas_mode = ACTIVE_VESSEL.control.sas_mode.stability_assist
        else:
            ACTIVE_VESSEL.control.sas = False
    except:
        pass

def reset_button_handler(pressed:bool):
    if pressed:
        print("Stage")
        ACTIVE_VESSEL.control.activate_next_stage()

def throttle_axis_handler(position:float):
    value = (position + 1) / 2
    inverted = 1 - value
    percentage = int(100 * inverted)

    print(f"Throttle: {percentage}%")
    ACTIVE_VESSEL.control.throttle = inverted

def yaw_axis_handler(position:float):
    print(f"Yaw: {position}")
    ACTIVE_VESSEL.control.yaw = position

def pitch_axis_handler(position:float):
    print(f"Pitch: {position}")
    ACTIVE_VESSEL.control.pitch = position

def roll_axis_handler(position:float):
    print(f"Roll: {position}")
    ACTIVE_VESSEL.control.roll = position

def sync_vessel(device):
    for axis in range(device.get_numaxes()):
        axis_event_handler(axis, device.get_axis(axis))

    for button in range(device.get_numbuttons()):
        button_event_handler(button, bool(device.get_button(button)))

def connect_ksp():
    while True:
        try:
            return krpc.connect()
        except:
            time.sleep(1)

def active_vessel(ksp):
    try:
        return ksp.space_center.active_vessel
    except:
        return None

def init():
    pygame.init()
    pygame.joystick.init()

    EVENT_HANDLERS[pygame.JOYBUTTONDOWN] = lambda event: button_event_handler(event.button, True)
    EVENT_HANDLERS[pygame.JOYBUTTONUP] = lambda event: button_event_handler(event.button, False)
    EVENT_HANDLERS[pygame.JOYAXISMOTION] = lambda event: axis_event_handler(event.axis, event.value)

    AXIS_HANDLERS[AXIS_PITCH] = pitch_axis_handler
    AXIS_HANDLERS[AXIS_ROLL] = roll_axis_handler
    AXIS_HANDLERS[AXIS_THROTTLE] = throttle_axis_handler
    AXIS_HANDLERS[AXIS_YAW] = yaw_axis_handler

    BUTTON_HANDLERS[BUTTON_DUAL_RATES] = dual_rates_switch_handler
    BUTTON_HANDLERS[BUTTON_GEAR] = gear_switch_handler
    BUTTON_HANDLERS[BUTTON_MODE_DOWN] = mode_switch_handler
    BUTTON_HANDLERS[BUTTON_RESET] = reset_button_handler

def main():
    global ACTIVE_VESSEL

    init()

    if len(sys.argv) == 1:
        for name in enumerate_joysticks():
            print(name)

        sys.exit(0)

    device = get_joystick(sys.argv[1])

    while True:
        print("Connecting to KSP...")
        ksp = connect_ksp()
        print(f"Connected to kRPC version {ksp.krpc.get_status().version}")

        while True:
            # Use a timeout so the program will respond to ctrl+c to terminate it
            event = pygame.event.wait(50)

            vessel = active_vessel(ksp)

            if vessel != ACTIVE_VESSEL:
                ACTIVE_VESSEL = vessel

                if ACTIVE_VESSEL is None:
                    print("No vessel")
                else:
                    print(f"Vessel change: {ACTIVE_VESSEL.name}")
                    sync_vessel(device)

            if event.type == pygame.NOEVENT:
                continue
            elif event.type not in EVENT_HANDLERS:
                continue

            handler = EVENT_HANDLERS[event.type]
            handler(event)

main()
