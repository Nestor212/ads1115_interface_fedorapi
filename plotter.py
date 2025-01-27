import csv
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from tkinter import Tk, filedialog

# Initialize data storage
timestamps = []
temps = {f"TEMP{sensor}{channel}": [] for sensor in range(2) for channel in range(4)}  # TEMP00-TEMP03, TEMP10-TEMP13

# User-configurable running mean window size
window_size = 32  # Number of values to average

# Function to calculate the running mean
def running_mean(data, window):
    if len(data) < window:
        # Calculate mean for available data points only
        return [np.mean(data[:i+1]) for i in range(len(data))]
    return [np.mean(data[end-window:end]) for end in range(window, len(data)+1)]
    # return np.convolve(data, np.ones(window) / window, mode='valid')


# Function to select a file using a file dialog
def select_file():
    root = Tk()
    root.withdraw()  # Hide the root window
    root.attributes('-topmost', True)  # Bring the file dialog to the front
    file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
    return file_path

# Select the file
filename = select_file()
if not filename:
    print("No file selected. Exiting.")
    exit()

# Function to update the plot
def update_plot(frame):
    global timestamps, temps

    # Read the latest data from the CSV file
    with open(filename, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Skip already plotted rows
            if row["Timestamp"] in timestamps:
                continue

            # Check if all sensors have valid (non-None) data for the row
            if any(row[key] is None or row[key] == "" for key in temps.keys()):
                continue  # Skip rows with invalid data

            # Append new data
            timestamps.append(row["Timestamp"])
            for key in temps.keys():
                value = row.get(key)
                temps[key].append(float(value) if value else None)

    # Clear the plot
    plt.cla()

    # Plot only the running mean data
    for sensor_channel, temp_values in temps.items():
        # Remove None values from the list
        cleaned_values = [value for value in temp_values if value is not None]

        # Calculate running mean
        averaged_values = running_mean(cleaned_values, window_size)

        # Adjust timestamps for the running mean
        averaged_timestamps = timestamps[-len(averaged_values):]

        # Plot the running mean
        plt.plot(averaged_timestamps, averaged_values, label=f"{sensor_channel} (mean)")

    # Format the plot
    plt.title("Live Temperature Plot with Running Mean")
    plt.xlabel("Timestamp")
    plt.ylabel("Temperature (°F)")

    # Adjust x-axis to show fewer, readable timestamps
    if len(timestamps) > 0:
        plt.xticks(
            ticks=np.linspace(0, len(timestamps) - 1, min(len(timestamps), 10)).astype(int),
            labels=[timestamps[int(i)] for i in np.linspace(0, len(timestamps) - 1, min(len(timestamps), 10))],
            rotation=45,
            ha="right",
        )

    plt.legend(loc="upper left")
    plt.tight_layout()  # Adjust layout to fit labels


# Set up the plot
plt.figure(figsize=(10, 6))
ani = FuncAnimation(plt.gcf(), update_plot, interval=5000, cache_frame_data=False)  # Update every 5 seconds

# Show the live plot
plt.show()
