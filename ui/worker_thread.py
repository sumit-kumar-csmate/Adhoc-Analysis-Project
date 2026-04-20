"""
Background worker thread for processing files without freezing UI
"""

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ProcessingWorker(QThread):
    """Background thread for AI agent processing"""
    
    # Signals for UI updates
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)  # status message
    processing_complete = pyqtSignal(str, bool)  # output_path, success
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, agent, material: str, file_path: str):
        super().__init__()
        self.agent = agent
        self.material = material
        self.file_path = file_path
        self._is_running = True
    
    def run(self):
        """Main processing logic executed in background thread"""
        try:
            # Update status
            self.status_updated.emit("Loading file...")
            
            # Load data file
            if self.file_path.endswith('.xlsx') or self.file_path.endswith('.xls'):
                df = pd.read_excel(self.file_path)
            elif self.file_path.endswith('.csv'):
                df = pd.read_csv(self.file_path)
            else:
                raise ValueError(f"Unsupported file format: {self.file_path}")
            
            logger.info(f"Loaded file with {len(df)} rows")
            
            # Find Product_Description column
            desc_column = None
            for col in df.columns:
                if col.strip().lower() == 'product_description':
                    desc_column = col
                    break
            
            if desc_column is None:
                raise ValueError("Column 'Product_Description' not found in file")
            
            self.status_updated.emit(f"Found {len(df)} rows to process...")
            
            # Set agent material
            self.agent.set_material(self.material)
            
            # Process each row
            classifications = []
            total_rows = len(df)
            
            for idx, row in df.iterrows():
                if not self._is_running:
                    self.status_updated.emit("Processing cancelled")
                    return
                
                description = str(row[desc_column])
                
                # Update status
                self.status_updated.emit(f"Processing row {idx + 1} of {total_rows}...")
                
                # Classify description
                classification = self.agent.classify_description(description)
                classifications.append(classification)
                
                # Update progress
                self.progress_updated.emit(idx + 1, total_rows)
            
            # Insert new columns into dataframe
            self.status_updated.emit("Adding classification columns...")
            
            # Define column order: insert after Product_Description
            desc_col_idx = df.columns.get_loc(desc_column)
            
            # Create classification dataframe
            classification_df = pd.DataFrame(classifications)
            
            # Rename columns to match output format
            column_mapping = {
                'material_type': 'Material Type',
                'grade': 'Grade',
                'tradename': 'Tradename',
                'origin': 'Origin',
                'manufacturer': 'Manufacturer',
                'specifications': 'Specifications'
            }
            classification_df.rename(columns=column_mapping, inplace=True)
            
            # Insert classification columns after Product_Description
            for i, col_name in enumerate(['Material Type', 'Grade', 'Tradename', 
                                           'Origin', 'Manufacturer', 'Specifications']):
                df.insert(desc_col_idx + i + 1, col_name, classification_df[col_name])
            
            # Save modified file (in-place)
            self.status_updated.emit("Saving file...")
            
            if self.file_path.endswith('.xlsx') or self.file_path.endswith('.xls'):
                df.to_excel(self.file_path, index=False)
            elif self.file_path.endswith('.csv'):
                df.to_csv(self.file_path, index=False)
            
            logger.info(f"Successfully saved file: {self.file_path}")
            
            # Emit completion signal
            self.status_updated.emit("Processing complete!")
            self.processing_complete.emit(self.file_path, True)
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            self.error_occurred.emit(str(e))
            self.processing_complete.emit("", False)
    
    def stop(self):
        """Stop the processing thread"""
        self._is_running = False
