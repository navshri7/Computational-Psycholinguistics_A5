#!/usr/bin/env python3
"""
Question 2: Compute the probability of each parse tree for the sentence
"time flies like an arrow" using the grammar rules from Figure 1.

Grammar rules and probabilities:
    S   -> NP VP       1.0
    NP  -> N N         0.25
    NP  -> D N         0.4
    NP  -> N           0.35
    VP  -> V NP        0.6
    VP  -> V ADVP      0.4
    ADVP-> ADV NP      1.0
    N   -> time        0.4
    N   -> flies       0.2
    N   -> arrow       0.4
    D   -> an          1.0
    ADV -> like        1.0
    V   -> flies       0.5
    V   -> like        0.5

The sentence is ambiguous and has two valid parse trees:

  Parse Tree 1 (intended reading):
    "Time moves the way an arrow does"
    Structure: [NP time] [VP flies [ADVP like [NP an arrow]]]

  Parse Tree 2 (alternative reading):
    "Time-flies (a type of fly) like an arrow"
    Structure: [NP time flies] [VP like [NP an arrow]]
"""

import math


def compute_tree_probability(rules: dict) -> float:
    """Multiply all rule probabilities for a given parse tree."""
    prob = 1.0
    for rule, p in rules.items():
        prob *= p
    return prob


def main():
    print("=" * 60)
    print("Question 2: Parse Tree Probabilities")
    print("Sentence: 'time flies like an arrow'")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Parse Tree 1: [NP time] [VP flies [ADVP like [NP an arrow]]]
    # Rules used:
    #   S    -> NP VP      : 1.0
    #   NP   -> N          : 0.35    (for "time")
    #   N    -> time       : 0.4
    #   VP   -> V ADVP     : 0.4
    #   V    -> flies      : 0.5
    #   ADVP -> ADV NP     : 1.0
    #   ADV  -> like       : 1.0
    #   NP   -> D N        : 0.4     (for "an arrow")
    #   D    -> an         : 1.0
    #   N    -> arrow      : 0.4
    # ------------------------------------------------------------------

    tree1_rules = {
        "S -> NP VP":    1.0,
        "NP -> N":       0.35,
        "N -> time":     0.4,
        "VP -> V ADVP":  0.4,
        "V -> flies":    0.5,
        "ADVP -> ADV NP":1.0,
        "ADV -> like":   1.0,
        "NP -> D N":     0.4,
        "D -> an":       1.0,
        "N -> arrow":    0.4,
    }

    prob1 = compute_tree_probability(tree1_rules)
    weight1 = -math.log2(prob1)

    print("\nParse Tree 1 (intended reading):")
    print("  Structure: [NP time] [VP flies [ADVP like [NP an arrow]]]")
    print("\n  Rules used:")
    for rule, p in tree1_rules.items():
        print(f"    {rule:<25} p = {p}")
    print(f"\n  P(Tree 1) = {' x '.join(str(p) for p in tree1_rules.values())}")
    print(f"           = {prob1:.5f}")
    print(f"  Weight    = -log2({prob1:.5f}) = {weight1:.5f} bits")

    # ------------------------------------------------------------------
    # Parse Tree 2: [NP time flies] [VP like [NP an arrow]]
    # Rules used:
    #   S  -> NP VP     : 1.0
    #   NP -> N N       : 0.25    (for "time flies")
    #   N  -> time      : 0.4
    #   N  -> flies     : 0.2
    #   VP -> V NP      : 0.6
    #   V  -> like      : 0.5
    #   NP -> D N       : 0.4    (for "an arrow")
    #   D  -> an        : 1.0
    #   N  -> arrow     : 0.4
    # ------------------------------------------------------------------

    tree2_rules = {
        "S -> NP VP":  1.0,
        "NP -> N N":   0.25,
        "N -> time":   0.4,
        "N -> flies":  0.2,
        "VP -> V NP":  0.6,
        "V -> like":   0.5,
        "NP -> D N":   0.4,
        "D -> an":     1.0,
        "N -> arrow":  0.4,
    }

    prob2 = compute_tree_probability(tree2_rules)
    weight2 = -math.log2(prob2)

    print("\nParse Tree 2 (alternative reading):")
    print("  Structure: [NP time flies] [VP like [NP an arrow]]")
    print("\n  Rules used:")
    for rule, p in tree2_rules.items():
        print(f"    {rule:<25} p = {p}")
    print(f"\n  P(Tree 2) = {' x '.join(str(p) for p in tree2_rules.values())}")
    print(f"           = {prob2:.5f}")
    print(f"  Weight    = -log2({prob2:.5f}) = {weight2:.5f} bits")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  P(Tree 1) = {prob1:.5f}  (weight = {weight1:.5f})")
    print(f"  P(Tree 2) = {prob2:.5f}  (weight = {weight2:.5f})")
    print(f"\n  Tree 1 is {prob1/prob2:.2f}x more probable than Tree 2.")
    print("  A probabilistic parser would select Tree 1 as the best parse.")
    print("=" * 60)


if __name__ == "__main__":
    main()