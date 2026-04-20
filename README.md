# Trade Data AI Analyzer - Electron Edition

A modern **Electron desktop application** that uses AI to analyze international trade data. Features material-specific AI agents powered by Google's Gemini 2.0 Flash API with a beautiful glassmorphism UI.

## 🎯 What Changed from PyQt6

This application has been **converted from PyQt6 to Electron** for:
✅ Better UI flexibility with HTML/CSS  
✅ Easier styling with modern web technologies  
✅ Cross-platform compatibility  
✅ Cleaner glass effect design without animated gradients  

## 🚀 Features

- **Material-Specific AI Agents**: Specialized agents for CAPB, Fatty Alcohol, Fatty Alcohol Ethoxylate, LAB, and Soda Ash
- **Intelligent Classification**: Extracts Material Type, Grade, Tradename, Origin, Manufacturer, and Specifications
- **In-Place File Editing**: Automatically inserts classification columns into your Excel/CSV files
- **Clean Glassmorphism UI**: Solid dark background with elegant glass-effect cards
- **Flask REST API Backend**: Robust Python backend with Electron frontend
- **Native File Dialogs**: Electron's native file picker for seamless UX

## 📋 Prerequisites

- **Node.js 16+** ([Download here](https://nodejs.org/))
- **Python 3.8+**
- **Google Gemini API key** ([Get one here](https://aistudio.google.com/))

## ⚙️ Installation

### 1. Clone or download this repository

### 2. Set up API key
Copy `.env.example` to `.env` and add your OpenAI API key (from proxy):
```bash
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_BASE_URL=https://proxy.abhibots.com/v1
```

### 3. Install dependencies
```bash
setup_venv.bat
```
This will install both Node.js and Python dependencies.

## 🎯 Usage

### Launch the application
```bash
START_APP.bat
```

Or manually:
```bash
npm start
```

### Using the app
1. **Select material type** from the dropdown menu
2. **Choose your trade data file** (Excel or CSV)
   - File must contain a `Product_Description` column
3. **Click "Analyze Data"** and wait for processing
4. **Check your file** - new classification columns will be inserted

## 📊 Supported Data Formats

- **Excel**: `.xlsx`, `.xls`
- **CSV**: `.csv`

**Required Column**: `Product_Description` (case-insensitive)

## 🏗️ Architecture

```
AI Agent Analyser/
├── electron/
│   ├── main.js              # Electron main process
│   └── preload.js           # IPC communication bridge
├── backend/
│   └── flask_app.py         # Flask REST API server
├── frontend/
│   ├── index.html           # UI structure
│   ├── styles.css           # Glassmorphism styling
│   └── app.js               # Frontend logic
├── core/
│   └── ai_agent.py          # AI Agent with Gemini integration
├── config/
│   └── materials_config.json # Material-specific configurations
├── package.json             # Node.js dependencies
├── requirements.txt         # Python dependencies
├── .env                     # API key configuration
└── START_APP.bat            # Launch script
```

## 🔧 Configuration

### Materials Configuration
Edit `config/materials_config.json` to add new materials or modify existing ones.

### Application Settings
The Flask backend runs on `http://127.0.0.1:5000`  
Electron automatically connects to this backend on startup.

## 📤 Output Columns

The application adds these columns to your data:
1. **Material Type** - Specific variant or type of the material
2. **Grade** - Quality or purity grade
3. **Tradename** - Brand or commercial name
4. **Origin** - Country of origin or manufacturing location
5. **Manufacturer** - Company name
6. **Specifications** - Technical specifications and details

## 🎨 UI Highlights

- **Clean Background**: Solid dark gradient (no animations)
- **Glass Effect Cards**: Subtle transparent cards with borders
- **Blue Accent Colors**: Clean, consistent color scheme
- **Responsive Design**: Works at different window sizes
- **Modern Typography**: Segoe UI font family

## ⚡ Development

### Run in development mode
```bash
npm run dev
```

### Build for distribution
```bash
npm run build
```

## 🐛 Troubleshooting

**Flask backend won't start**
- Check that Python virtual environment is activated
- Verify `OPENAI_API_KEY` is set in `.env`
- Ensure port 5000 is not in use

**Electron window is blank**
- Wait for Flask backend to fully start (2-3 seconds)
- Check console for errors (F12)
- Verify backend is running at http://127.0.0.1:5000

**File selection doesn't work**
- Ensure you're running the Electron app, not just opening the HTML file
- Check that `preload.js` is properly loaded

## 📝 How It Works

1. **Electron** launches and starts the **Flask backend** process
2. **Flask** initializes the AI agent with Gemini API
3. **Frontend** (HTML/CSS/JS) loads and fetches available materials via REST API
4. User selects material and file using **native Electron file picker**
5. Frontend sends analysis request to Flask backend
6. **AI Agent** processes each row using material-specific prompts
7. Results are inserted into the original file and saved
8. User receives success notification

## 🤝 Contributing

To add new materials:
1. Edit `config/materials_config.json`
2. Add material configuration with appropriate prompts
3. Restart the application

## 📧 Support

For issues or questions, check the troubleshooting section above.

---

**Built with ❤️ using Electron, Flask, and Google Gemini AI**
