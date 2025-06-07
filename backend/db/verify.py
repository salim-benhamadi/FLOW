import logging
from database import DatabaseConnection
from sqlalchemy import text
import sys
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def init_database():
    """Initialize the database with tables and default settings"""
    logger.info("Starting database initialization...")
    
    try:
        logger.info("Establishing database connection...")
        db = DatabaseConnection()
        
        # Initialize tables
        logger.info("Initializing database tables...")
        if not db.initialize_tables():
            logger.error("Failed to initialize tables")
            return False
        
        logger.info("Tables initialized successfully")
        return True
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = init_database()
    if not success:
        sys.exit(1)