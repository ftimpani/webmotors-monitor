from flask import Blueprint, jsonify, request
from src.scraper import WebMotorsScraper
import threading
import logging
from datetime import datetime

scraper_bp = Blueprint('scraper', __name__)
logger = logging.getLogger(__name__)

# Global variable to track scraping status
scraping_status = {
    'is_running': False,
    'last_run': None,
    'last_result': None
}

@scraper_bp.route('/scraper/status', methods=['GET'])
def get_scraper_status():
    """Obter status do scraper"""
    return jsonify(scraping_status)

@scraper_bp.route('/scraper/run', methods=['POST'])
def run_scraper():
    """Executar scraping manualmente"""
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraper is already running'}), 400

    def run_scraping():
        try:
            scraping_status['is_running'] = True
            scraper = WebMotorsScraper()
            scraper.run_scraping_cycle()
            scraping_status['last_result'] = 'success'
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            scraping_status['last_result'] = f'error: {str(e)}'
        finally:
            scraping_status['is_running'] = False
            scraping_status['last_run'] = datetime.utcnow().isoformat()

    # Run scraping in a separate thread
    thread = threading.Thread(target=run_scraping)
    thread.start()

    return jsonify({'message': 'Scraping started'})