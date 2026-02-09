"""Utility functions."""
import uuid


def generate_id() -> str:
    """Generate a UUID4 string for entity IDs."""
    return str(uuid.uuid4())
