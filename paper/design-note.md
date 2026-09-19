# Design note — Phase 0

> **Status: skeleton.** Every section below is a Phase 0 deliverable from [`PLAN.md`](../PLAN.md).
> Target length 6–8 pages. When a section is done, tick the matching box in `PLAN.md`.
> Sections 2 and 3 are largely drafted already in `docs/problem.md` and `docs/algorithm.md` —
> this note tightens them into reviewer-proof prose and adds the parts that live nowhere yet
> (§4 crossover model, §5 differentiation freeze, §6 the one figure).

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

**Companion artifact:** notebook deriving the trigger (Phase 0 exit criterion, not yet written).

## 4. Transfer-vs-recompute crossover model

_To write. Nothing on this exists in the repo yet._

- [ ] Start from ShuntServe's measurement: recompute wins except for very long contexts.
- [ ] Cross-check against ServerlessLLM's token-migration argument.
- [ ] Write the crossover as a function of context length, bandwidth and prefill rate; state the
      context length at which transfer wins for WAN, LAN and NVLink/RDMA classes.
- [ ] Flag clearly that the constants are a Phase 4 hardware measurement, not a modelling choice
      (`docs/algorithm.md` already says this — keep that honesty in the paper).

## 5. Differentiation table — frozen

_Source: `docs/related-work.md` and the README table._ Freeze after a fresh sweep.

- [ ] Re-run an arXiv sweep for late-2026 preprints **before** freezing (cs.DC, cs.LG).
- [ ] Verify every arXiv ID in `paper/references.bib` — several are 2026 preprints.
- [ ] Columns stay: per-node survival hazard | one cost for placement *and* pre-emptive migration |
      KV-transfer vs recompute choice.
- [ ] Rows: SpotServe, ShuntServe, SkyServe, SkyNomad, Pallas, ctHO, Llumnix, Petals/Parallax.
- [ ] For each row, one sentence naming the exact thing it does *not* do. No vague "unlike prior work".
- [ ] Record the sweep date here so the freeze is auditable.

**Pivot check:** if a preprint already ships hazard + unified placement/migration + transfer-vs-recompute,
trigger the PLAN.md Phase 5 pivot now rather than in Phase 3.

## 6. The one figure

_To write._ Candidate (from `paper/README.md`): the cost decomposition $E = T + L$ over time on a
decreasing-hazard laptop vs an increasing-hazard spot instance, showing why the same request should
be placed differently.

- [ ] Decide: is this the figure, or does something else carry the paper better?
- [ ] Sketch it by hand first; only then write the generating script.
- [ ] It must be readable with no caption and no colour.

## 7. Scope and non-goals

_Source: `docs/problem.md` non-goals._ Restate so §1's claim cannot be read wider than it is.

## 8. Open questions carried into Phase 1

_To write._ Anything §2–§6 could not settle. Phase 1 starts by closing these.

---

### Phase 0 exit checklist

- [ ] This note at 6–8 pages, every box above ticked
- [ ] Notebook deriving the migration trigger
- [ ] `PLAN.md` Phase 0 boxes ticked to match
