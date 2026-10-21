# GrooveScripting v0.4.0

Standalone executables for Windows, Linux and macOS (Apple silicon and Intel). Python is not required.

## New
- `groovtheory`: scales, chord symbols, Euclidean rhythms and roman-numeral progressions.
- Chord tokens in note patterns (`Cm7@3`, `Am@3/1`) and `euclid(5,8)` drum patterns.
- Nine new scales/modes (dorian, phrygian, lydian, mixolydian, locrian, harmonic/melodic minor, blues, whole tone, minor pentatonic).
- New effects: `highpass`, `normalize`, `limiter`, `chorus`.
- macOS builds added to the release workflow.

## Running
Linux/macOS (make executable first: `chmod +x ./groovescripting-*`):

```sh
./groovescripting-linux-x64 --version
./groovescripting-linux-x64 groovseq examples/first-groove.json --output groove.wav
```

macOS binaries are unsigned; clear quarantine with `xattr -d com.apple.quarantine ./groovescripting-macos-arm64`.

Windows:

```powershell
.\groovescripting-windows-x64.exe --version
```
