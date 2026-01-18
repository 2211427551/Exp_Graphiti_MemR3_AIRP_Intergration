"""
Neo4j initialization script for AIRP Memory System.
Tests Neo4j connection and initializes Graphiti indices.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.services.memory.graphiti_client import GraphitiClient

configure_logging()
logger = get_logger(__name__)


async def main():
    """Initialize Neo4j and build Graphiti indices."""
    logger.info("Starting Neo4j initialization")

    try:
        # Create Graphiti client
        client = GraphitiClient()

        # Initialize connection
        await client.initialize()

        logger.info("Neo4j initialization successful")
        logger.info(f"Neo4j URI: {settings.neo4j_uri}")
        logger.info(f"Database: {settings.neo4j_database}")

        # Close connection
        await client.close()

    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
