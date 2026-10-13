#!/bin/bash

# Name of your virtual environment folder
VENV_DIR="venv"

# 1. Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 2. Activate the virtual environment
source "$VENV_DIR/bin/activate"

# 3. Upgrade pip and install dependencies from requirements.txt
echo "Checking and installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

# 4. Run the measurement script first (runs until you press Ctrl + C)
echo "--------------------------------------------------------"
echo "Starting sound measurement. Press Ctrl + C to stop & finish."
echo "--------------------------------------------------------"
python gm1355b.py

# 5. Once the first script exits (via Ctrl+C), run the report generator
echo "--------------------------------------------------------"
echo "Measurement stopped. Generating report..."
echo "--------------------------------------------------------"
python analyze.py

# 6. Deactivate when finished
deactivate
echo "All tasks completed successfully."