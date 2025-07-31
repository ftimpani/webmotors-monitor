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

# --- Configuração do Banco de Dados para PostgreSQL ---
# Pega a URL do banco de dados da variável de ambiente que o Render vai criar.
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # O Render usa "postgres://" mas o SQLAlchemy espera "postgresql://"
    # Esta linha faz a conversão automática.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Aviso caso a variável de ambiente não seja encontrada.
    print("ATENÇÃO: A variável DATABASE_URL não foi encontrada. O banco de dados não está configurado.")
# --- Fim da Configuração ---

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
