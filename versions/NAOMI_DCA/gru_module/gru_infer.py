
import torch
import torch.nn.functional as F
from .gru_setup import load_model_and_vocab, HCP_CODES, DEVICE

SEQ_LEN = 10

def extract_therapist_codes(history, max_len=SEQ_LEN):
    """
    Extracts last `max_len` therapist codes from full stage history.
    Pads with '<START>' if needed.
    """
    t_codes = [code for speaker, code in history if speaker == "T"]
    return ['<START>'] * max(0, max_len - len(t_codes)) + t_codes[-max_len:]

def get_code_probabilities(history):
    """
    Given a conversation history like:
    [("C", "*"), ("T", "RCHT+"), ("C", "*"), ("T", "QECHT+")],
    returns a dict of probabilities over HCP_CODES.
    """
    model, vocab = load_model_and_vocab()
    codes = extract_therapist_codes(history)
    input_ids = [vocab.get(code, 0) for code in codes]
    x = torch.tensor([input_ids]).to(DEVICE)

    with torch.no_grad():
        probs = torch.softmax(model(x), dim=-1).squeeze(0).cpu()

    return {
        code: probs[vocab[code]].item() if code in vocab else 0.0
        for code in HCP_CODES
    }

# === Optional: test case ===
if __name__ == '__main__':
    test_history = [("C", "*"), ("T", "RCHT+"), ("C", "*"), ("T", "QECHT+")]
    probs = get_code_probabilities(test_history)
    for code, prob in sorted(probs.items(), key=lambda x: -x[1]):
        print(f"{code:8s} → {prob:.4f}")