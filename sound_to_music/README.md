# wave-pipeline

MIDI와 단일 샘플(SFZ)을 이용해 밴드 4트랙(기타/베이스/키보드/드럼)을 합성하고, 가벼운 마스터 체인(HPF → 노이즈 게이트 → 소량 리버브 → 리미터)을 거쳐 **최종 1개의 WAV**를 만드는 파이프라인입니다.  
기준 경로는 `/root/wave`이며, 산출물은 기본적으로 **`/root/wave/result/{MIDI이름}_result.wav`** 입니다.

---

## 0) 설치

```bash
# /root/wave 에서
pip install -r requirements.txt

### 시스템 의존성 (rubberband-cli)
#Ubuntu/Debian:
apt-get update && apt-get install -y rubberband-cli
#macOS (Homebrew):
#brew install rubberband
```

> **librosa 주의:** 저장소에 포함된 `librosa.py`는 경량 shim입니다. 

---

## 1) 디렉터리 구조

```text
/root/wave/
  midi_input/                 # MIDI 파일 (예: this_love.mid)
  sound_input/
    guitar/                   # 원본 WAV (기타)
    bass/                     # 원본 WAV (베이스)
    keyboard/                 # 원본 WAV (키보드)
    drum/                     # 원본 WAV (드럼; 여러 파일 또는 1개)
  rave/
    rave_guitar.ts            # RAVE 체크포인트
    rave_bass.ts
    rave_keyboard.ts
  rave_output/
    guitar/                   # RAVE 추론 결과
    bass/
    keyboard/
  sfz_output/                 # autosfz_builder가 만드는 *_sf/Instrument.sfz
  result/                     # 최종 {song}_result.wav
  autosfz_builder.py
  midi_render.py
  rave_infer.py
  requirements.txt
  librosa.py                  # 경량 shim(선택)
```

필요 폴더 생성:

```bash
mkdir -p /root/wave/{midi_input,sound_input/{guitar,bass,keyboard,drum},rave_output/{guitar,bass,keyboard},sfz_output,result}
```

---

## 2) 실행 순서

### (1) RAVE 추론 → `/root/wave/rave_output/**`

```bash
python rave_infer.py --ts /root/wave/rave/rave_bass.ts   --in_dir /root/wave/sound_input/bass --out_dir /root/wave/rave_output/bass --sr 48000 --suffix _rave

python rave_infer.py --ts /root/wave/rave/rave_guitar.ts   --in_dir /root/wave/sound_input/guitar --out_dir /root/wave/rave_output/guitar --sr 48000 --suffix _rave

python rave_infer.py --ts /root/wave/rave/rave_keyboard.ts   --in_dir /root/wave/sound_input/keyboard --out_dir /root/wave/rave_output/keyboard --sr 48000 --suffix _rave
```

### (2) SFZ 빌드 → `/root/wave/sfz_output/**`

**멜로딕(베이스/기타/키보드)**

```bash
python autosfz_builder.py --mode melodic --root-in /root/wave/rave_output/bass   --root-out /root/wave/sfz_output/bass --sr 48000 --snap-to-nearest --do-loop --trim-db -40

python autosfz_builder.py --mode melodic --root-in /root/wave/rave_output/guitar   --root-out /root/wave/sfz_output/guitar --sr 48000 --snap-to-nearest --do-loop --trim-db -40

python autosfz_builder.py --mode melodic --root-in /root/wave/rave_output/keyboard   --root-out /root/wave/sfz_output/keyboard --sr 48000 --snap-to-nearest --do-loop --trim-db -40
```

**드럼**

- 여러 파일을 연속 키에 매핑:

```bash
python autosfz_builder.py --mode drum --root-in /root/wave/sound_input/drum   --root-out /root/wave/sfz_output/drum --kit-name Drum --start-key 36 --normalize --one-shot
```

- 단일 WAV로 전체 키(GM 35–81) 매핑:

```bash
for w in /root/wave/sound_input/drum/*.wav; do
  python autosfz_builder.py --mode drum-one \
    --in-wav "$w" --root-out /root/wave/sfz_output/drum --keys gm --one-shot
done
```

실행 후 `sfz_output/` 아래에 각각 `*_sf/Instrument.sfz`가 생성됩니다.

### (3) MIDI 렌더

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
  --sr 48000 --debug --out "$OUT" --debug

출력 경로를 지정하지 않으면 자동으로 `/root/wave/result/{MIDI이름}_result.wav`에 저장합니다.

---

## 3) 각 스크립트 요약

### `rave_infer.py`
- 인자: `--ts`(체크포인트), `--in_dir`, `--out_dir`, `--sr`, `--suffix`
- 역할: 원본 WAV를 RAVE로 변환하여 `rave_output/<part>/`에 저장

### `autosfz_builder.py`
- 모드:
  - `melodic`: 단일 샘플로 전음역 커버(무음 트림, 루프 크로스페이드 옵션)
  - `drum`: 폴더 내 다수 WAV를 키 연속 매핑
  - `drum-one`: 단일 WAV를 지정 키들에 복제 매핑(`--keys gm` 지원)
- 출력: 각 소스마다 `*_sf/Instrument.sfz` 폴더 생성

### `midi_render.py`
- 인자: `--midi`, `--guitar-sfz`, `--bass-sfz`, `--keys-sfz`, `--drum-sfz`, `--sr`, `--gain`, `--out`, `--debug`
- 역할: SFZ 샘플러로 MIDI 합성 → v2 soft 체인(HPF/게이트/리버브/리미터) 적용 → 최종 WAV 저장

