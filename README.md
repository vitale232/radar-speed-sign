# Radar Speed Sign

This project is a work in progress.

We're trying to make a relatively inexpensive sign that can sit on the side
of the road and report a motorists speed. These types of signs are generally
only considered effective when actively placed, making it a great solution
for the neighbors that speed by your home.

The project is based on a Raspberry Pi, OmniPreSense Radar chip, and an
LED Matrix purchased from Adafruit.

## Dependencies

Big thanks to the [`rpi-rgb-led-matrix` lib](https://github.com/hzeller/rpi-rgb-led-matrix)
for the heavy lifting. We're using their Python Bindings. The project is
licensed under [GNU Public License v2](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/COPYING)

Another big thanks to [`pyserial`](https://github.com/pyserial/pyserial) for making
the radar data easy to retrieve in Python. This project is licensed uner the
[3-clause BSD](https://github.com/pyserial/pyserial/blob/master/LICENSE.txt)


