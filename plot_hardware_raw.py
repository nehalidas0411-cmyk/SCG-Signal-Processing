import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv("data/raw/hardware_scg_01.csv")

t = (df["timestamp_ms"].to_numpy() - df["timestamp_ms"].iloc[0]) / 1000

fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

for ax, col, name in zip(
    axes,
    ["ax_raw", "ay_raw", "az_raw"],
    ["X-axis", "Y-axis", "Z-axis"]
):
    acceleration = df[col].to_numpy() / 16384.0
    ax.plot(t, acceleration, linewidth=0.5)
    ax.set_ylabel("Acceleration (g)")
    ax.set_title(name)
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Time (seconds)")
fig.suptitle("Real MPU6050 Chest Acceleration — Raw Signals")
fig.tight_layout()

Path("figures").mkdir(exist_ok=True)
fig.savefig("figures/hardware_raw_axes.png", dpi=150)
plt.show()
