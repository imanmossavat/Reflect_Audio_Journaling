import spacy
import subprocess
from pathlib import Path

def load_model(model_name: str):
    """Try loading a spaCy model or fallback to HuggingFace/blank."""
    try:
        return spacy.load(model_name)
    except OSError:
        # Attempt to download spaCy model if possible
        if not Path(model_name).exists() and model_name.startswith(("en_", "nl_", "de_", "xx_")):
            print(f"[!] spaCy model '{model_name}' not found. Trying to download...")
            try:
                subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
                print(f"[+] Model '{model_name}' downloaded successfully.")
                return spacy.load(model_name)
            except subprocess.CalledProcessError:
                print(f"[x] Failed to download '{model_name}'. Using blank pipeline.")
                return spacy.blank("en")

        # Try loading a HuggingFace model
        if Path(model_name).exists() or "/" in model_name or "-" in model_name:
            try:
                from transformers import pipeline
                print(f"[~] Loading HuggingFace pipeline for '{model_name}'...")
                return pipeline("ner", model=model_name, aggregation_strategy="simple")
            except Exception as e:
                print(f"[x] Failed to load as HuggingFace model: {e}")
                return spacy.blank("en")

        print(f"[x] Could not load '{model_name}'. Using blank English model.")
        return spacy.blank("en")
