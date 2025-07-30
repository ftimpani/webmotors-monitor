from flask import Blueprint, request, jsonify
from src.models.vehicle import db, Vehicle, VehicleHistory
from datetime import datetime, timedelta
import json

vehicle_bp = Blueprint('vehicle', __name__)

@vehicle_bp.route('/vehicles', methods=['GET'])
def get_vehicles():
    """Obter lista de veículos com filtros opcionais"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', 'active')
    brand = request.args.get('brand')
    model = request.args.get('model')

    query = Vehicle.query

    if status:
        query = query.filter(Vehicle.status == status)
    if brand:
        query = query.filter(Vehicle.brand.ilike(f'%{brand}%'))
    if model:
        query = query.filter(Vehicle.model.ilike(f'%{model}%'))

    vehicles = query.order_by(Vehicle.last_seen.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'vehicles': [vehicle.to_dict() for vehicle in vehicles.items],
        'total': vehicles.total,
        'pages': vehicles.pages,
        'current_page': page
    })

@vehicle_bp.route('/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle(vehicle_id):
    """Obter detalhes de um veículo específico"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    return jsonify(vehicle.to_dict())

@vehicle_bp.route('/vehicles/recent', methods=['GET'])
def get_recent_vehicles():
    """Obter veículos adicionados recentemente (últimas 24 horas)"""
    since = datetime.utcnow() - timedelta(hours=24)
    vehicles = Vehicle.query.filter(
        Vehicle.first_seen >= since,
        Vehicle.status == 'active'
    ).order_by(Vehicle.first_seen.desc()).limit(50).all()

    return jsonify([vehicle.to_dict() for vehicle in vehicles])

@vehicle_bp.route('/vehicles/removed', methods=['GET'])
def get_removed_vehicles():
    """Obter veículos removidos recentemente (últimas 24 horas)"""
    since = datetime.utcnow() - timedelta(hours=24)
    vehicles = Vehicle.query.filter(
        Vehicle.updated_at >= since,
        Vehicle.status.in_(['sold', 'removed'])
    ).order_by(Vehicle.updated_at.desc()).limit(50).all()

    return jsonify([vehicle.to_dict() for vehicle in vehicles])

@vehicle_bp.route('/vehicles/stats', methods=['GET'])
def get_stats():
    """Obter estatísticas do sistema"""
    total_active = Vehicle.query.filter(Vehicle.status == 'active').count()
    total_sold = Vehicle.query.filter(Vehicle.status == 'sold').count()
    total_removed = Vehicle.query.filter(Vehicle.status == 'removed').count()

    # Veículos adicionados nas últimas 24 horas
    since_24h = datetime.utcnow() - timedelta(hours=24)
    added_24h = Vehicle.query.filter(Vehicle.first_seen >= since_24h).count()

    # Veículos removidos nas últimas 24 horas
    removed_24h = Vehicle.query.filter(
        Vehicle.updated_at >= since_24h,
        Vehicle.status.in_(['sold', 'removed'])
    ).count()

    return jsonify({
        'total_active': total_active,
        'total_sold': total_sold,
        'total_removed': total_removed,
        'added_last_24h': added_24h,
        'removed_last_24h': removed_24h
    })

@vehicle_bp.route('/vehicles/history/<int:vehicle_id>', methods=['GET'])
def get_vehicle_history(vehicle_id):
    """Obter histórico de um veículo específico"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    history = VehicleHistory.query.filter(
        VehicleHistory.vehicle_id == vehicle_id
    ).order_by(VehicleHistory.timestamp.desc()).all()

    return jsonify([h.to_dict() for h in history])

@vehicle_bp.route('/vehicles/search', methods=['GET'])
def search_vehicles():
    """Buscar veículos por termo"""
    query_term = request.args.get('q', '')
    if not query_term:
        return jsonify({'error': 'Query parameter q is required'}), 400

    vehicles = Vehicle.query.filter(
        Vehicle.title.ilike(f'%{query_term}%') |
        Vehicle.brand.ilike(f'%{query_term}%') |
        Vehicle.model.ilike(f'%{query_term}%')
    ).filter(Vehicle.status == 'active').limit(50).all()

    return jsonify([vehicle.to_dict() for vehicle in vehicles])