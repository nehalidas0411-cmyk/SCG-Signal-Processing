import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, welch
from pathlib import Path

FS = 250
df = pd.read_csv("data/raw/hardware_scg_01.csv")

t = (df.timestamp_ms.to_numpy() - df.timestamp_ms.iloc[0]) / 1000
z = df.az_raw.to_numpy(dtype=float) / 16384.0

# Select a relatively quiet segment
mask = (t >= 105) & (t <= 130)
segment = z[mask]

def bandpass(x, low, high):
    sos = butter(4, [low, high], btype="bandpass",
                 fs=FS, output="sos")
    return sosfiltfilt(sos, x)

cardiac = bandpass(segment, 0.8, 20)
respiratory = bandpass(segment, 0.1, 0.5)

fig, axs = plt.subplots(2, 2, figsize=(13, 8))

for row, (signal, name, low, high) in enumerate([
    (cardiac, "Cardiac", 0.8, 3.0),
    (respiratory, "Respiratory", 0.1, 0.5)
]):
    # Time-domain signal
    axs[row, 0].plot(np.arange(len(signal)) / FS, signal)
    axs[row, 0].set_title(f"{name} filtered waveform")
    axs[row, 0].set_xlabel("Time within segment (s)")
    axs[row, 0].set_ylabel("Acceleration (g)")
    axs[row, 0].grid(alpha=0.3)

    # Welch power spectral density
    nperseg = min(len(signal), 4096)
    f, psd = welch(signal, fs=FS, nperseg=nperseg)

    valid = (f >= low) & (f <= high)
    axs[row, 1].plot(f[valid], psd[valid])
    axs[row, 1].set_title(f"{name} power spectral density")
    axs[row, 1].set_xlabel("Frequency (Hz)")
    axs[row, 1].set_ylabel("PSD (g²/Hz)")
    axs[row, 1].grid(alpha=0.3)

    if np.any(valid):
        peak = f[valid][np.argmax(psd[valid])]
        print(f"{name} spectral peak: {peak:.3f} Hz")
        print(f"Equivalent periodic rate: {peak * 60:.1f} cycles/min")

Path("figures").mkdir(exist_ok=True)
fig.tight_layout()
fig.savefig("figures/hardware_psd_analysis.png", dpi=150)
plt.show()
