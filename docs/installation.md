# Install on Linux and Windows

Requires Python 3.10 or newer and an internet connection for dependencies. Use a virtual environment to keep the installation separate from system Python. Git is needed only for cloning: alternatively download and extract the source ZIP from the Pages site, open its `groovescripting` directory and start at the virtual-environment command.

## Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install python3 python3-venv git libportaudio2 libsndfile1
git clone https://github.com/djshellshoxxx/groovescripting.git
cd groovescripting
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[playback]"
groovseq examples/grooves/house.json --output house.wav
groovplay house.wav
```

Check `python3 --version` first. On other distributions install Python 3.10+, its virtual-environment support, Git, PortAudio and libsndfile with that distribution's package manager, then follow the commands starting at `git clone`. Fedora audio packages are `portaudio` and `libsndfile`; Arch audio packages are also `portaudio` and `libsndfile`. Run in a desktop session for local playback. For offline WAV generation install `.` instead of `.[playback]`.

In a new terminal run `cd groovescripting` and `source .venv/bin/activate` again. Use `deactivate` to leave the environment. Package installation does not need sudo.

## Windows (PowerShell)

Install Python 3.10+ from https://www.python.org/downloads/windows/ and Git from https://git-scm.com/downloads/win. Reopen PowerShell, then check `py -3 --version` and `git --version`. If the Python launcher is unavailable, replace `py -3` with your installed `python` command.

```powershell
git clone https://github.com/djshellshoxxx/groovescripting.git
cd groovescripting
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[playback]"
.\.venv\Scripts\groovseq.exe examples/grooves/house.json --output house.wav
.\.venv\Scripts\groovplay.exe house.wav
```

These commands call the virtual environment directly, so PowerShell script activation and execution-policy changes are unnecessary. In later sessions open the repository directory and reuse the `.venv\Scripts\*.exe` commands. They also work in Command Prompt. If you activate the environment with `.\.venv\Scripts\Activate.ps1`, the short commands such as `groovseq` become available, but activation is optional.

For optional Windows master-volume control:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[playback,windows-volume]"
```

## Verify and troubleshoot

On Linux with the environment active:

```bash
groovseq --help
groovplay --devices
groovplay --diagnose
```

On Windows:

```powershell
.\.venv\Scripts\groovseq.exe --help
.\.venv\Scripts\groovplay.exe --devices
.\.venv\Scripts\groovplay.exe --diagnose
```

If playback fails, verify the generated WAV with `groovinfo` and select an available output with `groovplay house.wav --device ID`. On Windows prefix both tool names with `.\.venv\Scripts\` and append `.exe`. If a command cannot be found, reactivate the Linux environment or use the full Windows executable path. If a WAV already exists, choose a new output name or add `--overwrite`. Shell launchers in `scripts/` require the installed engine; `GROOVESCRIPTING_PYTHON` can select the virtual-environment interpreter.

## Update or remove

From the checkout, run `git pull --ff-only`, then repeat the package installation command. On Linux uninstall with `python -m pip uninstall groovescripting`; on Windows use `.\.venv\Scripts\python.exe -m pip uninstall groovescripting`. Your projects and WAVs remain in place.
