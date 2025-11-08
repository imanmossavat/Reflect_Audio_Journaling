# install_models.py
import subprocess
import sys

models = ["en_core_web_sm", "nl_core_news_sm"]

for model in models:
    subprocess.check_call([sys.executable, "-m", "spacy", "download", model])
