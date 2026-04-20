# Quick Start Guide - Trade Data AI Analyzer

## 🚀 Get Started in 3 Steps

### Step 1: Configure API Key (REQUIRED)
Open `.env` file and replace with your actual OpenAI API key (from proxy):
```bash
OPENAI_API_KEY=sk-proxy-...your_key_here
OPENAI_BASE_URL=https://proxy.abhibots.com/v1
```

### Step 2: Launch Application
Double-click: `START_APP.bat`

### Step 3: Analyze Data
1. Select material type from dropdown
2. Click "Choose File" and select your Excel/CSV
3. Click "Analyze Data"
4. Wait for completion
5. Check your file - new columns added!

---

## 📋 File Requirements

**Required Column**: `Product_Description` (case-insensitive)

**Supported Formats**: 
- Excel: .xlsx, .xls
- CSV: .csv

---

## 🧪 Test with Sample Data

Try the provided sample file:
```
sample_data\trade_data_sample.csv
```
Contains 15 entries covering all 5 materials.

---

## 🎯 Available Materials

1. **CAPB** - Cocamidopropyl Betaine
2. **Fatty Alcohol** - C12-C18 alcohols
3. **Fatty Alcohol Ethoxylate** - Non-ionic surfactants
4. **LAB** - Linear Alkyl Benzene
5. **Soda Ash** - Sodium Carbonate

---

## 📤 Output Columns Added

✅ Material Type  
✅ Grade  
✅ Tradename  
✅ Origin  
✅ Manufacturer  
✅ Specifications  

---

## ❓ Troubleshooting

**App won't start?**
- Check `.env` file has valid API key (OPENAI_API_KEY)
- Run `setup_venv.bat` to reinstall dependencies

**"Column not found" error?**
- Ensure file has `Product_Description` column

**Need help?**
- See full [README.md](file:///c:/AI%20Agent%20Analyser/README.md)
- See detailed [walkthrough.md](file:///C:/Users/Admin/.gemini/antigravity/brain/398b04a6-7ea3-4733-9a8c-4729fd12fb14/walkthrough.md)
