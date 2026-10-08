"""Routers. Each versioned router declares its FULL prefix (API_V1 + resource) and is included without a prefix,
so `route.path` — which the request logger records as `path_template` — is the complete route template."""

API_V1 = "/api/v1"
