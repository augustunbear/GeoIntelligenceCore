"""Safe serving-instance provenance without credentials or query strings."""
from urllib.parse import urlsplit
from .http import origin, UnsafeEndpoint


def instance_context(context, gateway, provider_id):
    cfg = gateway.providers.get(provider_id)
    endpoint = cfg.endpoint if cfg else None
    try:
        if endpoint:
            origin(endpoint)
            if urlsplit(endpoint).query or urlsplit(endpoint).fragment:
                endpoint = None
    except (ValueError, UnsafeEndpoint):
        endpoint = None
    return context.model_copy(update={'effective_conditions': {
        **{k: v for k, v in context.effective_conditions.items() if k not in ('provider_instance', 'provider_endpoint')}, 'provider_instance': provider_id,
        **({'provider_endpoint': endpoint} if endpoint else {})}})
