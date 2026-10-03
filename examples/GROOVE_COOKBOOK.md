# Groove cookbook

Ten editable starting points, not transcriptions of particular tracks. Each project contains drums, bass and lead and renders four bars. Run commands from the repository root after installing the package. The same commands work in Bash and PowerShell.

## Read the formulas

In 4/4 with subdivision 4, a bar contains 16 steps; step numbers 1, 5, 9 and 13 are beats 1–4. Drum strings use one character per step: `x` is a hit, `X` an accent and `.` a rest. Note patterns use space-separated tokens; each token advances one step. `C2:0.5` holds a note for half a beat, `C4+Eb4+G4` plays a chord and `~` extends the preceding note by one step. Duration does not change the step position of the next token. Patterns repeat over the project length.

Step duration in seconds = `60 / (bpm × subdivision)`. Bar duration = `60 × beats / bpm`. Loop duration = `bars × bar duration`. At 120 BPM a sixteenth step is 0.125 seconds and a four-bar 4/4 loop is eight seconds. Swing delays alternating steps by `swing / (2 × subdivision)` beats; it does not convert the grid to triplets.

## House / offbeat bass

Four kicks per bar, backbeat clap and bass on the offbeats.

124 BPM · 4 beats/bar · 4 steps/beat · swing 0

```text
Kick:  X...X...X...X...
Snare: ....x.......x...
Hat:   ..x...x...x...x.
Bass:  . . C2 . . . C2 . . . Eb2 . . . G1 .
Lead:  C4+Eb4+G4:0.5 . . . . . . . Bb3+D4+F4:0.5 . . . . . . .
```

```sh
groovseq examples/grooves/house.json --output house.wav --stems house-stems
groovinfo house.wav
groovplay house.wav
```

## Techno / driving pulse

Straight sixteenth hats and a repeating short bass pulse.

132 BPM · 4 beats/bar · 4 steps/beat · swing 0

```text
Kick:  X...x...X...x...
Snare: ....x.......x...
Hat:   xxxxxxxxxxxxxxxx
Bass:  C2 . C2 . C2 . Eb2 . C2 . C2 . Bb1 . G1 .
Lead:  C4 . . G4 . . Eb4 . C4 . . Bb3 . . G3 .
```

```sh
groovseq examples/grooves/techno.json --output techno.wav --stems techno-stems
groovinfo techno.wav
groovplay techno.wav
```

## Drum and bass / rolling break

Broken kick placement, snares on beats two and four, sustained sub notes.

174 BPM · 4 beats/bar · 4 steps/beat · swing 0

```text
Kick:  X.....x...x.....
Snare: ....X.......X...
Hat:   x.xXx.x.x.xXx.x.
Bass:  C2:0.5 . . . G1:0.5 . . . Bb1:0.5 . . . C2:0.5 . . .
Lead:  C4 . . . G4 . . . Eb4 . . . Bb4 . . .
```

```sh
groovseq examples/grooves/drum-and-bass.json --output drum-and-bass.wav --stems drum-and-bass-stems
groovinfo drum-and-bass.wav
groovplay drum-and-bass.wav
```

## Half time / heavy pocket

One central snare on beat three leaves space for long bass notes.

86 BPM · 4 beats/bar · 4 steps/beat · swing 0.08

```text
Kick:  X.........x.....
Snare: ........X.......
Hat:   x.x.x.x.x.x.x.x.
Bass:  C2:1 . . . . . G1:0.5 . Bb1:1 . . . . . . .
Lead:  C4:1 . . . . . . . Eb4:1 . . . . . . .
```

```sh
groovseq examples/grooves/half-time.json --output half-time.wav --stems half-time-stems
groovinfo half-time.wav
groovplay half-time.wav
```

## Hip hop / swung steps

Swing delays alternating steps; light timing and velocity variation adds movement.

92 BPM · 4 beats/bar · 4 steps/beat · swing 0.32

```text
Kick:  X......x..x.....
Snare: ....X.......X...
Hat:   x.x.x.x.x.x.x.x.
Bass:  C2 . . Eb2 . . G1 . C2 . . . Bb1 . G1 .
Lead:  C4+Eb4+G4:1 . . . . . . . Bb3+D4+F4:1 . . . . . . .
```

```sh
groovseq examples/grooves/hip-hop.json --output hip-hop.wav --stems hip-hop-stems
groovinfo hip-hop.wav
groovplay hip-hop.wav
```

## UK garage / syncopation

Sparse kicks, swung offbeat hats and short chord stabs.

130 BPM · 4 beats/bar · 4 steps/beat · swing 0.24

```text
Kick:  X.........x.....
Snare: ....X.......X...
Hat:   ..x...x...x...x.
Bass:  . C2 . . G1 . . C2 . . Eb2 . . G1 . Bb1
Lead:  C4+Eb4+G4:0.25 . . . . . C4+Eb4+G4:0.25 . . . Bb3+D4+F4:0.25 . . . . .
```

```sh
groovseq examples/grooves/garage.json --output garage.wav --stems garage-stems
groovinfo garage.wav
groovplay garage.wav
```

## Hard trance / octave drive

Alternating bass octaves support a straight kick and minor lead.

145 BPM · 4 beats/bar · 4 steps/beat · swing 0

```text
Kick:  X...X...X...X...
Snare: ....X.......X...
Hat:   ..x...x...x...x.
Bass:  C2 C3 C2 C3 C2 C3 C2 C3 Bb1 Bb2 Bb1 Bb2 G1 G2 G1 G2
Lead:  C4 . G4 . Eb5 . G4 . Bb3 . F4 . D5 . F4 .
```

```sh
groovseq examples/grooves/hard-trance.json --output hard-trance.wav --stems hard-trance-stems
groovinfo hard-trance.wav
groovplay hard-trance.wav
```

## Electro / broken machine

Broken kick accents with a dry bass and spaced melodic phrase.

118 BPM · 4 beats/bar · 4 steps/beat · swing 0

```text
Kick:  X.....x...X..x..
Snare: ....X.......X...
Hat:   x.x.x.x.x.x.x.x.
Bass:  C2 . . G1 . C2 . . Eb2 . . Bb1 . G1 . .
Lead:  C4 . Eb4 . . G4 . . Bb4 . . G4 . Eb4 . .
```

```sh
groovseq examples/grooves/electro.json --output electro.wav --stems electro-stems
groovinfo electro.wav
groovplay electro.wav
```

## Dub / spacious pulse

Long bass notes and short chord stabs leave room for a later delay effect.

72 BPM · 4 beats/bar · 4 steps/beat · swing 0.1

```text
Kick:  X.......x.......
Snare: ....x.......x...
Hat:   ..x...x...x...x.
Bass:  C2:1 . . . . . G1:0.5 . Bb1:1 . . . . . C2:0.5 .
Lead:  C4+Eb4+G4:0.25 . . . C4+Eb4+G4:0.25 . . . Bb3+D4+F4:0.25 . . . Bb3+D4+F4:0.25 . . .
```

```sh
groovseq examples/grooves/dub.json --output dub.wav --stems dub-stems
groovinfo dub.wav
groovplay dub.wav
```

## 7/8 / uneven loop

Seven eighth-note groups per bar, represented as seven quarter-note beats at double tempo.

240 BPM · 7 beats/bar · 2 steps/beat · swing 0

```text
Kick:  X.....x...x...
Snare: ....x.......x.
Hat:   x.x.x.x.x.x.x.
Bass:  C2 . . G1 . . Bb1 . . C2 . G1 . .
Lead:  C4 . Eb4 . G4 . Bb4 . G4 . Eb4 . C4 .
```

```sh
groovseq examples/grooves/seven-eight.json --output seven-eight.wav --stems seven-eight-stems
groovinfo seven-eight.wav
groovplay seven-eight.wav
```

## Make it your own

Edit `bpm`, `bars`, `swing`, the track patterns and synthesis `params` in a copied JSON file. Keep the seed fixed for repeatable variation. Reduce track gains if a combination clips; `groovinfo` reports signal statistics. Add `--overwrite` when replacing an existing render. Stems can be imported into a DAW for effects and arrangement. The 7/8 recipe uses seven beats at 240 BPM with two steps per beat, equivalent to seven eighth notes at 120 BPM; its 14-step pattern lasts one bar.
