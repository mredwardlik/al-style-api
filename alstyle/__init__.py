"""A client and a command line tool for the Al-Style dealer API."""

from .client import DEFAULT_URL, ApiError, Client

__version__ = '2.0.0'

__all__ = ['DEFAULT_URL', 'ApiError', 'Client']
