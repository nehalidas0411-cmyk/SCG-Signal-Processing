"""BSP demo: compare digital filters on the latest ESP32 SCG recording.
Run from SCG-Signal-Processing with: .\.venv\Scripts\python.exe live_bsp_demo.py
Optional: --file path/to/recording.csv
"""
from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal

ROOT = Path(__file__).resolve().parent
DEFAULT_RECORDINGS = ROOT.parent / 'SCG-Microcontroller-Monitor' / 'recordings'
REQUIRED = {'timestamp_ms', 'ax_raw', 'ay_raw', 'az_raw'}

def newest_valid_csv(folder):
    if not folder.is_dir():
        raise FileNotFoundError(f'Recordings folder not found: {folder}')
    for p in sorted(folder.glob('*.csv'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            if REQUIRED.issubset(pd.read_csv(p, nrows=1).columns):
                return p
        except (OSError, ValueError, pd.errors.ParserError):
            pass
    raise FileNotFoundError(f'No recording CSV with required columns found in {folder}')

def filter_set(fs, low, high):
    # Same cutoff frequencies; response shapes differ by filter family.
    designs = {
        'Butterworth IIR': ('sos', signal.butter(4, [low, high], btype='bandpass', fs=fs, output='sos')),
        'Chebyshev I IIR': ('sos', signal.cheby1(4, 0.5, [low, high], btype='bandpass', fs=fs, output='sos')),
        'Elliptic IIR': ('sos', signal.ellip(4, 0.5, 40, [low, high], btype='bandpass', fs=fs, output='sos')),
    }
    # FIR length selected to be manageable for the low-frequency respiratory band.
    width = low * 0.5
    taps = int(np.ceil(3.3 * fs / max(width, 0.01)))
    taps = max(101, min(taps | 1, 3001))
    if taps % 2 == 0:
        taps += 1
    designs['FIR (Hamming)'] = ('fir', signal.firwin(taps, [low, high], pass_zero=False, fs=fs, window='hamming'))
    return designs

def apply_filters(x, fs, low, high):
    designs = filter_set(fs, low, high)
    outputs = {}
    for name, (kind, coeff) in designs.items():
        try:
            if kind == 'sos':
                outputs[name] = signal.sosfiltfilt(coeff, x)
            else:
                # FFT convolution, centered approximation to zero-phase FIR filtering;
                # edge samples are not used for physiological interpretation.
                outputs[name] = signal.fftconvolve(x, coeff, mode='same')
        except ValueError as exc:
            print(f'Warning: {name} unavailable: {exc}')
    return designs, outputs

def estimate_rates(heart, resp, fs, fs_resp):
    envelope = np.abs(signal.hilbert(heart))
    w = max(1, int(round(0.15 * fs)))
    smooth = np.convolve(envelope, np.ones(w)/w, mode='same')
    hp, _ = signal.find_peaks(smooth, distance=max(1,int(0.6*fs)), prominence=0.2*np.std(smooth))
    rp, _ = signal.find_peaks(resp, distance=max(1,int(2*fs_resp)), prominence=0.2*np.std(resp))
    hr = np.median(60/(np.diff(hp)/fs)) if len(hp)>1 else np.nan
    rr = np.median(60/(np.diff(rp)/fs_resp)) if len(rp)>1 else np.nan
    return hr, rr, hp, rp

def main():
    ap = argparse.ArgumentParser(description='SCG BSP live-recording filter comparison')
    ap.add_argument('--file', type=Path, help='CSV recording (default: newest in Microcontrollers recordings folder)')
    ap.add_argument('--recordings', type=Path, default=DEFAULT_RECORDINGS)
    args = ap.parse_args()
    file = args.file if args.file else newest_valid_csv(args.recordings)
    df = pd.read_csv(file)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f'CSV missing columns: {sorted(missing)}')
    df = df.dropna(subset=list(REQUIRED))
    if len(df) < 2500:
        raise ValueError('Need at least ~10 seconds of data; record 90–120 seconds for the demo.')
    t = (df.timestamp_ms.to_numpy(dtype=float) - float(df.timestamp_ms.iloc[0]))/1000
    dt = np.diff(t)
    if not np.all(dt>0):
        raise ValueError('Timestamps must be strictly increasing.')
    fs = 1/np.median(dt)
    if not 248 <= fs <= 252:
        raise ValueError(f'Estimated sample rate {fs:.2f} Hz is not close to 250 Hz; check recording.')
    az = signal.detrend(df.az_raw.to_numpy(dtype=float)/16384, type='constant')
    # Use actual estimated fs for cardiac; respiratory resampling matches BSP pipeline.
    cardiac_designs, cardiac = apply_filters(az, fs, 0.8, 20)
    resp_in = signal.resample_poly(az, 1, 10)
    fs_resp = fs/10
    resp_designs, resp = apply_filters(resp_in, fs_resp, 0.1, 0.5)
    if not cardiac or not resp:
        raise RuntimeError('Filters failed; check recording length and sampling rate.')
    rt = np.arange(len(resp_in))/fs_resp
    output = ROOT/'outputs'/'live_filter_comparison'
    output.mkdir(parents=True, exist_ok=True)
    print(f'\nRecording: {file}\nSamples: {len(az):,} | Duration: {t[-1]:.1f}s | fs: {fs:.2f} Hz')
    print('Filter comparison is OFFLINE: all filters process the same newly recorded CSV.')
    print('FIR is centered convolution; IIR is forward-backward zero-phase filtering.')
    print('\nCandidate estimates (not clinically validated):')
    results=[]
    for name in cardiac:
        if name not in resp: continue
        hr, rr, _, _ = estimate_rates(cardiac[name],resp[name],fs,fs_resp)
        results.append({'filter':name,'heart_rate_bpm':hr,'resp_rate_per_min':rr})
        print(f'  {name:19s} HR={hr:6.1f} BPM | RR={rr:5.1f} breaths/min')
    pd.DataFrame(results).to_csv(output/'estimated_rates.csv',index=False)

    fig, ax = plt.subplots(3,1,figsize=(12,9),sharex=False)
    show = t<=min(15,t[-1])
    ax[0].plot(t[show],az[show],lw=.7,color='black'); ax[0].set_title('Raw Z-axis chest acceleration (first 15 s)')
    for name,y in cardiac.items(): ax[1].plot(t[show],y[show],lw=.8,label=name,alpha=.8)
    ax[1].set_title('Cardiac 0.8–20 Hz: filter-family comparison')
    showr=rt<=min(60,rt[-1])
    for name,y in resp.items(): ax[2].plot(rt[showr],y[showr],lw=1,label=name,alpha=.8)
    ax[2].set_title('Respiration 0.1–0.5 Hz: filter-family comparison (first 60 s)')
    for a in ax: a.set_xlabel('Time (s)');a.set_ylabel('Acceleration (g)');a.grid(alpha=.25)
    ax[1].legend(fontsize=8,ncol=2);ax[2].legend(fontsize=8,ncol=2)
    fig.tight_layout();fig.savefig(output/'01_raw_and_filtered.png',dpi=160)

    fig2, ax2=plt.subplots(2,1,figsize=(11,8))
    for axis,designs,srate,xlim,title in [(ax2[0],cardiac_designs,fs,(0,30),'Cardiac magnitude response'),(ax2[1],resp_designs,fs_resp,(0,2),'Respiratory magnitude response')]:
        for name,(kind,coeff) in designs.items():
            if kind=='sos': f,h=signal.sosfreqz(coeff,worN=8192,fs=srate)
            else: f,h=signal.freqz(coeff,worN=8192,fs=srate)
            axis.plot(f,20*np.log10(np.maximum(abs(h),1e-8)),label=name)
        axis.set(xlim=xlim,ylim=(-85,5),title=title,xlabel='Frequency (Hz)',ylabel='Magnitude (dB)')
        axis.grid(alpha=.3);axis.legend(fontsize=8)
    fig2.tight_layout();fig2.savefig(output/'02_frequency_response.png',dpi=160)

    fig3,ax3=plt.subplots(figsize=(11,5))
    for name,y in cardiac.items():
        f,p=signal.welch(y,fs=fs,nperseg=min(4096,len(y)))
        ax3.semilogy(f,p,label=name)
    ax3.set(xlim=(0,30),title='Welch PSD of cardiac-filter outputs',xlabel='Frequency (Hz)',ylabel='PSD (g²/Hz)')
    ax3.grid(alpha=.3);ax3.legend(fontsize=8)
    fig3.tight_layout();fig3.savefig(output/'03_cardiac_psd.png',dpi=160)
    print(f'\nSaved comparison graphs and rate table to: {output}')
    plt.show()

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)