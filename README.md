# WAVE: Image-to-Music Multimodal Generation Pipeline

WAVE is a multimodal generation pipeline that transforms a single image into music by
(1) designing realistic sound sources from the image context and
(2) converting those sounds into musical instruments and compositions.

Rather than relying on a single end-to-end generative model, WAVE adopts a **modular, design-driven pipeline** in which each stage explicitly addresses a different semantic alignment problem between modalities.

---

## 1. Motivation & Problem Statement

Recent advances in multimodal generation have enabled transformations across heterogeneous modalities such as image, text, and audio. Among these, **image-to-audio generation** presents a particularly challenging problem due to the fundamental gap between visual perception and acoustic representation.

A naïve approach that directly connects a Vision-Language Model (VLM) to an audio generation model often fails in practice. Common failure cases include:
- semantic misalignment between image content and generated sound,
- hallucinated sound sources that do not exist in the scene,
- generation of musical content when realistic sound effects are required.

These issues arise not only from limitations of individual models, but also from **poorly designed intermediate representations**. In particular, the textual output of a VLM must satisfy strict constraints in order to function as a valid and effective input to a text-to-audio model.

To address this challenge, WAVE frames the problem as a **pipeline design task**, rather than a single-model optimization problem.

---

## 2. Overall Pipeline

WAVE is composed of two sequential phases, each responsible for a distinct transformation.

Image 
↓ 
Phase 1: Image-to-Sound 
Scene and mood understanding 
Sound source design in text form 
Realistic sound effect generation 
↓
Phase 2: Sound-to-Music 
Timbre transfer via generative audio models 
Instrument-specific SoundFont generation 
MIDI-based music rendering 
↓
Music


WAVE is **not** a fully automated end-to-end music generation system.  
Instead, it is a **two-phase modular pipeline** in which intermediate representations are explicitly designed to ensure semantic consistency and controllability.

---

## 3. Phase 1: Image-to-Sound

### 3.1 Objective

The goal of Phase 1 is to generate **realistic sound effects** that could plausibly occur in the given image scene.  
The target output is **not music**, but sound effects or ambience that can later serve as musical material.

---

### 3.2 Design Principle: Backward Design

A key design principle of Phase 1 is **backward design**.

Instead of starting from image understanding and hoping that the resulting text works well for audio generation, we first analyze the requirements of the **text-to-audio model**:
- What type of textual descriptions produce high-quality, low-noise audio?
- Which constraints prevent the model from generating music instead of sound effects?
- How should timbre, material, and action be specified?

Only after answering these questions do we design the expected output format of the VLM.  
This approach ensures that the intermediate textual representation is **audio-oriented**, not merely descriptive.

---

### 3.3 Text-to-Audio Model Selection

We evaluated multiple text-to-audio generation models, including Make-an-Audio and AudioLDM2, under identical prompt conditions.

Empirical comparison showed that:
- Make-an-Audio frequently produced hallucinated sounds and excessive noise,
- AudioLDM2 preserved scene-level ambience more reliably and generated cleaner, more realistic audio.

Based on these observations, **AudioLDM2** was selected as the sound generation model for Phase 1.

---

### 3.4 Prompt Engineering for AudioLDM2

To ensure consistent and realistic sound generation, we designed a structured prompt format consisting of:
- a shared scene-level description (scene and mood),
- object-specific sound descriptions (material, action, timbre),
- optional mapping to musical instrument sessions,
- explicit constraints enforcing non-musical, realistic audio generation.

We further conducted ablation studies by removing individual prompt components, confirming that:
- mood and scene constraints strongly influence timbral quality,
- explicit non-musical constraints are necessary to prevent unintended music generation,
- instrument mapping information significantly affects tonal characteristics.

---

### 3.5 Image-to-Text (VLM) Selection

The VLM is responsible for generating text that conforms to the audio-oriented prompt design.

We evaluated two candidate models:
- LLaVA-NEXT-7B
- Qwen2.5-VL-7B

To assess their suitability, we constructed a small benchmark using:
- MSCOCO (daily-life images with clear objects),
- ArtEmis (artistic images emphasizing mood and abstraction).

For 22 images, we manually constructed a Golden Dataset consisting of:
- scene description,
- mood description,
- structured sound source annotations.

Human evaluation focused on hallucination, consistency, and usability as audio prompts.  
**Qwen2.5-VL-7B** consistently outperformed LLaVA across all criteria and was selected as the final VLM.

---

### 3.6 Phase 1 Output

The output of Phase 1 consists of:
- structured sound source descriptions,
- AudioLDM2-generated sound effect audio files.

These outputs serve as the direct input to Phase 2.

---

## 4. Phase 2: Sound-to-Music

### 4.1 Objective

Phase 2 transforms sound effects into **musical components** by converting environmental sounds into instrument timbres and rendering them as a musical composition.

---

### 4.2 Pipeline Overview
Sound effect 
↓
RAVE (timbre transfer)
↓
Instrument-specific SoundFont
↓
MIDI score rendering (PrettyMIDI)
↓
Music

---

### 4.3 Timbre Transfer with RAVE

For timbre conversion, we employ **RAVE (Realtime Audio Variational autoEncoder)**, a generative audio model designed for high-quality audio synthesis and timbre manipulation.

RAVE models were trained on subsets of the NSynth dataset corresponding to:
- keyboard,
- bass,
- electric guitar.

Each model learns a latent representation via standard VAE training, followed by adversarial fine-tuning to improve audio quality.

---

### 4.4 SoundFont Generation

To enable MIDI-based music rendering, instrument-specific SoundFonts are generated from the converted audio:
- pitch-shifted samples are extracted using librosa,
- samples are organized into SoundFont structures using automated scripts,
- drum sounds are handled via direct key mapping rather than timbre transfer.

This process allows a single sound source to cover a full pitch range.

---

### 4.5 MIDI Rendering

Finally, generated SoundFonts are used to render MIDI scores using PrettyMIDI.
Existing MIDI compositions are replayed using image-derived instrument timbres, producing music that reflects the original scene’s acoustic character.

---

## 5. Results

Phase 1 successfully generates scene-consistent sound effects with reduced hallucination and improved realism.  
Phase 2 demonstrates that environmental sounds can be meaningfully transformed into musical timbres and integrated into multi-instrument compositions.

Audio demos and generated results are provided in the repository.

---

## 6. Limitations & Future Work

### Limitations
- automatic session assignment may result in duplication or omission in some cases,
- SoundFont generation relies on simplified velocity and looping heuristics,
- musical arrangement remains structurally simple.

### Future Work
- flexible session structures beyond fixed instrument counts,
- automated arrangement and section-level composition,
- user-in-the-loop controls for sound-to-instrument mapping,
- deployment as an interactive application.

---

## 7. Repository Structure
├─ image_to_sound/ # Phase 1: Image-to-Sound pipeline
├─ sound_to_music/ # Phase 2: Sound-to-Music pipeline
├─ Report/ # Project report and documentation
├─ README.md # This file

---

## 8. Execution

Each phase includes a dedicated README with detailed execution instructions.  
This root README focuses on **system design and modeling rationale** rather than step-by-step usage.




