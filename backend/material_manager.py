"""
Material Management Endpoints
"""

from flask import Flask, request, jsonify
import json
import os

def add_material_routes(app, config_path='config/materials_config.json'):
    """Add material management routes to Flask app"""
    
    @app.route('/api/materials/manage', methods=['GET'])
    def get_all_materials_detail():
        """Get all materials with full configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify({'success': True, 'materials': config['materials']})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/materials/manage', methods=['POST'])
    def add_material():
        """Add a new material"""
        try:
            data = request.json
            material_name = data.get('name')
            material_config = data.get('config')
            
            if not material_name or not material_config:
                return jsonify({'success': False, 'error': 'Missing name or config'}), 400
            
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Check if material already exists
            if material_name in config['materials']:
                return jsonify({'success': False, 'error': 'Material already exists'}), 400
            
            # Add new material
            config['materials'][material_name] = material_config
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'Material added successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/materials/manage/<material_name>', methods=['PUT'])
    def update_material(material_name):
        """Update an existing material"""
        try:
            material_config = request.json
            
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Check if material exists
            if material_name not in config['materials']:
                return jsonify({'success': False, 'error': 'Material not found'}), 404
            
            # Update material
            config['materials'][material_name] = material_config
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'Material updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/materials/manage/<material_name>', methods=['DELETE'])
    def delete_material(material_name):
        """Delete a material"""
        try:
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Check if material exists
            if material_name not in config['materials']:
                return jsonify({'success': False, 'error': 'Material not found'}), 404
            
            # Delete material
            del config['materials'][material_name]
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'Material deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/materials/export', methods=['GET'])
    def export_materials():
        """Export all materials as JSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Return the entire materials config
            return jsonify(config)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/materials/import', methods=['POST'])
    def import_materials():
        """Import materials from JSON"""
        try:
            data = request.json
            import_data = data.get('materials')
            mode = data.get('mode', 'merge')  # 'merge' or 'replace'
            
            if not import_data:
                return jsonify({'success': False, 'error': 'No materials data provided'}), 400
            
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if mode == 'replace':
                # Replace all materials
                config['materials'] = import_data
            else:
                # Merge materials (add new, update existing)
                for material_name, material_config in import_data.items():
                    config['materials'][material_name] = material_config
            
            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            material_count = len(import_data)
            return jsonify({
                'success': True, 
                'message': f'Successfully imported {material_count} material(s)',
                'count': material_count
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
