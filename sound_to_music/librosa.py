# 로컬 경량 shim: 필요한 최소 기능만 제공합니다.
# - load, resample
# - effects.pitch_shift (rubberband 있으면 사용, 없으면 2-단계 resample 근사)
# - util.normalize, util.fix_length
# - feature.rms (간단)
# - yin (매우 단순한 오토코릴레이션 기반 근사; 실패 시 np.nan)
import os, math
import numpy as np
import soundfile as sf
from scipy.signal import resample as sp_resample, resample_poly

def load(path, sr=None, mono=False):
    y, s = sf.read(path, always_2d=False)
    if y.ndim > 1 and mono:
        y = y.mean(axis=1)
    y = y.astype(np.float32)
    if sr is not None and sr != s:
        g = math.gcd(s, sr)
        up, down = sr // g, s // g
        y = resample_poly(y, up, down).astype(np.float32)
        s = sr
    return y, s

def resample(y, orig_sr, target_sr, res_type="kaiser_best"):
    if orig_sr == target_sr: return y.astype(np.float32)
    g = math.gcd(orig_sr, target_sr)
    up, down = target_sr // g, orig_sr // g
    return resample_poly(y, up, down).astype(np.float32)

class effects:
    @staticmethod
    def pitch_shift(y, sr, n_steps):
        try:
            import pyrubberband as rb
            return rb.pitch_shift(y, sr, n_steps).astype(np.float32)
        except Exception:
            r = 2.0 ** (n_steps / 12.0)
            n1 = max(1, int(round(len(y) / r)))
            y1 = sp_resample(y, n1)
            y2 = sp_resample(y1, len(y))
            return y2.astype(np.float32)

class util:
    @staticmethod
    def normalize(y):
        m = np.max(np.abs(y)) if y.size else 0.0
        return (y / m).astype(np.float32) if m > 0 else y.astype(np.float32)
    @staticmethod
    def fix_length(y, size):
        if len(y) >= size: return y[:size].astype(np.float32)
        out = np.zeros(size, dtype=np.float32); out[:len(y)] = y
        return out

class feature:
    @staticmethod
    def rms(y, frame_length=2048, hop_length=512, center=True):
        if center:
            pad = frame_length // 2
            y = np.pad(y, (pad, pad), mode='reflect')
        n_frames = 1 + (len(y) - frame_length) // hop_length
        if n_frames <= 0: return np.array([], dtype=np.float32)
        out = np.zeros(n_frames, dtype=np.float32)
        for i in range(n_frames):
            s = i * hop_length
            frame = y[s:s+frame_length]
            out[i] = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
        return out

def yin(y, fmin, fmax, sr, frame_length=2048, hop_length=256):
    """아주 단순한 오토코릴레이션 기반 근사 YIN. 잡음/무음이면 np.nan 반환."""
    if len(y) < frame_length: return np.array([np.nan], dtype=np.float32)
    if np.max(np.abs(y)) < 1e-6: return np.array([np.nan], dtype=np.float32)
    out = []
    for s in range(0, len(y) - frame_length, hop_length):
        frame = y[s:s+frame_length].astype(np.float32)
        frame = frame - np.mean(frame)
        ac = np.correlate(frame, frame, mode='full')[frame.size-1:]
        ac /= (np.max(ac) + 1e-9)
        # 주기 탐색
        pmin = max(1, int(sr / fmax))
        pmax = min(len(ac)-1, int(sr / fmin))
        if pmax <= pmin:
            out.append(np.nan); continue
        idx = np.argmax(ac[pmin:pmax]) + pmin
        freq = sr / idx if ac[idx] > 0.2 else np.nan
        out.append(freq)
    return np.array(out, dtype=np.float32)