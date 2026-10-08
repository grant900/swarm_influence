import numpy as np
from dsp import *

DUR = 176.0
N = int(DUR * SR)
rng = np.random.default_rng(11)


def zbus():
    return np.zeros((2, N), dtype=np.float64)


# ---------------- brightness (pad filter movement) ----------------
def g_fn(t):
    pts = [(0, .52), (35, .56), (47, .74), (51.5, .74), (52.5, .45), (53, .6), (80, .64), (92, .74),
           (95, .72), (127, .72), (128, .5), (130, .5), (131, .72), (152, .72), (153, .5), (176, .45)]
    xs, ys = zip(*pts)
    g = np.interp(t, xs, ys) + 0.07 * np.sin(TWO_PI * t / 17.0) + 0.03 * np.sin(TWO_PI * t / 6.3)
    return np.clip(g, 0.3, 0.88)


# ---------------- voices ----------------
def pad_note(f, t0, dur, atk, rel, gain):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ta = t0 + t
    g = g_fn(ta)
    env = np.ones(n)
    na, nr = int(atk * SR), int(rel * SR)
    env[:na] = ramp_in(na)
    env[n - nr:] *= ramp_out(nr)
    K = max(2, int(min(12, 2800 // f)))
    out = np.zeros((2, n))
    cents = (-9, 0, 8)
    pans = (-0.8, 0.0, 0.8)
    for vi, (c, p) in enumerate(zip(cents, pans)):
        ph = TWO_PI * f * 2 ** (c / 1200) * t + vi * 1.7
        s = np.zeros(n)
        gk = np.ones(n)
        for k in range(1, K + 1):
            s += k ** -1.2 * gk * np.sin(k * ph)
            gk = gk * g
        lfo = 0.85 + 0.15 * np.sin(TWO_PI * (0.05 + 0.03 * vi) * ta + vi * 2.1)
        s *= lfo * env
        gl, gr = pan_gains(p)
        out[0] += s * gl
        out[1] += s * gr
    return out * gain / len(cents)


CH = {  # root midi (low), intervals (third, fifth)
    "Am": (33, 3, 7), "F": (29, 4, 7), "Dm": (38, 3, 7), "E": (40, 4, 7), "C": (36, 4, 7), "G": (43, 4, 7)}


def pad_voicing(ch, wide=False):
    r, th, fi = CH[ch]
    v = [(r, 1.0), (r + 12, 0.8), (r + 12 + fi, 0.6), (r + 12 + th, 0.5)]
    if wide:
        v += [(r + 24 + th, 0.28), (r + 24 + fi, 0.22)]
    return v


def pad_chord(bus, ch, t_start, t_end, ov, gain=1.0, wide=False, voicing=None):
    t0 = max(0.0, t_start - ov / 2)
    dur = (t_end + ov / 2) - t0
    atk = ov if t_start > 0 else 2.5
    for m, w in (voicing or pad_voicing(ch, wide)):
        place(bus, pad_note(mtof(m), t0, dur, atk, ov, gain * w), t0)


def pluck(f, bright=0.7, tau=0.22, detune=1.004):
    n = int(tau * 6 * SR)
    t = np.arange(n) / SR
    K = max(1, int(min(8, 6000 // f)))
    out = np.zeros((2, n))
    for vi, (d, p) in enumerate(((1.0, -0.35), (detune, 0.35))):
        s = np.zeros(n)
        for k in range(1, K + 1):
            s += k ** -1.4 * bright ** (k - 1) * np.sin(TWO_PI * k * f * d * t + vi) * np.exp(-t * (1 + 0.7 * (k - 1)) / tau)
        s *= 1 - np.exp(-t / 0.002)
        gl, gr = pan_gains(p)
        out[0] += s * gl
        out[1] += s * gr
    return edge_fade(out * 0.5, 0.2, 10)


def bell(f, tau=3.0, vel=1.0):
    dur = min(tau * 4.5, 14)
    n = int(dur * SR)
    t = np.arange(n) / SR
    ratios = [1, 2.0, 3.01, 4.2, 5.43]
    amps = [1, .4, .18, .1, .05]
    out = np.zeros((2, n))
    for vi, (d, p) in enumerate(((0.9985, -0.4), (1.0015, 0.4))):
        s = np.zeros(n)
        for i, (r, a) in enumerate(zip(ratios, amps)):
            if f * r * d > 8000:
                continue
            s += a * np.sin(TWO_PI * f * r * d * t + vi * 0.9) * np.exp(-t * (1 + 0.9 * i) / tau)
        s *= ramp_in(int(0.004 * SR)).tolist() + [1] * (n - int(0.004 * SR)) if False else 1
        s[:int(0.004 * SR)] *= ramp_in(int(0.004 * SR))
        gl, gr = pan_gains(p)
        out[0] += s * gl
        out[1] += s * gr
    return edge_fade(out * 0.5 * vel, 0, 60)


def bass_note(f, dur=0.3, tau=0.22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k in range(1, 7):
        s += k ** -1.1 * 0.7 ** (k - 1) * np.sin(TWO_PI * k * f * t)
    s *= np.exp(-t / tau)
    s = np.tanh(1.5 * s)
    return edge_fade(s, 4, 25)


def clap(seed):
    r = np.random.default_rng(seed)
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = signal.sosfilt(signal.butter(2, [900, 3200], "bandpass", fs=SR, output="sos"), r.standard_normal(n))
    e = np.exp(-t / 0.07) * (1 - np.exp(-t / 0.002))
    for d in (0.0, 0.011, 0.023):
        e += 0.5 * np.exp(-np.clip(t - d, 0, None) / 0.012) * (t >= d) * 0
    return edge_fade(x * e, 0.5, 20)


# ---------------- harmony ----------------
P2 = ["Am", "F", "Dm", "E"]
P3 = ["Am", "F", "C", "G", "Am", "F", "Dm", "E"]
BEAT = 0.6
BAR = 4 * BEAT


def arp_tones(ch, up=0):
    r, th, fi = CH[ch]
    b = r + 24
    while b >= 58:
        b -= 12
    b += up
    return [b, b + th, b + fi, b + 12, b + 12 + th]


# ================= build buses =================
pad = zbus(); heart = zbus(); ticks = zbus(); arp = zbus(); bass = zbus()
bellb = zbus(); air = zbus(); claps = zbus(); fxm = zbus()

# ---- Section 1 pad (0-52)
for ch, a, b in (("Am", 0, 13.5), ("F", 13.5, 26), ("Dm", 26, 39), ("E", 39, 53)):
    pad_chord(pad, ch, a, b, ov=4.0, gain=1.0)
print("pad s1 done")

# ---- heartbeat 0-51.2 (accelerates 35->47)
t = 4.0
k_lub = kick(0.45, 72, 40, 0.04, 0.16, 1.8)
k_dub = kick(0.35, 64, 38, 0.035, 0.11, 1.8)
while t < 51.0:
    bpm = 64 + 16 * np.clip((t - 35) / 12, 0, 1)
    place(heart, k_lub, t, 0, 1.0)
    place(heart, k_dub, t + 0.30 * 64 / bpm, 0, 0.55)
    t += 60 / bpm

# ---- air + rumble (whole piece)
na = N
air_noise = np.stack([filt(rng.standard_normal(na), "high", 6500, 3) for _ in range(2)])
rum = np.stack([filt(rng.standard_normal(na), "low", 120, 3) for _ in range(2)])
air += filt(air_noise, 'low', 15000, 2)
fxm += rum  # rumble routed with its own gain, still pre-vc

# ---- Section 2 (53-95): arp, kick, ticks
S2, S3, S4 = 53.0, 95.0, 152.0
bar_events2 = []
b = 0
while S2 + b * BAR < S3:
    ts = S2 + b * BAR
    bar_events2.append((P2[b % 4], ts, min(ts + BAR, S3)))
    b += 1
for ch, ts, te in bar_events2:
    pad_chord(pad, ch, ts, te, ov=0.7, gain=1.0, wide=True)

bar_events3 = []
b = 0
while S3 + b * BAR < S4:
    ts = S3 + b * BAR
    bar_events3.append((P3[b % 8], ts, min(ts + BAR, S4)))
    b += 1
for ch, ts, te in bar_events3:
    pad_chord(pad, ch, ts, te, ov=0.7, gain=1.0, wide=True)
print("pad s2/3 done")

# closing pad
pad_chord(pad, "Am", 152, 158, ov=3.0, gain=0.9, wide=True)
pad_chord(pad, "F", 158, 164, ov=3.0, gain=0.9, wide=True)
pad_chord(pad, "Dm", 164, 168, ov=3.0, gain=0.9, wide=True)
final = [(33, 1.0), (45, 0.85), (52, 0.6), (60, 0.5), (64, 0.38), (71, 0.25)]
pad_chord(pad, "Am", 168, 175.5, ov=3.0, gain=0.95, voicing=final)
print("closing pad done")

# kick + ticks + arp + bass + claps sections 2 and 3
k_beat = kick(0.4, 95, 42, 0.035, 0.13, 1.6)
k_acc = kick(0.4, 100, 44, 0.035, 0.14, 1.6)
tick_hi = tick_burst(6200, 0.04, 0.005, seed=1, tone=2600)
tick_lo = tick_burst(4800, 0.04, 0.006, seed=2, tone=1900)
tick16 = tick_burst(7500, 0.03, 0.003, seed=3)
clap_s = [clap(5), clap(6)]
ARP_PATTERN8 = [0, 1, 2, 1, 3, 2, 1, 2]
ARP_PATTERN16 = [0, 2, 1, 3, 2, 4, 3, 2, 0, 2, 1, 3, 4, 3, 2, 1]
BASS_STEPS = [(1.0, 0), (0.5, 12), (0.8, 0), (0.55, 12), (1.0, 0), (0.5, 12), (0.8, 0), (0.55, 12)]
BASS_STEPS = [(1.0, 0), (0.55, 0), (0.8, 0), (0.5, 12), (1.0, 0), (0.55, 0), (0.8, 0), (0.5, 12)]

pl_cache = {}
def pl(m, bright, tau):
    key = (m, bright, tau)
    if key not in pl_cache:
        pl_cache[key] = pluck(float(mtof(m)), bright, tau)
    return pl_cache[key]

for ev_list, t_end in ((bar_events2, S3), (bar_events3, S4)):
    sec3 = ev_list is bar_events3
    for bi, (ch, ts, te) in enumerate(ev_list):
        tones = arp_tones(ch)
        # kicks and ticks on beats/8ths
        for beat in range(4):
            tb = ts + beat * BEAT
            if tb >= te - 1e-6:
                break
            place(arp if False else heart, k_acc if beat == 0 else k_beat, tb, 0, 1.0 if beat == 0 else 0.8)
            if sec3 and beat in (1, 3):
                place(claps, clap_s[beat // 3], tb, -0.1 + 0.2 * (beat == 3), 1.0)
        for step in range(8):
            tb = ts + step * BEAT / 2
            if tb >= te - 1e-6:
                break
            place(ticks, tick_hi if step % 2 == 0 else tick_lo, tb, -0.3 if step % 2 == 0 else 0.3, 1.0 if step % 2 == 0 else 0.7)
            if sec3 or tb > 84:
                place(ticks, tick16, tb + BEAT / 4, 0.0, 0.5)
        if not sec3:
            for step in range(8):
                tb = ts + step * BEAT / 2
                if tb >= te - 1e-6:
                    break
                m = tones[ARP_PATTERN8[step]]
                inten = 0.55 + 0.45 * np.clip((tb - 80) / 12, 0, 1)
                place(arp, pl(m, 0.55 + 0.25 * inten, 0.24), tb, 0, 0.85 * inten + 0.15)
        else:
            tones3 = arp_tones(ch)
            for step in range(16):
                tb = ts + step * BEAT / 4
                if tb >= te - 1e-6:
                    break
                m = tones3[ARP_PATTERN16[step]]
                acc = 1.0 if step % 4 == 0 else (0.7 if step % 2 == 0 else 0.5)
                place(arp, pl(m, 0.85, 0.2), tb, 0, acc)
                if step % 8 == 4:  # high sparkle octave
                    place(arp, pl(m + 12, 0.7, 0.3), tb, 0, 0.45)
            for step in range(8):
                tb = ts + step * BEAT / 2
                if tb >= te - 1e-6:
                    break
                gain_b, oct_ = BASS_STEPS[step]
                f = float(mtof(CH[ch][0] + oct_ + (12 if CH[ch][0] < 33 else 0)))
                place(bass, bass_note(f, 0.3, 0.22), tb, 0, gain_b)
print("seq done")

# riser pad hits at 130 re-entry handled in fx
# ---- closing bells
bell_notes = [(152.3, "E5", 1.0), (154.7, "C5", 0.85), (157.0, "A4", 0.9), (159.5, "C5", 0.8), (161.8, "A4", 0.8),
              (164.4, "D5", 0.85), (166.2, "F5", 0.7), (168.6, "E5", 0.85), (171.0, "A4", 0.8), (173.0, "C5", 0.6)]
NN = {"A4": 69, "C5": 72, "D5": 74, "E5": 76, "F5": 77}
for tb, nm, v in bell_notes:
    place(bellb, bell(float(mtof(NN[nm])), 3.2, v), tb)
# soft low bell tolls
place(bellb, bell(float(mtof(45)), 5.0, 0.7), 152.0)
place(bellb, bell(float(mtof(45)), 5.0, 0.6), 168.0)

# ---- fx: riser + boom (music)
def music_riser(t0=47.5, t1=51.8):
    T = t1 - t0
    n = int(T * SR)
    t = np.arange(n) / SR
    u = t / T
    outs = []
    for ch in range(2):
        nz = rng.standard_normal(n)
        fc = 250 * (9000 / 250) ** u
        bp = tv_biquad(nz, fc, q=1.4, kind="bp")
        outs.append(bp)
    noise = np.stack(outs)
    f = 110 * 8 ** u
    ph = TWO_PI * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.5 * np.sin(2.005 * ph) + 0.25 * np.sin(3.01 * ph)
    trem = 1 - 0.25 * (0.5 + 0.5 * np.sin(TWO_PI * np.cumsum(1.5 + 9 * u ** 2) / SR))
    amp = u ** 2.4
    sig = (noise * 1.4 * amp + tone * 0.45 * u ** 3) * trem
    sig = filt(sig, "low", 8000, 4)
    sig = edge_fade(sig, 20, 25)  # review fix: softer end
    # sub swell
    sub = np.sin(TWO_PI * np.cumsum(40 + 25 * u) / SR) * u ** 2
    sig = sig + 0.5 * sub
    return sig

riser = music_riser()
fx = zbus()
place(fx, riser, 47.5)
bm = boom(4.5, 0.45)
place(fx, bm, 52.0, 0, 1.0)
# reverb of boom/riser, own rev
fx_rev = reverb(fx, rt60=3.2, damp_hz=5000, seed=40)
# gate: boom + tail must be nearly silent by ~53.0
boomgate = curve([(0, 1), (52.35, 1), (52.95, 0.0), (130 - 0.01, 0), (176, 0)], N, 0.02)
_tt = np.arange(N) / SR
pregate = np.interp(_tt, [0, 51.72, 51.9], [1.0, 1.0, 0.0])  # review fix: ~100 ms gap before boom
gate_all = np.where(_tt < 51.98, pregate, boomgate)
fx_mix = (fx + 0.55 * fx_rev) * gate_all

# re-entry hit at 130.0 and swell 128.2-130
hit = zbus()
place(hit, boom(2.0, 0.28, 60, 36), 130.0, 0, 0.35)
sw_n = int(1.8 * SR)
swt = np.arange(sw_n) / SR
sw = np.stack([tv_biquad(rng.standard_normal(sw_n), 300 * (5000 / 300) ** (swt / 1.8), 1.2, "bp") for _ in range(2)])
sw = sw * (swt / 1.8) ** 2.2 * 1.0
# review fix: noise swell removed so 128-130 is pad only

# ---------------- gain automation ----------------
g_pad = curve([(0, 0), (2, .55), (35, .6), (47, .9), (51.5, .9), (52.0, 0), (52.8, 0), (54.2, .75), (80, .75), (92, .85),
               (95, .8), (127.8, .8), (128, .4), (130, .4), (131.5, .8), (150.5, .8), (152.5, .6), (168, .65), (176, .65)], N, 0.3)
g_heart = curve([(0, 0), (3.5, 0), (8, .5), (35, .6), (47, 1.0), (50.5, 1.0), (51.3, 0), (52.9, 0), (53.0, .65), (80, .65), (92, .85),
                 (94.9, .8), (95, .9), (127.8, .9), (128, 0), (130, 0), (130.05, .9), (149.5, .9), (151.5, 0), (176, 0)], N, 0.05)
g_ticks = curve([(0, 0), (52.9, 0), (53, .5), (80, .5), (92, .8), (94.9, .8), (95, .85), (127.8, .85), (128, 0), (130, 0), (130.1, .85),
                 (150, .85), (151.5, 0), (176, 0)], N, 0.05)
g_arp = curve([(0, 0), (53.0, 0), (54, .55), (80, .6), (92, .95), (95, .8), (127.8, .85), (128, 0), (130, 0), (130.1, .9),
               (149.5, .85), (152, 0), (176, 0)], N, 0.15)
g_bass = curve([(0, 0), (94, 0), (96, .9), (127.8, .9), (128, 0), (130, 0), (130.05, .95), (149, .9), (151.5, 0), (176, 0)], N, 0.05)
g_clap = curve([(0, 0), (95, 0), (96, .5), (127.8, .5), (128, 0), (130.1, 0), (130.2, .55), (149, .5), (151, 0), (176, 0)], N, 0.05)
g_bell = curve([(0, 0), (151.9, 0), (152.0, 1), (176, 1)], N, 0.05)
g_air = curve([(0, .01), (35, .016), (47, .05), (51.5, .05), (52, 0), (53, .015), (95, .02), (128, .01), (176, .012)], N, 0.5)
g_rum = curve([(0, .15), (35, .2), (47, .45), (51.5, .45), (52, .05), (53, .12), (128, .1), (152, .1), (176, 0)], N, 0.3)
m_vc = curve([(0, .6), (46.8, .6), (47.3, .35), (51.0, .35), (52.0, 1.0), (176, 1.0)], N, 0.2)  # mid-band gain (voice clearance)

# arp echo (ping-pong)
arp_mono = arp.sum(0)
echo = np.zeros_like(arp)
d = 0.75 * BEAT
for i in range(1, 5):
    sh = int(i * d * SR)
    e = np.zeros(N); e[sh:] = arp_mono[:N - sh]
    e = filt(e, "low", 2800)
    echo[(i - 1) % 2] += 0.42 ** i * e * 1.4
arp_all = (arp + echo) * g_arp

pad_s = pad * g_pad
fxm_g = np.zeros((2, N))
fxm_g[:] = fxm * g_rum
air_g = air * g_air

# reverb sends
print("reverb...")
pad_rev = reverb(pad_s, 4.5, 6000, 100)
arp_rev = reverb(arp_all, 2.2, 5000, 200)
bell_rev = reverb(bellb * g_bell, 5.5, 6500, 300)
dry = (pad_s + 0.50 * pad_rev
       + heart * g_heart * 1.0
       + ticks * g_ticks * 0.22
       + arp_all * 0.55 + 0.35 * arp_rev
       + bass * g_bass * 0.8
       + claps * g_clap * 0.22
       + bellb * g_bell * 0.7 + 0.8 * bell_rev
       + air_g + fxm_g)
hit_r = reverb(hit, 2.5, 4000, 400)

# voice clearance split
low = signal.sosfiltfilt(sos("low", 250, 4), dry, axis=-1)
high = signal.sosfiltfilt(sos("high", 4500, 4), dry, axis=-1)
mid = dry - low - high
dry_vc = low + high + mid * m_vc

DRY_G, FX_G = 0.45, 1.5
# review fix: voice clearance on the fx bus too (riser sits under the 47.6-50.9 s line)
fx_low = signal.sosfiltfilt(sos("low", 250, 4), fx_mix, axis=-1)
fx_high = signal.sosfiltfilt(sos("high", 4500, 4), fx_mix, axis=-1)
m_fx = curve([(0, .25), (51.0, .25), (52.0, 1.0), (176, 1.0)], N, 0.1)
fx_mix = fx_low + fx_high + (fx_mix - fx_low - fx_high) * m_fx
# review fix: brief dip of the bed right before the impact so it lands
dip = np.interp(np.arange(N) / SR, [0, 51.6, 51.9, 52.0, 52.8], [1, 1, 0.15, 0.15, 1])
dry_vc = dry_vc * dip
mix = dry_vc * DRY_G + fx_mix * FX_G + 0.8 * (hit + 0.5 * hit_r)
# master: saturation, DC removal, fade
mid_, side_ = (mix[0] + mix[1]) / 2, (mix[0] - mix[1]) / 2
side_ *= np.interp(np.arange(N) / SR, [0, 150, 153, 176], [1, 1, 0.55, 0.55])  # review fix: mono compat
mix = np.stack([mid_ + side_, mid_ - side_])
mix = np.tanh(mix * 1.3)
mix = signal.sosfiltfilt(sos("high", 22, 2), mix, axis=-1)
tt = np.arange(N) / SR
fade = np.where(tt > 170, np.cos(np.clip((tt - 170) / 6.0, 0, 1) * np.pi / 2) ** 2, 1.0)
fade *= np.where(tt < 0.5, np.sin(np.clip(tt / 0.5, 0, 1) * np.pi / 2) ** 2, 1.0)
mix *= fade
mix[:, -1] = 0
write_wav("music.wav", mix, peak_db=-3.0)
for a, b in ((0, 10), (20, 35), (40, 47), (49, 51.8), (52.0, 52.3), (52.5, 52.8), (52.8, 52.99), (55, 75), (80, 92), (96, 127), (128, 130), (131, 150), (153, 168), (172, 176)):
    seg = mix[:, int(a * SR):int(b * SR)]
    sc = 10 ** (-3 / 20) / np.max(np.abs(mix))  # (already normalized in file; mix here is pre-norm)
    print(f"{a:6.1f}-{b:6.1f}  RMS(pre-norm) = {20*np.log10(np.sqrt(np.mean(seg**2))*sc+1e-9):6.1f} dBFS")

vb = signal.sosfiltfilt(signal.butter(4,[300,4000],"bandpass",fs=SR,output="sos"), mix, axis=-1)
for a, b in ((0, 10), (20, 35), (40, 47), (55, 75), (96, 127), (153, 168)):
    sl = slice(int(a*SR), int(b*SR))
    print(f"voice-band 300-4k {a}-{b}: {20*np.log10(np.sqrt(np.mean(vb[:,sl]**2))*sc+1e-9):.1f} dBFS  (total {20*np.log10(np.sqrt(np.mean(mix[:,sl]**2))*sc+1e-9):.1f})")
