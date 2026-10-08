import numpy as np, sys
from scipy.io import wavfile
from scipy import signal
for f in sys.argv[1:]:
    sr,x=wavfile.read("../audio/"+f); x=x.astype(float)/32768
    print(f, sr, x.shape, "peak",20*np.log10(np.abs(x).max()+1e-12), "dc",x.mean(0), "clip", int((np.abs(x)>=0.9999).sum()))
    if f=="music.wav":
        m=x.mean(1); h=signal.sosfilt(signal.butter(4,6000,"high",fs=sr,output="sos"),m)
        e=np.abs(h); w=int(0.05*sr)
        loc=np.convolve(e,np.ones(w)/w,"same")+1e-6
        r=e/loc
        idx=np.argsort(r)[-8:]
        print("top transient ratios (t, ratio):",[(round(i/sr,3),round(r[i],1)) for i in sorted(idx)])
        print("t=0 sample",x[0],"end",x[-1], "rms last 1s", np.sqrt((x[-sr:]**2).mean()))
