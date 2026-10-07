# Audio, effects and arrangement helpers

All buffers are finite float64 matrices (frames, channels). Supported channel counts are 1 and 2. Audio is read through SoundFile; sample rate conversion uses polyphase resampling with integer rational factors. Writers refuse existing files unless overwrite is explicit. WAV and FLAC are supported and integer output is clipped only at encoding; internal processing retains floating point headroom.

`read(path)` returns buffer and rate. `info(path)` returns path, rate, frames, channels, duration, per-channel peak/RMS and clipped-sample count. `write(path,data,rate,overwrite=False,format='wav',subtype='PCM_16')` validates then encodes.

Mix tracks contain a path or data with sample_rate, gain in linear units, pan [-1,1], mute, solo, offset_seconds and optional trim_seconds. Positive offsets insert silence; negative offsets remove leading samples. Mono becomes stereo with constant-power pan. Stereo balance attenuates the opposite channel. Output duration is the longest shifted track. normalize scales to peak 1 only when nonzero; limit clips [-1,1]. Report contains peak before/after, frames and active track count.

Pseudocode: validate tracks → select nonmuted solo tracks if any → load → resample → trim → channel-map/pan → offset → accumulate aligned buffers → normalize/limit → report.

Effects execute in supplied order. Names: gain (db), fade (in_seconds,out_seconds), lowpass (hz, resonance [0,1]), saturation (drive positive), delay (seconds, feedback [0,1), mix [0,1], repeats <=64), reverb (seconds,mix [0,1],decay [0,1)). Tail policy cut returns original length; full retains generated tails; wrap folds tails onto the original timeline. Lowpass is a two-pole biquad whose resonance changes Q. Reverb is a deterministic multitap diffusion approximation.

Pseudocode: validate buffer, rate and tail policy → for each effect validate bounds → process → retain extended tails during chain → cut/full/fold at end.

Project version 1 contains bpm, beats (beats per bar), subdivision, swing, bars, sample_rate, channels, seed, tracks and optional sections. Tracks specify name, instrument drum/bass/lead, params, preset, pattern, gain, pan, mute, solo, offset in beats, trim in beats, and optional automation lanes. Version 1 automation supports absolute-beat gain, pan, cutoff and saturation lanes with linear or step curves. Sections have name, bars, repeat and track-name-keyed overrides; variation changes the deterministic seed. Unknown track references are rejected. Project serialization uses JSON and validates before saving/loading. Version 1 must be explicitly declared. Unknown global, track, section, override and renderer parameter keys are rejected. Mute and solo require booleans. Section overrides cannot change track name or instrument. Stems have exact mix length and alignment and sum to mix. Render callback contract: `render_fn(instrument, params)` → buffer or (buffer,rate); includes arrangement settings, pattern and deterministic seed. Sections concatenate independently rendered arrangements. Declared section lengths use cumulative beat boundaries to prevent rounding drift; offset and instrument tails are cut at the section boundary. Beat times and section boundaries use Decimal half-up rounding through the shared music clock. Global humanize and velocity_humanize override track/preset values only when present. Missing globals retain track/preset values.

Pseudocode: validate schema → expand section repeats → merge track overrides → derive seed from global seed/section/variation → render instruments → mix each aligned track separately → pad stems → sum → concatenate sections and zero-fill absent stems.

Humanization is supplied as deterministic seed and params to the renderer; timing and velocity humanization are renderer responsibilities. Troubleshooting logging is owned by the shared CLI; helpers raise actionable exceptions without writing unsolicited logs.

## Arrangement tail policy

render_project(project, render_fn, tail='cut') accepts cut/full/wrap. cut preserves the global declared timeline; full retains tails only beyond the final section; wrap folds each section's tails into that section. Track/preset humanization remains when a global value is omitted. Section boundaries are cumulative absolute beats rounded once, avoiding section-by-section drift. Stems include this instrument policy, but are pre-master: final ordered effects, normalization and limiting remain on the mixdown.
