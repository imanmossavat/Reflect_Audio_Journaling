# 1. Create a new environment with Python 3.11
conda create -n REFLECT python=3.11

# 2. Activate it
conda activate REFLECT

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install your dependencies
pip install -r requirements.txt

# 5. Run your script to download SpaCy models
python install_models.py
