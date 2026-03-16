import spacy
import subprocess
import importlib.util
from transformers import pipeline

def load_model(model_name: str):
    """Load spaCy model, download if missing, else try HF."""

    def is_spacy_model(name):
        return importlib.util.find_spec(name) is not None

    if is_spacy_model(model_name):
        try:
            print(f"[+] Loading installed spaCy model '{model_name}'")
            return spacy.load(model_name)
        except Exception as e:
            print(f"[x] Installed spaCy model failed to load: {e}")

    if model_name.startswith(("en_", "nl_", "de_", "xx_")):
        print(f"[!] spaCy model '{model_name}' not found. Downloading...")
        try:
            subprocess.run(
                ["python", "-m", "spacy", "download", model_name],
                check=True
            )
            print(f"[+] Download successful, loading model…")
            return spacy.load(model_name)
        except Exception as e:
            print(f"[x] Failed to download '{model_name}': {e}")

    try:
        print(f"[~] Trying HuggingFace model '{model_name}'")
        return pipeline("ner", model=model_name, aggregation_strategy="simple")
    except Exception as e:
        print(f"[x] HF load failed: {e}")

    # Step 5: last resort
    print("[x] Returning blank English spaCy model.")
    return spacy.blank("en")
