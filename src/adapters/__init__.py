"""
Adapters layer - External integrations (Microsoft Graph API).
"""

from .graph_client import GraphClient
from .graph_authenticator import GraphAuthenticator

__all__ = ["GraphClient", "GraphAuthenticator"]

