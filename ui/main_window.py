"""
Main PyQt6 application window with premium glassmorphism design
"""

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QComboBox, QPushButton, 
                              QProgressBar, QTextEdit, QFileDialog, QMessageBox,
                              QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QLinearGradient, QBrush, QPainter
import logging

from core.ai_agent import TradeDataAgent
from ui.worker_thread import ProcessingWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize AI agent
        try:
            self.agent = TradeDataAgent()
            self.available_materials = self.agent.get_available_materials()
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize AI agent:\n{str(e)}\n\n"
                                "Please check your .env file and ensure OPENAI_API_KEY is set.")
            sys.exit(1)
        
        self.worker = None
        self.selected_file = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Trade Data AI Analyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set solid dark background
        self.setStyleSheet("""  
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #0f0f1e);
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(central_widget)
        
        # Main layout with improved spacing
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(50, 40, 50, 40)
        main_layout.setSpacing(25)
        
        # Title with enhanced glass effect
        title_label = QLabel("🔬 Trade Data AI Analyzer")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            color: white;
            background: rgba(255, 255, 255, 0.08);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 18px;
            padding: 25px;
        """)
        main_layout.addWidget(title_label)
        
        # Material selection card
        material_card = self.create_glass_card()
        material_layout = QVBoxLayout(material_card)
        material_layout.setSpacing(15)
        
        material_label = QLabel("Select Material Type:")
        material_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        material_label.setStyleSheet("color: white; margin-bottom: 5px;")
        material_layout.addWidget(material_label)
        
        self.material_combo = QComboBox()
        self.material_combo.addItems(self.available_materials)
        self.material_combo.setFont(QFont("Segoe UI", 13))
        self.material_combo.setStyleSheet(self.get_combo_style())
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        self.material_combo.setFixedHeight(55)
        material_layout.addWidget(self.material_combo)
        
        # Material info
        self.material_info_label = QLabel("")
        self.material_info_label.setFont(QFont("Segoe UI", 11))
        self.material_info_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); margin-top: 8px;")
        self.material_info_label.setWordWrap(True)
        self.material_info_label.setMinimumHeight(50)
        material_layout.addWidget(self.material_info_label)
        
        main_layout.addWidget(material_card)
        
        # File upload card
        file_card = self.create_glass_card()
        file_layout = QVBoxLayout(file_card)
        file_layout.setSpacing(15)
        
        file_label = QLabel("Upload Trade Data File:")
        file_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        file_label.setStyleSheet("color: white; margin-bottom: 5px;")
        file_layout.addWidget(file_label)
        
        # File selection button
        file_button_layout = QHBoxLayout()
        file_button_layout.setSpacing(15)
        
        self.select_file_btn = QPushButton("📁 Choose File")
        self.select_file_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.select_file_btn.setStyleSheet(self.get_button_style())
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_file_btn.setFixedHeight(45)
        self.select_file_btn.setMinimumWidth(150)
        file_button_layout.addWidget(self.select_file_btn)
        
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setFont(QFont("Segoe UI", 11))
        self.file_path_label.setStyleSheet("color: rgba(255, 255, 255, 0.65);")
        file_button_layout.addWidget(self.file_path_label, 1)
        
        file_layout.addLayout(file_button_layout)
        
        # Process button
        self.process_btn = QPushButton("🚀 Analyze Data")
        self.process_btn.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.process_btn.setStyleSheet(self.get_process_button_style())
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setEnabled(False)
        self.process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_btn.setFixedHeight(55)
        file_layout.addWidget(self.process_btn)
        
        main_layout.addWidget(file_card)
        
        # Progress card
        progress_card = self.create_glass_card()
        progress_layout = QVBoxLayout(progress_card)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setStyleSheet("color: white;")
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(QFont("Segoe UI", 10))
        self.progress_bar.setStyleSheet(self.get_progress_style())
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_card)
        
        # Set initial material
        if self.available_materials:
            self.material_combo.setCurrentIndex(0)
            self.on_material_changed(self.available_materials[0])
    
    def create_glass_card(self):
        """Create a glassmorphism card widget with enhanced glass effect"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 18px;
                border: 2px solid rgba(255, 255, 255, 0.15);
                padding: 30px;
            }
        """)
        return card
    
    def get_combo_style(self):
        """Get combobox stylesheet"""
        return """
            QComboBox {
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.35);
                border-radius: 10px;
                padding: 14px 18px;
                color: white;
                font-size: 14px;
                min-height: 25px;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.22);
                border-color: rgba(255, 255, 255, 0.5);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid white;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 50, 0.98);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                selection-background-color: rgba(70, 130, 255, 0.6);
                color: white;
                padding: 8px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: rgba(70, 130, 255, 0.3);
            }
        """
    
    def get_button_style(self):
        """Get button stylesheet"""
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.25);
                border: 2px solid rgba(255, 255, 255, 0.4);
                border-radius: 12px;
                padding: 12px 24px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.35);
                border-color: rgba(255, 255, 255, 0.6);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.4);
            }
        """
    
    def get_process_button_style(self):
        """Get process button stylesheet with solid accent color"""
        return """
            QPushButton {
                background: rgba(70, 130, 255, 0.25);
                border: 2px solid rgba(70, 130, 255, 0.6);
                border-radius: 14px;
                padding: 16px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(70, 130, 255, 0.35);
                border-color: rgba(70, 130, 255, 0.8);
            }
            QPushButton:pressed {
                background: rgba(70, 130, 255, 0.2);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 0.15);
                border-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.3);
            }
        """
    
    def get_progress_style(self):
        """Get progress bar stylesheet with solid accent"""
        return """
            QProgressBar {
                background: rgba(255, 255, 255, 0.08);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 28px;
            }
            QProgressBar::chunk {
                background: rgba(70, 180, 255, 0.6);
                border-radius: 8px;
            }
        """
    
    def on_material_changed(self, material_name):
        """Handle material selection change"""
        if material_name:
            info = self.agent.get_material_info(material_name)
            if info:
                full_name = info.get('full_name', material_name)
                description = info.get('description', '')
                self.material_info_label.setText(f"📋 {full_name}\n{description}")
    
    def select_file(self):
        """Open file dialog to select data file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Trade Data File",
            "",
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*.*)"
        )
        
        if file_path:
            self.selected_file = file_path
            self.file_path_label.setText(os.path.basename(file_path))
            self.process_btn.setEnabled(True)
            self.status_label.setText(f"File loaded: {os.path.basename(file_path)}")
    
    def start_processing(self):
        """Start processing the selected file"""
        if not self.selected_file:
            QMessageBox.warning(self, "No File", "Please select a file first.")
            return
        
        material = self.material_combo.currentText()
        
        # Disable controls
        self.process_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.material_combo.setEnabled(False)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Starting analysis for {material}...")
        
        # Create and start worker thread
        self.worker = ProcessingWorker(self.agent, material, self.selected_file)
        self.worker.progress_updated.connect(self.on_progress_update)
        self.worker.status_updated.connect(self.on_status_update)
        self.worker.processing_complete.connect(self.on_processing_complete)
        self.worker.error_occurred.connect(self.on_error)
        
        self.worker.start()
    
    def on_progress_update(self, current, total):
        """Update progress bar"""
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
    
    def on_status_update(self, status):
        """Update status label"""
        self.status_label.setText(status)
    
    def on_processing_complete(self, output_path, success):
        """Handle processing completion"""
        # Re-enable controls
        self.process_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.material_combo.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"Analysis complete!\n\nFile has been updated with classification columns:\n{output_path}"
            )
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setValue(0)
    
    def on_error(self, error_message):
        """Handle processing error"""
        QMessageBox.critical(self, "Processing Error", f"An error occurred:\n\n{error_message}")
        self.status_label.setText("Error occurred")
        
        # Re-enable controls
        self.process_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.material_combo.setEnabled(True)
    
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark palette for clean background
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
