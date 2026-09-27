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
python3 main.py --target moon

# 4. Run Pipeline for Mars Target
echo ""
echo "🔴 [Phase 2] Evaluating Earth Analogs for Mars Jezero Crater..."
python3 main.py --target mars --no-vis

echo ""
echo "======================================================================"
echo "🎉 Analysis complete! All plots saved in 'results/'"
echo "🌐 Open 'dashboard/index.html' in your browser to inspect the interactive map!"
echo "======================================================================"
