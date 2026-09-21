# Design note — Phase 0

> **Status: skeleton, scaffolded.** Every section below is a Phase 0 deliverable from [`PLAN.md`](../PLAN.md).
> Target length 6–8 pages. When a section is done, tick the matching box in `PLAN.md`.
> Sections 2 and 3 are largely drafted already in `docs/problem.md` and `docs/algorithm.md` —
> this note tightens them into reviewer-proof prose. The prose is what is missing; each remaining
> section now has a runnable artifact behind it:
>
> | § | Artifact | State |
> |---|---|---|
> | 3 | [`notebooks/derive-trigger.ipynb`](../notebooks/derive-trigger.ipynb) | runs; derivations are TODO, numerical checks are live |
> | 4 | [`src/hazardserve/crossover.py`](../src/hazardserve/crossover.py), [`docs/crossover.md`](../docs/crossover.md) | model written, constants assumed |
> | 5 | [`docs/sweep-log.md`](../docs/sweep-log.md) | log created, sweep not yet run |
> | 6 | [`examples/plot_cost_decomposition.py`](../examples/plot_cost_decomposition.py) | figure renders; candidate, not chosen |

---

## 1. The claim, in one paragraph

_To write._ The single sentence a reviewer should be able to repeat back. Must name: what is
predictable (per-node departure hazard, conditioned on current uptime), what it buys
(fewer unplanned KV losses and less wasted work at equal latency), and why one function is
enough for two decisions.

## 2. Problem formulation

_Source: `docs/problem.md`._ Lift and tighten. Must survive these challenges:

- [ ] Why is session length the right random variable, rather than time-to-next-reclaim-signal?
- [ ] What exactly is censored, and does Kaplan-Meier's independent-censoring assumption hold
      when the scheduler's own placement decisions influence which nodes are observed?
- [ ] State the capacity/queueing model precisely enough that $T_i$ is well defined.
- [ ] Say plainly what is assumed known: $P_r$, noisy $\hat L_r$, node rates, bandwidth.

## 3. The decision rule, derived

_Source: `docs/algorithm.md`._ Derive $E_i(r) = T_i + L_i$ rather than assert it.

- [ ] Derive the migration trigger from $E$ — show that "migrate iff risk removed pays for the
      move" is the stationary point of the same objective, not a separate heuristic.
- [ ] State the assumptions explicitly: append-only KV, tokens streamed so recompute is always
      possible, $\hat L_r$ noisy.
- [ ] Justify the hysteresis $h$: what failure mode does it prevent (the thrashing noted in
      `docs/algorithm.md`), and what is the cost of setting it too high (the v0 trigger barely
      fires — see the volunteer-fleet numbers in the README).
- [ ] Complexity and decision latency: $O(\text{nodes} \times \text{cells})$, 16-cell Riemann sum.
- [ ] **Explain why the trigger does not fire.** `notebooks/derive-trigger.ipynb` §3 prints the two
      conditions per uptime, and `risk_gain` is *negative at every uptime* in the WAN two-node case:
      the planned-migration cost $C$ is a full re-prefill of the context (≈ 18 s at 4.5 k tokens and
      250 tok/s), which exceeds $L_i$ before the hysteresis is even consulted, and the same $C$ then
      fails the $\Delta T < h$ test. Either pre-emptive migration pays only in a characterisable
      regime (fast link, long request, late in a node's life) — in which case say so and characterise
      it — or $C$ is mis-specified because the destination can prefill while the source keeps
      decoding. **This is the most consequential open question in Phase 0** and it decides whether
      the paper's second decision survives.

**Companion artifact:** [`notebooks/derive-trigger.ipynb`](../notebooks/derive-trigger.ipynb) —
skeleton, runs end to end. Already established there: the 16-cell Riemann sum matches a
200 k-draw Monte Carlo of the same integral to < 0.5 %, and cells beyond 32 buy nothing, so the
production integral is not the approximation to worry about.

## 4. Transfer-vs-recompute crossover model

_Source: [`docs/crossover.md`](../docs/crossover.md) and `src/hazardserve/crossover.py` (both new).
The model is written; the prose and the citations are not._

- [x] Crossover written as a function of context length, bandwidth **and** prefill rate:
      $c^\star = (O_t - O_r) / (1/p_j - \text{kv\_bytes}/\min(B_i,B_j))$, with $\infty$ when the
      denominator is non-positive. Pinned to `MigrationCost` by `tests/test_crossover.py`.
- [x] Constants carry their provenance in `LINK_CLASSES` and every one is marked *assumed*.
- [ ] Start from ShuntServe's measurement: recompute wins except for very long contexts — cite it
      against the table in `docs/crossover.md` and say where the two disagree.
- [ ] Cross-check against ServerlessLLM's token-migration argument.
- [ ] Make the second axis a claim, not a footnote: the crossover moves with the destination's
      prefill rate as much as with bandwidth (1 300 tokens at 3 000 tok/s vs 80 at 250 tok/s over the
      same LAN). Prior work states it against context length alone.

## 5. Differentiation table — frozen

_Source: `docs/related-work.md` and the README table. Sweeps are recorded in
[`docs/sweep-log.md`](../docs/sweep-log.md), which is where the freeze becomes auditable._

- [ ] Re-run an arXiv sweep for late-2026 preprints **before** freezing (cs.DC, cs.LG); queries and
      the null results are listed in the sweep log.
- [ ] Verify every arXiv ID in `paper/references.bib` — several are 2026 preprints.
- [ ] Columns stay: per-node survival hazard | one cost for placement *and* pre-emptive migration |
      KV-transfer vs recompute choice.
- [ ] Rows: SpotServe, ShuntServe, SkyServe, SkyNomad, Pallas, ctHO, Llumnix, Petals/Parallax.
- [ ] For each row, one sentence naming the exact thing it does *not* do. No vague "unlike prior work".
- [ ] Add the sweep row to `docs/sweep-log.md` and reference its date here.

**Pivot check:** if a preprint already ships hazard + unified placement/migration + transfer-vs-recompute,
trigger the PLAN.md Phase 5 pivot now rather than in Phase 3.

## 6. The one figure

_Candidate drawn: `python examples/plot_cost_decomposition.py` → `paper/figures/cost-decomposition.png`.
Two identical nodes, identical request; only the hazard shape differs._

- [x] Generating script exists, greyscale and linestyle only, no colour needed.
- [ ] **Decide: is this the figure?** Drawing it surfaced a problem. At realistic parameters $L$ is
      only 1–10 % of $E$, so the honest single-panel version shows two nearly flat lines. The script
      currently splits into two panels (E on the true scale, then $L$ alone, where the two archetypes
      cross at ~11 minutes of uptime). A two-panel figure whose left half looks like nothing is a
      weak candidate — either argue that the small ratio *is* the story (single-digit-% gains are
      what the pivot threshold in `PLAN.md` also expects), or find a figure that carries more.
- [ ] Re-cut from trace data in Phase 2. Today's session lengths are synthetic Weibulls, so the
      figure illustrates the model; it is not evidence.
- [ ] Caption must state that both nodes have identical speed, or the reader will credit hardware.

## 7. Scope and non-goals

_Source: `docs/problem.md` non-goals._ Restate so §1's claim cannot be read wider than it is.

## 8. Open questions carried into Phase 1

_To write._ Anything §2–§6 could not settle. Phase 1 starts by closing these. Already on the list:

- [ ] Is the planned-migration cost $C$ mis-specified? (§3 — decides whether the migration decision
      survives at all.)
- [ ] Is one-loss truncation defensible — the model charges at most one unplanned loss per request,
      but at high churn the fallback node can die too.
- [ ] Does Kaplan-Meier's independent-censoring assumption survive a scheduler that steers work
      toward long-lived nodes and therefore observes them differently?
- [ ] Which of $h$, `check_interval`, `min_remaining` actually moves the headline number?
- [ ] Does the one figure carry the paper, or is $L/E \approx 1\text{–}10\,\%$ too small to show? (§6)

---

### Phase 0 exit checklist

- [ ] This note at 6–8 pages, every box above ticked
- [ ] Notebook deriving the migration trigger — *skeleton exists and runs; the derivations in §2–§4
      of the notebook are still TODO*
- [ ] Differentiation table frozen, with a sweep row in `docs/sweep-log.md`
- [ ] The one figure chosen (not merely drawn)
- [ ] `PLAN.md` Phase 0 boxes ticked to match
