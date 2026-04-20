"""
Analysis History Management
Stores and manages analysis history using SQLite
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path


class AnalysisHistory:
    def __init__(self, db_path='data/analysis_history.db'):
        self.db_path = db_path
        # Ensure data directory exists
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                material_type TEXT NOT NULL,
                rows_processed INTEGER NOT NULL,
                columns_added INTEGER NOT NULL,
                processing_time REAL,
                status TEXT DEFAULT 'completed',
                error_message TEXT,
                categories TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                actual_cost REAL DEFAULT 0.0
            )
        ''')
        
        # Safe migration for existing tables
        try:
            cursor.execute("SELECT prompt_tokens FROM analysis_runs LIMIT 1")
        except sqlite3.OperationalError:
            # Columns don't exist, alter table
            try:
                cursor.execute("ALTER TABLE analysis_runs ADD COLUMN prompt_tokens INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE analysis_runs ADD COLUMN completion_tokens INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE analysis_runs ADD COLUMN total_tokens INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE analysis_runs ADD COLUMN actual_cost REAL DEFAULT 0.0")
            except Exception as e:
                print(f"Migration error: {e}")
                
        conn.commit()
        conn.close()
    
    def add_analysis(self, file_name, file_path, material_type, rows_processed, 
                    columns_added, processing_time=None, categories=None, 
                    status='completed', error_message=None,
                    prompt_tokens=0, completion_tokens=0, total_tokens=0, actual_cost=0.0):
        """Add a new analysis record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        categories_json = json.dumps(categories) if categories else None
        
        cursor.execute('''
            INSERT INTO analysis_runs 
            (timestamp, file_name, file_path, material_type, rows_processed, 
             columns_added, processing_time, status, error_message, categories,
             prompt_tokens, completion_tokens, total_tokens, actual_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, file_name, file_path, material_type, rows_processed,
              columns_added, processing_time, status, error_message, categories_json,
              prompt_tokens, completion_tokens, total_tokens, actual_cost))
        
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return record_id
    
    def get_all_analyses(self, limit=100, offset=0):
        """Get all analysis records with pagination"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM analysis_runs 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        results = []
        for row in rows:
            record = dict(row)
            if record['categories']:
                record['categories'] = json.loads(record['categories'])
            results.append(record)
        
        return results
    
    def get_analysis_by_id(self, analysis_id):
        """Get a specific analysis record by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM analysis_runs WHERE id = ?', (analysis_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            record = dict(row)
            if record['categories']:
                record['categories'] = json.loads(record['categories'])
            return record
        return None
    
    def get_statistics(self):
        """Get overall statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total analyses
        cursor.execute('SELECT COUNT(*) FROM analysis_runs WHERE status = "completed"')
        total_analyses = cursor.fetchone()[0]
        
        # Total rows processed
        cursor.execute('SELECT SUM(rows_processed) FROM analysis_runs WHERE status = "completed"')
        total_rows = cursor.fetchone()[0] or 0
        
        # Average processing time
        cursor.execute('SELECT AVG(processing_time) FROM analysis_runs WHERE status = "completed" AND processing_time IS NOT NULL')
        avg_time = cursor.fetchone()[0] or 0
        
        # Token and cost totals
        cursor.execute('SELECT SUM(total_tokens), SUM(actual_cost) FROM analysis_runs WHERE status = "completed"')
        totals = cursor.fetchone()
        total_tokens_used = totals[0] or 0
        total_cost = totals[1] or 0.0
        
        # Material type breakdown
        cursor.execute('''
            SELECT material_type, COUNT(*) as count 
            FROM analysis_runs 
            WHERE status = "completed"
            GROUP BY material_type
        ''')
        material_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Recent analyses
        cursor.execute('''
            SELECT material_type, rows_processed, timestamp 
            FROM analysis_runs 
            WHERE status = "completed"
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        recent = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_analyses': total_analyses,
            'total_rows_processed': total_rows,
            'average_processing_time': round(avg_time, 2),
            'material_breakdown': material_breakdown,
            'recent_analyses': recent,
            'total_tokens_used': total_tokens_used,
            'total_cost': round(total_cost, 2)
        }
    
    def delete_analysis(self, analysis_id):
        """Delete an analysis record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM analysis_runs WHERE id = ?', (analysis_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        
        return deleted > 0
    
    def export_to_csv(self):
        """Export all analysis history to CSV format"""
        import csv
        import io
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, file_name, material_type, rows_processed, 
                   columns_added, processing_time, status 
            FROM analysis_runs 
            ORDER BY timestamp DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Timestamp', 'File Name', 'Material Type', 
                        'Rows Processed', 'Columns Added', 'Processing Time (s)', 'Status'])
        
        # Write data
        writer.writerows(rows)
        
        return output.getvalue()
