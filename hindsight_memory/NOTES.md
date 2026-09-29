# Hindsight Methods Confirmed Signatures

- `Hindsight(base_url: str, api_key: str | None = None, timeout: float = 300.0, user_agent: str | None = None, max_attempts: int = 3)`
- `create_bank(self, name: str, description: str | None = None, ...)`
- `retain(self, bank_id: str, text: str, tags: list[str] | None = None, ...)`
- `recall(self, bank_id: str, query: str, tags: list[str] | None = None, tags_match: Literal['any', 'all', 'any_strict', 'all_strict', 'exact'] = 'any', ...)`
- `reflect(self, bank_id: str, query: str, tags: list[str] | None = None, tags_match: Literal['any', 'all', 'any_strict', 'all_strict', 'exact'] = 'any', ...)`

Note: Wait after retain before recall because memory takes time to be processed.
Tags are passed as `tags=["tag:value", ...]`.
