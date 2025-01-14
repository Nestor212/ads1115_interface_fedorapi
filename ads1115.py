# SPDX-FileCopyrightText: 2018 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`ads1x15`
====================================================

CircuitPython base class driver for ADS1015/1115 ADCs.

* Author(s): Carter Nelson
"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADS1x15.git"

import time
import gpiod
from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Dict, List, Optional

    from busio import I2C
except ImportError:
    I2C = None

_ADS1X15_DEFAULT_ADDRESS = const(0x48)
_ADS1X15_POINTER_CONVERSION = const(0x00)
_ADS1X15_POINTER_CONFIG = const(0x01)
_ADS1X15_POINTER_LO_THRES = const(0x02)
_ADS1X15_POINTER_HI_THRES = const(0x03)

_ADS1X15_CONFIG_OS_SINGLE = const(0x8000)
_ADS1X15_CONFIG_MUX_OFFSET = const(12)
_ADS1X15_CONFIG_COMP_QUEUE = {
    0: 0x0003,
    1: 0x0000,
    2: 0x0001,
    4: 0x0002,
}
_ADS1X15_CONFIG_GAIN = {
    2 / 3: 0x0000,
    1: 0x0200,
    2: 0x0400,
    4: 0x0600,
    8: 0x0800,
    16: 0x0A00,
}

GPIO_CHIP = "/dev/gpiochip0"

def configure_gpio_line(pin: int, direction: str):
    """Helper function to configure a GPIO line."""
    chip = gpiod.Chip(GPIO_CHIP)
    line = chip.get_line(pin)

    if direction == "in":
        config = gpiod.LineRequest(consumer="ads1x15", type=gpiod.LINE_REQ_DIR_IN)
    elif direction == "out":
        config = gpiod.LineRequest(consumer="ads1x15", type=gpiod.LINE_REQ_DIR_OUT)
    else:
        raise ValueError("Invalid GPIO direction")

    line.request(config)
    return line

class Mode:
    """An enum-like class representing possible ADC operating modes."""

    CONTINUOUS = 0x0000
    SINGLE = 0x0100

class Comp_Mode:
    """An enum-like class representing possible ADC Comparator operating modes."""

    TRADITIONAL = 0x0000
    WINDOW = 0x0010

class Comp_Polarity:
    """An enum-like class representing possible ADC Comparator polarity modes."""

    ACTIVE_LOW = 0x0000
    ACTIVE_HIGH = 0x0008

class Comp_Latch:
    """An enum-like class representing possible ADC Comparator latching modes."""

    NONLATCHING = 0x0000
    LATCHING = 0x0004

class ADS1x15:
    """Base functionality for ADS1x15 analog to digital converters."""

    def __init__(
        self,
        i2c: I2C,
        gain: float = 1,
        data_rate: Optional[int] = None,
        mode: int = Mode.SINGLE,
        comparator_queue_length: int = 0,
        comparator_low_threshold: int = -32768,
        comparator_high_threshold: int = 32767,
        comparator_mode: int = Comp_Mode.TRADITIONAL,
        comparator_polarity: int = Comp_Polarity.ACTIVE_LOW,
        comparator_latch: int = Comp_Latch.NONLATCHING,
        address: int = _ADS1X15_DEFAULT_ADDRESS,
        alert_pin: Optional[int] = None,
    ):
        self._last_pin_read = None
        self.buf = bytearray(3)
        self.initialized = False
        self.i2c_device = I2CDevice(i2c, address)
        self.gain = gain
        self.data_rate = self._data_rate_default() if data_rate is None else data_rate
        self.mode = mode
        self.comparator_queue_length = comparator_queue_length
        self.comparator_low_threshold = comparator_low_threshold
        self.comparator_high_threshold = comparator_high_threshold
        self.comparator_mode = comparator_mode
        self.comparator_polarity = comparator_polarity
        self.comparator_latch = comparator_latch
        self.alert_pin = alert_pin
        if alert_pin is not None:
            self.alert_line = configure_gpio_line(alert_pin, "in")
        else:
            self.alert_line = None
        self.initialized = True
        self._write_config()

    def wait_for_alert(self, timeout: Optional[float] = None):
        """Wait for an ALERT signal if alert_pin is configured."""
        if self.alert_line is None:
            raise RuntimeError("No ALERT pin configured.")

        if self.alert_line.event_wait(timeout):
            print("Alert signal received.")
        else:
            print("Timeout waiting for alert signal.")

    def _data_rate_default(self) -> int:
        raise NotImplementedError("Subclasses must implement _data_rate_default!")

    def _conversion_value(self, raw_adc: int) -> int:
        raise NotImplementedError("Subclass must implement _conversion_value function!")

    def _read(self, pin: int) -> int:
        if self.mode == Mode.CONTINUOUS and self._last_pin_read == pin:
            return self._conversion_value(self.get_last_result(True))

        self._last_pin_read = pin
        self._write_config(pin)

        if self.mode == Mode.SINGLE:
            while not self._conversion_complete():
                pass
        else:
            time.sleep(2 / self.data_rate)

        return self._conversion_value(self.get_last_result(False))

    def _conversion_complete(self) -> int:
        return self._read_register(_ADS1X15_POINTER_CONFIG) & 0x8000

    def get_last_result(self, fast: bool = False) -> int:
        return self._read_register(_ADS1X15_POINTER_CONVERSION, fast)

    def _write_register(self, reg: int, value: int):
        self.buf[0] = reg
        self.buf[1] = (value >> 8) & 0xFF
        self.buf[2] = value & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self.buf)

    def _read_register(self, reg: int, fast: bool = False) -> int:
        with self.i2c_device as i2c:
            if fast:
                i2c.readinto(self.buf, end=2)
            else:
                i2c.write_then_readinto(bytearray([reg]), self.buf, in_end=2)
        return self.buf[0] << 8 | self.buf[1]

    def _write_config(self, pin_config: Optional[int] = None) -> None:
        if pin_config is None:
            pin_config = (
                self._read_register(_ADS1X15_POINTER_CONFIG) & 0x7000
            ) >> _ADS1X15_CONFIG_MUX_OFFSET

        config = _ADS1X15_CONFIG_OS_SINGLE if self.mode == Mode.SINGLE else 0

        config |= (pin_config & 0x07) << _ADS1X15_CONFIG_MUX_OFFSET
        config |= _ADS1X15_CONFIG_GAIN[self.gain]
        config |= self.mode
        config |= self.rate_config[self.data_rate]
        config |= self.comparator_mode
        config |= self.comparator_polarity
        config |= self.comparator_latch
        config |= _ADS1X15_CONFIG_COMP_QUEUE[self.comparator_queue_length]
        self._write_register(_ADS1X15_POINTER_CONFIG, config)

    def _read_config(self) -> None:
        config_value = self._read_register(_ADS1X15_POINTER_CONFIG)

        self.gain = next(
            key
            for key, value in _ADS1X15_CONFIG_GAIN.items()
            if value == (config_value & 0x0E00)
        )
        self.data_rate = next(
            key
            for key, value in self.rate_config.items()
            if value == (config_value & 0x00E0)
        )
        self.comparator_queue_length = next(
            key
            for key, value in _ADS1X15_CONFIG_COMP_QUEUE.items()
            if value == (config_value & 0x0003)
        )
        self.mode = Mode.SINGLE if config_value & 0x0100 else Mode.CONTINUOUS
        self.comparator_mode = (
            Comp_Mode.WINDOW if config_value & 0x0010 else Comp_Mode.TRADITIONAL
        )
        self.comparator_polarity = (
            Comp_Polarity.ACTIVE_HIGH
            if config_value & 0x0008
            else Comp_Polarity.ACTIVE_LOW
        )
        self.comparator_latch = (
            Comp_Latch.LATCHING if config_value & 0x0004 else Comp_Latch.NONLATCHING
        )