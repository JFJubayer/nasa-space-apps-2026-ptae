#!/usr/bin/env bash
# ==============================================================================
# NASA Space Apps Challenge 2026 - PTAE Run Demo Script
# ==============================================================================
set -e

echo "======================================================================"
echo "🚀 NASA Space Apps 2026: Planetary Terrestrial Analog Engine (PTAE)"
echo "======================================================================"

# 1. Setup Virtual Environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "🔌 Activating virtual environment..."
source venv/bin/activate

# 2. Check and Install Requirements
echo "📥 Checking dependencies..."
pip install -q -r requirements.txt || true

# 3. Run Pipeline for Moon Target
echo ""
echo "🌕 [Phase 1] Evaluating Earth Analogs for Artemis III Lunar South Pole..."
python3 main.py --target moon --data-dir data_synthetic_demo --output results_synthetic_demo/moon --json-out results_synthetic_demo/results_moon.json

# 4. Run Pipeline for Mars Target
echo ""
echo "🔴 [Phase 2] Evaluating Earth Analogs for Mars Jezero Crater..."
python3 main.py --target mars --data-dir data_synthetic_demo --output results_synthetic_demo/mars --no-vis --json-out results_synthetic_demo/results_mars.json

echo ""
echo "======================================================================"
echo "🎉 Five-site synthetic illustration complete. Outputs: 'results_synthetic_demo/'"
echo "   Synthetic results are separate from the checked-in 20-site real-data dashboard."
echo "🌐 View the unchanged real-data dashboard with: cd dashboard && python -m http.server 8000"
echo "   Then open http://localhost:8000 in your browser."
echo "======================================================================"
