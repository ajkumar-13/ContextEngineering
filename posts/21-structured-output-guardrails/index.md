# 21 · Structured output and guardrails

> **TL;DR.** Everything before this post shapes the model's *input*; structured output and guardrails are the control surface on its *response*. A fluent answer that will not parse is a production incident, so this post covers the mechanisms that make output typed and valid (JSON Schema and `response_format`, tool-call arguments, Pydantic / Instructor / Outlines, and grammar-constrained decoding), the reliability loop that recovers from the failures that remain (validate, feed the error back, retry), and the guardrail layer that enforces content, safety, and privacy rules at runtime. Where evaluation ([Post 20](../20-evaluation/index.md)) *measures* quality offline, guardrails *enforce* it on every live response.
>
> **After reading this you will be able to:**
> - Choose the right output mechanism (`response_format`, tool call, or constrained decoding) for a given task.
> - Wire a validate-and-retry loop that turns a malformed response into a valid one instead of an exception.
> - Assemble an output-side guardrail layer (schema, moderation, PII filtering, refusal handling) that complements the input-side six layers.

![Response control loop: model output enters a validate-against-schema gate; valid output passes through a moderation and redaction gate and is returned, while invalid output loops back with the error appended for a capped retry.](diagrams/00-hero-structured-output-guardrails.svg)
*Guardrails are the control surface on the response: validate against a schema, retry on failure, moderate before returning.*

---

## 1. A fluent answer that will not parse is an incident

The six layers of context ([Post 02](../02-six-layers-of-context/index.md)) are all input-side: they decide what the model sees. But a system in production is judged on what the model *returns*, and the rest of the pipeline almost never wants prose. It wants a record: a classification label a router will branch on, an extraction result a database will store, a set of arguments a function will execute. When the model returns a paragraph where a JSON object was expected, a JSON object with a trailing comma, or a plausible answer wrapped in an apologetic preamble, the downstream service does not degrade gracefully. It throws.

This is the failure the input layers cannot prevent. A prompt can be perfectly assembled and the model perfectly capable, and the call still fails because the *shape* of the response was never constrained. In a chat window a stray sentence is harmless; in an automated pipeline it is a `JSONDecodeError` at 3 a.m., a dropped order, or a silent fallback that ships wrong data. For any programmatic consumer, an unparseable response is not a quality problem to be nudged with better wording. It is a control problem to be solved with a mechanism.

[Post 15](../15-tools-and-mcp/index.md), §9 gave the primer: tool calling and structured output are two views of the same machinery. This post is the deep treatment of the output side, from the wire format up through the guardrail layer that sits around it.

---

## 2. The mechanisms that make output typed

![Four rungs of output guarantee, from a prompt instruction up to grammar-constrained decoding, each with what it still leaves to you](diagrams/01-guarantee-ladder.svg)

*The last column is the one that matters at design time: which rung you are on decides how much defensive code you still owe.*

There is a ladder of guarantees here, from "asked nicely" at the bottom to "valid by construction" at the top. Knowing which rung a given technique sits on tells you exactly how much defensive code you still need downstream.

**JSON Schema and `response_format`.** Every major provider now accepts a schema alongside the prompt and a flag that says "return an object matching this". OpenAI exposes it as `response_format` with a JSON Schema (OpenAI, "Structured Outputs" docs); Anthropic supports the same intent through its tool-use and structured-output paths (Anthropic, "Tool use" docs). The schema is the contract: field names, types, which keys are required, which values are drawn from an enum. The wire format underneath is always JSON Schema, whatever SDK sugar sits on top.

**Tool-call arguments.** When you define a tool, its `parameters` field *is* a JSON Schema, and the arguments the model emits for that tool are validated against it by the provider. This is why a tool call and a structured answer are the same object with different intent: one is parsed to *act*, the other to *store*. §3 draws the line between them.

**Schema-authoring libraries.** In Python the schema is rarely hand-written. Three framework-agnostic tools dominate, each cited briefly:

- **Pydantic** lets you declare the schema as a class and get runtime validation plus `.model_json_schema()` for free; most SDKs accept a Pydantic model directly (Pydantic project docs).
- **Instructor** patches the provider client so a call returns an already-validated Pydantic object, retrying automatically when validation fails (Instructor project docs).
- **Outlines** enforces the schema *during* generation rather than after, using constrained decoding (Outlines project docs).

**Grammar-constrained decoding.** This is the top rung, and the only one that offers a hard guarantee. Instead of asking for JSON and hoping, the decoder compiles the schema to a state machine (a grammar) and, at every generation step, masks the token distribution so that only tokens which keep the output valid can be sampled. A closing brace cannot be omitted because the grammar will not permit the sequence to end without it; a field typed as an integer cannot receive a letter because letter tokens are masked out at that position. The output is valid JSON *by construction*, not by luck. This is the mechanism behind provider "strict" and "JSON mode" flags and behind Outlines. The consequence for a system designer: with genuine constrained decoding, `json.loads` on the response cannot fail, so the residual risk moves from *syntactic* validity (guaranteed) to *semantic* validity (still your job), which §4 addresses.

```
   ┌─────────────────────────────────────────────┐
   │  grammar-constrained decoding               │  valid JSON by construction
   ├─────────────────────────────────────────────┤
   │  strict response_format / JSON Schema       │  provider-enforced shape
   ├─────────────────────────────────────────────┤
   │  tool-call arguments (schema-validated)     │  provider-enforced shape
   ├─────────────────────────────────────────────┤
   │  "please reply in JSON" in the prompt       │  best-effort, must validate
   └─────────────────────────────────────────────┘
```

*The ladder of output guarantees: each rung down needs more defensive parsing than the one above it.*

---

## 3. `response_format` versus `tool_choice`: is the answer the payload?

![response_format beside tools and tool_choice, with the three tool_choice settings and the test that picks between them](diagrams/02-payload-or-action.svg)

*The presence of a menu, and of the option to call nothing, is the whole test.*

The single most useful distinction on the output side is whether the model's job is to *return data* or to *choose an action*. Both produce a schema-conforming JSON object; the intent, and therefore the right mechanism, differs.

Use **`response_format`** (a strict schema on the response) when there is exactly one shape you want back and you want it every time: a classification label, an extraction result, a filled form, a graded rubric. The answer *is* the payload. There is no decision about *whether* to respond in this shape, only *what* to put in the fields.

Use a **tool** (optionally pinned with `tool_choice`) when the model is deciding *whether and which* action to take, possibly among several, possibly none. `tool_choice` has three common settings across providers: `auto` (the model decides whether to call a tool at all), `required` / `any` (it must call one of them), and a named tool (it must call this specific one). The presence of a menu, and of the option to call nothing, is the signal that you want tools rather than a single response schema.

The rule of thumb from [Post 15](../15-tools-and-mcp/index.md) holds: one always-required shape means `response_format`; a menu of optional capabilities the model selects among means tools. Forcing a single structured answer through a dummy tool works, but it muddies the trace ([Post 22](../22-observability/index.md)), because the span looks like the model *called* something when it merely answered. One related trick: setting `tool_choice` to a specific tool forces structured output on providers whose `response_format` support is thinner than their tool support, since a forced named tool call is a schema-constrained object by another name.

---

## 4. Reliability: the failures that remain, and the retry loop

Constrained decoding removes syntactic failures. Everything softer than that leaves a residue, and even the strong path leaves *semantic* gaps. A robust system plans for both.

**JSON-mode failure modes.** When you rely on a plain "reply in JSON" instruction or a loose JSON mode rather than a strict schema, the classic failure shapes recur: a prose preamble before the object ("Sure, here is the JSON:"), Markdown code fences around it (` ```json `), a trailing comma, single quotes, an unescaped newline inside a string, or the object truncated because the response hit the `max_tokens` ceiling mid-structure. Truncation is the sneaky one, and a context-budget interaction ([Post 04](../04-tokens-windows-budgets/index.md)): a large output schema needs enough output-token headroom to finish, or it produces broken JSON no prompting can fix.

**Schema strictness.** A schema that lists the fields you want is not the same as a schema that *forbids* the fields you do not. Setting `additionalProperties: false` on every object is the difference: without it, the model can invent extra keys that pass validation and then confuse the consumer; with it, an unexpected key is a validation error you catch immediately. Mark genuinely required fields in `required`, constrain string fields to enums wherever the value space is closed, and prefer a strict schema (which the provider compiles into the decoder) over a lenient one you validate after the fact. Strictness at the schema is cheaper than defensiveness at every call site.

**The validate-and-retry loop.** The pattern that turns a flaky output into a reliable one is small and worth memorising: validate the response against the schema; on success, return it; on failure, feed the *validation error itself* back to the model as a follow-up message and ask it to correct the output, then re-validate. The error message is the repair instruction, because it names exactly which field was wrong and why.

```python
from pydantic import ValidationError

def parse_with_retry(client, messages, schema, max_attempts=3):
    for attempt in range(max_attempts):
        resp = client.call(messages, response_schema=schema)
        try:
            return schema.model_validate_json(resp.text)   # Pydantic
        except ValidationError as e:
            messages += [
                {"role": "assistant", "content": resp.text},
                {"role": "user",
                 "content": f"That did not validate: {e}. Return corrected JSON only."},
            ]
    raise RuntimeError("schema validation failed after retries")
```

*The validate-and-retry loop: the validation error becomes the model's repair instruction on the next attempt.*

Two operational notes. This is exactly what Instructor does under the hood, so on Python you often get the loop for free. And cap the attempts (three is a common ceiling, illustrative) while counting exhaustions as a hard error the dashboard tracks ([Post 22](../22-observability/index.md), §4 lists schema-validation errors as a first-class error kind), because a loop that silently swallows failures hides a real regression. Constrained decoding removes the *syntactic* retry, but a *semantic* retry (valid JSON that violates a required cross-field invariant) still earns its place.

---

## 5. Output guardrails as a defence layer

Schema validation is the first guardrail, not the only one. A guardrail is any programmatic check between the model's raw output and the consumer, with the authority to pass, block, rewrite, or re-ask. Where the six input layers govern what goes *in*, guardrails govern what is allowed *out*, and they form a defence layer with several distinct jobs.

- **Schema enforcement.** Everything in §2 to §4: the output has the right shape and types. The floor, not the ceiling.
- **Content moderation.** Screen the output for disallowed content (hate, self-harm instructions, and similar categories) using a moderation classifier, either the provider's or a dedicated model. This is a second pass over the *response*, distinct from moderating the input.
- **PII and output filtering.** Detect and redact personally identifiable information (PII: names, emails, payment details) that should not leave the boundary, and strip system-internal details the model may have leaked into its answer. The capstone ([Post 30](../30-capstone-email-reply-agent/index.md)) applies output filtering to an outbound email, where the guardrail is the last check before text reaches a real recipient.
- **Refusal and safety handling.** When the model refuses, or when a guardrail blocks, the system needs a defined behaviour: return a safe canned message, escalate to a human, or re-ask with a narrowed instruction. A refusal that surfaces as a schema-validation crash is a bug; a refusal that is caught and handled is a feature. Track refusal rate on the dashboard, because a sudden jump usually means a recent prompt or rule change is over-firing ([Post 20](../20-evaluation/index.md), §7).

**Guardrails frameworks as a class.** Rather than hand-roll each check, several open frameworks package the pattern: a declarative set of validators (schema, regex, moderation, PII, topical rails) that run on every response and can block or fix it. Guardrails AI and NVIDIA NeMo Guardrails are two widely used examples (project docs for each). Their value is the value of any policy layer: one place to declare the rules, one place to test them, one place to change them. The framework is replaceable; the discipline of running output through an enforcement layer is not.

A guardrail can act at three points, and mature systems use all three: *before* generation (validate the input, though that is the input layers' job), *during* generation (constrained decoding, §2), and *after* generation (the moderation, PII, and refusal checks above). The after-generation checks are the ones this section is about: the last line before an output becomes an action or a stored record.

---

## 6. Where guardrails sit: measure versus enforce

Guardrails are easy to confuse with the two neighbouring disciplines. Drawing the lines precisely keeps a system from either duplicating work or leaving a gap.

**Evaluation measures; guardrails enforce.** Evaluation ([Post 20](../20-evaluation/index.md)) runs offline, on a golden set, in CI, and produces a *number* (a schema-validity rate, for example) that tells you whether the system is good enough to ship. It does nothing at runtime. A guardrail runs *online*, on every live response, and produces a *decision*: pass this one, block that one. Evaluation catches a regression before it ships; a guardrail catches the one bad response that slips through anyway. They are complements, and they share fixtures: schema validity is both an eval metric and a runtime guardrail, so the same schema tests the golden set offline and gates real traffic online.

**Security is the adversarial case.** Guardrails and security ([Post 23](../23-security/index.md)) overlap on the output boundary, but the threat models differ. Output guardrails mostly guard against the model's *accidental* failures: a malformed object, an inadvertent PII leak, an off-topic answer. Security guards against an *adversary* actively trying to make the model exfiltrate data or take a forbidden action, often via prompt injection arriving through retrieved or tool-returned content. An output guardrail is a real part of the security stack, because filtering at the output boundary is one of the architectural defences ([Post 23](../23-security/index.md)), but it is a layer within security, not a substitute for it. A recipient allow-list on an outbound action is a guardrail *and* a security control; a moderation pass on a generated paragraph is a guardrail that is only incidentally one.

The clean mental model: evaluation is the *test suite*, guardrails are the *runtime asserts*, and security is the *threat model*. All three touch the output; only guardrails act on it, in production, one response at a time.

---

## Common pitfalls

- **Parsing without validating.** Calling `json.loads` and assuming the fields are present. Loose JSON mode guarantees syntax at best, never semantics; validate against a schema, always.
- **A lenient schema.** Omitting `additionalProperties: false` and `required`, so the model can add or drop fields and still "pass". A schema that forbids nothing enforces nothing.
- **No retry loop.** Treating the first malformed response as a fatal error when feeding the validation message back would have fixed it on the second attempt.
- **A retry loop with no ceiling.** Retrying forever (or silently) hides a real regression and burns tokens; cap the attempts and count exhaustions as a tracked error.
- **`max_tokens` too low for the schema.** A large output object truncated mid-structure produces broken JSON that no prompt wording can repair; size the output budget to the schema ([Post 04](../04-tokens-windows-budgets/index.md)).
- **Guardrails only on the input.** Moderating what goes in but not what comes out leaves the PII leak, the off-topic answer, and the leaked system detail unguarded.
- **Confusing eval with guardrails.** Assuming an offline eval score protects production; the score measures, only a runtime guardrail enforces.

---

## Further reading

- OpenAI, *"Structured Outputs"* docs: `response_format` with JSON Schema and strict mode.
- Anthropic, *"Tool use"* docs: schema-validated tool arguments and the structured-output path.
- Outlines (project docs): grammar-constrained decoding that guarantees valid JSON at generation time.
- Instructor and Pydantic (project docs): the validate-and-retry pattern and schema authoring in Python.
- Guardrails AI and NVIDIA NeMo Guardrails (project docs): output-guardrail frameworks referenced in §5.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 22 — Observability, tracing, and cost](../22-observability/index.md)**: how schema-validation errors, refusal rate, and retry counts show up in the trace and on the dashboard.
- **[Post 20 — Evaluation](../20-evaluation/index.md)**: the offline discipline that measures what guardrails enforce at runtime.
