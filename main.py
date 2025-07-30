import os
import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.vehicle import db, Vehicle, VehicleHistory
from src.routes.scraper_routes import scraper_bp
from src.routes.vehicle import vehicle_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'src', 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

app.register_blueprint(vehicle_bp, url_prefix='/api')
app.register_blueprint(scraper_bp, url_prefix='/api')

# Configuração do Banco de Dados para funcionar no Render e localmente
db_path_on_render = '/var/data/app.db'
local_db_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

if os.path.exists('/var/data'):
    # Estamos no ambiente do Render, que cria a pasta /var/data
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path_on_render}"
else:
    # Estamos rodando localmente, crie a pasta 'database' se necessário
    os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{local_db_path}"


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
