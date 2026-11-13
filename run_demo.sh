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

# 3. Real-data global analog search (downloads open data on first run)
echo ""
echo "🌍 [Phase 1] Global analog search on real LOLA / MOLA / SRTM / NASA POWER data..."
python3 -m src.global_search

# 4. Legacy synthetic-terrain demo
echo ""
echo "🌕 [Phase 2] Legacy synthetic demo: Moon, then Mars..."
python3 main.py --target moon
python3 main.py --target mars --no-vis

echo ""
echo "======================================================================"
echo "🎉 Analysis complete! Results in 'dashboard/global_results.json' and 'results/'"
echo "🌐 Run: python3 -m http.server --directory dashboard 8000  and open http://localhost:8000/"
echo "======================================================================"
