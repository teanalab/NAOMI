# utils/kl.py

import numpy as np

def kl_divergence(p, q, eps=1e-8):
    p = np.clip(p, eps, 1)
    q = np.clip(q, eps, 1)
    return np.sum(p * np.log(p / q))