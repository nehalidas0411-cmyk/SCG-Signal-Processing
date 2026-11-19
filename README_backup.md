# SCG Signal Processing: Heart Rate and Respiration Rate Estimation

## Overview

This project focuses on the design and implementation of digital filters for estimating heart rate (HR) and respiration rate (RR) from Seismocardiography (SCG) signals.

SCG is a non-invasive technique that captures small mechanical vibrations of the chest caused by cardiac activity and respiration. The project uses an MPU6050 accelerometer connected to an ESP32 to acquire these vibrations, followed by digital signal processing to separate the cardiac and respiratory components.

**Current status:** The pipeline has been tested using simulated data and a real ESP32–MPU6050 hardware recording. Hardware integration and offline analysis are complete; physiological accuracy validation remains pending.

## Objectives

- Explore and analyse SCG signals in the time and frequency domains.
- Design and compare different digital filters.
- Separate cardiac and respiratory components.
- Estimate heart rate in beats per minute (BPM).
- Estimate respiration rate in breaths per minute.
- Explore causal filtering for real-time processing.
- Prepare the pipeline for future ESP32-based data acquisition.

## Hardware (implemented)

- ESP32 DevKit V1
- MPU6050 (GY-521) accelerometer module

## Technologies Used

- Python 3.9
- NumPy and Pandas
- SciPy
- Matplotlib and Seaborn
- Scikit-learn
- PyWavelets
- Jupyter Notebook

## Project Structure

```text
SCG-Signal-Processing/
│
├── data/
│   ├── raw/
│   │   └── sample_scg.csv
│   └── processed/
│
├── notebooks/
│   ├── 01_explore.ipynb
│   ├── 02_filters.ipynb
│   └── 03_rates.ipynb
│
├── src/
│   └── scg_pipeline.py
│
├── figures/
├── requirements.txt
├── .gitignore
└── README.md
```

## Methodology

### 1. Signal Acquisition and Exploration
- Load accelerometer data from CSV.
- Convert raw accelerometer readings into acceleration in g.
- Estimate sampling frequency from timestamps.
- Examine the signal using time-domain plots, FFT, Power Spectral Density (PSD), and spectrograms.

### 2. Digital Filter Design
- Design and compare Butterworth, Chebyshev Type I, Chebyshev Type II, and Elliptic IIR filters.
- Explore FIR filtering using the Kaiser window and Parks–McClellan method.
- Apply filtering for cardiac and respiratory frequency components.
- Compare causal and zero-phase filtering.
- Explore decimation from 250 Hz to 25 Hz for respiration processing.

### 3. Heart Rate Estimation
- Apply a 0.8–20 Hz Butterworth bandpass filter.
- Extract the signal envelope using the Hilbert transform.
- Detect heartbeat peaks.
- Estimate heart rate from the intervals between detected peaks.

### 4. Respiration Rate Estimation
- Downsample the signal to 25 Hz.
- Apply a 0.1–0.5 Hz Butterworth bandpass filter.
- Detect respiratory peaks.
- Estimate respiration rate from breathing-cycle intervals.

### 5. Signal Quality Assessment
The pipeline evaluates recording duration, sampling frequency, sampling jitter, signal statistics, and the presence of finite values. These checks are preliminary engineering checks, not a clinically validated signal-quality assessment.

### 6. Real-Time Processing Exploration
Causal filtering and block-based processing have been explored using simulated data. Further validation is required before considering the implementation ready for live hardware use.

## Preliminary Results

The pipeline was tested using a 30-second simulated recording sampled at 250 Hz.

| Parameter | Preliminary result |
|---|---:|
| Sampling frequency | 250 Hz |
| Recording duration | Approximately 30 seconds |
| Estimated heart rate | 73.71 BPM |
| Estimated respiration rate | 15 breaths/min |

These are results from simulated data, not measurements from a person or validated hardware recordings. They should not be interpreted as clinical performance results.

## Installation

Clone the repository:

```bash
git clone https://github.com/Tanishkaaa016/SCG-Signal-Processing.git
cd SCG-Signal-Processing
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Running the Project

Open the project folder in VS Code and run the notebooks in order:

1. `01_explore.ipynb` – Signal exploration and preprocessing.
2. `02_filters.ipynb` – Digital filter design and comparison.
3. `03_rates.ipynb` – Heart rate and respiration rate estimation.

The main processing functions are available in `src/scg_pipeline.py`.

## Future Work

- Complete ESP32 and MPU6050 hardware integration.
- Record and analyse real SCG signals.
- Validate sampling frequency and signal quality using hardware recordings.
- Evaluate HR and RR estimates against suitable reference measurements.
- Improve real-time processing and peak detection.
- Test the pipeline across multiple recordings.## Instructions for Hardware Integration and Processing

This section outlines the steps to follow once the ESP32 and MPU6050 hardware setup is completed.

The original hardware-integration instructions at the bottom can remain as a guide, but they're now historical instructions rather than outstanding work.

### Step 1: Record SCG Data

Use the ESP32 connected to the MPU6050 accelerometer to collect chest vibration data.

Export the readings as a CSV file containing the following columns:

| Column | Description |
|---|---|
| `sample_index` | Sequential sample number |
| `timestamp_ms` | Timestamp in milliseconds |
| `ax_raw` | Raw X-axis acceleration |
| `ay_raw` | Raw Y-axis acceleration |
| `az_raw` | Raw Z-axis acceleration |

Ensure that timestamps are recorded consistently and that the actual sampling frequency is measured.

### Step 2: Add the Hardware CSV

1. Download or export the recorded CSV file.
2. Place it inside `data/raw/`.
3. Give it a descriptive name, for example:

   `hardware_scg_01.csv`

4. Do not overwrite or delete `sample_scg.csv`, as it is the original simulated dataset.

The directory should look like:

```text
data/
├── raw/
│   ├── sample_scg.csv
│   └── hardware_scg_01.csv
└── processed/
```

### Step 3: Verify the Recording

Before processing, check:

- All required columns are present.
- There are no missing or invalid readings.
- Timestamps are increasing and consistent.
- Actual sampling frequency is calculated from timestamps.
- Recording duration is sufficient for analysis.
- The signal is not flat, clipped, or excessively noisy.

Use the existing signal-quality assessment functions in `src/scg_pipeline.py` as an initial engineering check.

### Step 4: Process the Hardware Recording

Open `notebooks/03_rates.ipynb`.

Update the input file path to the new hardware recording:

```python
file_path = "data/raw/hardware_scg_01.csv"
```

Run the processing pipeline:

```python
import scg_pipeline

results = scg_pipeline.process_scg_recording(file_path)
```

The pipeline performs:

- Signal loading and preprocessing.
- Heartbeat filtering.
- Respiration filtering.
- Heart rate estimation.
- Respiration rate estimation.
- Preliminary signal-quality assessment.

**Important:** The existing pipeline assumes a sampling frequency close to 250 Hz for respiration processing. If the actual hardware sampling frequency differs, update the resampling and filter-design functions before processing.

### Step 5: Analyse and Validate Results

Inspect the filtered cardiac and respiratory signals and verify that detected peaks correspond to meaningful signal patterns.

Compare the estimated values against independent reference measurements:

- Heart rate: pulse oximeter or another suitable reference.
- Respiration rate: an independent respiratory measurement.

Record the estimated values, reference values, and errors. Do not consider the estimates clinically validated without appropriate testing.

### Step 6: Save the Results

Save the following in the appropriate folders:

- Original hardware recording → `data/raw/`
- Processed signals and result CSVs → `data/processed/`
- Analysis plots → `figures/`

Use recording-specific filenames to avoid overwriting results
