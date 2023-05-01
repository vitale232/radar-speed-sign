#!/usr/bin/env python

from datetime import datetime
import inspect
from multiprocessing import Process, Value
import os
import sys
import time

import cv2
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics
import serial



OPS_DIRECTION_PREF = "R+"  # Means data in only
# exclusive thresholds, using greater than logic
EMOTE_THRESHOLD = 36
SLOW_DOWN_THRESHOLD = 30
BLINK_THRESHOLD = 28
MIN_DISPLAYABLE_SPEED = 1
MIN_LOG_SPEED = 14
MIN_VIDEO_SPEED = 14


class Config:
    def __init__(
        self,
        ops_direction_pref,
        emote_threshold,
        slow_down_threshold,
        blink_threshold,
        min_displayable_speed,
        min_log_speed,
        min_video_speed,
    ) -> None:
        self.ops_direction_pref = ops_direction_pref
        self.emote_threshold = emote_threshold
        self.slow_down_threshold = slow_down_threshold
        self.blink_threshold = blink_threshold
        self.min_displayable_speed = min_displayable_speed
        self.min_log_speed = min_log_speed
        self.min_video_speed = min_video_speed


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
    canvas = emote("Sys.", "Ready", matrix, canvas, animation_font, RED, 7)

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
                print(f"No display {speed = }")
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


def capture_video(
    is_recording,
    speed,
    current_datetime,
    duration=10,
    datetime_format="%Y-%m-%d_%H:%M:%S",
):
    # Initialize video capture
    cap = cv2.VideoCapture(0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    formatted_datetime = current_datetime.strftime(datetime_format)
    out = cv2.VideoWriter(f"vid_{formatted_datetime}.avi", fourcc, fps, (width, height))

    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Add metadata
            frame_with_metadata = overlay_metadata(
                frame, f"{speed.value} mph | {datetime.now().strftime(datetime_format)}"
            )

            # Display the resulting frame

            # Save the frame to disk
            out.write(frame_with_metadata)

            # Exit if 'q' key is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if time.time() > start_time + duration:
                break
        else:
            break

    # Release resources and close windows
    cap.release()
    out.release()
    is_recording.value = False
    return


def overlay_metadata(frame, metadata):
    height, width, _ = frame.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    font_thickness = 2
    text_color = (255, 255, 255)  # White
    rectangle_height = int(height * 0.1)

    # Draw a black rectangle at the top of the frame
    cv2.rectangle(frame, (0, 0), (width, rectangle_height), (0, 0, 0), -1)

    # Overlay the metadata
    y_offset = int(rectangle_height * 0.5)
    x_offset = 10
    cv2.putText(
        frame,
        metadata,
        (x_offset, y_offset),
        font,
        font_scale,
        text_color,
        font_thickness,
        cv2.LINE_AA,
    )
    return frame


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
        is_saving_video = Value("B", False)
        matrix_process = Process(
            target=paint_matrix,
            args=(
                config,
                shared_velocity,
            ),
        )
        matrix_process.start()

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
                observed_at = datetime.now()
                if velocity > config.min_log_speed:
                    datum = f"{observed_at}, {velocity_mph}\n"
                    print(f"{datum=}")
                    output_file.write(datum)
                    output_file.flush()
                if velocity > config.min_video_speed:
                    print(f"value: {is_saving_video.value}")
                    if is_saving_video.value == 0:
                        is_saving_video.value = 1
                        video_process = Process(
                            target=capture_video,
                            args=(is_saving_video, shared_velocity, observed_at),
                        )
                        video_process.start()
                    else:
                        print("Skip save")

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
        MIN_LOG_SPEED,
        MIN_VIDEO_SPEED,
    )
    main(config)
