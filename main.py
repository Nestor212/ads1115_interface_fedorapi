import time
import csv
import socket
import ads1115 as ads  # Use the custom driver instead
from smbus2 import SMBus

# Voltage Divider Circuit Details
r1 = 56000  # Resistor R1 in ohms
vIn = 5.5

# UNIX domain socket path
HOST = "localhost"
PORT = 65432

#coeff_a = [1.0986, 1.0991, 1.0964, 1.0989, 1.1000, 1.0972, 1.0988, 1.1004]
#coeff_b = [-0.0005, -0.0005, -0.0009, -0.0006, -0.0005, -0.0009, -0.0007, -0.0005]

coeff_a = [0.9880, 0.9855, 0.9804, 0.9827, 0.9880, 0.9804, 0.9829, 0.9829]
coeff_b = [-0.0010, -0.0009, -0.0007, -0.0002, -0.0010, -0.0007, -0.0008, -0.0008]

# Lookup table for converting resistance to temperature for a 100k NTC thermistor
# The table contains tuples of (resistance in ohms, temperature in Celsius)
thermistor_table = [
    ##
    (322000, 32.0), (315000, 33.0), (308000, 34.0), (299000, 35.0), (293500, 36.0),
    (283500, 37.0), (274000, 38.0), (261700, 40.0), (254000, 41.0), (242000, 43.0),
    (228000, 45.0), (214800, 47.0), (210000, 48.0), (197300, 50.0), (186500, 52.0),
    ## Temperatures < 55.64°C exceed adc voltage range (4.096V)
    
    (178600, 54.0), (152900, 60.0), (139700, 63.0), (108300, 73.0), (99400, 77.0),
    (89900, 81.0), (81800, 85.0), (63300, 95.0), (62000, 96.0), (60700, 97.0),
    (60000, 98.0), (58100, 99.0), (56600, 100.0), (55100, 101.0), (54400, 102.0),
    (52800, 103.0), (51800, 104.0), (50400, 105.0), (49500, 106.0), (48500, 107.0),
    (47100, 108.0), (46000, 109.0), (45000, 110.0), (44000, 111.0), (42900, 112.0),
    (42300, 113.0), (41200, 114.0), (40200, 115.0), (39400, 116.0), (38600, 117.0),
    (37600, 118.0), (36900, 119.0), (36000, 120.0), (35300, 121.0), (34900, 122.0),
    (33700, 123.0), (33400, 124.0), (32600, 125.0), (32800, 126.0), (31900, 127.0),
    (31200, 128.0), (30700, 129.0), (29900, 130.0), (29200, 131.0), (28700, 132.0),
    (28200, 133.0), (27600, 134.0), (26900, 135.0), (26200, 136.0), (25500, 137.0),
    (25300, 138.0), (23750, 140.0), (22670, 141.0), (22300, 142.0), (22000, 147.0),
    (21500, 148.0), (21000, 150.0), (20510, 150.2), (20000, 152.0), (17500, 158.5),
    (11250, 180.0), (11000, 182.0), (10860, 183.0), (10500, 187.0), (10450, 185.0),
    (10200, 187.0), (10000, 190.0), (9890, 189.0), (9600, 190.0), (9500, 192.5),
    (8370, 200.0), (7500, 207.0), (7000, 211.0), (6500, 217.0), (6000, 220.0),
    (5700, 223.0), (5510, 225.0), (5300, 228.0), (5000, 231.0), (4800, 234.0),
    (4610, 236.0), (4410, 239.0), (4200, 242.0), (4000, 245.0), (3800, 248.7),
    (3450, 255.0), (3200, 259.4), (2100, 283.0), (1600, 301.0), (1520, 304.0),
    (1400, 310.0)
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
    
    # print(f"Raw ADC: {raw_reading}, Voltage: {voltage:.3f} V")
    # Calibrate the voltage using the provided coefficients
    calibrated_voltage = (voltage - coeff_b[0]) / coeff_a[0]
    
    # query_temperature(calibrated_voltage)

    # Voltage to resistance conversion
    rTherm = r1 * (1 / ((vIn / calibrated_voltage) - 1))
    # print(f"Voltage: {calibrated_voltage:.3f} V, Resistance: {rTherm:.2f} ohms")
    
    # Lookup temperature from the table
    temperature = lookup_temperature(rTherm)
    return [round(temperature, 2) if temperature is not None else None, round(calibrated_voltage, 3)]

# CSV file for logging
time_stamp = time.strftime("%Y%m%d_%H%M")
filename = f"Logs/Smoker_log_{time_stamp}.csv"

with open(filename, "w", newline="") as csvfile:
    fieldnames = ["Timestamp", "TEMP00", "VOLT00", "TEMP01", "VOLT01",
                  "TEMP02", "VOLT02", "TEMP03", "VOLT03", "TEMP10", "VOLT10",
                  "TEMP11", "VOLT11", "TEMP12", "VOLT12", "TEMP13", "VOLT13"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    try:
        while True:
            try:
                # Read sensor values and store results in a dictionary
                readings = {"Timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

                # Loop through both ADS instances and their channels
                for sensor, ads in enumerate([ads1, ads2]):
                    for channel in range(4):
                        temperature, voltage = convert_to_temperature(ads._read(channel))
                        readings[f"TEMP{sensor}{channel}"] = temperature
                        readings[f"VOLT{sensor}{channel}"] = voltage

                # Write to CSV
                writer.writerow(readings)
                csvfile.flush()


                # Print to console for monitoring
                print(readings)

                # Wait 1 second before next reading
                time.sleep(1)

            except OSError as e:
                print(f"OS error occurred: {e}. Reinitializing I2C and ADS modules...")
                initialize_ads_modules()

    except KeyboardInterrupt:
        print("Logging stopped by user.")