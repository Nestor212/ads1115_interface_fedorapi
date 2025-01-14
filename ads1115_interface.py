import time
import csv
import gpiod
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize two ADS1115 modules on different I2C addresses
ads1 = ADS1115(i2c, address=0x48)  # Default address
ads2 = ADS1115(i2c, address=0x49)  # Secondary address

# Define GPIO chip and lines for additional controls 
GPIO_CHIP = "/dev/gpiochip0"  # Adjust if needed
gpio_chip = gpiod.Chip(GPIO_CHIP)

ENABLE_PIN = 17  # GPIO pin number
enable_line = gpio_chip.get_line(ENABLE_PIN)
config = gpiod.LineRequest()
config.consumer = "sensor_logger"
config.request_type = gpiod.LINE_REQ_DIR_OUT

enable_line.request(config)

def enable_sensors(enable):
    enable_line.set_value(1 if enable else 0)

# Enable sensors
enable_sensors(True)

# Open a CSV file for logging
time_stamp = time.strftime("%Y%m%d_%H%M%S")
filename = f"ads1115_log_{time_stamp}.csv"

with open(filename, "w", newline="") as csvfile:
    fieldnames = ["Timestamp", "ADS1_CH0", "ADS1_CH1", "ADS1_CH2", "ADS1_CH3",
                  "ADS2_CH0", "ADS2_CH1", "ADS2_CH2", "ADS2_CH3"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()

    try:
        while True:
            # Read all 4 channels from both ADS1115 modules
            readings = {
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ADS1_CH0": AnalogIn(ads1, ADS1115.P0).voltage,
                "ADS1_CH1": AnalogIn(ads1, ADS1115.P1).voltage,
                "ADS1_CH2": AnalogIn(ads1, ADS1115.P2).voltage,
                "ADS1_CH3": AnalogIn(ads1, ADS1115.P3).voltage,
                "ADS2_CH0": AnalogIn(ads2, ADS1115.P0).voltage,
                "ADS2_CH1": AnalogIn(ads2, ADS1115.P1).voltage,
                "ADS2_CH2": AnalogIn(ads2, ADS1115.P2).voltage,
                "ADS2_CH3": AnalogIn(ads2, ADS1115.P3).voltage,
            }

            # Write to CSV
            writer.writerow(readings)

            # Print to console for monitoring
            print(readings)

            # Wait 1 second before next reading
            time.sleep(1)

    except KeyboardInterrupt:
        print("Logging stopped by user.")

# Disable sensors before exiting
enable_sensors(False)
