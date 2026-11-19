import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, welch
from pathlib import Path

FS = 250
df = pd.read_csv("data/raw/hardware_scg_01.csv")
t = (df.timestamp_ms.to_numpy() - df.timestamp_ms.iloc[0]) / 1000

# Convert MPU6050 raw counts to g
axes = {
    name: df[col].to_numpy(dtype=float) / 16384
    for name, col in [
        ("X", "ax_raw"),
        ("Y", "ay_raw"),
        ("Z", "az_raw")
    ]
}

def bandpass(signal, low, high):
    sos = butter(4, [low, high], btype="bandpass",
                 fs=FS, output="sos")
    return sosfiltfilt(sos, signal)

Path("figures").mkdir(exist_ok=True)

fig, axs = plt.subplots(3, 2, figsize=(14, 10))

for i, (name, signal) in enumerate(axes.items()):
    cardiac = bandpass(signal, 0.8, 20)
    respiratory = bandpass(signal, 0.1, 0.5)

    # Zoom into a section away from the major movement spike
    mask = (t >= 55) & (t <= 65)

    axs[i, 0].plot(t[mask], cardiac[mask], linewidth=0.8)
    axs[i, 0].set_title(f"{name}-axis: Cardiac band (0.8-20 Hz)")
    axs[i, 0].set_xlabel("Time (s)")
    axs[i, 0].set_ylabel("Acceleration (g)")
    axs[i, 0].grid(alpha=0.3)

    axs[i, 1].plot(t, respiratory, linewidth=0.8)
    axs[i, 1].set_title(f"{name}-axis: Respiratory band (0.1-0.5 Hz)")
    axs[i, 1].set_xlabel("Time (s)")
    axs[i, 1].set_ylabel("Acceleration (g)")
    axs[i, 1].grid(alpha=0.3)

fig.suptitle("Real MPU6050 SCG: Cardiac and Respiratory Filtering")
fig.tight_layout()
fig.savefig("figures/hardware_filtered_signals.png", dpi=150)
plt.show()
