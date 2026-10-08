import os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import oaconvolve

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio") + os.sep
TWO_PI = 2 * np.pi


def mtof(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69) / 12)


def pan_gains(p):
    a = (p + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def ramp_in(n):
    return np.sin(np.linspace(0, np.pi / 2, n, endpoint=False)) ** 2


def ramp_out(n):
    return np.cos(np.linspace(0, np.pi / 2, n)) ** 2


def edge_fade(x, fin_ms=2.0, fout_ms=6.0):
    """Click-free edges on last axis. Returns a copy."""
    x = np.array(x, dtype=float)
    n = x.shape[-1]
    a = min(int(fin_ms * SR / 1000), n)
    b = min(int(fout_ms * SR / 1000), n)
    if a > 1:
        x[..., :a] *= ramp_in(a)
    if b > 1:
        x[..., n - b:] *= ramp_out(b)
    return x


def place(bus, x, t0, pan=0.0, gain=1.0):
    """Add mono (n,) or stereo (2,n) x into bus (2,N) at time t0."""
    i0 = int(round(t0 * SR))
    N = bus.shape[1]
    if i0 >= N:
        return
    if x.ndim == 1:
        gl, gr = pan_gains(pan)
        x = np.stack([x * gl, x * gr])
    n = min(x.shape[1], N - i0)
    if n <= 0:
        return
    bus[:, i0:i0 + n] += gain * x[:, :n]


def curve(points, N, smooth=0.05):
    xs, ys = zip(*points)
    t = np.arange(N) / SR
    y = np.interp(t, xs, ys)
    k = int(smooth * SR)
    if k > 1:
        y = uniform_filter1d(y, k, mode="nearest")
    return y


def sos(kind, fc, order=2):
    return signal.butter(order, fc, btype=kind, fs=SR, output="sos")


def filt(x, kind, fc, order=2):
    return signal.sosfilt(sos(kind, fc, order), x, axis=-1)


def tv_biquad(x, fc, q=1.0, kind="bp", block=256):
    """Time-varying RBJ biquad. fc: array same length as x (Hz)."""
    y = np.empty_like(x)
    zi = np.zeros(2)
    for s in range(0, len(x), block):
        f = float(np.clip(fc[s], 20, 0.45 * SR))
        w0 = TWO_PI * f / SR
        al = np.sin(w0) / (2 * q)
        c = np.cos(w0)
        if kind == "bp":
            b = np.array([al, 0, -al])
        elif kind == "lp":
            b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2])
        else:
            b = np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2])
        a = np.array([1 + al, -2 * c, 1 - al])
        yb, zi = signal.lfilter(b / a[0], a / a[0], x[s:s + block], zi=zi)
        y[s:s + block] = yb
    return y


def make_ir(rt60, damp_hz, seed, predelay=0.015):
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.1 * SR)
    t = np.arange(n) / SR
    env = 10 ** (-3 * t / rt60)
    ir = rng.standard_normal(n) * env
    # progressive darkening: blend of dark and bright versions
    dark = filt(ir, "low", damp_hz * 0.35)
    bright = filt(ir, "low", damp_hz)
    mixk = np.clip(t / rt60, 0, 1)
    ir = bright * (1 - mixk) + dark * mixk
    ir = filt(ir, "high", 90)
    ir[:int(0.004 * SR)] *= ramp_in(int(0.004 * SR))
    ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
    ir /= np.sqrt(np.sum(ir ** 2))
    return ir


def reverb(bus, rt60=3.0, damp_hz=6000, seed=1, predelay=0.015):
    """bus (2,N) -> wet-only (2,N), decorrelated per channel."""
    N = bus.shape[1]
    out = np.zeros_like(bus, dtype=float)
    for ch in range(2):
        ir = make_ir(rt60, damp_hz, seed + 17 * ch, predelay)
        out[ch] = oaconvolve(bus[ch], ir)[:N]
    return out


def normalize(x, peak_db):
    p = np.max(np.abs(x))
    return x * (10 ** (peak_db / 20) / p) if p > 0 else x


def write_wav(name, x, peak_db=None):
    x = np.asarray(x, dtype=float)
    if peak_db is not None:
        x = normalize(x, peak_db)
    x = x - x.mean(axis=-1, keepdims=True) * 0  # (DC handled upstream)
    pcm = np.clip(np.round(x.T * 32767), -32768, 32767).astype(np.int16)
    wavfile.write(OUT + name, SR, pcm)
    print(f"{name}: {pcm.shape[0]/SR:.3f}s peak={20*np.log10(np.max(np.abs(pcm))/32768+1e-12):.2f}dBFS")


# ---------- shared synth voices ----------
def kick(dur=0.4, f0=95, f1=42, tau_f=0.035, tau_a=0.13, drive=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / tau_f)
    ph = TWO_PI * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / tau_a)
    s = np.tanh(drive * s) / np.tanh(drive)
    return edge_fade(s, 0.5, 15)


def boom(dur=4.0, tau=0.5, f_start=66, f_end=27, seed=3):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f_end + (f_start - f_end) * np.exp(-t / 0.4)
    ph = TWO_PI * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t / tau)
    f2 = 48 + 60 * np.exp(-t / 0.08)
    thud = np.sin(TWO_PI * np.cumsum(f2) / SR) * np.exp(-t / (tau * 0.45))
    crack = filt(rng.standard_normal(n), "low", 1800) * np.exp(-t / 0.07)
    rumble = filt(rng.standard_normal(n), "low", 110, 3) * np.exp(-t / (tau * 1.1))
    s = 1.0 * sub + 0.55 * thud + 0.35 * crack + 1.3 * rumble
    s = np.tanh(1.4 * s)
    s = edge_fade(s, 0.5, 40)
    return s


def tick_burst(fc=5500, dur=0.04, tau=0.006, seed=0, tone=None):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = signal.sosfilt(signal.butter(2, [fc * 0.75, min(fc * 1.35, 20000)], "bandpass", fs=SR, output="sos"), x)
    s = x * np.exp(-t / tau)
    if tone:
        s += 0.8 * np.sin(TWO_PI * tone * t) * np.exp(-t / (tau * 1.4))
    return edge_fade(s, 0.3, 5)
