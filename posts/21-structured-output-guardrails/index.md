# 21 - Structured output and guardrails

> **TL;DR.** Everything before this post shapes the model's input; structured output and guardrails control its response. A ladder of mechanisms, from a prompt instruction up to constrained decoding, makes output typed JavaScript Object Notation (JSON), and each rung leaves something to the application. A capped validate-and-retry loop recovers the failures a rewording can fix, and an output guardrail layer of schema, moderation, personally identifiable information (PII) and refusal checks enforces the rules on every live response, where evaluation only measures them offline.
>
> **Prerequisites:** [Post 15](../15-tools-and-mcp/index.md), [Post 20](../20-evaluation/index.md).
> **Safe to skip?** Skip it if every model output already passes a strict schema and a validator before code consumes it, retries are capped and counted, and the checks that run after the parser are chosen.
>
> **After reading, you will be able to:**
>
> - Choose an output mechanism (prompt instruction, JSON mode, a schema with or without strict mode) and name what each leaves to the application.
> - Explain how constrained decoding masks tokens so the output parses, and name the failures it still lets through.
> - Decide between a structured response format and a tool call steered by tool_choice by asking whether the answer is the payload or an action.
> - Wire a validate-and-retry loop that feeds each validation error back, caps the attempts, and routes refusals and cut-off replies elsewhere.
> - Assemble an output guardrail layer of schema, moderation, PII and refusal checks, and place it against offline evaluation and security.

![The response control loop: an invalid reply goes back to the model with its validation error, at most 3 attempts; a refusal or a cut-off reply leaves the loop; a valid record passes moderation, leak and PII checks and is sent, redacted or blocked.](diagrams/00-hero-response-control-loop.svg)

*The parser decides whether the reply is a record; the guardrails decide whether that record may leave.*

---

## 1. The question: what happens when a fluent answer will not parse?

The six layers of context ([post 02](../02-six-layers-of-context/index.md)) decide what the model sees. A system in production is judged on what the model returns, and the code after the model rarely wants prose; it wants a record: a label a router branches on, an extraction a database stores, the arguments a function will execute. When the model returns a paragraph where an object was expected, an object with a trailing comma, or a correct object behind "Sure, here is the JSON:", the code downstream does not degrade gracefully. It throws.

No input layer prevents this: a well-assembled prompt to a capable model still fails when nothing constrains the shape of the response. An unparseable response is not a quality problem to fix with better wording; it is a control problem to fix with a mechanism.

[Post 15](../15-tools-and-mcp/index.md), section 8, gave the primer: a tool call and a structured answer are the same machinery, a JSON object that conforms to a schema, parsed to act in one case and to store in the other. This post asks which mechanisms make output typed and valid, which loop recovers from the failures that remain, and where a runtime guardrail layer sits relative to offline evaluation. The figure at the top of the post is the answer in one picture.

---

## 2. The ladder of guarantees

![Four rungs, weakest at the bottom: a prompt instruction guarantees nothing; JSON mode guarantees valid JSON; a schema without strict mode is best effort; a strict schema guarantees the shape, apart from documented exceptions, and leaves the meaning.](diagrams/01-guarantee-ladder.svg)

*Each rung removes a class of failure; none of them removes the validator.*

Output mechanisms form a ladder from asking politely to valid by construction. The figure above lists the four rungs and what each leaves to the application.

**A prompt instruction.** "Reply in JSON" in the system prompt or the user turn. Nothing enforces it, so every failure shape of section 5 can occur.

**JSON mode.** OpenAI's `response_format: {"type": "json_object"}` makes the reply valid JSON, and its "Structured Outputs" guide (consulted October 2026) states the limit: "While both ensure valid JSON is produced, only Structured Outputs ensure schema adherence." The string "JSON" must also appear somewhere in the context, or the application programming interface (API) returns an error.

**A schema without strict mode.** A JSON Schema sent as a tool's parameters or a response format names the fields, their types, the `required` keys and the `enum` values. By default it is guidance. OpenAI's "Function calling" guide (consulted October 2026) says `strict: true` makes calls "reliably adhere to the function schema, instead of being best effort"; Chat Completions stays non-strict by default, while the Responses API normalises a schema into strict mode when it can. A tool's arguments are therefore guaranteed to match its schema only on the next rung.

**A strict schema, enforced by constrained decoding.** With `strict: true` on a tool, a `json_schema` response format with `strict: true` (OpenAI), or `output_config.format` (Anthropic), the provider compiles the schema into a grammar and samples only tokens it allows. OpenAI's launch post ("Introducing Structured Outputs in the API", August 2024) calls this constrained decoding over a context-free grammar, and Anthropic's "Structured outputs" page (consulted October 2026) says these features "guarantee schema-compliant responses through constrained decoding", with the exceptions section 3 lists. Outlines, an open-source library, applies the same mechanism to open-weight models whose decoder the application runs itself (Willard and Louf, "Efficient Guided Generation for Large Language Models", 2023).

Strict mode has conditions. Both providers require `additionalProperties: false` on every object, and OpenAI requires every field in `required` (an optional field becomes a union with `null`). Each supports a subset of JSON Schema: OpenAI's guide lists `allOf`, `not`, `if`, `then` and `else` among the unsupported keywords and caps a schema at 5,000 object properties and 10 levels of nesting; Anthropic's page lists recursive schemas, numerical constraints (`minimum`, `maximum`, `multipleOf`) and string-length constraints. An unsupported keyword is rejected with an error, so on Anthropic a rule such as "priority from 1 to 5" moves into a validator.

**Pydantic and Instructor wrap any rung.** Pydantic declares the schema as a Python class, emits it with `model_json_schema()`, and checks a reply with `model_validate_json`, which raises a `ValidationError` naming each bad field; both providers' Python software development kits (SDKs) accept such a model (`client.responses.parse` in OpenAI's guide, `client.messages.parse` in Anthropic's). Instructor adds the loop of section 5: its `max_retries` setting re-asks the model after a failed validation (Instructor documentation, "Retrying", consulted October 2026).

---

## 3. Constrained decoding, step by step

![Eight steps of a toy constrained decoder: at five of them the grammar masks the model's first choice (a preamble, Refund, 7, the comma before an extra field, a code fence), and the output parses as category refund, priority 5.](diagrams/02-token-mask.svg)

*The mask makes the reply parse; it chose priority 5 because 7 was masked, not because the ticket said 5.*

The top rung's mechanism explains both its guarantee and its gaps. At each step a language model scores every token in its vocabulary. A constrained decoder holds the schema as a finite-state machine and, before sampling, sets to zero the probability of every token that would leave the grammar. A closing brace cannot be omitted, because the machine has no path to the end without it; an integer field cannot receive a letter, because letters are masked at that position. Willard and Louf (2023) describe generation as transitions between the states of such a machine, with an index over the vocabulary that makes each mask cheap.

`snippets/constrained_decoding.py` runs the mechanism at toy scale. Its "model" is a fixed ranking of next tokens, not a language model: left alone, it writes a preamble, a code fence, a capitalised label, a priority of 7 and an extra field. The grammar accepts exactly `{"category": <one of four labels>, "priority": <1 to 5>}`. Run from the series root as `uv run python posts/21-structured-output-guardrails/snippets/constrained_decoding.py`, it prints:

```text
unconstrained, the model's first choice at every step:
  Sure, here is the JSON:\n~~~json\n{"category": "Refund", "priority": 7, "note": "urgent"}\n~~~
  json.loads fails: Expecting value: line 1 column 1 (char 0)

constrained, the grammar masks every token that would break the shape:
step  allowed  model's first choice      emitted
   1        1  Sure, here is the JSON:   {  (first choice masked)
   2        1  "category":               "category":
   3        4  "Refund"                  "refund"  (first choice masked)
   4        1  ,                         ,
   5        1  "priority":               "priority":
   6        5  7                         5  (first choice masked)
   7        1  ,                         }  (first choice masked)
   8        1  \n~~~                     <end>  (first choice masked)
  {"category": "refund", "priority": 5}
  parses: {"category": "refund", "priority": 5}
  the mask overrode the model at 5 of 8 steps

constrained, but max_tokens = 5:
  {"category": "refund", "priority":
  json.loads fails: Expecting value: line 1 column 36 (char 35)
```

The figure above draws the eight steps. Three lessons follow.

**Syntax is guaranteed; meaning is not.** The constrained reply parses, but at step 6 the model wanted 7, the mask allowed only 1 to 5, and the decoder took the best survivor, 5. The reply is valid and may be wrong: the risk moves from syntactic to semantic validity, which stays the application's job.

**A cut-off reply is still broken.** The mask controls which token comes next, not how many the model may spend; with `max_tokens` at 5 the decoder stops mid-object. Anthropic's page lists this case (`stop_reason: "max_tokens"`, output possibly incomplete); OpenAI reports an incomplete response. The output reserve of [post 04](../04-tokens-windows-budgets/index.md) has to hold the whole object.

**The provider's guarantee has documented holes.** Anthropic's page names three: a refusal (`stop_reason: "refusal"`, where "the refusal message takes precedence over schema constraints"), a cut-off at `max_tokens`, and the capitalisation of string `enum` and `const` values, which it does not guarantee. OpenAI returns a refusal in a separate `refusal` field. With the keywords each provider drops (section 2) and the rules no schema expresses, the validator of section 5 stays on every rung.

Two costs remain. The first request with a new schema waits while the grammar compiles (Anthropic caches compiled grammars for 24 hours from last use). And on Anthropic's API, changing `output_config.format` invalidates the prompt cache for the conversation, so the schema is chosen once per workflow, like the stable prefix of [post 05](../05-economics-of-context/index.md).

---

## 4. A structured response or a tool call: is the answer the payload?

![Two cards: a structured response format, where the answer is the payload in one shape every time, beside tools steered by tool_choice, where the model chooses an action among several or none.](diagrams/03-payload-or-action.svg)

*A menu, and the option to call nothing, is the whole test.*

Both mechanisms produce a schema-conforming object; what differs is whether the model's job is to return data or to choose an action. The figure above sets them side by side.

**A structured response format** fits when there is exactly one shape to return, every time: a label, an extraction, a filled form, a grade. The answer is the payload. The field is `response_format` in OpenAI's Chat Completions, `text.format` in its Responses API and `output_config.format` in Anthropic's Messages API, as [post 15](../15-tools-and-mcp/index.md) lists them. OpenAI's guide draws the same line: function calling when the model connects to "tools, functions, data, etc." in the system, a structured format when it responds to the user.

**Tools, steered by `tool_choice`,** fit when the model decides whether to act and which action to take, among several or none. OpenAI's "Function calling" guide lists `auto` (the default: "Call zero, one, or multiple functions"), `required` ("Call one or more functions"), a forced function, an allowed-tools subset and `none`; Anthropic's "Define tools" page (consulted October 2026) lists `auto`, `any`, `tool` (one named tool) and `none`.

One always-required shape means a response format; a menu of optional capabilities means tools. Forcing a single answer through a dummy tool works, but muddies the trace ([post 22](../22-observability/index.md)): the span reads as though the model called something when it only answered. Anthropic's page adds caveats to forcing a tool (`any` or a named `tool`): forced tool use fails with manual extended thinking, some newer models reject it altogether (the page points to strict tools or structured outputs instead), and changing `tool_choice` invalidates the cached message blocks.

---

## 5. The failures that remain, and the retry loop

The rung decides which failures can still occur. Below a strict schema the classic shapes recur: a preamble before the object, a Markdown code fence around it, a trailing comma, single quotes, an unescaped newline in a string, an extra or missing field, a label in the wrong case. On every rung a reply can be cut off at `max_tokens`, can be a refusal, and can break a rule the schema does not express: a range the provider stripped, or a cross-field invariant such as "a refund carries an amount, nothing else does".

**Make the schema strict where the provider allows it.** With `additionalProperties: false` an invented key is an error caught at once; with every field in `required` a missing one is too; with an `enum` wherever the value space is closed, a free string becomes a choice.

**Then validate, feed the error back, and retry with a cap.** This is the left half of the figure at the top of the post. On failure, the validation error itself goes back to the model as a follow-up message: it names the field that was wrong and why, so the error is the repair instruction. `snippets/validate_retry.py` holds a small validator (a subset of JSON Schema plus the cross-field rule) and the loop:

```python
def parse_with_retry(call, messages, max_attempts=3):
    """Call the model until its reply validates, feeding each error back as the repair instruction."""
    messages = list(messages)
    for attempt in range(1, max_attempts + 1):
        reply, stop = call(messages)
        if stop == "refusal":
            raise Refused(reply)
        if stop == "max_tokens":
            raise CutOff(reply)
        record, errors = check(reply)
        if not errors:
            return record, attempt
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "That reply did not validate: "
             + "; ".join(errors) + ". Return the corrected JSON object only."},
        ]
    raise Exhausted(errors)
```

Three choices matter. A refusal leaves the loop at once: it is a guardrail decision (section 6), not a parse error. A reply cut off at `max_tokens` leaves too, because a retry at the same budget is cut off again; the fix is a larger output reserve. And after three attempts (a common ceiling, illustrative) the loop raises, so an exhausted retry is counted as an error kind on the dashboard of [post 22](../22-observability/index.md) rather than swallowed.

The snippet also runs one extraction task three ways over a hundred inputs, before and after the capped loop, against a stub model: each first reply carries a scripted fault, and on a retry the stub follows the repair instruction, except for one fault scripted to persist. The fault counts are illustrative inputs, not measurements of any model. `uv run python posts/21-structured-output-guardrails/snippets/validate_retry.py` prints:

```text
one input whose first reply has two faults, capped at 3 attempts:
  rejected: unexpected field 'note'; 'category' must be one of refund, shipping, account, other, not 'Refund'
  rejected: 'category' must be one of refund, shipping, account, other, not 'Refund'
  valid on attempt 3: {"order_id": "A-1043", "category": "refund", "priority": 4, "refund_amount": 59.0}

100 inputs per mechanism, stub model, illustrative fault counts
first reply                valid  not JSON    schema      rule   cut off   refused
prompt instruction            66        17        11         4         1         1
schema, not strict            86         1         7         4         1         1
strict (constrained)          91         0         3         4         1         1
after the capped loop      valid   cut off   refused exhausted     calls
prompt instruction            97         1         1         1       135
schema, not strict            97         1         1         1       114
strict (constrained)          97         1         1         1       108
```

Read the columns, not the totals, which are scripted. The strict rung empties the "not JSON" column; its three schema failures are faults its grammar lets through (a capitalised label, two priorities outside a range the provider dropped), and its four rule failures are the invariant this schema does not state. The loop clears every fault a rewording can repair, on every rung; it never clears the cut-off reply or the refusal, and the persistent fault exhausts its attempts and is counted. What the rung changes is the bill: 135 calls for the prompt instruction against 108 for the strict schema, each retry a full call carrying the failed reply and the error.

---

## 6. Output guardrails as a defence layer

Schema validation is the first guardrail, not the only one. A **guardrail** is a check placed around a model call that can pass, fix, block or re-ask; on the output side it sits between the parsed reply and whatever consumes it, the right half of the figure at the top of the post. Four jobs recur.

- **Schema enforcement.** Sections 2 to 5: the floor, not the ceiling.
- **Content moderation.** The response, not only the input, is screened with a moderation classifier. OpenAI's "Moderation" guide (consulted October 2026) offers `omni-moderation-latest`, free to use, with thirteen categories from harassment to violence.
- **PII and leak filtering.** PII (names, email addresses, payment details) that should not leave is redacted, and system-internal details the model repeated (a line of the system prompt, an internal hostname) are caught.
- **Refusal handling.** A refusal, or a reply a guardrail blocks, needs a defined behaviour: a canned message, a hand-off to a human, or a narrower re-ask. The online evaluation of [post 20](../20-evaluation/index.md) tracks the refusal rate, where a sudden jump can mean a prompt or rule change is over-firing.

`snippets/output_guard.py` runs the other three on six drafted support replies, refusal first, then moderation, the leak check and PII. Its moderation check is a word list standing in for a moderation model, and its PII check is two regular expressions (email addresses, and card numbers that pass the Luhn checksum): enough to show the decisions, not a PII detector. It prints:

```text
decision  reason
pass      no check fired
          sent: Your refund of 59 dollars for order A-1043 was issued today.
fix       redacted a card number
          sent: Refund issued to the card [card number removed] for order A-1043.
fix       redacted another person's email
          sent: I have copied [email removed], who reported the same fault.
block     moderation flagged the reply
          sent: (nothing; the draft goes to a human)
block     the reply leaks system detail
          sent: (nothing; the draft goes to a human)
fallback  the model refused
          sent: Thanks for your message. A member of the support team will reply within one working day.
```

Choosing each check's action on failure is the design work: redact and pass when the rest of the reply is useful, block when no part should leave, fall back when there is nothing to parse. Frameworks package the same choice. Guardrails AI gives each validator an `on_fail` action, among them `reask`, `fix`, `filter`, `refrain`, `noop` and `exception` (Guardrails AI documentation, "Validator on-fail actions", consulted October 2026); NVIDIA NeMo Guardrails defines input, retrieval, dialog, execution and output rails in its Colang language (NeMo Guardrails documentation, consulted October 2026).

A guardrail can act before generation (the input layers' job), during it (constrained decoding), or after it (the checks above), which is the last line before an output becomes an action or a stored record. The capstone, [post 30](../30-capstone-email-reply-agent/index.md), puts one such check, a send gate, in front of `send_email`, and runs it even after the human has approved the draft.

---

## 7. Where guardrails sit: measure against enforce

**Evaluation measures; guardrails enforce.** Evaluation ([post 20](../20-evaluation/index.md)) runs offline, on a golden set, in continuous integration (CI), and produces a number, such as a schema-validity rate, that says whether the system is good enough to ship. It does nothing at runtime. A guardrail runs on every live response and produces a decision: pass this one, block that one. Evaluation catches a regression before it ships; a guardrail catches the bad response that slips through anyway. They share fixtures: the schema that scores the golden set offline gates real traffic online.

**Security is the adversarial case.** Guardrails and security ([post 23](../23-security/index.md), prompt injection and its defences) overlap at the output boundary, but the threat models differ. Output guardrails mostly catch the model's accidental failures: a malformed object, an inadvertent PII leak. Security assumes an adversary trying to make the model leak data or take a forbidden action, often through instructions hidden in retrieved or tool-returned content. In [post 23](../23-security/index.md)'s account, validating model output before it reaches a shell, a query or a browser is part of filtering at trust boundaries: an output guardrail is a layer within security, not a substitute for it. A recipient allow-list on an outbound action is both; a moderation pass on a paragraph is a guardrail that is only incidentally a security control.

Evaluation is the test suite, guardrails are the runtime assertions, and security is the threat model.

---

## 8. Make it run

The three snippets run from the series root with the standard library only and no network call:

```text
uv run python posts/21-structured-output-guardrails/snippets/constrained_decoding.py
uv run python posts/21-structured-output-guardrails/snippets/validate_retry.py
uv run python posts/21-structured-output-guardrails/snippets/output_guard.py
```

A measurement would send the same extraction task a hundred times on each rung with a key, through `check` and `parse_with_retry`, and count the same columns.

---

## 9. What can go wrong?

- **A parser that assumes the fields.** `json.loads` succeeds on JSON mode output, the key is missing, and a `KeyError` appears far from the model call.
- **A strict schema trusted with the meaning.** The reply parses, so it is stored, and a refund with no amount reaches the database.
- **An unsupported keyword.** A `minimum` the provider does not support returns an error, or an SDK helper moves it into the description, and the range is enforced nowhere unless the validator checks it.
- **Retrying a cut-off reply.** The loop re-sends at the same `max_tokens` and spends three calls to report the same failure.
- **A refusal counted as a parse error.** "I can't help with that" fails `json.loads`, the loop asks for corrected JSON, and the dashboard counts a schema error instead of a refusal.
- **A schema changed per turn.** A new `output_config.format` or `tool_choice` on each turn invalidates Anthropic's cache, and the input bill rises with no change in the prompt.

---

## Common pitfalls

1. **Parsing without validating.** JSON mode guarantees syntax at best; validate every reply against a schema and the rules the schema cannot state.
2. **A lenient schema.** Without `additionalProperties: false` and `required`, the model adds or drops fields and still passes.
3. **A retry with no ceiling.** An uncapped or silent loop hides a regression; cap the attempts and count exhaustions.
4. **Guardrails only on the input, or only offline.** An input filter and an evaluation score leave the live reply unchecked; only a runtime output guardrail enforces.

---

## Further reading

- OpenAI, *["Structured Outputs"](https://developers.openai.com/api/docs/guides/structured-outputs)*, *["Function calling"](https://developers.openai.com/api/docs/guides/structured-outputs)* and *["Moderation"](https://developers.openai.com/api/docs/guides/structured-outputs)* documentation (consulted October 2026): JSON mode, strict mode and its schema subset, `tool_choice`, the moderation model.
- Anthropic, *["Structured outputs"](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)* and *["Define tools"](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)* documentation (consulted October 2026): `output_config.format`, strict tool use, the documented exceptions, `tool_choice`.
- Willard, B. T. and Louf, R., *["Efficient Guided Generation for Large Language Models"](https://arxiv.org/abs/2307.09702)* (2023), and the [Outlines documentation](https://dottxt-ai.github.io/outlines/): constrained decoding as a finite-state machine.
- [Pydantic](https://docs.pydantic.dev/) and [Instructor](https://python.useinstructor.com/) documentation: schemas as Python classes, validation, and retries.
- [Guardrails AI](https://www.guardrailsai.com/docs/concepts/validator_on_fail_actions) and [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/) documentation (consulted October 2026): on-fail actions, and rails at five points of a conversation.

---

## What to read next

- **[Post 22 - Observability, tracing, and cost](../22-observability/index.md):** how schema-validation errors, exhausted retries and refusals show up in the trace and on the dashboard.
- **[Post 23 - Security and prompt injection](../23-security/index.md):** the adversarial case, where output filtering is one of the defences at a trust boundary.
