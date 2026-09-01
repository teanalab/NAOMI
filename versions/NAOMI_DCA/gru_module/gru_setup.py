
import json
import torch
import torch.nn as nn
import os

BASE_DIR = os.path.dirname(__file__)
VOCAB_PATH = os.path.join(BASE_DIR, 'vocab.json')
MODEL_PATH = os.path.join(BASE_DIR, 'gru_model.pt')
# Constants
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
EMBED_DIM = 32
HIDDEN_DIM = 64

HCP_CODES = [
    "GINFO+", "GINFO-", "EA", "AF", "SPT", "RCHT+", "RCHT-", "RCML+", "RCML-",
    "RO", "RAMB", "AR", "RBA", "SUM", "QECHT+", "QECHT-", "QECML+", "QECML-",
    "QEB", "QEF", "ADV-", "ADV+", "RC", "CON"
]

# GRU model definition (same as training)
class CodeGRU(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(self, x):
        emb = self.embed(x)
        _, h = self.gru(emb)
        return self.fc(h.squeeze(0))

# Cached model and vocab
_model = None
_vocab = None

def load_model_and_vocab():
    global _model, _vocab
    if _model is not None and _vocab is not None:
        return _model, _vocab

    # Load vocab
    with open(VOCAB_PATH) as f:
        vocab = json.load(f)
    vocab = {k: int(v) for k, v in vocab.items()}

    # Load model
    model = CodeGRU(len(vocab), EMBED_DIM, HIDDEN_DIM).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()

    _model = model
    _vocab = vocab
    return model, vocab