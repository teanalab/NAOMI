import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Absolute or project-relative path to your model
BASE_DIR = os.path.dirname(__file__)  # This is /yourproject/utils/
MODEL_PATH = os.path.join(BASE_DIR, "../models/modernbert-patient-final")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model = None
_tokenizer = None
_id2label = None

def load_model_and_tokenizer():
    global _model, _tokenizer, _id2label

    if _model is not None:
        return _model, _tokenizer, _id2label

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(DEVICE)
    _model.eval()
    _id2label = _model.config.id2label
    return _model, _tokenizer, _id2label

def predict_client_code(text):
    model, tokenizer, id2label = load_model_and_tokenizer()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred_id = torch.argmax(probs, dim=-1).item()
    return id2label[pred_id]