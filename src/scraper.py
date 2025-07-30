import time
import random
import json
import logging
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.models.vehicle import db, Vehicle, VehicleHistory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebMotorsScraper:
    def __init__(self):
        self.base_url = "https://www.webmotors.com.br"

        # --- Configuração do Selenium ---
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Roda o Chrome sem abrir uma janela visual
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        logger.info("Iniciando o driver do Selenium...")
        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Driver do Selenium iniciado com sucesso.")
        # --- Fim da Configuração do Selenium ---

    def get_vehicle_listings(self, page=1, max_pages=2): # Reduzido para 2 para testes mais rápidos
        """
        Obter listagens de veículos usando Selenium para renderizar a página.
        """
        vehicles = []
        for page_num in range(1, max_pages + 1):
            try:
                url = f"{self.base_url}/carros-usados/estoque?page={page_num}"
                logger.info(f"Acessando página {page_num} com Selenium: {url}")

                self.driver.get(url)

                # Espera até que os cards dos veículos estejam presentes na página (até 15 segundos)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='vehicle-card']"))
                )

                # Pega o HTML da página DEPOIS que o JavaScript rodou
                page_html = self.driver.page_source
                soup = BeautifulSoup(page_html, 'html.parser')

                vehicle_elements = soup.find_all('div', attrs={'data-testid': 'vehicle-card'})

                if not vehicle_elements:
                    logger.warning(f"Nenhum card de veículo encontrado na página {page_num}.")
                    break

                for element in vehicle_elements:
                    vehicle_data = self.extract_vehicle_data(element)
                    if vehicle_data:
                        vehicles.append(vehicle_data)

                logger.info(f"Encontrados {len(vehicle_elements)} veículos na página {page_num}.")
                time.sleep(random.uniform(2, 4)) # Pausa para não sobrecarregar o site

            except Exception as e:
                logger.error(f"Erro ao raspar dados da página {page_num}: {e}")
                break

        return vehicles

    def close_driver(self):
        """Fecha o navegador do Selenium."""
        if self.driver:
            self.driver.quit()
            logger.info("Driver do Selenium fechado.")

    # Os métodos abaixo (extract_vehicle_data, save_vehicles_to_db, etc.) continuam os mesmos
    # pois eles operam nos dados já coletados, não na forma de coletar.

    def extract_vehicle_data(self, element):
        try:
            title_elem = element.find('h2') or element.find('h3')
            title = title_elem.get_text(strip=True) if title_elem else 'N/A'

            price_elem = element.find('strong', attrs={'data-testid': 'price-value'})
            price = price_elem.get_text(strip=True) if price_elem else 'N/A'

            link_elem = element.find('a', href=True)
            url = urljoin(self.base_url, link_elem['href']) if link_elem else None

            webmotors_id = self.extract_id_from_url(url) if url else None
            if not webmotors_id:
                return None

            details = self.extract_additional_details(element)

            return {
                'webmotors_id': webmotors_id, 'title': title, 'price': price,
                'url': url, 'brand': details.get('brand'), 'model': details.get('model'),
                'year': details.get('year'), 'mileage': details.get('mileage'),
                'fuel_type': details.get('fuel_type'), 'transmission': details.get('transmission'),
                'location': details.get('location')
            }
        except Exception as e:
            logger.error(f"Erro ao extrair dados de um veículo: {e}")
            return None

    def extract_additional_details(self, element):
        details = {}
        try:
            info_list = element.find('div', attrs={'data-testid': 'vehicle-specifics'})
            if info_list:
                items = info_list.find_all('span')
                if len(items) > 0: details['year'] = items[0].get_text(strip=True)
                if len(items) > 1: details['mileage'] = items[1].get_text(strip=True)

            location_elem = element.find('p', attrs={'data-testid': 'vehicle-location'})
            if location_elem:
                details['location'] = location_elem.get_text(strip=True)

        except Exception as e:
            logger.error(f"Erro ao extrair detalhes adicionais: {e}")
        return details

    def extract_id_from_url(self, url):
        if not url: return None
        try:
            parts = url.strip('/').split('/')
            for part in reversed(parts):
                if part.isdigit():
                    return part
        except Exception as e:
            logger.error(f"Erro ao extrair ID da URL {url}: {e}")
        return None

    def save_vehicles_to_db(self, vehicles_data):
        new_vehicles = 0
        updated_vehicles = 0
        for vehicle_data in vehicles_data:
            try:
                existing_vehicle = Vehicle.query.filter_by(webmotors_id=vehicle_data['webmotors_id']).first()
                if existing_vehicle:
                    changes = {}
                    for key, value in vehicle_data.items():
                        if key not in ['webmotors_id', 'url'] and getattr(existing_vehicle, key) != value:
                            changes[key] = {'old': getattr(existing_vehicle, key), 'new': value}
                            setattr(existing_vehicle, key, value)
                    existing_vehicle.last_seen = datetime.utcnow()
                    existing_vehicle.updated_at = datetime.utcnow()
                    if changes:
                        history = VehicleHistory(vehicle_id=existing_vehicle.id, action='updated', changes=json.dumps(changes))
                        db.session.add(history)
                        updated_vehicles += 1
                else:
                    new_vehicle = Vehicle(**vehicle_data)
                    db.session.add(new_vehicle)
                    db.session.flush()
                    history = VehicleHistory(vehicle_id=new_vehicle.id, action='added', changes=json.dumps(vehicle_data))
                    db.session.add(history)
                    new_vehicles += 1
            except Exception as e:
                logger.error(f"Erro ao salvar veículo {vehicle_data.get('webmotors_id')}: {e}")
                continue
        try:
            db.session.commit()
            logger.info(f"Salvos {new_vehicles} novos veículos e atualizados {updated_vehicles} veículos.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao commitar no banco de dados: {e}")
        return new_vehicles, updated_vehicles

    def mark_missing_vehicles_as_removed(self, current_ids):
        try:
            missing_vehicles = Vehicle.query.filter(Vehicle.status == 'active', ~Vehicle.webmotors_id.in_(current_ids)).all()
            removed_count = 0
            for vehicle in missing_vehicles:
                vehicle.status = 'removed'
                vehicle.updated_at = datetime.utcnow()
                history = VehicleHistory(vehicle_id=vehicle.id, action='removed', changes=json.dumps({'status': {'old': 'active', 'new': 'removed'}}))
                db.session.add(history)
                removed_count += 1
            db.session.commit()
            logger.info(f"Marcados {removed_count} veículos como removidos.")
            return removed_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao marcar veículos como removidos: {e}")
            return 0

    def run_scraping_cycle(self):
        logger.info("Iniciando ciclo de scraping com Selenium.")
        try:
            vehicles_data = self.get_vehicle_listings()
            if not vehicles_data:
                logger.warning("Nenhum veículo encontrado durante o scraping.")
                return
            new_count, updated_count = self.save_vehicles_to_db(vehicles_data)
            current_ids = [v['webmotors_id'] for v in vehicles_data if v.get('webmotors_id')]
            removed_count = self.mark_missing_vehicles_as_removed(current_ids)
            logger.info(f"Ciclo de scraping concluído: {new_count} novos, {updated_count} atualizados, {removed_count} removidos.")
        except Exception as e:
            logger.error(f"Erro no ciclo de scraping: {e}")
        finally:
            # Garante que o navegador seja sempre fechado ao final
            self.close_driver()