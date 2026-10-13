# 20 - Evaluation

> **TL;DR.** A change to an LLM (large language model) system counts as an improvement only when a measurement says so, and evaluation makes that measurement routine. It is a pyramid of four tiers (unit, component, end-to-end, online), each scored by the cheapest metric family that can judge it (deterministic, LLM judge, human), with a golden set under the component and end-to-end tiers and a regression gate in CI (continuous integration) that blocks a drop larger than its tolerance. The judge is the workhorse and has four failure modes to manage: position, verbosity and self-preference, from the paper that named the method, and rubric drift.
>
> **Prerequisites:** [Post 11](../11-rag-in-depth/index.md).
> **Safe to skip?** Skip it if a golden set, a judge calibrated against human labels and a CI gate that blocks regressions already guard every change to the system.
>
> **After reading, you will be able to:**
>
> - Place a check on the four-tier evaluation pyramid and pick its metric family (deterministic, LLM judge or human) and its scoring shape (absolute or pairwise).
> - Wire a regression gate on a golden set that blocks a pull request when a metric drops by more than its tolerance, and read which cases flipped.
> - Define faithfulness, answer relevancy, context precision and context recall, and say which inputs each needs and what failure each catches.
> - Recognise position bias, verbosity bias, self-preference and rubric drift in an LLM judge, and apply the mitigation for each.
> - Choose the online signals to watch and turn each production incident into an offline fixture.

![A pyramid of four tiers from unit at the base to online at the top, each with what it checks and when it runs; the three offline tiers sit behind a CI gate on a golden set, and online incidents flow back into the golden set.](diagrams/00-hero-evaluation.svg)

*Cheap deterministic checks run on every commit at the base; the online tier is the slow source of truth, and its incidents flow back down as golden cases.*

---

## 1. The question: what turns changing a system into improving it?

A team without evaluation works in a loop: someone notices a bad output, edits the prompt, the bad case is fixed, and other cases regress unseen, until no one can say whether the last release was better than the one before. A fix can break cases far from it: a rule added to layer 01, the system prompt, can contradict an older rule, as two refund rules do in section 6 of [post 14](../14-system-prompt-as-software/index.md). The failure modes of [post 06](../06-context-failure-modes/index.md) name what breaks; only a measurement before and after a fix says whether it was cured.

The fix is structural: every component gets a fixed test set, a metric, and a gate that acts on the metric. [Post 11](../11-rag-in-depth/index.md) built the minimum version for a retrieval pipeline and post 14 one for a system prompt (each in its section 6); this post generalises both into one harness. It is the discipline classical software adopted with automated tests, with one difference: a model's output varies between runs and rarely has one correct string, so the tests need scores, tolerances and, for qualities no string comparison captures, a judge.

---

## 2. The four-tier evaluation pyramid

This post says "tier" for the levels of the pyramid, so that "layer" keeps its series meaning, one of the six layers of the window.

**Unit.** The deterministic code around the model: chunkers, parsers, schema validators, the prompt assembler. Ordinary tests (pytest, Jest), run on every commit.

**Component.** Each piece that uses a model or ranks for one, scored alone: a retriever by recall@N, the fraction of the relevant chunks in the top-N candidates for the golden questions; a reranker by precision@k or nDCG@5 (normalised discounted cumulative gain over the top 5, which rewards relevant items placed higher); an intent classifier by its agreement with human labels, a prompt block with free-text output by a judge. Run on every pull request that touches the component.

**End-to-end.** The full pipeline on real questions, scored by application-level checks: the right answer, a real source cited, the right tool called. Cases cost more, so there are fewer; the author's rule of thumb is 50 to 200 (illustrative). Run on every pull request that touches what the answer depends on.

**Online.** Production traffic and its signals (section 7): the source of truth, and the slowest loop.

With only end-to-end evaluation a team cannot tell which component broke; with only unit tests it ships components that pass alone and fail together. Frequency and cost in the figure are an order, not numbers.

**Golden sets.** The component and end-to-end tiers rest on a golden set: a fixed, human-checked collection of inputs with the expected output that defines "correct" for that component, such as questions with the passages that should come back, or tasks with the answer, its source and the tool call. Grow it from real failures: every production incident becomes a new case (section 7). Keep it small and reviewed rather than large and generated; the author's rule of thumb is that fifty carefully labelled cases catch more regressions than a thousand noisy ones, because a wrong label fails a good change. Label each case by its answer phrase, not by chunk id, so that a chunker change cannot move the labels ([post 11](../11-rag-in-depth/index.md), section 10). The golden set is the asset; the harness is replaceable.

---

## 3. The three families of metrics

Each tier can be scored in three ways; the figure below places each family on the tiers it serves.

![A table of the four tiers by the three metric families, an example metric in each cell: deterministic checks at every tier, the judge from the component tier up, people labelling the golden set, calibrating the judge and giving feedback online.](diagrams/01-metric-families.svg)

*Read a row for the options at one tier, a column for where each family pays: deterministic checks everywhere, the judge for the end-to-end bulk, people to calibrate the judge.*

**Deterministic.** Exact match, JSON (JavaScript Object Notation) schema validity, a regular expression, citation validity, recall@N against labelled passages. Cheap, repeatable and narrow: usable wherever the right answers can be written down.

**LLM judge.** A second model grades the output against a rubric: far cheaper than human labelling, noisier than a deterministic check, since the same output can score differently on two runs. On their benchmark, Zheng et al. (2023) found GPT-4 as a judge agreeing with human preferences over 80% of the time, the level at which humans agree with each other. With its failure modes managed (section 6), it carries the end-to-end tier.

**Human.** A person labels outputs against the rubric: slowest, most expensive, and the only ground truth for subjective qualities (tone, helpfulness). Its main job is calibration: a regular sample labelled by people and by the judge shows whether the judge still agrees; the author's rule of thumb is fifty to a hundred outputs per release (illustrative).

**Absolute or pairwise.** Absolute scoring (Zheng et al. call it single answer grading) rates one output alone: "faithful: yes or no", "helpfulness: 1 to 5". Pairwise scoring shows two outputs and asks which is better. Zheng et al. state the trade: absolute results "may become unstable, as absolute scores are likely to fluctuate more than relative pairwise results if the judge model changes", while the number of pairs grows quadratically with the candidates. Chatbot Arena collects human preferences as pairwise votes (Chiang et al., 2024). A regression gate needs absolute scores, a number per output to threshold; a common arrangement picks between two variants pairwise and guards the winner absolutely.

---

## 4. The minimum harness

A starter layout, one folder per tier plus the versioned judge prompts (counts illustrative):

```text
fixtures/
  unit/
    test_chunker.py            # pytest
  component/
    retriever_questions.yml    # 100 questions -> expected passages
  end_to_end/
    support_tasks.yml          # 50 tasks with answer, source, tool call
  judge_prompts/
    faithfulness_v3.md
```

The runner on top is interchangeable; as their documentation describes them (consulted October 2026):

- **promptfoo**, for prompts: "matrix views" of outputs across prompts and inputs, with deterministic assertions (`contains`, `regex`, `is-json`) and model-assisted ones (`llm-rubric`).
- **Ragas**, for a RAG (retrieval-augmented generation) pipeline: the metrics of section 5, from samples with the fields `user_input`, `response`, `retrieved_contexts` and `reference`.
- **DeepEval**, one harness across tiers: it "plugs into Pytest" and lists RAG, agent and safety metrics.
- **LangSmith** (LangChain), hosted: evaluators over datasets before shipping and over production traffic after.
- A **custom orchestrator** on pytest, such as this post's companion.

Having one matters more than which; the author's estimate for a first setup is about one engineering week (illustrative).

**The gate.** The harness runs in CI on every pull request, and its last step decides:

```yaml
# .github/workflows/eval.yml (sketch)
on: pull_request
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/unit
      - run: python eval/run.py end_to_end
      - run: python eval/check_regression.py   # exits non-zero on a regression
```

The companion's `check_regression(current, baseline, tolerance=0.05)` fails when any baseline metric falls by more than the tolerance (an absolute drop on a score between 0 and 1; its README calls 0.05 a default to set per metric) or is missing. A failed gate exits non-zero, and the pull request cannot merge.

**The gate on a twenty-case golden set.** The snippet `eval_gate.py` runs that gate against the toy pipeline of [post 11](../11-rag-in-depth/index.md): BM25 (Best Matching 25) and a character-trigram ranker over headed chunks, fused by reciprocal rank fusion. The golden set is post 11's ten questions plus ten more over the same four documents, each labelled by a phrase only its answer-bearing chunks contain. With no model offline, the answer is a stand-in, the text of the top-ranked chunk, so `answer_match` (the companion's containment check: is the gold phrase inside the answer, ignoring case and spacing) asks whether the first chunk carries the answer. `context_recall@3` is the share of each case's relevant chunks in the top 3, averaged over cases. Three changes to post 11's pipeline drop the BM25 half, the contextual headers, or both. Running `uv run python posts/20-evaluation/snippets/eval_gate.py` from the series root prints:

```text
golden set: 20 cases (10 from post 11, 10 added), 17 chunks
run                  context_recall@3  answer_match  gate, tolerance 0.05
baseline (post 11)              0.950         0.750  saved
BM25 dropped                    0.925         0.750  pass
headers dropped                 0.875         0.700  blocked by context_recall@3
both dropped                    0.800         0.700  blocked by context_recall@3
BM25 dropped: recall fell on g02 g07, rose on g06; match fell on g02 g07, rose on g04 g05
headers dropped: recall fell on g03 g17; match fell on g07 g14, rose on g05
both dropped: recall fell on g04 g07 g17; match fell on g02 g07, rose on g05
one case on 20 moves a score by 0.050
one-case drops of 20 blocked by cur < base - 0.05: 0.20, 0.40; by check_regression: none
```

The figure below draws each drop against the tolerance.

![Bars of the drop from the baseline for each change and metric against a dashed tolerance line at 0.05. BM25 dropped: recall 0.025, answer match 0, passes. Headers dropped: recall 0.075, answer match 0.05, blocked. Both dropped: recall 0.15, answer match 0.05, blocked.](diagrams/02-gate-run.svg)

*A drop has to pass the line to block; one case on twenty sits exactly on it.*

Dropping the headers is blocked: recall falls by 0.075 as cases g03 and g17 lose some or all of their passages. Dropping BM25 passes, yet its mean hides four flips: `answer_match` fell on g02 and g07 and rose on g04 and g05. Reading the flipped cases, as post 11 recommends, shows that a passing change still broke two questions. Without the headers, `answer_match` falls by exactly 0.05, one net case, and that metric passes: the gate fires only on a drop larger than the tolerance, and on twenty cases one case is 0.05, so the size of the set sets the gate's resolution. Under a real model the tolerance must also clear run-to-run noise (section 5).

**Caching and sampling.** Model calls in the harness are cached by a hash of prompt, model and parameters, so a repeated fixture costs nothing. Pull requests run a subset (say 50 of 200 end-to-end tasks, illustrative), nightly runs the full set, and a release adds a human sample.

---

## 5. The retrieval metrics (Ragas)

Ragas began as a paper (Es et al., 2023) that defined three reference-free metrics: faithfulness, answer relevance and context relevance. The library's documentation (Ragas, "Available metrics", consulted October 2026) lists the four the series uses:

- **Faithfulness** "measures how factually consistent a response is with the retrieved context": the claims in the response that the context supports, divided by all its claims. It catches unsupported answers. Inputs: question, response, retrieved contexts.
- **Answer relevancy** "measures how relevant a response is to the user input": a model writes questions the response would answer (three by default), and the score is the mean cosine similarity of their embeddings to the user's question. It catches answers that drift. Inputs: question, response.
- **Context precision** evaluates "the retriever's ability to rank relevant chunks higher than irrelevant ones": the mean of precision@k at the position of each relevant retrieved chunk. It catches noise in layer 04, retrieved chunks, and good chunks ranked low. Inputs: question, retrieved contexts, and a reference answer (or the response, in a reference-free variant).
- **Context recall** "measures how many of the relevant documents (or pieces of information) were successfully retrieved": with a judge, the share of the reference answer's claims that the retrieved context supports. It catches missed evidence, and it always needs a reference: an answer, reference contexts, or reference ids, in an ID-based variant that needs no model and that the companion's `context_recall@3` follows. Two deterministic checks complete a RAG dashboard: **citation validity** (every cited source id is in the retrieved set) and **citation presence** (the answer cites at least one source).

**The noise floor.** Every judged metric has a noise floor: the spread between runs of the unchanged harness on the same fixtures. A drop smaller than the floor cannot be told from a re-roll, so the tolerance has to sit above it; measure it by running the unchanged suite several times with the cache off. The size of the golden set adds a second limit. On $n$ cases one case moves a mean by $1/n$, and post 11's standard error $\sqrt{p(1-p)/n}$ says how far a score on the set may sit from the score on all traffic: for $n = 20$ and $p = 0.75$, about 0.097, nearly two cases. A gate on twenty cases can say these twenty got worse, not that traffic got worse by less than about 0.1.

---

## 6. The four LLM-judge failure modes

Zheng et al. (2023) gave the approach its name ("We call this approach 'LLM-as-a-judge'") and examined its limitations: position bias, verbosity bias, self-enhancement bias, and limited capability in grading maths and reasoning. The series' four failure modes take the first three and add rubric drift. The paper's fourth has its own fix: a judge given a reference answer it wrote first failed on 3 of 20 maths judgements instead of 14 (Table 4).

![Two cited charts from Zheng et al. 2023. Verdicts unchanged when the answers swap places: 23.8 percent for Claude-v1, 46.2 for GPT-3.5, 65.0 for GPT-4, 77.5 for GPT-4 with few-shot examples. Padded answer preferred: 91.3 percent for Claude-v1 and GPT-3.5, 8.7 for GPT-4.](diagrams/03-judge-biases.svg)

*The strongest judge tested kept its verdict under a swap two times in three; the weaker ones preferred a padded answer almost every time.*

- **Position bias.** In pairwise judging, the judge favours one position. The paper judged two similar answers to each first-turn question of MT-bench (its 80 multi-turn questions) in both orders: GPT-4 kept its verdict after the swap in 65.0% of cases and favoured the first answer in 30.0%; Claude-v1 was consistent in 23.8% and favoured the first in 75.0% (Table 2), as the figure above shows. Mitigation: judge both orders and declare a win only when the same answer wins both, a tie otherwise, the paper's conservative approach; or score absolutely. Few-shot examples in the judge prompt raised GPT-4's consistency to 77.5%, at the price of a longer prompt.
- **Verbosity bias.** The judge favours a longer answer that is not better. The paper's "repetitive list" attack padded 23 answers with a rephrased copy of their own list; the padded answer won in 91.3% of cases for Claude-v1 and GPT-3.5 and 8.7% for GPT-4 (Table 3). Mitigation: tell the rubric to ignore length, and test the judge on padded answers.
- **Self-preference.** The judge favours answers from its own model. The paper's term is self-enhancement bias; it saw GPT-4 favour itself with a 10% higher win rate and Claude-v1 with a 25% higher one, and concluded that its limited data could not determine whether the bias exists. Mitigation, cheap enough to apply on suspicion: a judge from another model family, or several judges averaged.
- **Rubric drift.** Over months, the judge's reading of the rubric on edge cases moves from what "good" meant at calibration, as the judge model is upgraded, its prompt edited, the mix of cases shifted. The paper does not measure it. Mitigation: version the judge prompt and model like code, re-score a human-labelled sample on a schedule, and re-score the saved baseline whenever the judge changes.

---

## 7. Online evaluation

The online tier is what the offline pyramid approximates. The signals worth watching:

- **Task completion.** Did the user get what they came for? Instrument it where a workflow has a success state; otherwise use end-of-session labels or a judge over sampled transcripts.
- **Explicit feedback.** Thumbs up and down: cheap, sparse, and given only by users who choose to. A smoke alarm, not a primary metric.
- **Refusal rate.** A sudden jump can mean a new prompt or rule is over-firing.
- **Cost per session.** A rise may point at a context bug: bloat, repeated retrieval, sub-agent loops ([post 22](../22-observability/index.md) traces it).
- **Latency at the 95th percentile (p95).** An average hides the slowest request in twenty.

The rule that joins the tiers: every online incident produces an offline fixture. The incident becomes a case in the golden set, and the case stays, so the same bug cannot return unseen.

---

## 8. What changes once evaluation exists

With a gate in CI, a prompt edit is an ordinary diff that passes or fails, a pipeline rewrite is checked case by case, and a new engineer gets feedback from one CI run. The cost is the setup week and the gate's run time per pull request (illustratively twenty minutes), against every change that would otherwise ship on a guess.

---

## 9. Make it run

The companion [`code/20-eval-ragas`](../../code/20-eval-ragas/) holds `evalkit`: a dependency-free offline core (`load_golden_set`, `score_run`, `check_regression`, `recall_at_k`, `answer_match`) and a judge scaffold, `evalkit.judge.faithfulness(answer, context)`, that needs an API (application programming interface) key and is not run here; Ragas is an optional extra, not installed in the series environment. The six offline tests run from the series root:

```text
uv run --with pytest python -m pytest -p no:cacheprovider code/20-eval-ragas/tests
```

They end with `6 passed` in under a second. The companion's fixture `tests/fixtures/golden_set.json` holds three cases, enough for its tests; the twenty-case set of section 4 is built by the snippet, which imports `evalkit` from `code/20-eval-ragas/src` and post 11's pipeline from its snippet, and prints in under a second:

```text
uv run python posts/20-evaluation/snippets/eval_gate.py
```

---

## 10. What can go wrong?

- **A tolerance that equals one case.** With twenty cases and a tolerance of 0.05, a one-case drop sits on the boundary, and floating point decides it. The snippet's last line tries all twenty one-case drops: `cur < base - 0.05` blocks those from 0.20 and 0.40, because 0.20 minus 0.05 is computed as slightly more than 0.15, while the companion's gate, which allows $10^{-9}$ of rounding, blocks none. Set the tolerance between multiples of $1/n$ (0.075 for twenty cases, illustrative).
- **A passing mean that hides flips.** A change breaks two cases and fixes two others, and the gate passes. Print the cases that fell on every run and read them before merging.
- **A noise floor measured with the cache on.** Every rerun returns the cached verdict, the floor reads as zero, and a tolerance set from it fails real reruns at random.
- **A judge changed with the system.** Judge prompt and system prompt change in one pull request, and no one can say which moved the scores. Change one at a time, and re-score the baseline under a new judge.
- **Tuning on the golden set.** Rules written while looking at the golden cases overstate quality on new traffic, as [post 17](../17-advanced-retrieval/index.md) shows for its router. Keep a held-out slice no one tunes against.

---

## Common pitfalls

1. **No fixtures.** Without a golden set every discussion of quality is anecdote.
2. **Only end-to-end evaluation.** Too slow and too coarse to say which component regressed.
3. **A judge with no calibration.** Its scores drift from human judgement and no one notices.
4. **The same model judging itself.** Self-preference may inflate the scores; a judge from another family removes the doubt.
5. **No cost cap on the evaluation.** The bill makes the team run it less, the gate becomes optional, and the system goes back to changing without improving.

---

## Further reading

- Zheng, L. *et al.*, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (NeurIPS 2023): Tables 2 to 4.
- Chiang, W.-L. *et al.*, "Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference" (ICML 2024).
- Es, S. *et al.*, "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (EACL 2024 demo), and the Ragas "Available metrics" documentation (consulted October 2026).
- Liu, Y. *et al.*, "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment" (EMNLP 2023).
- Saad-Falcon, J. *et al.*, "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems" (NAACL 2024).
- promptfoo, DeepEval and LangSmith evaluation documentation (consulted October 2026).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 21 - Structured output and guardrails](../21-structured-output-guardrails/index.md):** the runtime checks that enforce on every response what this harness measures offline.
- **[Post 22 - Observability, tracing, and cost](../22-observability/index.md):** the traces that turn online incidents into the golden cases of this post.
