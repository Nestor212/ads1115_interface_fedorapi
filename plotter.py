import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import filedialog
import sys  # Needed for proper exit handling

# Initialize data storage
timestamps = []
temps = {f"TEMP{sensor}{channel}": [] for sensor in range(2) for channel in range(4)}  # TEMP00-TEMP03, TEMP10-TEMP13

# User-configurable running mean window size
window_size = 8  # Number of values to average
paused = False  # Global flag for pause state

# Function to calculate the running mean
def running_mean(data, window):
    if len(data) < window:
        return [np.mean(data[:i+1]) for i in range(len(data))]
    return [np.mean(data[end-window:end]) for end in range(window, len(data)+1)]

# Function to select a file using a file dialog
def select_file():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    root.attributes('-topmost', True)  # Bring the file dialog to the front
    file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")], initialdir="Logs/")
    return file_path

# Select the file
filename = select_file()
if not filename:
    print("No file selected. Exiting.")
    sys.exit()

# Function to toggle the pause state
def toggle_pause():
    global paused
    paused = not paused
    pause_button.config(text="Continue" if paused else "Pause")

# Function to update the plot
def update_plot(frame):
    global timestamps, temps, paused
    if paused:
        return  # Skip updating the plot when paused

    # Read the latest data from the CSV file
    with open(filename, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Timestamp"] in timestamps:
                continue
            if any(row[key] is None or row[key] == "" for key in temps.keys()):
                continue  # Skip rows with invalid data

            timestamps.append(row["Timestamp"])
            for key in temps.keys():
                value = row.get(key)
                temps[key].append(float(value) if value else None)

    # Clear the plot
    ax.clear()

    # Plot only the running mean data
    for sensor_channel, temp_values in temps.items():
        cleaned_values = [value for value in temp_values if value is not None]
        averaged_values = running_mean(cleaned_values, window_size)
        averaged_timestamps = timestamps[-len(averaged_values):]

        ax.plot(averaged_timestamps, averaged_values, label=f"{sensor_channel} (mean)")

    ax.set_title("Live Temperature Plot with Running Mean")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Temperature (°F)")

    if len(timestamps) > 0:
        ax.set_xticks(
            np.linspace(0, len(timestamps) - 1, min(len(timestamps), 10)).astype(int)
        )
        ax.set_xticklabels(
            [timestamps[int(i)] for i in np.linspace(0, len(timestamps) - 1, min(len(timestamps), 10))],
            rotation=45,
            ha="right"
        )

    ax.legend(loc="upper left")
    fig.tight_layout()
    canvas.draw()  # Ensure updates are reflected on the GUI

# Properly handle closing the window
def on_closing():
    print("Closing plot...")
    ani.event_source.stop()  # Stop the animation loop
    root.quit()  # Stop Tkinter mainloop
    root.destroy()  # Destroy the window
    sys.exit()  # Ensure full exit from the terminal

# Set up the Tkinter GUI
root = tk.Tk()
root.title("Smoker Plot")

# Create Matplotlib figure and embed in Tkinter
fig, ax = plt.subplots(figsize=(10, 6))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Add Matplotlib toolbar for zoom/pan functionality
toolbar = NavigationToolbar2Tk(canvas, root)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)

# Create pause button
pause_button = tk.Button(root, text="Pause", command=toggle_pause, font=("Arial", 12))
pause_button.pack()

# Create Matplotlib animation
ani = FuncAnimation(fig, update_plot, interval=1500, cache_frame_data=False)

# Set the close event to properly exit
root.protocol("WM_DELETE_WINDOW", on_closing)

# Run the Tkinter event loop
root.mainloop()
