"""Opt-in rights-aware cache with full source and tenant identity."""
from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any
from geo_intelligence_core.models.evidence import Rights

@dataclass(frozen=True)
class CacheKey:
    provider_id: str
    source_id: str
    source_version: str
    language: str
    method: str
    path: str
    params: dict[str, Any]
    purpose: str
    private: bool
    scope_token: str | None = None

    def canonical(self) -> str:
        if not all((self.provider_id, self.source_id, self.source_version, self.language,
                    self.method, self.path, self.purpose)) or (self.private and not self.scope_token):
            raise ValueError('complete identity and private scope required')
        if not self.private and self.scope_token:
            raise ValueError('scoped record requires private key')
        return json.dumps((self.provider_id, self.source_id, self.source_version, self.language,
                           self.method.upper(), self.path, self.params, self.purpose,
                           self.private, self.scope_token), sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)

class Cache:
    def __init__(self, *, enabled=False):
        self.enabled = enabled
        self._items = {}

    def _permitted(self, key, rights):
        if not self.enabled or not all(rights.allows(a, key.purpose) for a in ('use', 'retain', 'cache')):
            return None
        try:
            return key.canonical()
        except (ValueError, TypeError):
            return None

    def get(self, key: CacheKey, rights: Rights) -> Any | None:
        identity = self._permitted(key, rights)
        return deepcopy(self._items[identity]) if identity is not None and identity in self._items else None

    def put(self, key: CacheKey, value: Any, rights: Rights) -> bool:
        identity = self._permitted(key, rights)
        if identity is None:
            return False
        self._items[identity] = deepcopy(value)
        return True
