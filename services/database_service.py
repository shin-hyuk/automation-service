"""
Database service for Gary Wealth Data API
Handles all Supabase database operations
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from supabase import create_client, Client
from config.settings import config

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client lazily"""
        if self._initialized:
            return
            
        try:
            # Validate configuration
            config.validate_required_config()
            
            # Create Supabase client
            self.client = create_client(config.supabase_url, config.supabase_key)
            self._initialized = True
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    def insert_wealth_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert wealth data into the database
        
        Args:
            data: Complete JSON payload to store
            
        Returns:
            Dictionary containing the inserted record information
            
        Raises:
            Exception: If database operation fails
        """
        # Initialize client if not done yet
        self._initialize_client()
        
        if not self.client:
            raise Exception("Database client not initialized")
        
        try:
            # Prepare record with current timestamp
            current_timestamp = datetime.now(timezone.utc).isoformat()
            
            db_record = {
                'date': current_timestamp,
                'data': data
            }
            
            # Insert into database
            result = self.client.table('utgl_gary_wealth_records').insert(db_record).execute()
            
            if not result.data:
                raise Exception("No data returned from insert operation")
            
            inserted_record = result.data[0]
            logger.info(f"Successfully inserted wealth data record at: {inserted_record.get('date')}")
            
            return {
                'success': True,
                'inserted_at': inserted_record.get('date'),
                'record': inserted_record
            }
            
        except Exception as e:
            logger.error(f"Database insert operation failed: {str(e)}")
            raise Exception(f"Failed to store wealth data: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a basic health check on the database connection
        
        Returns:
            Dictionary with health status
        """
        try:
            # Initialize client if not done yet
            self._initialize_client()
            
            if not self.client:
                return {'healthy': False, 'error': 'Client not initialized'}
            
            # Simple query to test connection
            result = self.client.table('utgl_gary_wealth_records').select('count').limit(1).execute()
            
            return {
                'healthy': True,
                'connection': 'active',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

# Global database service instance
db_service = DatabaseService()
