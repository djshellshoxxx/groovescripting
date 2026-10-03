# Engineering research, 2026-10-03

Primary references:
- NumPy RNG https://numpy.org/doc/stable/reference/random/index : Generator and deterministic seeded streams. Pin PCG64 generator rather than promise binary identity across unbounded versions.
- SciPy resample_poly https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html : polyphase rational resampling with antialiasing FIR, appropriate for different input sample rates.
- SoundFile https://python-soundfile.readthedocs.io/en/latest/ : libsndfile-backed WAV/FLAC IO; modern wheels include libsndfile for common platforms; source installations may require system libsndfile.

Selection: Python makes CLI parsing, portable packaging and composition approachable. NumPy/SciPy run major array operations in compiled code. Bash and PowerShell invoke the same engine to keep deterministic scheduling and DSP consistent. This is offline synthesis; no hard realtime processing claim.

Existing projects reviewed via their official documentation: SoundFile provides file IO rather than synthesis; sounddevice provides PortAudio device integration. GrooveScripting implements its own pattern, synth and arrangement layer. No third-party code copied. Dependencies: NumPy BSD-3-Clause; SciPy BSD-3-Clause; SoundFile BSD-3-Clause with libsndfile LGPL-2.1; sounddevice MIT; optional pycaw MIT and comtypes MIT. Their packaged licenses remain distributed with those dependencies. Verify precise installed license metadata in release report.
