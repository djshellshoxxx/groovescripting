# Demo reproduction

From the source checkout, after installation:

```sh
groovdrm --preset examples/presets/drum-electronic.json --sample-rate 16000 --channels 1 --seed 0 --normalize --output docs/audio/drums.wav --overwrite
groovbss --preset examples/presets/bass-acid.json --sample-rate 16000 --channels 1 --seed 0 --normalize --output docs/audio/bass.wav --overwrite
groovld --preset examples/presets/lead-soft_chord.json --sample-rate 16000 --channels 1 --seed 0 --normalize --output docs/audio/chords.wav --overwrite
groovseq examples/first-groove.json --sample-rate 16000 --channels 1 --output docs/audio/groove.wav --overwrite
```

The single-instrument presets default to 120 BPM and one four-beat bar, giving 32,000 frames each. Groove uses the committed project seed42, tempo140 and two bars, giving54,857 frames. Normalization is explicit for the instrument demos to keep resonant/multivoice peaks below full scale. WAV PCM16 encoding may vary with dependency versions; exact byte identity is only asserted within one tested dependency environment.
