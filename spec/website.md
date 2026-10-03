# Website specification

The static GitHub Pages site serves as the installation guide, command reference and downloadable release directory for GrooveScripting. It uses a dark navy and gray Circuit Drift Labs identity, accessible contrast, semantic headings, keyboard focus indicators and a responsive layout. It must work without JavaScript; JavaScript enhances search and copy buttons only.

The command reference covers groovdrm, groovbss, groovld, groovmix, groovseq, groovfx, groovplay and groovinfo. Shared flags explain units and constraints. Every tool has a runnable command, its input/output behavior and a downloadable example where applicable. Bash and PowerShell launchers delegate to the installed Python engine rather than reimplementing DSP. Troubleshooting documents --log-file, --log-level and --log-format, playback diagnostics, offline rendering and reproducible seed/sample-rate choices.

Download links target bundled source, launchers and project JSON. The packaging step creates those bundles before publishing; deployment must fail if bundled downloads are absent. No site claims that audio hardware or OS volume controls were verified. Audio demos, when supplied by the build, identify their command and seed. The optional browser synthesizer is outside this release scope.

Acceptance: responsive from 320 px; all local links resolve; all command names and logging flags are searchable; command copy buttons work with a graceful clipboard failure message; examples validate against the implemented version 1 schema; Pages workflow deploys docs only after tests and bundle creation succeed.
