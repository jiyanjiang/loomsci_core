# loomsci_core 0.1.0-beta.19 · Public Beta

- Version: `0.1.0-beta.19`
- Package: `releases/loomsci_core-0.1.0-beta.19.zip`
- SHA256: `73aa7a85537b03abd801acf334cfcb393d6a174dda22727d46ddd2799128adc3`

## FTS5 search

- Add FTS5 indexes and triggers for posts, tasks, and facts.
- Search uses FTS5 with a LIKE fallback.
- Add 10k/50k benchmark and tests.

Benchmark: 10k posts + 50k facts, p95 0.3 ms on the test host.

This release carries beta.18 templates, beta.17 evaluation, and beta.16 app
registry.
