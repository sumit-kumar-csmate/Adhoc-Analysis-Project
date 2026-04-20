"""
Flask backend API for Electron app
Enhanced with preview, real-time progress, history tracking, and progressive results streaming
"""

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import os
import sys
import logging
import time
import json
import uuid

# Add core to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.ai_agent import TradeDataAgent
from backend.material_manager import add_material_routes
from backend.analysis_history import AnalysisHistory
from backend.cost_estimator import cost_estimator
import pandas as pd

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend_debug.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

# Initialize AI agent and history manager
try:
    agent = TradeDataAgent()
    history = AnalysisHistory()
    logger.info("Flask app initialized with AI agent and history manager")
except Exception as e:
    logger.error(f"Failed to initialize: {e}")
    agent = None
    history = None

# In-memory store for completed analysis results (job_id -> result data)
# Allows deferred Excel write — file is only saved when user clicks Download
analysis_results_store = {}

# Add material management routes
add_material_routes(app)


@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/materials', methods=['GET'])
def get_materials():
    """Get list of available materials"""
    if not agent:
        return jsonify({'error': 'AI agent not initialized'}), 500
    
    try:
        materials = agent.get_available_materials()
        materials_info = []
        
        for material in materials:
            info = agent.get_material_info(material)
            materials_info.append({
                'name': material,
                'full_name': info.get('full_name', material),
                'description': info.get('description', '')
            })
        
        return jsonify({'materials': materials_info})
    except Exception as e:
        logger.error(f"Error getting materials: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/materials/enhance-prompt', methods=['POST'])
def enhance_prompt_endpoint():
    """Enhance a draft prompt using the AI agent with material context"""
    if not agent:
        return jsonify({'success': False, 'error': 'AI agent not initialized'}), 500

    try:
        data = request.json
        draft_prompt = data.get('draft_prompt')
        categories = data.get('categories', [])
        material_name = data.get('material_name', '')
        material_description = data.get('material_description', '')
        
        if not draft_prompt:
            return jsonify({'success': False, 'error': 'No draft prompt provided'})
        
        enhanced_prompt = agent.enhance_prompt(
            draft_prompt=draft_prompt,
            categories=categories,
            material_name=material_name,
            material_description=material_description
        )
        
        return jsonify({
            'success': True, 
            'enhanced_prompt': enhanced_prompt
        })
    except Exception as e:
        logger.error(f"Error enhancing prompt: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/preview', methods=['POST'])
def preview_file():
    """Preview file data and validate structure"""
    try:
        data = request.json
        file_path = data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load file
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.xlsb'):
            df = pd.read_excel(file_path, engine='pyxlsb')
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Identify description column
        desc_column = identify_description_column(df)
        
        # Get preview data (first 10 rows)
        preview_data = df.head(10).to_dict('records')
        
        # Calculate cost estimate
        cost_estimate = None
        if desc_column:
            try:
                # Get descriptions to calculate accurate token estimate
                descriptions = df[desc_column].astype(str).tolist()
                avg_desc_length = sum(len(d) for d in descriptions) // max(1, len(descriptions))
                
                # Default to 3 columns for estimate (typical extraction)
                cost_estimate = cost_estimator.estimate_pre_analysis(
                    row_count=len(df),
                    column_count=3,
                    avg_description_length=avg_desc_length,
                    model="flash"
                )
            except Exception as cost_err:
                logger.warning(f"Cost estimation failed: {cost_err}")
                cost_estimate = None
        
        return jsonify({
            'success': True,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'has_product_description': desc_column is not None,
            'product_description_column': desc_column,
            'preview_data': preview_data,
            'cost_estimate': cost_estimate
        })
        
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        return jsonify({'error': str(e)}), 500


def identify_description_column(df):
    """
    Identify the column containing product descriptions.
    Logic:
    1. If only 1 column, use it key.
    2. If multiple, look for 'product_description' (case-insensitive).
    3. Fallback to first column.
    """
    if len(df.columns) == 1:
        return df.columns[0]
    
    # helper for clean comparison
    clean_cols = [c.strip().lower() for c in df.columns]
    
    if 'product_description' in clean_cols:
        return df.columns[clean_cols.index('product_description')]
        
    if 'description' in clean_cols:
         return df.columns[clean_cols.index('description')]

    # Fallback to first column
    if len(df.columns) > 0:
        return df.columns[0]
        
    return None


@app.route('/api/cost/estimate', methods=['POST'])
def estimate_cost():
    """Estimate analysis cost based on parameters"""
    try:
        data = request.json
        row_count = data.get('row_count', 0)
        column_count = data.get('column_count', 3)
        avg_description_length = data.get('avg_description_length', 400)
        model = data.get('model', 'flash')
        
        estimate = cost_estimator.estimate_pre_analysis(
            row_count=row_count,
            column_count=column_count,
            avg_description_length=avg_description_length,
            model=model
        )
        
        return jsonify({
            'success': True,
            'estimate': estimate
        })
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cost/rates', methods=['GET'])
def get_cost_rates():
    """Get current pricing rates"""
    return jsonify({
        'success': True,
        'rates': {
            'flash': {
                'input_per_million': cost_estimator.config.FLASH_INPUT_RATE,
                'output_per_million': cost_estimator.config.FLASH_OUTPUT_RATE
            },
            'pro': {
                'input_per_million': cost_estimator.config.PRO_INPUT_RATE,
                'output_per_million': cost_estimator.config.PRO_OUTPUT_RATE
            },
            'exchange_rate': cost_estimator.config.USD_TO_INR
        }
    })


@app.route('/api/cost/calculate', methods=['POST'])
def calculate_cost():
    """
    Calculate accurate cost based on file data and material selection.
    Uses actual descriptions for precise input token calculation,
    and material config for correct output column count.
    """
    try:
        data = request.json
        file_path = data.get('file_path')
        material = data.get('material')
        mode = data.get('mode', 'specific')
        model = data.get('model', 'flash')
        
        if not file_path:
            return jsonify({'error': 'file_path is required'}), 400
        
        # Load file to get actual descriptions
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Find description column
        desc_column = identify_description_column(df)
        if not desc_column:
            return jsonify({'error': 'Product_Description column not found'}), 400
        
        # Get actual descriptions (convert to string)
        descriptions = df[desc_column].astype(str).tolist()
        
        # Determine output column count based on mode and material
        if mode == 'universal':
            # Universal mode always has 5 columns
            column_count = 5
            column_names = ['Material Name', 'Grade', 'Manufacturer', 'Key Specifications', 'Category']
        else:
            # Get column count from material config
            if material and material in agent.materials_config:
                material_config = agent.materials_config[material]
                # Categories define how many output columns
                categories = material_config.get('classification_categories', [])
                column_count = len(categories)
                column_names = categories
            else:
                # Default to 3 if material not found
                column_count = 3
                column_names = ['Grade', 'Origin', 'Manufacturer']
        
        # Use accurate estimation from actual descriptions
        estimate = cost_estimator.estimate_from_descriptions(
            descriptions=descriptions,
            column_count=column_count,
            model=model
        )
        
        # Add column info to response
        estimate['column_names'] = column_names
        estimate['material'] = material
        estimate['mode'] = mode
        
        return jsonify({
            'success': True,
            'estimate': estimate
        })
        
    except Exception as e:
        logger.error(f"Error calculating cost: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    """Analyze uploaded file (non-streaming version)"""
    if not agent or not history:
        return jsonify({'error': 'Backend not initialized'}), 500
    
    try:
        data = request.json
        file_path = data.get('file_path')
        material = data.get('material')
        
        if not file_path or not material:
            return jsonify({'error': 'Missing file_path or material'}), 400
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        start_time = time.time()
        
        # Load file
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.xlsb'):
            df = pd.read_excel(file_path, engine='pyxlsb')
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Identify Product_Description column
        desc_column = identify_description_column(df)
        
        if desc_column is None:
            return jsonify({'error': 'Could not identify data column'}), 400
        
        # Get mode and material
        mode = request.json.get('mode', 'specific')
        material = request.json.get('material')
        
        # Set Up Agent based on Mode
        if mode == 'specific':
            if not material:
                return jsonify({'error': 'Material is required for specific mode'}), 400
            agent.set_material(material)
            categories = agent.get_classification_categories()
        else:
            # Universal Mode uses fixed schema
            categories = ['Material Name', 'Grade', 'Manufacturer', 'Key Specifications', 'Category']

        # Process each row
        classifications = []
        total_rows = len(df)
        
        for idx, row in df.iterrows():
            description = str(row[desc_column])
            classification = agent.classify_description(description, mode=mode)
            classifications.append(classification)
        
        # Insert new columns
        desc_col_idx = df.columns.get_loc(desc_column)
        classification_df = pd.DataFrame(classifications)
        
        for i, category in enumerate(categories):
            key = category if mode == 'universal' else agent._category_to_key(category)
            
            # Map universal keys to friendly names if needed
            if mode == 'universal':
                key_map = {
                    'Material Name': 'material_name',
                    'Grade': 'grade',
                    'Manufacturer': 'manufacturer',
                    'Key Specifications': 'key_specifications',
                    'Category': 'category'
                }
                data_key = key_map.get(category, category)
            else:
                data_key = key
                
            if data_key in classification_df.columns:
                df.insert(desc_col_idx + i + 1, category, classification_df[data_key])
        
        # Save file
        if file_path.endswith(('.xlsx', '.xls')):
            df.to_excel(file_path, index=False)
        elif file_path.endswith('.csv'):
            df.to_csv(file_path, index=False)
        
        processing_time = time.time() - start_time
        
        # Save to history
        file_name = os.path.basename(file_path)
        history.add_analysis(
            file_name=file_name,
            file_path=file_path,
            material_type=material,
            rows_processed=total_rows,
            columns_added=len(categories),
            processing_time=processing_time,
            categories=categories,
            status='completed'
        )
        
        return jsonify({
            'success': True,
            'message': 'Analysis complete',
            'rows_processed': total_rows,
            'columns_added': len(categories),
            'processing_time': round(processing_time, 2),
            'output_file': file_path
        })
        
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        
        # Log error to history
        if history and 'file_path' in locals() and 'material' in locals():
            history.add_analysis(
                file_name=os.path.basename(file_path) if file_path else 'unknown',
                file_path=file_path if file_path else None,
                material_type=material,
                rows_processed=0,
                columns_added=0,
                status='failed',
                error_message=str(e)
            )
        
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/stream', methods=['GET'])
def analyze_file_stream():
    """Analyze file with real-time progress streaming via SSE"""
    if not agent or not history:
        return jsonify({'error': 'Backend not initialized'}), 500
    
    file_path = request.args.get('file_path')
    material = request.args.get('material')
    
    if not file_path or not material:
        return jsonify({'error': 'Missing file_path or material'}), 400
    
    def generate():
        try:
            start_time = time.time()

            # Load file
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Unsupported file format'})}\n\n"
                return

            # Find description column
            desc_column = identify_description_column(df)
            if desc_column is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Product_Description column not found'})}\n\n"
                return

            mode = request.args.get('mode', 'specific')
            total_rows = len(df)
            original_columns = list(df.columns)

            # Set up agent based on mode
            if mode == 'specific':
                agent.set_material(material)
                categories = agent.get_classification_categories()
            else:
                categories = ['Material Name', 'Grade', 'Manufacturer', 'Key Specifications', 'Category']

            descriptions = df[desc_column].astype(str).tolist()

            universal_key_map = {
                'Material Name': 'material_name',
                'Grade': 'grade',
                'Manufacturer': 'manufacturer',
                'Key Specifications': 'key_specifications',
                'Category': 'category'
            }

            # --- Batch classify: send partial_results per chunk as they complete ---
            CHUNK_SIZE = 20   # 20 per call — safe within Claude Haiku's 4096 output token limit
            MAX_WORKERS = 5
            completed = 0
            classifications = [{}] * total_rows

            chunks = [
                (descriptions[i:i + CHUNK_SIZE], i)
                for i in range(0, total_rows, CHUNK_SIZE)
            ]

            from concurrent.futures import ThreadPoolExecutor, as_completed as futures_as_completed

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_chunk = {
                    executor.submit(agent._classify_chunk, chunk, start, mode): (chunk, start)
                    for chunk, start in chunks
                }

                for future in futures_as_completed(future_to_chunk):
                    chunk, start = future_to_chunk[future]
                    chunk_results = {}
                    try:
                        result_map = future.result(timeout=120)
                        for idx, res in result_map.items():
                            classifications[idx] = res
                            chunk_results[idx] = res
                    except Exception as e:
                        logger.error(f"Chunk at {start} failed: {e}")

                    completed += len(chunk)

                    # Build partial rows to show in the frontend table immediately
                    partial_rows = []
                    for i, desc in enumerate(chunk):
                        row_idx = start + i
                        res = chunk_results.get(row_idx, {})
                        row_data = {col: str(df.iloc[row_idx][col]) for col in original_columns}
                        for cat in categories:
                            data_key = universal_key_map.get(cat, agent._category_to_key(cat)) if mode == 'universal' else agent._category_to_key(cat)
                            row_data[cat] = res.get(data_key, '')
                        partial_rows.append({'row_idx': row_idx, 'data': row_data})

                    yield f"data: {json.dumps({'type': 'partial_results', 'rows': partial_rows, 'current': min(completed, total_rows), 'total': total_rows, 'percent': round(min(completed, total_rows) / total_rows * 100, 1)})}\n\n"

            processing_time = time.time() - start_time

            # Store results in memory — file is written only when user clicks Download
            job_id = str(uuid.uuid4())
            analysis_results_store[job_id] = {
                'df': df,
                'classifications': classifications,
                'categories': categories,
                'mode': mode,
                'desc_column': desc_column,
                'file_path': file_path,
                'material': material,
                'total_rows': total_rows,
                'processing_time': processing_time,
                'created_at': time.time()
            }

            # Save to history
            file_name = os.path.basename(file_path)
            history.add_analysis(
                file_name=file_name,
                file_path=file_path,
                material_type=material,
                rows_processed=total_rows,
                columns_added=len(categories),
                processing_time=processing_time,
                categories=categories,
                status='completed'
            )

            # Send complete event with job_id — no file write yet
            yield f"data: {json.dumps({'type': 'complete', 'rows_processed': total_rows, 'columns_added': len(categories), 'processing_time': round(processing_time, 2), 'job_id': job_id, 'categories': categories, 'original_columns': original_columns})}\n\n"

        except Exception as e:
            logger.error(f"Error in stream analysis: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/download/<job_id>', methods=['GET'])
def download_results(job_id):
    """Write Excel/CSV and return output file path. Only called when user clicks Download."""
    if job_id not in analysis_results_store:
        return jsonify({'error': 'Job not found or expired. Please re-run the analysis.'}), 404

    job = analysis_results_store[job_id]
    df = job['df'].copy()
    classifications = job['classifications']
    categories = job['categories']
    mode = job['mode']
    desc_column = job['desc_column']
    file_path = job['file_path']

    universal_key_map = {
        'Material Name': 'material_name',
        'Grade': 'grade',
        'Manufacturer': 'manufacturer',
        'Key Specifications': 'key_specifications',
        'Category': 'category'
    }

    try:
        desc_col_idx = df.columns.get_loc(desc_column)
        classification_df = pd.DataFrame(classifications)

        for i, category in enumerate(categories):
            data_key = universal_key_map.get(category, category) if mode == 'universal' else agent._category_to_key(category)
            if data_key in classification_df.columns:
                df.insert(desc_col_idx + i + 1, category, classification_df[data_key])

        # Save to a NEW file (avoids Excel file-lock permission errors on source file)
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_analyzed{ext}"
        if output_path.endswith(('.xlsx', '.xls')):
            df.to_excel(output_path, index=False)
        elif output_path.endswith('.csv'):
            df.to_csv(output_path, index=False)

        # Clean up memory after download
        del analysis_results_store[job_id]

        logger.info(f"Download complete: {output_path}")
        return jsonify({'success': True, 'output_file': output_path})
    except Exception as e:
        logger.error(f"Download failed for job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500





@app.route('/api/history', methods=['GET'])
def get_history():
    """Get all analysis history"""
    if not history:
        return jsonify({'error': 'History manager not initialized'}), 500
    
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        analyses = history.get_all_analyses(limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'analyses': analyses,
            'count': len(analyses)
        })
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    """Get analysis statistics"""
    if not history:
        return jsonify({'error': 'History manager not initialized'}), 500
    
    try:
        stats = history.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/export', methods=['GET'])
def export_history():
    """Export history to CSV"""
    if not history:
        return jsonify({'error': 'History manager not initialized'}), 500
    
    try:
        csv_data = history.export_to_csv()
        
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=analysis_history.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting history: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

