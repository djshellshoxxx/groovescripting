# Example projects

`first-groove.json` renders two bars of drums, bass and lead at 140 BPM. `arrangement.json` adds an intro, repeated main section, break and return. Render from the repository root:

```sh
groovseq examples/first-groove.json --output groove.wav --stems stems
groovseq examples/arrangement.json --output arrangement.wav
```

Tracks use `drum`, `bass` or `lead`. Patterns loop across the requested length. `gain` is a linear multiplier; `pan` runs from -1 (left) to 1 (right). Track `offset` and `trim` use beats. Section track overrides reference the exact track name. A section’s `variation` offsets its deterministic random seed. Individual renderers control `tail` behavior. Read CLI help and the project specification before adding parameters.
