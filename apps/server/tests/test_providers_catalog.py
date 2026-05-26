from __future__ import annotations

from api.providers.catalog import PRESETS, list_presets
from api.providers.models import PRESET_KINDS


def test_provider_catalog_has_14_presets():
    assert len(PRESETS) == 14
    assert tuple(PRESETS.keys()) == PRESET_KINDS
    assert {p.kind for p in list_presets()} == set(PRESET_KINDS)
    for preset in list_presets():
        assert preset.label
        assert preset.base_url.startswith(("http://", "https://"))
        assert preset.auth_type in {"bearer", "oauth", "none"}
