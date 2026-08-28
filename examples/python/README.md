# PyHookKit

Typed Slack and Microsoft Teams notification delivery with semantic parity.

The Python 3.12 package follows inward dependencies:

```text
entrypoints/adapters -> application/ports -> domain
```

Fundamental and scenario scripts are thin composition examples. Reusable
behavior belongs under `src/pyhookkit`.

The F00 raw HTTP example is the deliberate exception: it uses only Python's
standard library to show provider requests before introducing `pyhookkit`.

Slack-only discovery, lifecycle, interaction, file, reaction, scheduling, and
event examples live under `slack_operations`. They are separate from paired
fundamentals because workspace administration and inbound Slack protocols do
not map to provider-neutral notification payloads.

Teams-specific presentation patterns live under `teams_adaptive_cards`. The
gallery demonstrates hierarchy, metrics, images, progressive disclosure,
mentions, and progress timelines without expanding the provider-neutral domain.

## Install locally

From this directory:

```shell
uv sync --extra dev --python 3.12
```

From the repository root:

```shell
python -m pip install ./examples/python
```

After the first PyPI release, installation will be:

```shell
python -m pip install pyhookkit
```

The stable public value objects are importable from the package root:

```python
from pyhookkit import CanonicalNotification, Severity
```
