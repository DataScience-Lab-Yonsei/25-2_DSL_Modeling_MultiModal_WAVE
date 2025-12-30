# Phase 2: Sound-to-Music Pipeline

Phase 2 transforms sound effects generated in Phase 1 into a **musical composition**.
Using MIDI and single-sample SoundFonts (SFZ), the pipeline synthesizes a four-track band
(guitar, bass, keyboard, drums), applies a lightweight mastering chain
(HPF → noise gate → light reverb → limiter), and produces a **single final WAV file**.

The pipeline assumes a fixed working directory at `/root/wave`.  
Final outputs are saved by default to:
```
/root/wave/result/{MIDI_name}_result.wav
```
This phase focuses on **timbre transformation and musical rendering**, not composition itself.

---

## 0. Installation
From `/root/wave`:
```bash
pip install -r requirements.txt

# System Dependency (rubberband-cli)
## Ubuntu / Debian
apt-get update && apt-get install -y rubberband-cli

## macOS (Homebrew)
## brew install rubberband
```
Note on librosa
The repository includes a lightweight shim (librosa.py) for internal use.

---

# 1. Directory Structure
/root/wave/
  midi_input/                 # MIDI files (e.g., this_love.mid)
  sound_input/
    guitar/                   # Input WAVs (guitar)
    bass/                     # Input WAVs (bass)
    keyboard/                 # Input WAVs (keyboard)
    drum/                     # Input WAVs (drum; single or multiple)
  rave/
    rave_guitar.ts            # RAVE checkpoints
    rave_bass.ts
    rave_keyboard.ts
  rave_output/
    guitar/                   # RAVE inference outputs
    bass/
    keyboard/
  sfz_output/                 # Generated *_sf/Instrument.sfz
  result/                     # Final {song}_result.wav
  autosfz_builder.py
  midi_render.py
  rave_infer.py
  requirements.txt
  librosa.py                  # Lightweight shim (optional)

Create required directories if missing:
```bash
mkdir -p /root/wave/{midi_input,sound_input/{guitar,bass,keyboard,drum},rave_output/{guitar,bass,keyboard},sfz_output,result}
```

---

## 2. Execution Order
### (1) Timbre Transfer with RAVE
Outputs are written to /root/wave/rave_output/**.
```bash
python rave_infer.py \
  --ts /root/wave/rave/rave_bass.ts \
  --in_dir /root/wave/sound_input/bass \
  --out_dir /root/wave/rave_output/bass \
  --sr 48000 --suffix _rave

python rave_infer.py \
  --ts /root/wave/rave/rave_guitar.ts \
  --in_dir /root/wave/sound_input/guitar \
  --out_dir /root/wave/rave_output/guitar \
  --sr 48000 --suffix _rave

python rave_infer.py \
  --ts /root/wave/rave/rave_keyboard.ts \
  --in_dir /root/wave/sound_input/keyboard \
  --out_dir /root/wave/rave_output/keyboard \
  --sr 48000 --suffix _rave
```
This step converts environmental sounds into instrument-specific timbres using pretrained RAVE models.

### (2) SoundFont (SFZ) Generation
Outputs are written to /root/wave/sfz_output/**.
#### Melodic Instruments (Bass / Guitar / Keyboard)
```bash
python autosfz_builder.py \
  --mode melodic \
  --root-in /root/wave/rave_output/bass \
  --root-out /root/wave/sfz_output/bass \
  --sr 48000 --snap-to-nearest --do-loop --trim-db -40

python autosfz_builder.py \
  --mode melodic \
  --root-in /root/wave/rave_output/guitar \
  --root-out /root/wave/sfz_output/guitar \
  --sr 48000 --snap-to-nearest --do-loop --trim-db -40

python autosfz_builder.py \
  --mode melodic \
  --root-in /root/wave/rave_output/keyboard \
  --root-out /root/wave/sfz_output/keyboard \
  --sr 48000 --snap-to-nearest --do-loop --trim-db -40
```
Each command generates a full-range SoundFont from a single timbre-transferred sample.

#### Drums
Multiple files mapped to consecutive keys:
```bash
python autosfz_builder.py \
  --mode drum \
  --root-in /root/wave/sound_input/drum \
  --root-out /root/wave/sfz_output/drum \
  --kit-name Drum --start-key 36 --normalize --one-shot

Single WAV mapped to all GM keys (35–81):
```bash
for w in /root/wave/sound_input/drum/*.wav; do
  python autosfz_builder.py --mode drum-one \
    --in-wav "$w" \
    --root-out /root/wave/sfz_output/drum \
    --keys gm --one-shot
done
```
After execution, each instrument directory contains:
```
*_sf/Instrument.sfz
```
### (3) MIDI Rendering
```bash
SONG="this_love"
OUT="/root/wave/result/${SONG}_result.wav"

BASS_SFZ=$(ls -1dt /root/wave/sfz_output/bass/*_sf 2>/dev/null | head -1)
GUITAR_SFZ=$(ls -1dt /root/wave/sfz_output/guitar/*_sf 2>/dev/null | head -1)
KEYS_SFZ=$(ls -1dt /root/wave/sfz_output/keyboard/*_sf 2>/dev/null | head -1)
DRUM_SFZ=$(ls -1dt /root/wave/sfz_output/drum/*_sf 2>/dev/null | head -1)

python midi_render.py \
  --midi /root/wave/midi_input/${SONG}.mid \
  --guitar-sfz "$GUITAR_SFZ" \
  --bass-sfz   "$BASS_SFZ" \
  --keys-sfz   "$KEYS_SFZ" \
  --drum-sfz   "$DRUM_SFZ" \
  --sr 48000 --debug --out "$OUT"
```
If no output path is specified, the result is saved to:
```swift
/root/wave/result/{MIDI_name}_result.wav
```

---

## 3. Script Overview
rave_infer.py
* Arguments: --ts, --in_dir, --out_dir, --sr, --suffix
* Function: Converts input WAV files into instrument timbres using RAVE

autosfz_builder.py
* Modes:
- melodic: single sample → full pitch range (looping & trimming supported)
- drum: multiple samples → consecutive key mapping
- drum-one: single sample → replicated across specified keys (--keys gm)
* Output: *_sf/Instrument.sfz directory

midi_render.py
* Arguments: --midi, --guitar-sfz, --bass-sfz, --keys-sfz, --drum-sfz,
--sr, --gain, --out, --debug
* Function: MIDI synthesis via SFZ sampler → soft mastering chain →
final WAV export

Phase 2 completes the WAVE pipeline by converting image-derived sounds into music,
closing the multimodal transformation loop.

