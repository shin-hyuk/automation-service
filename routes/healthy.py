"""
Simple health check for Data Collector API
"""
from flask import Blueprint, jsonify
from datetime import datetime
from services.database_service import db_service

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    try:
        # Get database health status
        db_health = db_service.health_check()
        
        # Overall health status
        overall_health = db_health.get('healthy', False)
        
        response = {
            'status': 'healthy' if overall_health else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'data-collector-api',
            'database': 'connected' if overall_health else 'disconnected'
        }
        
        status_code = 200 if overall_health else 503
        return jsonify(response), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'data-collector-api',
            'error': str(e)
        }), 503
