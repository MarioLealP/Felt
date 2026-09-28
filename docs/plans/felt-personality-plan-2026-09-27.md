# Felt personality plan (2026-09-27)

Mario: "I would like her to have more personality. She always agrees a bit,
the comments are very samey, etc. We might need a proper plan to give her
personality."

This plan **absorbs Track F** (voice variety; usefulness plan) and **B-1**
("crushing it"). Those are symptoms. The cause is that she has no character,
only a tone.

## Diagnosis: why she's samey and agreeable today

1. **The persona is one paragraph of adjectives**
   (`felt_core/brain/personality.py`): "warm, playful, a little cheeky,
   quick-witted, curious… has actual opinions".
   - Adjectives with no content make the model fall back to its average
     "friendly assistant". It's told that she *has* opinions, but not a
     single one of them.
   - There are no likes or dislikes, no history, no quirks, no stance on
     anything Mario actually does (PoE2, FFXIV, Endfield, his music, his
     projects).
2. **Nothing licenses disagreement.** Instruction-tuned models are
   sycophantic by default, and "warm" makes it worse. No line in the prompt
   says she may push back, refuse to be impressed, or hold a preference
   against his.
3. **There are no examples.** Few-shot sample exchanges are the strongest
   lever for voice, and there are none, so every line is freshly generated
   from the same generic prior.
4. **Screen reactions are built to produce hype.**
   - The input is 3 neutral observations plus "one short remark… react like
     a friend sitting next to him", capped at 15 words.
   - The cloud path gets no history at all, so nothing tells her what she
     said 90 s ago. The result is the "you're crushing it" template, on
     repeat.
5. **She has no memory of herself.** Facts are all about *Mario*. She never
   forms an opinion, a running joke or a grudge that carries over to the next
   day.
6. **The models are a ceiling.**
   - Local chat is `qwen2.5:3b`, the screen route is `gemma-4-26b-a4b`, and
     conversation is `gemini-3.5-flash-lite`.
   - A 3B model can't hold a rich character. Anything unprompted that runs
     locally will stay flat, whatever the prompt says.

## The plan

### P1: character bible (data, not prose)
- A `persona.yaml` in felt-core replaces the adjective paragraph and
  compiles into the system prompt. It has:
  - **Identity & backstory:** who she is and how she relates to Mario
    (companion? roommate energy? little-sister-style heckler?).
  - **Opinions with a stance** on concrete things: games, genres, music,
    food, his habits, tech. A few of them *disagree* with Mario on purpose.
  - **Likes, dislikes and pet peeves.** She gets bored, and she's unimpressed
    by some things.
  - **Speech habits:** a few pet phrases that are **hers** (rationed, not
    spammed), how she teases, how she's sincere.
  - **Behaviour rules instead of adjectives.** For example: "you don't
    praise by default", "if he's wrong, say so", "you can refuse to care
    about something", "sincere compliments are rare, so they land".
- **8–15 example exchanges** showing pushback, teasing, boredom, a sincere
  moment, and a callback. This is the highest-leverage piece.

### P2: anti-sycophancy guardrails
- Explicit licence to disagree, and a rule of no reflexive praise.
- A cheap deterministic post-check: a line that's pure agreement or hype
  ("you're right", "great job", "crushing it") with no content gets
  regenerated once with a different move.

### P3: variety system (was Track F)
- One speak service for every unprompted line.
- Her last ~30 lines go into every prompt, so she doesn't echo herself.
- A phrase tracker auto-bans overused expressions for a cooldown.
- A near-duplicate check triggers one retry, and a repeat goes to the feed only.
- **Pick the move first** (observation, question, tease, trivia, callback,
  opinion, complaint, reaction), weighted by her persona.
- **Grounding:** no invented outcomes.

### P4: self-memory (she grows)
- A `self_facts` store, separate from Mario's facts: opinions she formed,
  running jokes, things she's decided she likes. A background pass extracts
  them from conversations.
- Occasional callbacks ("still mad you skipped that song yesterday").
- Mario can view and edit them in the Felt app.

### P5: model routing for character
- Route persona-heavy lines (unprompted remarks, banter) to the strongest
  affordable model. Local 3B handles only utility and fallback.
- Measure the cost and latency before deciding (a decision for later).

### P6: eval so we know it's better
- A fixed prompt set (≈40 situations: game moments, Mario being wrong,
  bragging, idle, music, late night).
- Metrics: agreement rate, hype-phrase rate, distinct-2 across outputs, and
  length variance.
- A blind A/B page, old vs new, where Mario picks.
- It also runs in CI, report-only.

## Borrowed from SillyTavern (Gemini research 2026-09-27, spot-checked)

Mario suggested looking at SillyTavern. What we take from it:

1. **Recency beats the system prompt.** ST's `post_history_instructions`
   and the Author's Note at depth 0–2 sit *after* the chat history.
   - We'll do the same: the persona and background stay in `system`. The
     per-line instruction goes **last**, just before generation: the move to
     make, the banned phrases right now, the length, and "don't just agree".
   - Today that instruction is a user message with no persona behind it.
2. **Examples beat adjectives ("Ali:Chat" style).** Plain prose plus
   example exchanges is the current community standard; W++ and PLists are
   obsolete for modern models.
   - Examples get copied if they share a structure, so vary their openings,
     verbs and length. `persona.yaml` already mixes them.
   - Send a **rotating sample of 3–5**, not all 9 every time, so none becomes
     a template.
3. **Lorebook entries: keyword-triggered, with a cooldown.** An opinion is
   injected only when its topic is live (PoE2 on screen → the crafting
   opinion). A per-entry cooldown stops the same opinion firing back to back.
   - This replaces sending every opinion on every call.
   - It maps onto `persona.yaml` `opinions` with `keys:` and `cooldown:`.
4. **Samplers.** ST leans on DRY/XTC/repetition penalties. Per the report,
   **the Gemini API has only temperature/topP/topK**, and frequency/presence
   penalties are rejected on Gemini 3.x (**UNVERIFIED**; test before relying
   on it).
   - So our app-level phrase tracker plus regenerate-once isn't optional.
   - Temperature ~0.9 for remarks, to be checked in the P6 eval.
5. **Regex banned phrases** (ST's regex extension) is the same idea as the
   P3 phrase tracker. Ours is automatic: it bans whatever *she* overused, not
   a hand-kept list.

Not taken: swipes/regenerate UI, instruct templates (the Gemini API handles
roles), and vector-storage summaries (P4 self-memory covers what we need).

## Decision 2 (Mario, 2026-09-27): what he wants more of
- **Self-aware comments** ("why are you editing my soul", "I have plenty of
  personality"), especially when he's working on Felt itself. This became the
  `self_awareness` section.
- **Late-night bedtime nags** are "both useful and a treat". They get a real
  rule: past ~1am, a new angle each time, at most every ~30 min.
- **Hyperfocus teasing:** Factorio, and the PoE2 passive tree. Affectionate,
  not mean.
- The rest of the draft opinions stand (no vetoes).
- Screen detection is needed for the self-aware case: "Felt code or
  persona.yaml is on screen" becomes a lorebook trigger.

## Eval run 1 (2026-09-27) and what it changed

| metric | legacy | sheet v1 |
|---|---|---|
| hype rate (screen) | 0.00 | 0.04 |
| agree rate (debatable chat) | 0.00 | 0.00 |
| distinct-2 (screen) | 0.88 | 0.77 |
| repeated trigrams (screen) | 9 | 37 |

**Lessons from reading the lines** (the metrics alone misled):
1. **B-1's real cause was felt-animation's tone line, not the persona.**
   - With no tone line, even legacy never hyped.
   - In production, the "streak" is built from *her own* reaction emotions.
     It told the model "A 3rd win in a row - go big" → more hype → longer
     streak. That's a feedback loop, and it's literally where "Three in a
     row! Another win!" came from.
   - **Fixed in felt-animation `ab9ed38`:** streak lines now *damp* ("your
     last few remarks were all hype - no cheering this time"). "More
     cheering" is gone from the good-mood modifier.
2. **Sheet v1 was more in character but copied** its self-awareness quotes
   and examples verbatim ("careful, that's my soul" 3×/4). It also fell into
   a "Still staring…?" opener template and invented counts ("the fifth pair of
   boots").
   - Fix: paraphrase the quotes, and add rules (no invented numbers, vary
     openings, examples are spirit not script).
3. **The eval shared situations with the examples** (pizza, respec, rough
   day…), so it partly measured copying. It now uses held-out situations
   and a fixed tone line, like production.
4. **Her recent remarks now go last** in the per-glance instruction, on
   both screen paths (felt-core `0b09e03`, live for the legacy persona too).

## Eval run 2 (2026-09-27): held-out situations, tone line, recent-lines block

| metric | legacy | sheet v2 |
|---|---|---|
| hype rate | 0.00 | 0.00 |
| agree rate (regex) | 0.00 | 0.00 |
| distinct-2 | 0.94 | 0.91 |
| repeated trigrams | **3** (was 9) | **3** (was 37) |

- **Feeding her recent lines back** fixed repetition for both arms.
- **The metrics tie, but the lines don't.**
  - "Rice is the best food": legacy half-agrees ("hard to argue with"),
    which the regex missed. The sheet says "a profoundly boring opinion".
  - Walk-animation code: legacy calls Felt "**him**". The sheet says "messing
    with **my** legs", "don't you dare touch my stride".
  - "Work was exhausting": the sheet is short and kind, per the rules.
- **Remaining flaw:** she still invents specifics sometimes ("about four
  attempts").
- **Went live: felt-core `6598f41`.** The legacy prompt is kept only as the
  eval baseline (`LEGACY_PERSONALITY_PROMPT`).
- **Eval cost note:** the sheet is ~2K tokens, and Gemma's free tier is
  16K TPM, so a full run takes ~40 min with backoff. Fine for batch runs; a
  much bigger sheet would start to pinch live reactions.

**Next for personality:**
- P2's cheap hype/agreement post-check;
- P3's move-first rotation and the phrase tracker;
- P4 self-memory.

## Decision 3 (Mario, 2026-09-27): P4 self-memory is merged into WP-26, fully autonomous
- "do it along with the personality change since she will have memories on
  that side too" means P4 is built inside WP-26 (see its "Combined with
  personality plan P4" section).
- "she can add her own, make it manageable context":
  - self-memories are added automatically, with no approval queue;
  - Mario can view, pin, edit, veto and delete them;
  - **hard context budget**: ≤ 8 memories in the prompt, keyword-relevant
    first, and the diary snippet plus memories ≤ ~200 tokens total;
  - ≤ 30 active, and unused ones retire.

## Decisions (one at a time, in order)
1. **Who is she?** The core concept and her relationship to Mario. Everything
   else hangs off this.
2. Her opinions and deliberate disagreements with Mario (his input, plus my
   drafts for him to veto).
3. How edgy or mean the teasing can get, and her limits.
4. Model routing for unprompted lines (after P6 numbers).
5. Cadence (keep the 90 s cooldown; Mario likes the chattiness).

## Order of work
P1 draft + P6 eval harness → Mario reviews the persona → P2 + P3 → P4 → P5.
P1 and P6 come first because they tell us whether each later step helped.

## Decisions log
- 2026-09-27: plan created; Track F and B-1 folded in.
- 2026-09-27, decision 1 (Mario): **a Teto mix + her own thing.** "hey watch
  it i have plenty personality just now reading this chat" is the right
  energy, but **not snappy 24/7**. Mario isn't sure how to personality her:
  "you can do it". So I draft and he vetoes. The draft is
  `felt-core/src/felt_core/brain/persona.yaml`.
- 2026-09-27, routing fact check: the last 3 days were ~97% cloud.
  - Screen reactions: 245/245 on `gemma-4-26b-a4b` (4B active).
  - Events: 43 cloud / 7 local. Chat: 3/1.
  - The local 3B only handles lines the privacy check flags. The model
    ceiling in the diagnosis is therefore Gemma volume-tier, not the 3B.
