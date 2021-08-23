import serial

from Maxy import MaxyController, MaxModuleDef, MaxyModule_8x7seg, MaxyModule_2x4x7seg
import random
import time


maxy = MaxyController()
maxy.define_modules([
    MaxModuleDef("Right1", MaxyModule_8x7seg),
    MaxModuleDef("Right2", MaxyModule_8x7seg),
    MaxModuleDef("Right3", MaxyModule_8x7seg),
    MaxModuleDef("Right4", MaxyModule_8x7seg),
    MaxModuleDef("Left1", MaxyModule_8x7seg),
    MaxModuleDef("Left2", MaxyModule_8x7seg),
    MaxModuleDef("Left3", MaxyModule_8x7seg),
    MaxModuleDef("Left4", MaxyModule_8x7seg),
    MaxModuleDef("tail", MaxyModule_2x4x7seg, ["tail1", "tail2"]),
])

names = ["Right1", "Right2", "Right3", "Right4", "Left1", "Left2", "Left3", "Left4"]
port = "COM7"


retry_count = 0


def clamp(value, min_value, max_value):
    return min(max_value, max(min_value, value))


def retry_delay(count):
    # Uses a small exponential backoff ( 5, 10, 20 sec )
    return 5 * 2 ** clamp(count, 0, 2)


while True:
    try:
        print(f"Connecting to serial port {port}")
        retry_count += 1
        maxy.connect(port, 9600, 5)
        maxy.set_global_intensity(3)
        #maxy.reconnect()
        print("Connected!")
        retry_count = 0
        while True:
            maxy.name.Right1.immediate_target = 0
            maxy.name.Right1.target = random.randint(-9999999, 9999999)
            maxy.name.tail1.target = random.randint(-999, 9999)
            maxy.name.tail2.target = random.randint(-999, 999)
            maxy.index[1].target = random.randint(-9999999, 9999999)
            maxy.name.Right3.target = random.randint(-9999999, 9999999)
            maxy.index[3].target = random.randint(-9999999, 9999999)
            maxy.name.Left1.target = random.randint(-9999, 9999)
            maxy.name.Left2.target = random.randint(-999, 999)
            maxy.name.Left3.target = random.randint(-99, 99)
            maxy.name.Left4.target = random.randint(-9, 9)
            time.sleep(4.5)
    except serial.serialutil.SerialTimeoutException:
        print("Write timeout")
    except serial.serialutil.SerialException as e:
        print("Serial error:" + str(e))
    delay = retry_delay(retry_count)
    print(f"Waiting {delay} seconds before trying to reconnect")
    time.sleep(delay)


