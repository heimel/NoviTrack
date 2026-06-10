# NoviTrack

NoviTrack is a toolkit for tracking animal behavior and analyzing related
NoviTrack experiments, including behavior videos, Neurotar data, fiber
photometry, events, snippets, and session summaries.

The Python implementation in `novitrack` is the primary development path. The
MATLAB implementation remains available in `Toolbox` for existing users and for
checking analyses against the original tools.

NoviTrack is developed and maintained by Alexander Heimel.

## Documentation

See the [NoviTrack manual](docs/README.md) for installation, configuration,
analysis workflows, experiment operation, synchronization, and reference
information.

## Repository layout

```text
NoviTrack/
  docs/            NoviTrack manual and reference documentation
  novitrack/       Python NoviTrack package
  test_data/       Example database and expected preview outputs
  tests/           Python tests
  Toolbox/         MATLAB NoviTrack toolbox
```

Other files in the repository support acquisition computers, Raspberry Pi video
recording, documentation, and setup-specific helper scripts.

## Quick start

After completing the [Python installation](docs/python.md), open the database
browser from the NoviTrack repository root:

```python
import novitrack as nt

browser = nt.experiment_db()
```

Run the focused Python tests from the repository root with:

```bash
pytest tests
```
