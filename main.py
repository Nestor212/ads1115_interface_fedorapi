import time
import csv
import socket
import ads1115 as ads  # Use the custom driver instead
from smbus2 import SMBus

# Voltage Divider Circuit Details
r1 = 56000  # Resistor R1 in ohms
vIn = 5

# UNIX domain socket path
HOST = "localhost"
PORT = 65432

coeff_a = [1.0986, 1.0991, 1.0964, 1.0989, 1.1000, 1.0972, 1.0988, 1.1004]
coeff_b = [-0.0005, -0.0005, -0.0009, -0.0006, -0.0005, -0.0009, -0.0007, -0.0005]

# Lookup table for converting resistance to temperature for a 100k NTC thermistor
# The table contains tuples of (resistance in ohms, temperature in Celsius)
thermistor_table = [
    (170853, 57), (161700, 59), (153092, 61), (144992, 63), (137367, 65), 
    (130189, 67), (123368, 69), (117000, 71), (110998, 73), (105338, 75),
    (100000, 77), (94963, 79), (90208, 81), (85719, 83), (81479, 85),
    (77438, 87), (73654, 89), (70076, 91), (66692, 93), (63491, 95),
    (60461, 97), (57594, 99), (54878, 101), (52306, 103), (49847, 105),
    (47538, 107), (45349, 109), (43273, 111), (41303, 113), (39434, 115),
    (37660, 117), (35976, 119), (34376, 121), (32843, 123), (31399, 125),
    (30027, 127), (28722, 129), (27481, 131), (26300, 133), (25177, 135),
    (24107, 137), (23089, 139), (22111, 141), (21188, 143), (20308, 145),
    (19469, 147), (18670, 149), (17907, 151), (17180, 153), (16486, 155),
    (15824, 157), (15187, 159), (14584, 161), (14008, 163), (13458, 165),
    (12932, 167), (12430, 169), (11949, 171), (11490, 173), (11051, 175),
    (10627, 177), (10225, 179), (9841, 181), (9473, 183), (9121, 185), (8783, 187), 
    
    # Temperature values above 187 degrees F are approximated
    (8461, 189), (8151, 191), (7853, 193), (7567, 195),
    (7292, 197), (7026, 199), (6770, 201), (6523, 203), (6285, 205),
    (6055, 207), (5833, 209), (5618, 211), (5410, 213), (5209, 215),
    (5015, 217), (4827, 219), (4645, 221), (4469, 223), (4299, 225),
    (4134, 227), (3975, 229), (3820, 231), (3669, 233), (3524, 235),
    (3383, 237), (3246, 239), (3113, 241), (2984, 243), (2859, 245),
    (2737, 247), (2619, 249), (2504, 251), (2392, 253), (2283, 255),
    (2177, 257), (2074, 259), (1974, 261), (1876, 263), (1781, 265),
    (1688, 267), (1598, 269), (1510, 271), (1424, 273), (1340, 275),
    (1259, 277), (1179, 279), (1102, 281), (1026, 283), (952, 285),
    (880, 287), (810, 289), (742, 291), (676, 293), (612, 295),
    (550, 297), (489, 299), (430, 301)
]

# Function to send a voltage query to the C program
# INW, hasn't been tested yet
def query_temperature(voltage):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            # Send the QUERY command with the voltage
            query = f"QUERY {voltage:.3f}"
            s.sendall(query.encode())
            # Receive the response (temperature)
            response = s.recv(1024).decode()
            print(f"Voltage: {voltage:.3f} V, Response: {response}")
            return response
    except Exception as e:
        print(f"Socket error: {e}")
        return None

def lookup_temperature(rTherm):
    """
    Converts resistance to temperature using the above lookup table with linear interpolation.
    :param rTherm: Thermistor resistance in ohms
    :return: Temperature in Fahrenheit
    """
    for i in range(len(thermistor_table) - 1):
        r1, t1 = thermistor_table[i]
        r2, t2 = thermistor_table[i + 1]
        if r2 <= rTherm <= r1:
            return t1 + (t2 - t1) * ((rTherm - r1) / (r2 - r1))
    return None  # Out of range

# Function to reinitialize the ADS1115 modules
def initialize_ads_modules():
    global i2c, ads1, ads2
    i2c = SMBus(i2c_bus_number)
    ads1 = ads.ADS1115(i2c_device=i2c, address=0x48)
    ads2 = ads.ADS1115(i2c_device=i2c, address=0x49)

# Use SMBus to access the I2C bus
i2c_bus_number = 1
initialize_ads_modules()

def convert_to_temperature(raw_reading):
    # Convert ADC reading to voltage
    voltage = raw_reading * (4.096 / 32768)
    
    # Calibrate the voltage using the provided coefficients
    calibrated_voltage = (voltage - coeff_b[0]) / coeff_a[0]
    
    # query_temperature(calibrated_voltage)

    # Voltage to resistance conversion
    rTherm = r1 * (1 / ((vIn / calibrated_voltage) - 1))
    
    # Lookup temperature from the table
    temperature = lookup_temperature(rTherm)
    return round(temperature, 2) if temperature is not None else None

# CSV file for logging
time_stamp = time.strftime("%Y%m%d_%H%M")
filename = f"Logs/Smoker_log_{time_stamp}.csv"

with open(filename, "w", newline="") as csvfile:
    fieldnames = ["Timestamp", "TEMP00", "TEMP01", "TEMP02", "TEMP03",
                  "TEMP10", "TEMP11", "TEMP12", "TEMP13"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    try:
        while True:
            try:
                # Read all 4 channels from both ADS1115 modules and convert to temperature
                readings = {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "TEMP00": convert_to_temperature(ads1._read(0)),
                    "TEMP01": convert_to_temperature(ads1._read(1)),
                    "TEMP02": convert_to_temperature(ads1._read(2)),
                    "TEMP03": convert_to_temperature(ads1._read(3)),
                    "TEMP10": convert_to_temperature(ads2._read(0)),
                    "TEMP11": convert_to_temperature(ads2._read(1)),
                    "TEMP12": convert_to_temperature(ads2._read(2)),
                    "TEMP13": convert_to_temperature(ads2._read(3)),
                }

                # Write to CSV
                writer.writerow(readings)
                csvfile.flush()

                # Print to console for monitoring
                print(readings)

                # Wait 1 second before next reading
                time.sleep(3)

            except OSError as e:
                print(f"OS error occurred: {e}. Reinitializing I2C and ADS modules...")
                initialize_ads_modules()

    except KeyboardInterrupt:
        print("Logging stopped by user.")
