import time
import csv
import gpiod
from ads1115 import ADS1x15 # Use the custom driver instead
import board
import busio

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize two ADS1115 modules using the custom driver
ads1 = ADS1x15(i2c, address=0x48)  # Default address
ads2 = ADS1x15(i2c, address=0x49)  # Secondary address

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
                "ADS1_CH0": ads1._read(0),  # Read channel 0
                "ADS1_CH1": ads1._read(1),  # Read channel 1
                "ADS1_CH2": ads1._read(2),  # Read channel 2
                "ADS1_CH3": ads1._read(3),  # Read channel 3
                "ADS2_CH0": ads2._read(0),  # Read channel 0
                "ADS2_CH1": ads2._read(1),  # Read channel 1
                "ADS2_CH2": ads2._read(2),  # Read channel 2
                "ADS2_CH3": ads2._read(3),  # Read channel 3
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
