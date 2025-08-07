"""
Gary wealth data routes (first project for Data Collector API)
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime
from services.database_service import db_service

logger = logging.getLogger(__name__)

wealth_bp = Blueprint('wealth', __name__)

@wealth_bp.route('/utgl-gary-wealth-data', methods=['POST'])
def submit_wealth_data():
    """
    Endpoint to accept JSON input for UTGL Gary wealth data and store in database
    
    Expected JSON format:
    {
        "client_id": "string",
        "wealth_data": {
            "assets": "number",
            "liabilities": "number",
            "net_worth": "number",
            "investment_portfolio": "object",
            "timestamp": "string"
        }
    }
    """
    try:
        # Validate request content type
        if not request.is_json:
            logger.warning("Request received with invalid content type")
            return jsonify({
                'error': 'Content-Type must be application/json'
            }), 400
        
        # Get JSON data from request
        data = request.get_json()
        
        # Basic validation
        if not data:
            logger.warning("Empty JSON data received")
            return jsonify({
                'error': 'No JSON data provided'
            }), 400
        
        # Log the received data (be careful about logging sensitive data in production)
        client_id = data.get('client_id', 'unknown')
        logger.info(f"Received UTGL Gary wealth data for client: {client_id}")
        
        # Validate required fields
        required_fields = ['client_id', 'wealth_data']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return jsonify({
                'error': f'Missing required fields: {missing_fields}'
            }), 400
        
        # Store data using database service
        try:
            result = db_service.insert_wealth_data(data)
            
            # Prepare success response
            response = {
                'status': 'success',
                'message': 'UTGL Gary wealth data received and stored successfully',
                'inserted_at': result['inserted_at'],
                'client_id': client_id,
                'processed_at': datetime.utcnow().isoformat(),
                'data_summary': {
                    'total_fields': len(data),
                    'wealth_data_fields': len(data.get('wealth_data', {}))
                }
            }
            
            logger.info(f"Successfully processed wealth data for client: {client_id}")
            return jsonify(response), 200
            
        except Exception as db_error:
            logger.error(f"Database operation failed for client {client_id}: {str(db_error)}")
            return jsonify({
                'error': 'Database operation failed',
                'message': str(db_error)
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error processing wealth data: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to process wealth data'
        }), 500

@wealth_bp.route('/utgl-gary-wealth-data', methods=['GET'])
def wealth_data_info():
    """GET endpoint to provide information about the wealth data submission endpoint"""
    return jsonify({
        'endpoint': '/utgl-gary-wealth-data',
        'method': 'POST',
        'description': 'Submit UTGL Gary wealth data',
        'content_type': 'application/json',
        'required_fields': ['client_id', 'wealth_data'],
        'example_payload': {
            'client_id': 'GARY001',
            'wealth_data': {
                'assets': 1500000,
                'liabilities': 200000,
                'net_worth': 1300000,
                'investment_portfolio': {
                    'stocks': 800000,
                    'bonds': 300000,
                    'real_estate': 400000
                },
                'timestamp': '2024-01-15T10:30:00Z'
            }
        }
    }), 200
