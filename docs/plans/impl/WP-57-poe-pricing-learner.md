# WP-57: Felt learns PoE2 pricing on the side

Mario, 2026-10-01: "can we have EE2 its own thing, and have her learn
pricing on the side so at some point, can try her being the full price
person". Rares are the hard part: "some combinations dont matter".

## Phase 1 — collect (live since WP-29 v2)
Every item Mario price-checks (EE2 key / Ctrl+C) lands in felt-core's
event log as `poe_item_checked` with the full item text. Uniques and
currency already get a market price from `poe_price_check`.

## Phase 2 — her guess, silently (not started)
For each checked **rare**, she writes down which mods she thinks drive the
price and a rough value. Inputs: the item text, PoE2 wiki RAG (poe2rag), and
the trade API with **her** chosen stats (the same public API EE2 uses, rate-limited).
Store guess + actual search result; nothing spoken.

## Phase 3 — scorecard, then a trial
Weekly: how often her pick of important mods and her price land near the
market. When Mario likes the numbers, try her as the price person in a
league start (spoken: "that's like 3 divines, the life + res is what sells it").

## Open questions (one at a time, later)
- Where Mario's own judgment comes in (EE2 doesn't expose his stat toggles
  without a fork; maybe a quick "yes/no, that stat matters" reply to her).
- Rate limits on the trade API alongside EE2's own searches.
