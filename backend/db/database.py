
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd
import json
import asyncio
from contextlib import contextmanager
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent)) 
from backend.core.config import get_settings
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseConnection:
    _instance = None
    _engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the database connection"""
        self.settings = get_settings()
        self._create_engine()
        self.test_connection()

    def _create_engine(self) -> None:
        """Create SQLAlchemy engine for PostgreSQL"""
        if not self._engine:
            try:
                self._engine = create_engine(
                    self.settings.DATABASE_URL,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800
                )
                logger.info("Database engine created successfully")
            except Exception as e:
                logger.error(f"Error creating database engine: {str(e)}")
                raise

    # ============= Feedback Operations =============
    async def create_feedback(self, feedback_data: Dict) -> Optional[int]:
        """Create a new feedback entry"""
        try:
            query = """
            INSERT INTO feedback (
                severity, status, test_name, test_number, lot,
                insertion, initial_label, new_label, reference_id,
                input_id, created_at, updated_at
            ) VALUES (
                :severity, :status, :test_name, :test_number, :lot,
                :insertion, :initial_label, :new_label, :reference_id,
                :input_id, :created_at, :updated_at
            ) RETURNING id;
            """
            with self.get_connection() as conn:
                feedback_data.update({
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                result = conn.execute(text(query), feedback_data)
                return result.scalar()
        except Exception as e:
            logger.error(f"Error creating feedback: {str(e)}")
            return None

    async def update_feedback_status(self, feedback_id: int, status: str) -> bool:
        """Update feedback status"""
        try:
            query = """
            UPDATE feedback 
            SET status = :status, updated_at = :updated_at
            WHERE id = :feedback_id;
            """
            with self.get_connection() as conn:
                conn.execute(text(query), {
                    'status': status,
                    'updated_at': datetime.now(),
                    'feedback_id': feedback_id
                })
                return True
        except Exception as e:
            logger.error(f"Error updating feedback status: {str(e)}")
            return False

    async def get_pending_feedback(self) -> List[Dict]:
        """Get all pending feedback entries"""
        try:
            query = "SELECT * FROM feedback WHERE status = 'PENDING' ORDER BY created_at DESC"
            with self.get_connection() as conn:
                result = conn.execute(text(query))
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting pending feedback: {str(e)}")
            return []

    # ============= Input/Reference Data Operations =============
    async def save_input_data(self, input_data: Dict, measurements: List[Dict]) -> bool:
        """Save input data and its measurements"""
        try:
            with self.get_connection() as conn:
                # Insert input data
                input_query = """
                INSERT INTO input_data (
                    input_id, insertion, test_name, test_number,
                    lsl, usl, created_at
                ) VALUES (
                    :input_id, :insertion, :test_name, :test_number,
                    :lsl, :usl, :created_at
                );
                """
                conn.execute(text(input_query), {
                    **input_data,
                    'created_at': datetime.now()
                })

                # Insert measurements
                measurement_query = """
                INSERT INTO input_measurements (
                    input_id, chip_number, value
                ) VALUES (
                    :input_id, :chip_number, :value
                );
                """
                for measurement in measurements:
                    measurement['input_id'] = input_data['input_id']
                    conn.execute(text(measurement_query), measurement)

                return True
        except Exception as e:
            logger.error(f"Error saving input data: {str(e)}")
            return False

    async def save_reference_data(self, reference_data: Dict, measurements: List[Dict]) -> bool:
        """Save reference data and its measurements"""
        try:
            with self.get_connection() as conn:
                # Insert reference data
                ref_query = """
                INSERT INTO reference_data (
                    reference_id, product, lot, insertion, test_name,
                    test_number, lsl, usl, created_at
                ) VALUES (
                    :reference_id, :product, :lot, :insertion, :test_name,
                    :test_number, :lsl, :usl, :created_at
                );
                """
                conn.execute(text(ref_query), {
                    **reference_data,
                    'created_at': datetime.now()
                })

                # Insert measurements
                measurement_query = """
                INSERT INTO reference_measurements (
                    reference_id, chip_number, value
                ) VALUES (
                    :reference_id, :chip_number, :value
                );
                """
                for measurement in measurements:
                    measurement['reference_id'] = reference_data['reference_id']
                    conn.execute(text(measurement_query), measurement)

                return True
        except Exception as e:
            logger.error(f"Error saving reference data: {str(e)}")
            return False

    async def get_input_data_with_measurements(self, input_id: str) -> Optional[Dict]:
        """Get input data with all its measurements"""
        try:
            with self.get_connection() as conn:
                # Get input data
                input_query = "SELECT * FROM input_data WHERE input_id = :input_id"
                input_result = conn.execute(text(input_query), {'input_id': input_id})
                input_data = dict(input_result.fetchone())

                # Get measurements
                measurements_query = """
                SELECT chip_number, value 
                FROM input_measurements 
                WHERE input_id = :input_id 
                ORDER BY chip_number
                """
                measurements_result = conn.execute(text(measurements_query), {'input_id': input_id})
                measurements = [dict(row) for row in measurements_result]

                input_data['measurements'] = measurements
                return input_data
        except Exception as e:
            logger.error(f"Error getting input data: {str(e)}")
            return None

    # ============= Model Metrics Operations =============
    async def save_model_metrics(self, metrics_data: Dict) -> Optional[int]:
        """Save model training metrics"""
        try:
            query = """
            INSERT INTO model_metrics (
                accuracy, confidence, error_rate, model_version,
                model_path, training_reason, status, training_duration,
                created_at
            ) VALUES (
                :accuracy, :confidence, :error_rate, :model_version,
                :model_path, :training_reason, :status, :training_duration,
                :created_at
            ) RETURNING id;
            """
            with self.get_connection() as conn:
                metrics_data['created_at'] = datetime.now()
                result = conn.execute(text(query), metrics_data)
                return result.scalar()
        except Exception as e:
            logger.error(f"Error saving model metrics: {str(e)}")
            return None

    async def get_model_performance_history(self, limit: int = 10) -> List[Dict]:
        """Get model performance history"""
        try:
            query = """
            SELECT * FROM model_metrics 
            ORDER BY created_at DESC 
            LIMIT :limit
            """
            with self.get_connection() as conn:
                result = conn.execute(text(query), {'limit': limit})
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting model performance history: {str(e)}")
            return []

    # ============= Settings Operations =============
    async def get_model_settings(self) -> Optional[Dict]:
        """Get current model settings"""
        try:
            query = "SELECT * FROM model_settings ORDER BY created_at DESC LIMIT 1"
            with self.get_connection() as conn:
                result = conn.execute(text(query))
                row = result.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting model settings: {str(e)}")
            return None

    async def update_model_settings(self, settings_data: Dict) -> bool:
        """Update model settings"""
        try:
            query = """
            UPDATE model_settings SET
                confidence_threshold = :confidence_threshold,
                critical_issue_weight = :critical_issue_weight,
                high_priority_weight = :high_priority_weight,
                normal_priority_weight = :normal_priority_weight,
                auto_retrain = :auto_retrain,
                retraining_schedule = :retraining_schedule,
                updated_at = :updated_at
            WHERE id = :id;
            """
            with self.get_connection() as conn:
                settings_data['updated_at'] = datetime.now()
                conn.execute(text(query), settings_data)
                return True
        except Exception as e:
            logger.error(f"Error updating model settings: {str(e)}")
            return False

    # ============= API Logging Operations =============
    async def log_api_request(self, log_data: Dict) -> None:
        """Log API request"""
        try:
            query = """
            INSERT INTO api_logs (
                endpoint, method, status_code, response_time, created_at
            ) VALUES (
                :endpoint, :method, :status_code, :response_time, :created_at
            );
            """
            with self.get_connection() as conn:
                log_data['created_at'] = datetime.now()
                conn.execute(text(query), log_data)
        except Exception as e:
            logger.error(f"Error logging API request: {str(e)}")

    async def get_api_metrics(self, days: int = 7) -> Dict:
        """Get API usage metrics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_requests,
                AVG(response_time) as avg_response_time,
                COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
            FROM api_logs
            WHERE created_at >= NOW() - INTERVAL ':days days'
            """
            with self.get_connection() as conn:
                result = conn.execute(text(query), {'days': days})
                return dict(result.fetchone())
        except Exception as e:
            logger.error(f"Error getting API metrics: {str(e)}")
            return {}

    # ============= Utility Methods =============
    def execute_sql(self, sql: str, params: Optional[Dict] = None) -> bool:
        """Execute a single SQL statement with logging"""
        try:
            with self.get_connection() as conn:
                if params:
                    conn.execute(text(sql), params)
                else:
                    conn.execute(text(sql))
            return True
        except Exception as e:
            logger.error(f"Error executing SQL:\n{sql}\nError: {str(e)}")
            return False

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a query and return results as a list of dictionaries"""
        try:
            def _execute():
                with self.get_connection() as conn:
                    if params:
                        result = conn.execute(text(query), params)
                    else:
                        result = conn.execute(text(query))
                    
                    # Get column names
                    columns = result.keys()
                    
                    # Convert each row to a dictionary using column names
                    return [
                        {col: getattr(row, col) for col in columns}
                        for row in result
                    ]

            # Run the synchronous SQLAlchemy code in a thread pool
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _execute)
            
            # Process datetime objects to ISO format strings
            for row in result:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    elif value is None:
                        row[key] = None

            return result

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []

    def _process_params(self, params: Dict) -> Dict:
        """Process parameters for SQL query"""
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, (dict, list)):
                processed_params[key] = json.dumps(value)
            else:
                processed_params[key] = value
        return processed_params

    async def get_reference_data_list(self) -> List[Dict]:
        """Get list of all reference data"""
        try:
            query = """
                SELECT 
                    reference_id,
                    product,
                    lot,
                    insertion,
                    test_name,
                    test_number,
                    CAST(lsl AS FLOAT) as lsl,
                    CAST(usl AS FLOAT) as usl,
                    created_at::timestamp
                FROM reference_data
                ORDER BY created_at DESC
            """
            return await self.execute_query(query)
            
        except Exception as e:
            logger.error(f"Error getting reference data list: {str(e)}")
            return []

    async def get_reference_data_with_measurements(self, reference_id: str) -> Optional[Dict]:
        """Get reference data with its measurements"""
        try:
            # Get reference data
            ref_query = """
                SELECT * FROM reference_data 
                WHERE reference_id = :reference_id
            """
            ref_data = await self.execute_query(ref_query, {'reference_id': reference_id})
            
            if not ref_data:
                return None
                
            # Get measurements
            meas_query = """
                SELECT chip_number, value 
                FROM reference_measurements 
                WHERE reference_id = :reference_id 
                ORDER BY chip_number
            """
            measurements = await self.execute_query(meas_query, {'reference_id': reference_id})
            
            # Combine results
            result = ref_data[0]
            result['measurements'] = measurements
            return result
            
        except Exception as e:
            logger.error(f"Error getting reference data with measurements: {str(e)}")
            return None
        
    def _process_json_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process JSON columns in DataFrame"""
        for column in df.columns:
            if df[column].dtype == 'object':
                try:
                    df[column] = df[column].apply(
                        lambda x: json.loads(x) if isinstance(x, str) else x
                    )
                except:
                    pass
        return df

    def initialize_tables(self) -> bool:
        """Initialize database tables"""
        try:
            # Using Path for better file path handling
            init_sql_path = Path(__file__).parent / 'migrations' / 'init.sql'
            logger.info(f"Looking for SQL file at: {init_sql_path}")
            
            if not init_sql_path.exists():
                logger.error(f"SQL initialization file not found at: {init_sql_path}")
                return False
                
            logger.info("Reading SQL file...")
            with open(init_sql_path, 'r') as f:
                sql_content = f.read()

            # Split the SQL file into individual statements
            sql_statements = self._split_sql_statements(sql_content)
            logger.info(f"Found {len(sql_statements)} SQL statements to execute")

            with self.get_connection() as conn:
                for statement in sql_statements:
                    if statement.strip():
                        try:
                            conn.execute(text(statement))
                        except Exception as e:
                            logger.error(f"Error executing SQL statement: {str(e)}\nStatement: {statement}")
                            raise

            logger.info("Database tables initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize tables: {str(e)}")
            return False

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        statements = []
        current_statement = []
        in_function = False
        in_comment = False
        
        for line in sql_content.split('\n'):
            # Handle multi-line comments
            if '/*' in line and '*/' not in line:
                in_comment = True
                continue
            if '*/' in line:
                in_comment = False
                continue
            if in_comment or line.strip().startswith('--'):
                continue

            # Handle function/procedure definitions
            if 'CREATE OR REPLACE FUNCTION' in line or 'DO $$' in line:
                in_function = True
                
            if in_function:
                current_statement.append(line)
                if line.strip().endswith('LANGUAGE plpgsql;') or line.strip().endswith('END $$;'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []
                    in_function = False
            else:
                current_statement.append(line)
                if line.strip().endswith(';'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []

        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))

        return [stmt.strip() for stmt in statements if stmt.strip()]

    @contextmanager
    def get_connection(self):
        """Get a connection from the connection pool with error handling"""
        if not self._engine:
            self._create_engine()
        
        conn = None
        try:
            conn = self._engine.connect()
            # Start a transaction
            trans = conn.begin()
            try:
                yield conn
                # Commit the transaction
                trans.commit()
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise
        except Exception as e:
            logger.error(f"Error getting database connection: {str(e)}")
            raise
        finally:
            if conn is not None:
                conn.close()

    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            with self.get_connection() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """Check database health status"""
        try:
            with self.get_connection() as conn:
                start_time = asyncio.get_event_loop().time()
                conn.execute(text("SELECT 1"))
                end_time = asyncio.get_event_loop().time()
                
                # Get pool statistics
                pool_size = self._engine.pool.size()
                checked_out = len(self._engine._connection_cls._connection_records) - pool_size
                
                return {
                    "status": "healthy",
                    "latency_ms": round((end_time - start_time) * 1000, 2),
                    "connection_pool": {
                        "size": pool_size,
                        "checked_out": checked_out,
                        "available": pool_size - checked_out
                    },
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def cleanup(self):
        """Cleanup database connections"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections cleaned up")

    def __del__(self):
        """Destructor to ensure cleanup"""
        if self._engine:
            self._engine.dispose()

    # Additional utility methods
    async def get_table_stats(self) -> Dict[str, Dict]:
        """Get statistics for all tables"""
        try:
            query = """
            SELECT 
                schemaname,
                relname as table_name,
                n_live_tup as row_count,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size
            FROM pg_stat_user_tables
            WHERE schemaname = 'public';
            """
            with self.get_connection() as conn:
                result = conn.execute(text(query))
                return {
                    row.table_name: {
                        'schema': row.schemaname,
                        'row_count': row.row_count,
                        'total_size': row.total_size
                    }
                    for row in result
                }
        except Exception as e:
            logger.error(f"Error getting table statistics: {str(e)}")
            return {}
    
    async def update_reference_data(self, reference_id: str, update_data: Dict) -> bool:
        """Update reference data with training information for VAMOS"""
        try:
            # Build update query dynamically based on provided fields
            update_fields = []
            params = {"reference_id": reference_id}
            
            # Handle each possible field
            if "used_for_training" in update_data:
                update_fields.append("used_for_training = :used_for_training")
                params["used_for_training"] = update_data["used_for_training"]
            
            if "training_version" in update_data:
                update_fields.append("training_version = :training_version")
                params["training_version"] = update_data["training_version"]
            
            if "distribution_hash" in update_data:
                update_fields.append("distribution_hash = :distribution_hash")
                params["distribution_hash"] = update_data["distribution_hash"]
            
            if "quality_score" in update_data:
                update_fields.append("quality_score = :quality_score")
                params["quality_score"] = update_data["quality_score"]
            
            if not update_fields:
                logger.warning("No valid fields to update for reference data")
                return False
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            # Build final query
            query = f"""
                UPDATE reference_data 
                SET {', '.join(update_fields)}
                WHERE reference_id = :reference_id
            """
            
            # Execute using existing connection method
            with self.get_connection() as conn:
                result = conn.execute(text(query), params)
                # Check if any row was updated
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating reference data: {str(e)}")
            return False

    def execute_query_sync(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Synchronous wrapper for execute_query - use only when necessary"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.execute_query(query, params))
                    return future.result()
            else:
                return loop.run_until_complete(self.execute_query(query, params))
        except Exception as e:
            logger.error(f"Error in sync query execution: {e}")
            return []