#!/usr/bin/env python3
"""
Probabilistic Earley parser.
Usage: ./parse.py grammar.gr sentences.sen

For each sentence, prints the minimum-weight (= maximum-probability)
parse tree followed by its weight, or NONE if no parse exists.
Output format matches arith.par (pipe through prettyprint for spacing).
"""

from __future__ import annotations
import argparse
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(Path(__file__).stem)


# ---------------------------------------------------------------------------
# Grammar
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    """A PCFG rule  LHS -> RHS  with weight = -log2(prob)."""
    lhs:    str
    rhs:    Tuple[str, ...]
    weight: float = 0.0

    def __repr__(self) -> str:
        return f"{self.lhs} -> {' '.join(self.rhs)}"


class Grammar:
    def __init__(self, start_symbol: str, *files: Path) -> None:
        self.start_symbol = start_symbol
        self._expansions: Dict[str, List[Rule]] = {}
        for f in files:
            self._load(f)

    def _load(self, path: Path) -> None:
        with open(path) as f:
            for line in f:
                line = line.split("#")[0].rstrip()
                if not line:
                    continue
                prob_str, lhs, rhs_str = line.split("\t")
                prob   = float(prob_str)
                weight = -math.log2(prob) if prob > 0 else math.inf
                rhs    = tuple(rhs_str.split())
                rule   = Rule(lhs=lhs, rhs=rhs, weight=weight)
                self._expansions.setdefault(lhs, []).append(rule)

    def expansions(self, lhs: str) -> List[Rule]:
        return self._expansions.get(lhs, [])

    def is_nonterminal(self, symbol: str) -> bool:
        return symbol in self._expansions


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Item:
    """
    An Earley chart item: (start_position, rule, dot_position).
    Immutable and hashable so it can be used as a dict key for O(1) lookup.
    """
    rule:           Rule
    dot_position:   int      # 0 = before first rhs symbol
    start_position: int      # input position where this item started

    def next_symbol(self) -> Optional[str]:
        if self.dot_position >= len(self.rule.rhs):
            return None
        return self.rule.rhs[self.dot_position]

    def with_dot_advanced(self) -> Item:
        return Item(self.rule, self.dot_position + 1, self.start_position)

    def is_complete(self) -> bool:
        return self.dot_position == len(self.rule.rhs)

    def __repr__(self) -> str:
        rhs = list(self.rule.rhs)
        rhs.insert(self.dot_position, "·")
        return f"({self.start_position}, {self.rule.lhs} -> {' '.join(rhs)})"


# ---------------------------------------------------------------------------
# Column
# ---------------------------------------------------------------------------

class Column:
    """
    All items whose right edge is at position j.

    Key data structures:
      _entry       : Item -> {'weight': float, 'bp': backpointer}
                     O(1) lookup for duplicate detection and weight retrieval.
      _queue       : FIFO list of items to process (may contain duplicates
                     when an item is re-enqueued after a weight improvement).
      _next        : index of next item to pop from _queue.
      _waiting_for : symbol -> [items with that symbol after the dot].
                     Built incrementally; gives O(1) customer lookup in attach.
      _predicted   : set of nonterminals already predicted here.
                     Enables the O(1) batch duplicate check in predict.
    """

    def __init__(self) -> None:
        self._entry:       Dict[Item, Dict]       = {}
        self._queue:       List[Item]             = []
        self._next:        int                    = 0
        self._waiting_for: Dict[str, List[Item]]  = {}
        self._predicted:   set                    = set()

    # ------------------------------------------------------------------ push

    def push(self, item: Item, weight: float, bp=None) -> None:
        """
        Add item to this column.

        If item is NEW:
          - record in _entry
          - append to _queue
          - index in _waiting_for

        If item is a DUPLICATE:
          - if new weight < stored weight: update _entry and re-enqueue
            (re-enqueue so the improved weight propagates to dependants)
          - otherwise: discard silently

        The _entry hash table makes the duplicate check O(1).
        Without it, we would scan _queue linearly: O(n) per push,
        degrading total complexity from O(n^3) to O(n^4).
        """
        if item not in self._entry:
            self._entry[item] = {"weight": weight, "bp": bp}
            self._queue.append(item)
            nxt = item.next_symbol()
            if nxt is not None:
                self._waiting_for.setdefault(nxt, []).append(item)
        else:
            if weight < self._entry[item]["weight"]:
                self._entry[item]["weight"] = weight
                self._entry[item]["bp"]     = bp
                # Re-enqueue for reprocessing (see reading section B.2).
                # The item may be popped again; when _attach fires it will
                # propagate the lower weight to downstream items.
                self._queue.append(item)

    # ------------------------------------------------------------------ pop

    def pop(self) -> Optional[Item]:
        if self._next >= len(self._queue):
            return None
        item = self._queue[self._next]
        self._next += 1
        return item

    def __bool__(self) -> bool:
        return self._next < len(self._queue)

    # ------------------------------------------------------------------ accessors

    def weight(self, item: Item) -> float:
        return self._entry[item]["weight"]

    def bp(self, item: Item):
        return self._entry[item]["bp"]

    def customers_of(self, symbol: str) -> List[Item]:
        """O(1) hash lookup: items waiting for `symbol` after their dot."""
        return self._waiting_for.get(symbol, [])

    def all_items(self) -> List[Item]:
        return list(self._entry.keys())

    def already_predicted(self, nt: str) -> bool:
        return nt in self._predicted

    def mark_predicted(self, nt: str) -> None:
        self._predicted.add(nt)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class EarleyParser:
    def __init__(self, tokens: List[str], grammar: Grammar) -> None:
        self.tokens  = tokens
        self.grammar = grammar
        n = len(tokens)
        self.cols: List[Column] = [Column() for _ in range(n + 1)]
        self._run()

    # ------------------------------------------------------------------ main loop

    def _run(self) -> None:
        """Fill the Earley chart left to right."""
        self._predict(self.grammar.start_symbol, 0)

        for j, col in enumerate(self.cols):
            while col:
                item = col.pop()
                nxt  = item.next_symbol()
                if nxt is None:
                    self._attach(item, j)
                elif self.grammar.is_nonterminal(nxt):
                    self._predict(nxt, j)
                else:
                    self._scan(item, j)

    # ------------------------------------------------------------------ predict

    def _predict(self, nt: str, j: int) -> None:
        """
        Predict all rules for nonterminal `nt` in column j.

        BATCH DUPLICATE CHECK: if `nt` has already been predicted in column j,
        skip the entire batch in O(1) via the _predicted set.

        Without this check, every time any item in column j needs `nt` after
        its dot, we would call push() for every rule of `nt` — potentially
        hundreds of NP rules in wallstreet.gr — even though they are all
        already in the column. The batch check makes predict O(1) amortised
        per nonterminal per column rather than O(|rules|) per trigger.

        Predicted items get weight 0 and no backpointer.
        Their rule weight is credited when the item completes (in _attach).
        """
        col = self.cols[j]
        if col.already_predicted(nt):
            return
        col.mark_predicted(nt)

        for rule in self.grammar.expansions(nt):
            new_item = Item(rule, dot_position=0, start_position=j)
            col.push(new_item, weight=0.0, bp=None)
            log.debug(f"    PREDICT {new_item}")

    # ------------------------------------------------------------------ scan

    def _scan(self, item: Item, j: int) -> None:
        """
        If tokens[j] matches the terminal after the dot, advance the dot
        into column j+1.

        weight(new) = weight(item) + rule.weight
        bp          = ("scan", item, token)
        """
        if j >= len(self.tokens):
            return
        token = self.tokens[j]
        if token != item.next_symbol():
            return

        new_item   = item.with_dot_advanced()
        # Do NOT add item.rule.weight here — the rule weight is added once,
        # when the rule fully completes, inside _attach.
        new_weight = self.cols[j].weight(item)
        self.cols[j + 1].push(new_item,
                               weight=new_weight,
                               bp=("scan", item, token))
        log.debug(f"    SCAN    {new_item}  w={new_weight:.4f}")

    # ------------------------------------------------------------------ attach

    def _attach(self, completed: Item, j: int) -> None:
        """
        Constituent  (i, A -> alpha .)  just completed in column j.
        Find every customer in column i waiting for A, advance its dot,
        push result into column j.

        CUSTOMER INDEX: cols[i].customers_of(A) is an O(1) hash lookup
        returning a pre-built list. Without this index, attach would scan
        all of column i in O(n), making total time O(n^4) instead of O(n^3).

        WEIGHT ACCOUNTING:
          weight(new) = weight(customer) + weight(completed) + completed.rule.weight

        We add completed.rule.weight here — once, when the rule completes —
        so the total weight of any parse tree equals the sum of -log2(p)
        over all rules used, which equals -log2(product of probabilities).

        bp = ("attach", customer_item, completed_item)
        """
        i   = completed.start_position
        lhs = completed.rule.lhs
        w_c = self.cols[j].weight(completed)

        for customer in self.cols[i].customers_of(lhs):
            new_item   = customer.with_dot_advanced()
            w_k        = self.cols[i].weight(customer)
            new_weight = w_k + w_c + completed.rule.weight

            self.cols[j].push(new_item,
                               weight=new_weight,
                               bp=("attach", customer, completed))
            log.debug(f"    ATTACH  {new_item}  w={new_weight:.4f}")

    # ------------------------------------------------------------------ result

    def best_parse(self) -> Optional[Tuple[str, float]]:
        """
        Find the lowest-weight complete ROOT item spanning [0..n].
        Returns (tree_string, weight) or None if the sentence is not accepted.
        """
        best_item   = None
        best_weight = math.inf

        for item in self.cols[-1].all_items():
            if (item.rule.lhs        == self.grammar.start_symbol
                    and item.is_complete()
                    and item.start_position == 0):
                w = self.cols[-1].weight(item)
                if w < best_weight:
                    best_weight = w
                    best_item   = item

        if best_item is None:
            return None

        tree = self._build_tree(best_item, len(self.cols) - 1)
        return tree, best_weight

    # ------------------------------------------------------------------ tree reconstruction

    def _build_tree(self, item: Item, end: int) -> str:
        """
        Recursively build the parse tree string for a complete item
        ending at column `end`.

        Returns:  (LHS child1 child2 ... childK)

        How it works:
          A complete item  A -> X Y Z .  was built by a chain of
          attach/scan steps.  We unwind this chain iteratively to
          collect the children in reverse order, then reverse them.

          At each step the backpointer is one of:
            None                      -> predicted item, no children
            ("scan",   prev, token)   -> last symbol was scanned terminal
            ("attach", customer, comp)-> last symbol was a completed constituent

          We follow the LEFT pointer (customer / prev) to get the
          item before the last child was added, and collect the
          LAST child from the right pointer.
        """
        children = []
        cur_item = item
        cur_end  = end

        while True:
            bp = self.cols[cur_end].bp(cur_item)

            if bp is None:
                # Predicted item — bottom of the chain, no more children
                break

            kind = bp[0]

            if kind == "scan":
                # ("scan", prev_item, token)
                _, prev_item, token = bp
                # The scanned symbol is the one just before the dot
                symbol = cur_item.rule.rhs[cur_item.dot_position - 1]
                children.append(f"({symbol} {token})")
                cur_end  -= 1
                cur_item  = prev_item

            elif kind == "attach":
                # ("attach", customer_item, completed_item)
                _, customer_item, completed_item = bp
                mid = completed_item.start_position
                # Recursively build the subtree for the completed child
                child_tree = self._build_tree(completed_item, cur_end)
                children.append(child_tree)
                cur_end  = mid
                cur_item = customer_item

            else:
                break

        children.reverse()
        return f"({item.rule.lhs} {' '.join(children)})"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grammar",   type=Path, help="Path to .gr file")
    parser.add_argument("sentences", type=Path, help="Path to .sen file")
    parser.add_argument("-s", "--start_symbol", default="ROOT",
                        help="Grammar start symbol (default: ROOT)")
    parser.add_argument("--print-chart", action="store_true", default=False,
                        help="Print the final Earley chart for each sentence")
    parser.set_defaults(logging_level=logging.WARNING)
    v = parser.add_mutually_exclusive_group()
    v.add_argument("-v", "--verbose", dest="logging_level",
                   action="store_const", const=logging.DEBUG)
    v.add_argument("-q", "--quiet",   dest="logging_level",
                   action="store_const", const=logging.WARNING)
    return parser.parse_args()


def print_chart(earley: EarleyParser, tokens: List[str]) -> None:
    """Print the complete Earley chart column by column."""
    words = ["(start)"] + tokens
    for j, col in enumerate(earley.cols):
        label = f"before '{tokens[0]}'" if j == 0 else f"after '{words[j]}'"
        print(f"\nColumn {j}  [{label}]")
        print("-" * 55)
        for item in col.all_items():
            bp = col.bp(item)
            op = "predict" if bp is None else ("scan" if bp[0] == "scan" else "attach")
            complete = " *" if item.is_complete() else ""
            print(f"  {str(item):<45} [{op}]{complete}")


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=args.logging_level)
    grammar = Grammar(args.start_symbol, args.grammar)

    with open(args.sentences) as f:
        for sentence in f:
            sentence = sentence.strip()
            if not sentence:
                continue
            log.debug("=" * 60)
            log.debug(f"Parsing: {sentence}")
            tokens = sentence.split()
            earley = EarleyParser(tokens, grammar)
            if args.print_chart:
                print(f"Sentence: {sentence}")
                print_chart(earley, tokens)
                print()
            result = earley.best_parse()
            if result is None:
                print("NONE")
            else:
                tree, weight = result
                print(tree)
                print(f"{weight:.5f}")


if __name__ == "__main__":
    main()