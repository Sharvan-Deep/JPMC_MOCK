"""
ChromaDB Persistent Client & Collection Manager for Task 7.
Initializes and manages the local persistent ChromaDB client and single logical collection.
"""

from pathlib import Path
from typing import Optional
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from ai_service.config import Settings, get_settings
from ai_service.logging_config import logger


class ChromaDBManager:
    """Manages the lifecycle of the local persistent ChromaDB vector database."""

    _client_instance: Optional[ClientAPI] = None

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.storage_path = Path(self.settings.CHROMADB_STORAGE_PATH)
        self.collection_name = self.settings.CHROMADB_COLLECTION

    def get_client(self) -> ClientAPI:
        """Returns or initializes the singleton persistent ChromaDB client."""
        if ChromaDBManager._client_instance is None:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initializing persistent ChromaDB client at '{self.storage_path}'")
            ChromaDBManager._client_instance = chromadb.PersistentClient(
                path=str(self.storage_path.resolve())
            )
        return ChromaDBManager._client_instance

    def get_collection(self, name: Optional[str] = None) -> Collection:
        """
        Retrieves or creates the configured CSR documents collection.
        Uses cosine distance metric as default for semantic similarity search.
        """
        target_name = name or self.collection_name
        client = self.get_client()
        logger.info(f"Accessing ChromaDB collection '{target_name}'")
        return client.get_or_create_collection(
            name=target_name,
            metadata={"description": "Jaldhaara CSR document knowledge layer", "hnsw:space": "cosine"},
        )

    def reset_client_for_testing(self):
        """Resets the singleton client instance (used for test isolation)."""
        ChromaDBManager._client_instance = None
