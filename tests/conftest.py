"""Fixtures for the Grill tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load Grill Assistant from custom_components."""
    return
