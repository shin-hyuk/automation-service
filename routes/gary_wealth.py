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
        logger.info(f"Received raw JSON data with {len(data)} fields")
        
        # No field validation - accept any raw JSON data
        
        # Store data using database service
        try:
            result = db_service.insert_wealth_data(data)
            
            # Prepare success response
            response = {
                'status': 'success',
                'message': 'Raw JSON data received and stored successfully',
                'inserted_at': result['inserted_at'],
                'processed_at': datetime.utcnow().isoformat(),
                'data_summary': {
                    'total_fields': len(data)
                }
            }
            
            logger.info(f"Successfully processed raw JSON data")
            return jsonify(response), 200
            
        except Exception as db_error:
            logger.error(f"Database operation failed: {str(db_error)}")
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
        'description': 'Submit UTGL Gary wealth data - accepts any raw JSON',
        'content_type': 'application/json',
        'required_fields': 'None - accepts any JSON structure',
        'example_payload': {
            'userId': '1686e05d-8170-4760-8b3e-6eafeda51a8e',
            'accountId': '002-022-0692409',
            'balances': {
                'BTC': 9.999962,
                'ETH': 274.5007128797566,
                'HKD': 72193472.43
            },
            'positions': {},
            'orders': []
        }
    }), 200
