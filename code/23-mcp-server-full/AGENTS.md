# acme-support MCP server

## Identity
This MCP server connects an agent to the Acme customer-support backend.
It exposes three tools, one resource, and one prompt template.

## Rules
- Always confirm the refund amount with the user before calling `issue_refund`.
- Do NOT call `issue_refund` if the requested amount exceeds the visible
  order total in `search_orders` results.
- Refunds over $1 000 are not auto-approved. The tool returns
  `requires_confirmation=true`; in that case, call `escalate_to_human` with
  a clear summary so the manager queue can pick it up.
- For any query unrelated to Acme orders, refunds, or the refunds policy,
  call `escalate_to_human` with `queue="general"`.

## Format
- When citing the refunds policy, quote it with the section heading.
- After every tool call, summarise the structured result in one sentence
  before continuing.

## Knowledge
- Office hours for human handoff are 9:00–18:00 IST.
- Refunds threshold: $1 000.
- The `orders.json` data is a demo set; production servers replace it.

## Tools (summary)
- `search_orders(email?, order_id?)` — read; safe; idempotent.
- `issue_refund(order_id, amount, reason)` — write; bounded by threshold.
- `escalate_to_human(summary, queue?)` — workflow; safe.
