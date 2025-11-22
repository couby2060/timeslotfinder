"""
Adapters layer - External integrations (Microsoft Graph API).
"""

from .graph_client import GraphClient
from .graph_authenticator import GraphAuthenticator
from .mock_graph_client import MockGraphClient, MockGraphAuthenticator

__all__ = ["GraphClient", "GraphAuthenticator", "MockGraphClient", "MockGraphAuthenticator"]

