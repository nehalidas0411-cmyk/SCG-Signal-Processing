import numpy as np
import pandas as pd

from scipy import signal
from scipy.signal import find_peaks


def load_scg_data(file_path):

    # Load CSV
    df = pd.read_csv(file_path)

    # Check required columns
    required_columns = [
        "timestamp_ms",
        "ax_raw",
        "ay_raw",
        "az_raw"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing required column: {column}")

    # Generate time array
    time = (
        df["timestamp_ms"].to_numpy()
        - df["timestamp_ms"].iloc[0]
    ) / 1000

    # Estimate actual sampling frequency
    time_differences = np.diff(time)

    if np.any(time_differences <= 0):
        raise ValueError("Timestamps must be strictly increasing.")

    fs = 1 / np.median(time_differences)

    # Convert raw acceleration counts to g
    ax = df["ax_raw"].to_numpy() / 16384
    ay = df["ay_raw"].to_numpy() / 16384
    az = df["az_raw"].to_numpy() / 16384

    # Remove mean offset
    ax = signal.detrend(ax, type="constant")
    ay = signal.detrend(ay, type="constant")
    az = signal.detrend(az, type="constant")

    return time, fs, ax, ay, az

def extract_heartbeat(az, fs):

    if fs <= 40:
        raise ValueError(
            "Sampling frequency must be greater than 40 Hz "
            "for the selected heartbeat filter."
        )

    # Design Butterworth bandpass filter
    heart_sos = signal.butter(
        N=4,
        Wn=[0.8, 20],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    # Apply zero-phase filtering
    heart_signal = signal.sosfiltfilt(
        heart_sos,
        az
    )

    return heart_signal


def extract_respiration(az, fs):

    if not np.isclose(fs, 250, atol=2):
        raise ValueError(
            "This respiration pipeline currently expects "
            "a sampling frequency close to 250 Hz."
        )

    # Downsample to 25 Hz
    resp_signal = signal.resample_poly(
        az,
        up=1,
        down=10
    )

    fs_resp = fs / 10

    # Design Butterworth respiration bandpass filter
    resp_sos = signal.butter(
        N=4,
        Wn=[0.1, 0.5],
        btype="bandpass",
        fs=fs_resp,
        output="sos"
    )

    # Apply zero-phase filtering
    resp_filtered = signal.sosfiltfilt(
        resp_sos,
        resp_signal
    )

    return resp_filtered, fs_resp



def estimate_heart_rate(heart_signal, fs):

    # Calculate amplitude envelope
    analytic_signal = signal.hilbert(heart_signal)
    envelope = np.abs(analytic_signal)

    # Smooth envelope
    window_size = int(0.15 * fs)

    smoothed_envelope = np.convolve(
        envelope,
        np.ones(window_size) / window_size,
        mode="same"
    )

    # Detect heartbeat events
    min_distance = int(0.35 * fs)

    prominence = 0.2 * np.std(smoothed_envelope)

    heart_peaks, properties = find_peaks(
        smoothed_envelope,
        distance=min_distance,
        prominence=prominence
    )

    # Calculate intervals
    beat_times = heart_peaks / fs
    intervals = np.diff(beat_times)

    if len(intervals) == 0:
        return np.nan, heart_peaks, smoothed_envelope

    # Calculate heart rate
    heart_rates = 60 / intervals
    estimated_hr = np.median(heart_rates)

    return estimated_hr, heart_peaks, smoothed_envelope



def estimate_respiration_rate(resp_signal, fs_resp):

    # Detect respiratory peaks
    min_distance = int(fs_resp * 60 / 30)

    prominence = 0.2 * np.std(resp_signal)

    resp_peaks, properties = find_peaks(
        resp_signal,
        distance=min_distance,
        prominence=prominence
    )

    # Convert peak indices into time
    resp_peak_times = resp_peaks / fs_resp

    # Calculate intervals between breathing cycles
    resp_intervals = np.diff(resp_peak_times)

    if len(resp_intervals) == 0:
        return np.nan, resp_peaks

    # Calculate respiration rate
    resp_rates = 60 / resp_intervals

    estimated_rr = np.median(resp_rates)

    return estimated_rr, resp_peaks

def process_scg_recording(file_path):

    # Step 1: Load data
    time, fs, ax, ay, az = load_scg_data(file_path)

    # Step 2: Assess signal quality
    quality = assess_signal_quality(time, az, fs)

    print("\nSIGNAL QUALITY REPORT")
    print("---------------------")

    for parameter, value in quality.items():
        print(f"{parameter}: {value}")

    # Step 3: Extract heartbeat component
    heart_signal = extract_heartbeat(az, fs)

    # Step 4: Estimate heart rate
    estimated_hr, heart_peaks, heart_envelope = estimate_heart_rate(
        heart_signal, fs
    )

    # Step 5: Extract respiration component
    resp_signal, fs_resp = extract_respiration(az, fs)

    # Step 6: Estimate respiration rate
    estimated_rr, resp_peaks = estimate_respiration_rate(
        resp_signal, fs_resp
    )

    # Step 7: Display results
    print("\nSCG PROCESSING RESULTS")
    print("----------------------")
    print("Heart Rate:", round(estimated_hr, 2), "BPM")
    print("Respiration Rate:", round(estimated_rr, 2), "breaths/min")

    return {
        "heart_rate": estimated_hr,
        "respiration_rate": estimated_rr,
        "heart_signal": heart_signal,
        "heart_envelope": heart_envelope,
        "resp_signal": resp_signal,
        "heart_peaks": heart_peaks,
        "resp_peaks": resp_peaks,
        "time": time,
        "quality": quality
    }

def create_recording_report(results):

    quality = results["quality"]

    report = pd.DataFrame([{
        "duration_s": float(quality["duration_s"]),
        "sampling_frequency_hz": float(
            quality["sampling_frequency_hz"]
        ),
        "sampling_jitter_percent": float(
            quality["sampling_jitter_percent"]
        ),
        "signal_std": float(quality["signal_std"]),
        "signal_rms": float(quality["signal_rms"]),
        "peak_to_peak": float(quality["peak_to_peak"]),
        "quality_status": quality["quality_status"],
        "heart_rate_bpm": float(results["heart_rate"]),
        "respiration_rate_bpm": float(
            results["respiration_rate"]
        )
    }])

    return report


def save_scg_results(results, output_folder, recording_name):

    from pathlib import Path

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Save HR and RR summary
    summary = pd.DataFrame({
        "recording": [recording_name],
        "heart_rate_bpm": [results["heart_rate"]],
        "respiration_rate_bpm": [results["respiration_rate"]]
    })

    summary.to_csv(
        output_folder / f"{recording_name}_summary.csv",
        index=False
    )

    # Save filtered heartbeat signal
    heart_df = pd.DataFrame({
        "time_s": results["time"],
        "heart_signal": results["heart_signal"],
        "heart_envelope": results["heart_envelope"]
    })

    heart_df.to_csv(
        output_folder / f"{recording_name}_heart.csv",
        index=False
    )

    # Save filtered respiration signal
    fs_resp = 25
    resp_time = np.arange(len(results["resp_signal"])) / fs_resp

    resp_df = pd.DataFrame({
        "time_s": resp_time,
        "resp_signal": results["resp_signal"]
    })

    resp_df.to_csv(
        output_folder / f"{recording_name}_respiration.csv",
        index=False
    )

    print("Results saved successfully!")
    print("Output folder:", output_folder)

def assess_signal_quality(time, az, fs):

    # Check for missing or invalid values
    finite_check = (
        np.all(np.isfinite(time)) and
        np.all(np.isfinite(az))
    )

    # Calculate recording duration
    duration = time[-1] - time[0]

    # Calculate timestamp intervals
    time_differences = np.diff(time)

    # Calculate sampling interval statistics
    median_interval = np.median(time_differences)

    sampling_jitter = (
        np.std(time_differences) / median_interval
    ) * 100

    # Calculate signal statistics
    signal_mean = np.mean(az)
    signal_std = np.std(az)
    signal_rms = np.sqrt(np.mean(az ** 2))

    peak_to_peak = np.ptp(az)

    # Check for nearly constant signal
    flat_signal = signal_std < 1e-6

    # Check sampling consistency
    irregular_sampling = sampling_jitter > 5

    # Generate quality status
    if not finite_check:
        quality_status = "INVALID"

    elif duration < 29.5:
        quality_status = "SHORT RECORDING"

    elif flat_signal:
        quality_status = "POOR"

    elif irregular_sampling:
        quality_status = "CHECK SAMPLING"

    else:
        quality_status = "REQUIRES FURTHER VALIDATION"

    return {
        "duration_s": duration,
        "sampling_frequency_hz": fs,
        "sampling_jitter_percent": sampling_jitter,
        "signal_mean": signal_mean,
        "signal_std": signal_std,
        "signal_rms": signal_rms,
        "peak_to_peak": peak_to_peak,
        "finite_values": finite_check,
        "quality_status": quality_status
    }

def design_realtime_filters(fs):

    if fs <= 40:
        raise ValueError(
            "Sampling frequency must be greater than 40 Hz."
        )

    # Heartbeat bandpass filter
    heart_sos = signal.butter(
        N=4,
        Wn=[0.8, 20],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    # Respiration bandpass filter
    resp_sos = signal.butter(
        N=4,
        Wn=[0.1, 0.5],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    # Initialize filter states
    heart_zi = np.zeros((heart_sos.shape[0], 2))
    resp_zi = np.zeros((resp_sos.shape[0], 2))

    return heart_sos, resp_sos, heart_zi, resp_zi

def process_stream_block(
    az_block,
    heart_sos,
    resp_sos,
    heart_zi,
    resp_zi
):

    # Apply causal heartbeat filtering
    heart_output, heart_zi = signal.sosfilt(
        heart_sos,
        az_block,
        zi=heart_zi
    )

    # Apply causal respiration filtering
    resp_output, resp_zi = signal.sosfilt(
        resp_sos,
        az_block,
        zi=resp_zi
    )

    return (
        heart_output,
        resp_output,
        heart_zi,
        resp_zi
    )

def design_realtime_respiration_filters(fs):

    if not np.isclose(fs, 250, atol=2):
        raise ValueError(
            "This implementation expects approximately 250 Hz."
        )

    # Anti-aliasing FIR lowpass filter
    decimation_taps = signal.firwin(
        numtaps=101,
        cutoff=5,
        fs=fs
    )

    # Initialize FIR filter state
    decimation_zi = np.zeros(len(decimation_taps) - 1)

    # Respiration filter at 25 Hz
    fs_resp = fs / 10

    resp_sos = signal.butter(
        N=4,
        Wn=[0.1, 0.5],
        btype="bandpass",
        fs=fs_resp,
        output="sos"
    )

    # Initialize respiration IIR state
    resp_zi = np.zeros((resp_sos.shape[0], 2))

    return (
        decimation_taps,
        decimation_zi,
        resp_sos,
        resp_zi,
        fs_resp
    )
def process_realtime_respiration_block(
    az_block,
    decimation_taps,
    decimation_zi,
    resp_sos,
    resp_zi
):
    # Anti-aliasing FIR filter
    filtered_block, decimation_zi = signal.lfilter(
        decimation_taps,
        [1.0],
        az_block,
        zi=decimation_zi
    )

    # Downsample by 10
    decimated_block = filtered_block[::10]

    # Respiration IIR filter
    resp_output, resp_zi = signal.sosfilt(
        resp_sos,
        decimated_block,
        zi=resp_zi
    )

    return resp_output, decimation_zi, resp_zi