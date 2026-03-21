# Computational-Psycholinguistics_A5

## Folder Structure
```
.
├── parse.py            # Probabilistic Earley parser (Questions 1, 3, 4)
├── q2.py               # Parse tree probability computation (Question 2)
├── q1_grammar.gr       # Grammar from Figure 1 (Questions 1 & 2)
├── q1.sen              # Sentence file for Question 1
├── q3_grammar.gr       # Grammar for Question 3
├── q3.sen              # Sentence file for Question 3
└── README.md
```

## Usage

### Question 1 — Earley chart for "time flies like an arrow"
```bash
./parse.py --print-chart q1_grammar.gr q1.sen
```

### Question 2 — Parse tree probabilities
```bash
python3 q2.py
```

### Question 3 — Parse "the man shot the soldier with a gun"
```bash
./parse.py --print-chart q3_grammar.gr q3.sen
```

### General parser usage
```bash
./parse.py grammar.gr sentences.sen
```
Prints the minimum-weight parse tree and its weight for each
sentence, or `NONE` if no parse exists.

**Flags:**
- `--print-chart` — print the full Earley chart after parsing
- `-v` / `--verbose` — print debug trace of all chart operations
- `-s SYMBOL` — set the start symbol (default: `ROOT`)

## Requirements

Python 3.7+, no external libraries needed.

## Verification

Run on the wallstreet grammar to verify correctness:
```bash
./parse.py wallstreet.gr wallstreet.sen
```
