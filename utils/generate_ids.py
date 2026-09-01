import random

def generate_ids(n=40, length=8):
    # easy-to-type alphabet: no 0, 1, l, I, O
    chars = "abcdefghijkmnopqrstuvwxyz23456789"
    ids = ["".join(random.choice(chars) for _ in range(length)) for _ in range(n)]
    return ids

if __name__ == "__main__":
    ids = generate_ids()

    with open("valid_ids.txt", "w") as f:
        f.write("VALID_IDS = [\n")
        for id_ in ids:
            f.write(f"    '{id_}',\n")
        f.write("]\n")

    print("✅ IDs written to valid_ids.txt")
