import logging
from sqlalchemy import text
import sys
from pathlib import Path
from database import DatabaseConnection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
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
        
        # Verify table creation and default data
        if verify_tables():
            logger.info("Database initialization completed successfully")
            return True
        else:
            logger.error("Table verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def verify_tables():
    """Verify that all required tables exist and have the correct structure"""
    logger.info("Verifying database tables...")
    db = DatabaseConnection()
    
    required_tables = [
        'feedback',
        'input_data',
        'input_measurements',
        'reference_data',
        'reference_measurements',
        'model_metrics',
        'api_logs',
        'training',
        'model_settings'
    ]
    
    try:
        with db.get_connection() as conn:
            # Check each table
            for table in required_tables:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """), {"table_name": table}).scalar()
                
                if result:
                    logger.info(f"Table '{table}' exists")
                    # Get row count
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"Table '{table}' has {count} rows")
                else:
                    logger.error(f"Table '{table}' does not exist")
                    return False
            
            # Verify model_settings has default values
            settings_count = conn.execute(text(
                "SELECT COUNT(*) FROM model_settings"
            )).scalar()
            
            if settings_count == 0:
                logger.warning("No default settings found in model_settings")
                return False
                
            logger.info("All tables verified successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying tables: {str(e)}")
        return False

def verify_database_health():
    """Verify database health and connectivity"""
    logger.info("Verifying database health...")
    db = DatabaseConnection()
    
    try:
        with db.get_connection() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database health check passed")
            return True
    except Exception as e:
        logger.error(f"Error checking database health: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database initialization process...")
    
    # First check database health
    if verify_database_health():
        # Then initialize the database
        if init_database():
            logger.info("Database initialization completed successfully")
        else:
            logger.error("Database initialization failed")
            sys.exit(1)
    else:
        logger.error("Database health check failed")
        sys.exit(1)