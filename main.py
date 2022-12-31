#!/usr/bin/env python
import inspect
from multiprocessing import Process, Value
import os
import sys
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics
import serial

OPS_UNITS_PREF = "UC"  # cm/s for debugging
OPS_DIRECTION_PREF = "R+"  # In only
EMOTE_THRESHOLD = 133
SLOW_DOWN_THRESHOLD = 126
MIN_DISPLAYABLE_SPEED = 8


# OPS_UNITS_PREF = "US"  # mph for Americans
# OPS_DIRECTION_PREF = "R+"  # In only
# # exclusive thresholds, using `>`
# EMOTE_THRESHOLD = 34
# SLOW_DOWN_THRESHOLD = 28
# MIN_DISPLAYABLE_SPEED = -1


class Config:
    def __init__(
        self,
        ops_units_pref,
        ops_direction_pref,
        emote_threshold,
        slow_down_threshold,
        min_displayable_speed,
    ) -> None:
        self.ops_units_pref = ops_units_pref
        self.ops_direction_pref = ops_direction_pref
        self.emote_threshold = emote_threshold
        self.slow_down_threshold = slow_down_threshold
        self.min_displayable_speed = min_displayable_speed


def paint_matrix(config, value):
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    options.gpio_slowdown = 4

    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    # Based on: https://stackoverflow.com/a/18489147/2264081
    fonts_dir = os.path.join(
        os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda: 0))), "fonts"
    )

    digits_font = graphics.Font()
    digits_font.LoadFont(os.path.join(fonts_dir, "HighwayGothic30.bdf"))

    animation_font = graphics.Font()
    animation_font.LoadFont(os.path.join(fonts_dir, "HighwayGothic16.bdf"))

    RED = (255, 0, 0)
    # if USE_SCREEN:
    #     say_two_lines("Hello", "World", matrix, canvas, animation_font, RED, 5)

    # Initialize the USB port to read from the OPS-241A module
    speed = 0
    while True:
        matrix.Clear()

        # speed = conn.recv()
        speed = round(value.value)
        if speed > config.emote_threshold:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED)
            matrix.Clear()
            emote("HOLY", "SHIT!", matrix, canvas, animation_font, RED, 1)
            matrix.Clear()
            emote("SLOW", "DOWN", matrix, canvas, animation_font, RED, 1)
        elif speed > config.slow_down_threshold:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED)
            matrix.Clear()
            emote("SLOW", "DOWN", matrix, canvas, animation_font, RED, 2)
        elif speed > config.min_displayable_speed:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED)
        else:
            # print(f'No display {speed = }')
            matrix.Clear()


def show_speed(speed, matrix, canvas, font, color, timeout=0.25):
    graphics.DrawText(canvas, font, 0, 30, graphics.Color(*color), f"{speed: 2}")
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(timeout)
    return


def emote(line1, line2, matrix, canvas, font, color, iterations=2):
    n = 0
    while n < iterations:
        graphics.DrawText(canvas, font, 8, 15, graphics.Color(*color), line1)
        graphics.DrawText(canvas, font, 8, 30, graphics.Color(*color), line2)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.75)
        matrix.Clear()
        time.sleep(0.25)
        n += 1
    return


def send_serial_cmd(serial_port, print_prefix, command):
    data_for_send_str = command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(print_prefix, command)
    serial_port.write(data_for_send_bytes)
    # Initialize message verify checking
    ser_message_start = "{"
    ser_write_verify = False
    # Print out module response to command string
    while not ser_write_verify:
        data_rx_bytes = serial_port.readline()
        data_rx_length = len(data_rx_bytes)
        if data_rx_length != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                ser_write_verify = True
    return ser_write_verify


def read_velocity(serial_port):
    speed_available = False
    rxfloat = 0.0
    rxbytes = serial_port.readline()
    if len(rxbytes) != 0:
        rxstr = str(rxbytes)
        # print(f"{rxstr=}")
        if rxstr.find("{") == -1:
            try:
                rxfloat = float(rxbytes)
                speed_available = True
            except ValueError:
                print(f"Could not parse the number from the following string:: {rxstr}")
                speed_available = False
    if speed_available == True:
        return round(rxfloat)
    else:
        return 0


def main(config):
    print("\nInitializing OPS243 Module")
    ser = serial.Serial(
        port="/dev/ttyACM0",
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5,
        write_timeout=2,
    )
    send_serial_cmd(ser, "Set Speed Output Units: ", config.ops_direction_pref)
    send_serial_cmd(ser, "Set Direction Pref:", config.ops_direction_pref)
    ser.flush()
    try:
        # parent_conn, child_conn = mp.Pipe()
        value = Value("d", 0)
        p = Process(
            target=paint_matrix,
            args=(
                config,
                value,
            ),
        )
        p.start()

        while True:
            velocity = read_velocity(ser)
            print(f"{velocity=}")
            value.value = velocity
            # parent_conn.send(v)
    except KeyboardInterrupt:
        print("Cleaning up...")
        if not ser.closed:
            ser.close()
            sys.exit()


if __name__ == "__main__":
    config = Config(
        OPS_UNITS_PREF,
        OPS_DIRECTION_PREF,
        EMOTE_THRESHOLD,
        SLOW_DOWN_THRESHOLD,
        MIN_DISPLAYABLE_SPEED,
    )
    main(config)
