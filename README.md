# Dual Controller Architecture to Enable Adherence of LLM-based Counselors to Session- and Discourse-level Aspects of Motivational Interviewing Theory

Code for the EMNLP 2026 paper of the same name.

NAOMI is an LLM-based counselor for obesity-related health behavior change.
The Dual Controller Architecture adds two symbolic controllers around a
backbone LLM: a global controller that manages transitions between the four MI
processes (engaging, focusing, evoking, planning), and a local controller that
selects the counselor behavior code for each turn from a communication pattern
term, a distribution-matching term, and a GRU prior.

## Variants

| Paper | Directory | Adaptation |
|---|---|---|
| NAOMI-PT | `versions/NAOMI_PT/` | few-shot prompting |
| NAOMI-FT | `versions/NAOMI_FT/` | fine-tuned |
| NAOMI-RAG | `versions/NAOMI_RAG/` | retrieval |
| NAOMI-RAG+ | `versions/NAOMI_RAG+/` | retrieval, then revise |
| NAOMI-DCA | `versions/NAOMI_DCA/` | dual controller |

Internally v1, v2, v3, v31, and v4.

## Setup

```bash
conda env create -f environment.yml
conda activate naomi-b
python app.py
```

Python 3.12, a GPU able to serve a 70B model, and [Ollama](https://ollama.com)
for model serving. 

Tech Stack: Flask, LangChain, Ollama, PyTorch, FAISS.

Models:

```bash
ollama pull yermakhan/naomi-dca      # DCA agent
ollama pull yermakhan/mi-llama-v7    # backbone for FT, RAG, RAG+ (Fine-tuned Llama 3.1-70B )
ollama pull llama-guard3:1b          # safety check
```

`/v4` is the DCA condition, `/test_v4` the same agent without participant
logging.

## Not included

The MI session transcripts behind the fine-tuning and retrieval components are
clinical data covered by institutional data use agreements and IRB approval at
Wayne State University, and cannot be redistributed. The same applies to the
FAISS indexes built from them and to the user study transcripts. Appendix H.1
describes the corpus.

PT, FT and DCA run against the Ollama models above. The RAG variants expect
indexes at `data/faiss_db/faiss_index_ob_k3` and `..._k5`, which `rag.py` can
build from your own transcripts. The offline ablations read coded transcripts
that are not included.

Researchers with a data use agreement can contact the corresponding author.

## Layout

```
app.py            Flask server, one route per variant
constants.py      MI codes, target distributions, stage config
versions/         the five agents
ablations/        offline ablation suite (Appendix G)
utils/            KL divergence, postprocessing
```

## Citation

```bibtex
@inproceedings{magzym2026dual,
  title     = {Dual Controller Architecture to Enable Adherence of {LLM}-based
               Counselors to Session- and Discourse-level Aspects of
               Motivational Interviewing Theory},
  author    = {Magzym, Yermakhan and
               Carcone, April Idalski and
               Towner, Elizabeth and
               Mann, Christopher and
               Badr, M. Safwan and
               Kotov, Alexander},
  booktitle = {Proceedings of the 2026 Conference on Empirical Methods in
               Natural Language Processing},
  year      = {2026},
  note      = {To appear}
}
```