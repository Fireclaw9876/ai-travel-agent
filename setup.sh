#!/bin/bash

set -e

echo "Setting up virtual environment..."

python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

pip install --upgrade pip

# Required dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Installing dependencies manually..."
    pip install arcadepy flask email_validator anthropic python-dotenv
fi

echo "Creating .env file template..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
ARCADE_API_KEY=your_arcade_api_key
ANTHROPIC_API_KEY=your_openai_api_key
EOF
    echo ".env file created. Please edit it to add your API keys."
else
    echo ".env file already exists."
fi

# Ensure templates folder exists
if [ ! -d "templates" ]; then
    echo "Error: /templates is missing. Please ensure the templates folder exists in the project root."
    exit 1
fi

# Ensure city json file exists
if [ ! -f "cities.json" ]; then
    echo "Error: cities.json is missing. Please ensure it exists in the project root."
    exit 1
fi

echo "Setup completed successfully!"
echo "Steps to start:"
echo "1. Edit the .env file to add your Arcade & Anthropic API key"
echo "2. Edit the USER_ID in main.py"
echo "3. Run in terminal with python main.py"
