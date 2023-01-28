#!/usr/bin/env python

from datetime import datetime
import inspect
from multiprocessing import Process, Value
import os
import sys
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics
import serial


# OPS_UNITS_PREF = "UC"  # cm/s for debugging
# OPS_DIRECTION_PREF = "R+"  # In only
# EMOTE_THRESHOLD = 133
# SLOW_DOWN_THRESHOLD = 126
# MIN_DISPLAYABLE_SPEED = 8


OPS_DIRECTION_PREF = "R+"  # In only
# exclusive thresholds, using `>`
EMOTE_THRESHOLD = 36
SLOW_DOWN_THRESHOLD = 30
BLINK_THRESHOLD = 28
MIN_DISPLAYABLE_SPEED = 1
MIN_LOG_SPEED = 14


class Config:
    def __init__(
        self,
        ops_direction_pref,
        emote_threshold,
        slow_down_threshold,
        blink_threshold,
        min_displayable_speed,
        min_log_speed
    ) -> None:
        self.ops_direction_pref = ops_direction_pref
        self.emote_threshold = emote_threshold
        self.slow_down_threshold = slow_down_threshold
        self.blink_threshold = blink_threshold
        self.min_displayable_speed = min_displayable_speed
        self.min_log_speed = min_log_speed


def paint_matrix(config, speed_value):
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    # RPi 4
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
    speed = 0

    # Say hello, world
    canvas = emote("Sys.", "Ready", matrix, canvas, animation_font, RED, 10)
    time.sleep(0.2)
    canvas = emote("Sys.", "Ready", matrix, canvas, animation_font, RED, 10)
    time.sleep(0.2)
    canvas = emote("Sys.", "Ready", matrix, canvas, animation_font, RED, 10)

    while True:
        matrix.Clear()

        speed = speed_value.value
        if speed > config.emote_threshold:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED, 0.5)
            matrix.Clear()
            emote("HOLY", "SHIT!", matrix, canvas, animation_font, RED, 1)
            matrix.Clear()
            emote("SLOW", "DOWN", matrix, canvas, animation_font, RED, 1)
        elif speed > config.slow_down_threshold:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED, 0.5)
            matrix.Clear()
            emote("SLOW", "DOWN", matrix, canvas, animation_font, RED, 2)
        elif speed > config.blink_threshold:
            show_speed(speed, matrix, canvas, digits_font, RED)
            matrix.Clear()
            time.sleep(0.25)
            show_speed(speed, matrix, canvas, digits_font, RED)
        elif speed > config.min_displayable_speed:
            print(f"{speed=}")
            show_speed(speed, matrix, canvas, digits_font, RED)
        else:
            if speed > 5:
                print(f'No display {speed = }')
            # else:
            #     print(f"{speed=}")
            #     show_speed(speed, matrix, canvas, digits_font, RED)
            pass


def show_speed(speed, matrix, canvas, font, color, timeout=0.25):
    graphics.DrawText(canvas, font, 0, 30, graphics.Color(*color), f"{speed: 2}")
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(timeout)
    return canvas


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
    return canvas


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
        return rxfloat
    else:
        return 0.0


def main(config):
    print(f"\nInitializing OPS241 Module at {datetime.now()}")
    # OPS 241 API Doc: https://omnipresense.com/wp-content/uploads/2021/09/AN-010-X_API_Interface.pdf
    ser = serial.Serial(
        port="/dev/ttyACM0",
        baudrate=19_200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.50,
    )
    # send_serial_cmd(ser, "Set Speed Output Units: ", config.ops_units_pref)
    send_serial_cmd(ser, "Set Direction Pref:", config.ops_direction_pref)
    ser.flush()

    try:
        # Inspired by hzeller's comments here: https://github.com/hzeller/rpi-rgb-led-matrix/issues/695
        # Create a new process where the RGB Matrix can live and paint rapidly, without
        # affecting the main process's ability to read the serial data.
        # Shared mem is allocated and passed to the process where the RGB LED
        # matrix is initialized and painted.
        # The "i" means signed Int
        # More opts: https://docs.python.org/3/library/array.html#module-array
        shared_velocity = Value("i", 0)
        p = Process(
            target=paint_matrix,
            args=(
                config,
                shared_velocity,
            ),
        )
        p.start()

        output_csv_path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda: 0))),
            "speeds.csv",
        )
        with open(output_csv_path, "a") as output_file:
            print(f"Commence monitoring at {datetime.now()}")
            while True:
                velocity = read_velocity(ser)
                velocity_mph = round(velocity * 2.23694)
                shared_velocity.value = velocity_mph
                if velocity > config.min_log_speed:
                    datum = f"{datetime.now()}, {velocity_mph}\n"
                    print(f"{datum=}")
                    output_file.write(datum)
                    output_file.flush()

    except KeyboardInterrupt:
        print("Cleaning up...")
        if not ser.closed:
            ser.close()
            sys.exit()


if __name__ == "__main__":
    config = Config(
        OPS_DIRECTION_PREF,
        EMOTE_THRESHOLD,
        SLOW_DOWN_THRESHOLD,
        BLINK_THRESHOLD,
        MIN_DISPLAYABLE_SPEED,
        MIN_LOG_SPEED
    )
    main(config)
