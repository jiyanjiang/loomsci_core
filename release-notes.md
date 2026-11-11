# loomsci_core 0.1.0-beta.6 · Public Beta

- Version: `0.1.0-beta.6`
- Package: `releases/loomsci_core-0.1.0-beta.6.zip`
- SHA256: `a3557acd86e0616ea33bf566833d21bf1cf6c70c6869d1b2aef1f30808353498`

## DeepSeek settings

- `/app/settings` provides a one-field DeepSeek API key form.
- `GET /v1/settings/llm/deepseek` returns status without the key.
- `PUT /v1/settings/llm/deepseek/key` saves or clears the key.
- `POST /v1/settings/llm/deepseek/test` tests the connection.
- Keys are stored in `config.yaml` with mode 0600 and are never returned by the
  API, logs, backups, or exports.
- Summaries and the research add-on share the same configuration.

This release carries beta.5 runtime control, beta.4 `/app` routes, beta.3
loose-list fix, and the beta.2 post model.
