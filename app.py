"""
Automation Service API
A comprehensive automation service for collecting, processing, and storing financial data
"""
import logging
import os
from flask import Flask, jsonify
from dotenv import load_dotenv

# Import routes
from routes.healthy import health_bp
from routes.gary_wealth import wealth_bp
from config.settings import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_app() -> Flask:
    """
    Application factory pattern for creating Flask app
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Configure app
    app.config['DEBUG'] = config.debug
    app.config['ENV'] = config.environment
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(wealth_bp)
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'available_endpoints': {
                'health_checks': [
                    '/health (GET)'
                ],
                'wealth_data': [
                    '/utgl-gary-wealth-data (POST)',
                    '/utgl-gary-wealth-data (GET) - endpoint info'
                ]
            },
            'api_version': '1.0.0'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method not allowed',
            'message': 'Check the HTTP method and endpoint combination'
        }), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

    # Add root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'service': 'Automation Service',
            'version': '1.0.0',
            'description': 'Comprehensive automation service for financial data collection and processing',
            'current_projects': {
                'gary_wealth': '/utgl-gary-wealth-data'
            },
            'endpoints': {
                'health': '/health',
                'data_collection': 'Various endpoints as we scale'
            },
            'note': 'More endpoints will be added for different data types'
        }), 200
    
    logger.info(f"Automation Service initialized in {config.environment} mode")
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Validate configuration
    try:
        config.validate_required_config()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        exit(1)
    
    # Run the application
    logger.info(f"Starting Automation Service on port {config.port}")
    app.run(
        host='0.0.0.0',
        port=config.port,
        debug=config.debug
    )
