Standalone executables need no Python installation.

- `groovescripting-windows-x64.exe`: Windows 10/11 x64.
- `groovescripting-linux-x64`: Linux x64 (glibc 2.35+). Run `chmod +x groovescripting-linux-x64` first; playback needs `libportaudio2`.

Usage: `groovescripting-windows-x64.exe TOOL [flags]`, for example `groovseq examples/first-groove.json --output groove.wav`. Rename the file to a tool name (e.g. `groovseq.exe`) to run that tool directly. Tools: groovdrm, groovbss, groovld, groovmix, groovseq, groovfx, groovplay, groovinfo, groovmidi, groovlint, groovdebug, groovtest, groovtime, groovmerge. `groovtime` requires Git on PATH.

The wheel and source distribution are attached for `pip install`.

0.3.0 adds event tracing with provenance, groovlint, groovdebug, groovtest, groovtime and groovmerge, on top of the 0.2.0 variation, automation and MIDI features and the playback ASCII visualizer.
