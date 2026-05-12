# 16 · Evaluation

> **TL;DR.** An agent that is not measured will degrade. Evaluation is the single discipline that separates teams that *improve* their LLM systems from teams that just *change* them. This post lays out the **four-layer eval pyramid** (unit → component → end-to-end → online), the **three families of metrics** (deterministic, programmatic-judge, human), and a **practical harness** built on `promptfoo`, `Ragas`, and a small custom CI gate. The lesson the field keeps re-learning: ship the eval before you ship the next change.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Pick the right metric for each layer of an LLM system.
> - Wire up a regression gate that blocks bad PRs.
> - Avoid the four common LLM-as-judge failure modes.

---

## 1. Why eval is the first discipline

A typical pre-eval team operates like this: someone notices an output is bad, edits the prompt, the bad case is fixed, three other cases regress silently, repeat. Six months in, the system is a forest of accumulated edits and nobody can say whether last week's release was better or worse than the one before.

The fix is structural. **Every component of an LLM system needs a deterministic test set, a metric, and a CI gate.** None of the techniques in the rest of this post matter without that frame.

This is the same discipline classical software adopted in the 1990s with unit testing. The mistake worth not repeating: it took the industry a decade to make unit tests universal because they were "obviously a luxury for serious projects". They were not. They were table stakes.

---

## 2. The four-layer eval pyramid

```
                 ┌──────────────┐
                 │  4. ONLINE   │  ← real users, real traffic
                 ├──────────────┤
                 │ 3. END-TO-END│  ← full pipeline on gold tasks
                 ├──────────────┤
                 │ 2. COMPONENT │  ← retriever, reranker, prompt block
                 ├──────────────┤
                 │   1. UNIT    │  ← deterministic functions
                 └──────────────┘
```

**Layer 1 — Unit.** The deterministic helpers around the LLM: chunkers, parsers, schema validators, query rewriters that do not call the model. Standard pytest / Jest. Run on every commit.

**Layer 2 — Component.** The individual LLM-using pieces: a retriever ("recall@10 on the gold question set"), a reranker ("nDCG@5"), a prompt block ("does the classifier agree with humans on 100 fixtures"). Each component has its own metric and its own fixture set. Run on every PR that touches the component.

**Layer 3 — End-to-end.** The full pipeline answering real questions. The metrics are application-level: did the agent return the right answer; did it cite a real source; did it call the right tool. Slower, more expensive, fewer fixtures (50–200 typically). Run on every PR that touches anything load-bearing.

**Layer 4 — Online.** Production traffic, real users, the metrics that actually matter to the business: thumbs-up rate, escalation rate, task completion, latency at p95, cost per session. The truth source; the slowest feedback loop.

The pyramid is the right shape because each layer catches different bugs at different speeds. A team that has only end-to-end eval will be too slow to iterate; a team that has only unit eval will ship beautiful components that combine into a broken product.

---

## 3. The three families of metrics

Each layer can be scored in three ways.

**Deterministic.** Exact match, JSON schema validity, regex match, BLEU/ROUGE for translation, citation-presence-and-validity. Cheap, repeatable, narrow. Use wherever the answer space is constrained enough to enumerate.

**Programmatic-judge ("LLM-as-judge").** A second LLM evaluates the first's output against a rubric. Wide applicability, dramatically cheaper than human labelling, much louder than deterministic scoring. The judge has its own failure modes (covered in §6); used disciplined, it is the workhorse of layer-3 eval.

**Human.** A person labels each output as good / bad / partial against a rubric. Slowest, most expensive, the only true ground truth for subjective qualities (tone, helpfulness, sensitivity). Sample 50–100 outputs per release; treat as the calibration source for the LLM-judge.

The pattern that works: deterministic where you can, programmatic-judge for the bulk, human on a regular sample to keep the judge honest.

---

## 4. The minimum harness

A concrete starter stack — used at this exact level by serious teams shipping LLM systems in 2025:

```
fixtures/
  unit/
    chunker_test.py             # pytest
  component/
    retriever_questions.yml     # 100 query → expected-doc-id pairs
    classifier_fixtures.yml     # 50 input → expected-label pairs
  end_to_end/
    customer_support.yml        # 50 multi-turn task transcripts
  judge_prompts/
    citation_check.md
    helpfulness_rubric.md
```

The runner can be `promptfoo` (good for prompt regression and LLM-judge), `Ragas` (RAG-specific metrics: faithfulness, answer relevance, context precision/recall), `DeepEval` (broad framework with a wide built-in metric library), or a small custom orchestrator on top of pytest. The choice matters less than *having one*; the budget for the team's first eval setup should be one engineering week.

The gate sits in CI:

```yaml
# .github/workflows/eval.yml (sketch)
on: pull_request
jobs:
  eval:
    steps:
      - run: pytest tests/unit
      - run: python eval/run.py component
      - run: python eval/run.py end_to_end
      - run: python eval/check_regression.py    # blocks if drop > noise floor
```

Two operational choices that make the difference between an eval people actually run and an eval that rots:

- **Caching.** LLM calls in the eval are cached by `(prompt, model, params)` hash. The same fixture run twice costs zero the second time. Without this, the bill kills the practice.
- **Sampling for cost control.** End-to-end eval on a 200-task set costs real money. PR runs use a 50-task subset; nightly runs use the full set; releases use the full set + human sample. The right gradient.

---

## 5. The retrieval-specific metrics (Ragas family)

For RAG systems, four metrics are worth wiring up before the others:

- **Faithfulness.** Does every claim in the answer follow from the retrieved sources? An LLM-judge prompt that walks through claim-by-claim. Catches hallucination.
- **Answer relevance.** Does the answer address the question asked? Catches drift.
- **Context precision.** Of the retrieved chunks, what fraction are actually relevant? Catches over-retrieval.
- **Context recall.** Of the chunks needed to answer, what fraction were retrieved? Catches under-retrieval.

Ragas computes these automatically given `(question, answer, retrieved_contexts, ground_truth)` tuples. They are not perfect — every LLM-judge metric has noise — but they are good enough to detect regressions of 5 % or more, which is the bar that matters.

Pair these with two cheaper metrics: **citation validity** (does every cited source id exist in the retrieved set? deterministic) and **citation presence** (is at least one citation in the answer? deterministic). Together with the four LLM-judged metrics, these six numbers form the dashboard for a production RAG.

---

## 6. The four LLM-judge failure modes

LLM-as-judge is indispensable and treacherous in equal measure. The four ways it goes wrong:

- **Position bias.** When asked to compare two outputs A and B, the judge prefers whichever is presented first. Mitigation: present in both orders, average; or use a rubric-based absolute score instead of pairwise.
- **Length bias.** Longer answers score higher even when they are not better. Mitigation: normalise rubric items so length is not implicitly rewarded; use a length-aware judge prompt.
- **Self-preference.** A judge prefers outputs that look like its own. Mitigation: use a different model family for the judge than the one being evaluated, or use multiple judges and average.
- **Rubric drift.** The judge interprets the rubric loosely on edge cases; over time, "good" means something different from what it did at calibration. Mitigation: re-calibrate against human labels every few weeks; version the judge prompt.

A useful operational rule: **publish the judge prompt and version it like code.** Many teams treat the judge as infrastructure that does not need review; this is the same mistake as treating the system prompt as scratch.

---

## 7. Online evaluation

Layer 4 is what the offline pyramid is ultimately approximating. The metrics that matter:

- **Task completion.** Did the user end the session having achieved what they came for? For workflows with a clear success state, instrument it. For open-ended assistants, use end-of-session labelling (the user marks it themselves) or a periodic LLM-judge over sampled transcripts.
- **Thumbs / explicit feedback.** Cheap signal, sparse data, biased toward complaints. Useful as a smoke alarm; not a primary metric.
- **Refusal rate.** Sudden jumps signal a recent prompt or rule change is over-firing.
- **Cost per session.** Drift here is the leading indicator of a context-engineering bug — context bloat, repeated retrieval, sub-agent loops.
- **Latency p95.** The user cares about p95, not average. Surface it.

The rule for connecting online to offline: every online incident should generate an offline fixture. The fixture lives forever; the incident becomes the regression test.

---

## 8. The practice — what changes when you have eval

Three things shift the day you have an eval gate in CI.

- **Prompt edits stop being scary.** A diff is a diff; the gate either passes or it does not.
- **Refactoring becomes possible.** The retrieval pipeline was held together with sticky tape because nobody could verify a rewrite. Now they can.
- **Onboarding accelerates.** New engineers can change things and get fast feedback. Tribal knowledge stops being load-bearing.

The cost is one engineering week to set up and ~20 minutes per PR for the gate to run. The teams that have made this trade report it as the single best thing they did to ship faster.

---

## Common pitfalls

- **No fixtures.** Without them every conversation is anecdote.
- **Only end-to-end eval.** Too slow and too coarse to catch component regressions.
- **LLM-judge with no calibration.** The metric drifts; nobody notices.
- **Same model judging itself.** Self-preference inflates scores 10–20 %.
- **No regression gate.** The eval exists; nothing acts on it.
- **No cost cap on the eval.** The bill scares the team into running it less; the gate becomes optional; the system rots.

---

## Further reading

- Es, S. *et al.*, *"Ragas: Automated Evaluation of Retrieval Augmented Generation"* (2023).
- Liu, Y. *et al.*, *"G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment"* (2023).
- Saad-Falcon, J. *et al.*, *"ARES: An Automated Evaluation Framework for RAG"* (2023).
- Anthropic Engineering, *"Evaluating models"* (2024) — practical guide.
- promptfoo docs; DeepEval docs; LangSmith eval docs.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 17 — Observability, tracing, cost](../17-observability/index.md)** — the production side of the eval loop.
- **[Post 18 — Security and prompt injection](../18-security/index.md)** — the failure modes the eval gate cannot catch.
- **[Post 19 — Long context vs RAG](../19-long-context-vs-rag/index.md)** — using eval to make the architecture choice.
