# Fundamental test vectors

Each capability has one canonical `notification.json` and paired
`slack.expected.json` and `teams.expected.json` outputs.

The directories correspond to F01-F10 in
[`examples/python/fundamentals/`](../../../examples/python/fundamentals/README.md).
F00 is a raw transport example and reuses the Hello World expected payloads.

Expected files freeze provider JSON; tests separately assert semantic parity.
Update a snapshot only after confirming that the canonical meaning remains
unchanged or that an intentional behavior change is documented.
