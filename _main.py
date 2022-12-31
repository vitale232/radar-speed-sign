#!/usr/bin/env python
import sys
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics
import serial


USE_SCREEN = True
NO_OP_SECONDS = 0

EMOTE_THRESHOLD = 133
SLOW_DOWN_THRESHOLD = 126
MIN_DISPLAYABLE_SPEED = 8

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


def read_next_velocity(serial_port):
    while True:
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
                    print(
                        f"Could not parse the number from the following string:: {rxstr}"
                    )
                    speed_available = False
        if speed_available == True:
            return round(rxfloat)


def show_speed(speed, matrix, canvas, font, color, timeout=0.25):
    graphics.DrawText(canvas, font, 0, 30, graphics.Color(*color), f"{speed: 2}")
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(timeout)
    return


def say_hi(matrix, canvas, font, color, timeout=0.5):
    graphics.DrawText(canvas, font, 0, 30, graphics.Color(*color), "FeelBetter!")
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(timeout)
    return


def show_slow_down(matrix, canvas, font, color, iterations=2):
    n = 0
    while n < iterations:
        graphics.DrawText(canvas, font, 8, 15, graphics.Color(*color), "SLOW")
        graphics.DrawText(canvas, font, 8, 30, graphics.Color(*color), "DOWN")
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.75)
        matrix.Clear()
        time.sleep(0.25)
        n += 1
    return


def emote(matrix, canvas, font, color, iterations=2):
    n = 0
    print(f"{color=}")
    while n < iterations:
        graphics.DrawText(canvas, font, 8, 15, graphics.Color(*color), "FUCK")
        graphics.DrawText(canvas, font, 8, 30, graphics.Color(*color), "YOU!!")
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.75)
        matrix.Clear()
        time.sleep(0.25)
        n += 1
    return


def say_two_lines(line1, line2, matrix, canvas, font, color, iterations=2):
    n = 0
    print(f"{color=}")
    while n < iterations:
        graphics.DrawText(canvas, font, 0, 15, graphics.Color(*color), line1)
        graphics.DrawText(canvas, font, 0, 30, graphics.Color(*color), line2)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.75)
        matrix.Clear()
        time.sleep(0.25)
        n += 1
    return


def main(ser):
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    options.gpio_slowdown = 4

    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    digits_font = graphics.Font()
    digits_font.LoadFont("/home/vitale232/prj/matrix/fonts/HighwayGothic30.bdf")

    animation_font = graphics.Font()
    animation_font.LoadFont("/home/vitale232/prj/matrix/fonts/HighwayGothic16.bdf")

    RED = (255, 0, 0)
    # if USE_SCREEN:
    #     say_two_lines("Hello", "World", matrix, canvas, animation_font, RED, 5)

    # Initialize the USB port to read from the OPS-241A module
    ser.flush()

    # Initialize and query OPS243 Module
    # Ops_Speed_Output_Units = ["US", "UK", "UM", "UC"]
    # Ops_Blanks_Pref_Zero = "BZ"
    # Ops_Sampling_Frequency = "SX"
    # Ops_Transmit_Power = "PX"
    # Ops_Threshold_Control = "MX"
    # Ops_Overlook_Buffer = "OZ"
    OPS_UNITS_PREF = "UC"
    OPS_DIRECTION_PREF = "R+"  # In only

    print("\nInitializing OPS243 Module")
    # send_serial_cmd(ser, "Overlook buffer", Ops_Overlook_Buffer)
    send_serial_cmd(ser, "Set Speed Output Units: ", OPS_UNITS_PREF)
    send_serial_cmd(ser, "Set Direction Pref:", OPS_DIRECTION_PREF)
    # send_serial_cmd(ser, "Set Sampling Frequency: ", Ops_Sampling_Frequency)
    # send_serial_cmd(ser, "Set Transmit Power: ", Ops_Transmit_Power)
    # send_serial_cmd(ser, "Set Threshold Control: ", Ops_Threshold_Control)
    # send_serial_cmd(ser, "Set Blanks Preference: ", Ops_Blanks_Pref_Zero)
    ser.flush()

    speed = 0
    while True:
        matrix.Clear()
        speed = read_next_velocity(ser)
        if USE_SCREEN == True:
            if speed > EMOTE_THRESHOLD:
                print(f"{speed=}")
                show_speed(speed, matrix, canvas, digits_font, RED)
                matrix.Clear()
                emote(matrix, canvas, animation_font, RED, 1)
                matrix.Clear()
                show_slow_down(matrix, canvas, animation_font, RED, 1)
            elif speed > SLOW_DOWN_THRESHOLD:
                print(f"{speed=}")
                show_speed(speed, matrix, canvas, digits_font, RED)
                matrix.Clear()
                show_slow_down(matrix, canvas, animation_font, RED, 2)
                matrix.Clear()
            elif speed > MIN_DISPLAYABLE_SPEED:
                print(f"{speed=}")
                show_speed(speed, matrix, canvas, digits_font, RED)
                matrix.Clear()
            else:
                print(f'No display {speed = }')
                matrix.Clear()


if __name__ == "__main__":
    print(f"Waiting for {NO_OP_SECONDS} seconds... No Op...")
    time.sleep(NO_OP_SECONDS)
    print(f"Here goes")
    ser = serial.Serial(
        port="/dev/ttyACM0",
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5,
        write_timeout=2,
    )
    try:
        main(ser)
    except KeyboardInterrupt:
        print("Cleaning up...")
        if not ser.closed:
            ser.close()
            sys.exit()
