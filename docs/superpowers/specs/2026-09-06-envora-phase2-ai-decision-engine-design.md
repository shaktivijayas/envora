# Envora — Phase 2 Design: AI Decision Engine (Ambiguity Fallback Only)

## Purpose

Phase 1 (`docs/superpowers/specs/2026-09-04-envora-phase1-design.md`) built a
deterministic analyzer that never guesses: every `Detection` is either a
confident answer with verifiable evidence, or `LOW`/`None` with an honest
explanation of why nothing was found. It deliberately stops short of
inferring install/dev/build commands, because that inference sometimes
requires judgment a regex or manifest lookup can't supply.

Phase 2 is that judgment step — and nothing more. It is steps 4-5 of the
overall pipeline (steps 1-3, cloning through deterministic detection, are
Phase 1, already built and validated). Phase 2 reads Phase 1's
`AnalysisResult`, decides whether genuine ambiguity exists, and — only when
it does — asks Claude to resolve specifically that ambiguity, never more.

**Non-goals for this phase:**
- No Dockerfile/docker-compose.yml/devcontainer.json/.env.example generation
  (Phase 3).
- No build validation (Phase 4 — "does the generated environment actually
  run" is a separate, later concern; Phase 2 only *proposes* commands).
- No deterministic command-lookup table for confident repos (e.g. "npm
  detected → always suggest `npm install`"). That is a plausible future
  addition to Phase 1 or a later phase, but Phase 2's job is ambiguity
  resolution only — a repo Phase 1 is fully confident about get no AI
  involvement, by design, even though a human could obviously guess its
  commands. Phase 2's name is "only for genuine ambiguity"; it is not
  "always fill in commands."
- No open-ended agentic behavior. This is a single bounded extraction call,
  not a tool-use loop.

## Interface

```python
def enrich(repo_path: Path, result: AnalysisResult, *, ai_enabled: bool = True) -> AnalysisResult:
    ...
```

Called by the CLI immediately after Phase 1's `analyze(repo_path)`, always
— `--no-ai` sets `ai_enabled=False` on the call rather than skipping the
call itself. `enrich` always runs `find_weak_signals` internally regardless
of `ai_enabled` (so the log line in every run accurately reports which
fields were weak, even when AI was disabled). When `ai_enabled=False`, any
group that would otherwise be attempted is short-circuited straight to
`NOT_ATTEMPTED` with evidence text noting the `--no-ai` flag specifically
(distinct from the "no API key configured" phrasing, though both are the
same outcome category) — no network call is made. A group that was never
triggered still resolves to `NOT_NEEDED` regardless of the flag, since
`--no-ai` disables the AI step, not the trigger evaluation.

`AnalysisResult` (Phase 1's model) gains three new fields:

```python
@dataclass(frozen=True)
class AnalysisResult:
    # ...existing 7 Phase 1 fields, unchanged...
    install: Detection
    dev: Detection
    build: Detection
```

No new public type. `install`/`dev`/`build` reuse Phase 1's existing
`Detection(value, confidence, evidence)` — the same type every other field
already uses. `ports` keeps its existing `list[Detection]` shape; Phase 2
only ever replaces its contents wholesale under the rules below, never
appends to it as a fifth independent list.

## Trigger: Weak-Signal Detection

```python
@dataclass(frozen=True)
class WeakSignal:
    field: str          # "stack" | "package_manager" | "framework" | "runtime_version" | "ports"
    detection: Detection  # or the list's sole placeholder Detection, for stack/ports

def find_weak_signals(result: AnalysisResult) -> list[WeakSignal]:
    ...
```

Checks exactly five fields: `stack`, `package_manager`, `framework`,
`runtime_version`, `ports`. `env_vars` and `services` never participate —
Phase 2 doesn't produce those, so their confidence can't influence whether
Phase 2 runs.

**Weak, for a scalar field** (`package_manager`, `framework`,
`runtime_version`): `confidence` is `LOW` (which in Phase 1's design always
pairs with `value=None`).

**Weak, for a list field** (`stack`, `ports`): the list is *exactly* the
single no-signal placeholder Phase 1's detectors return when nothing was
found (`[Detection(value=None, confidence=LOW, evidence=[...])]`). A list
with some confident entries and no further candidates is not weak, even if
it's not exhaustive — e.g. a repo where `ports` found one `HIGH`-confidence
`EXPOSE` port is not weak just because there could theoretically be more
ports Phase 1 didn't catch. This definition is load-bearing: it's what
guarantees `ports`'s weak state is always exactly one placeholder to
replace or annotate, never a mix requiring a merge policy.

**Output:** a list of `WeakSignal`, not a boolean. An empty list means no
AI call happens at all (`install`/`dev`/`build` get their `NOT_NEEDED`
placeholder; `ports` passes through Phase 1's value untouched).

## Group Mapping: Weak Signals → What Gets Asked

Two independent "ask groups," each requested only if its trigger fires:

| Group | Triggered by any of | Produces |
|---|---|---|
| **command** | `stack`, `package_manager`, `framework`, `runtime_version` weak | `install`, `dev`, `build` |
| **ports** | `ports` weak | `ports` |

If both groups are triggered in the same run, this is **one API call**
with a schema covering both groups' fields — never two separate calls.
Shared context, one round trip, one place for retry logic to live. The
requested JSON schema is built dynamically to include only the group(s)
actually triggered; a repo with everything confident except
`runtime_version` gets an `install`/`dev`/`build`-only schema, never a
`ports` property it doesn't need.

## Prompt Construction

Fixed per call, once weak signals are known:

1. **Pruned file tree.** Reuses `envora.analyzer.walk.EXCLUDED_DIRS` and
   `MAX_SCAN_FILE_BYTES` directly (imported, never duplicated as a second
   constant) — the two lists exist for the same reason and must not drift
   apart. Additional caps specific to prompt-sizing: max depth 3, max 200
   entries.
2. **Key config file contents** = exactly the files Phase 1's detectors
   already read (`package.json`, `pyproject.toml`, lockfiles, `Dockerfile`,
   `docker-compose.yml`, etc. per each detector's existing file list). If
   Phase 1 didn't need to read a file to detect anything, Phase 2 doesn't
   read it either — Phase 2 resolves ambiguity within what Phase 1 already
   looked at, it doesn't expand the search.
3. **README raw text** (already a Phase 1 env-var source) — often the only
   place install/dev commands are stated in prose.
4. **Ground truth summary** — a compact list of every *non-weak* field's
   `value` + `confidence` (not full evidence), framed explicitly as
   established fact the model must build on, not re-derive or contradict.
   E.g.:
   ```
   Already established with confidence — treat as fact, do not re-derive:
     stack: python (HIGH)
     package_manager: poetry (HIGH)
     framework: fastapi (HIGH)

   Open questions (resolve these):
     runtime_version: no signal found
   ```
   This is what keeps the AI's job "fill this specific gap" rather than
   "redo Phase 1's classification with extra steps" — without it, a model
   re-reading raw files could contradict a Phase 1 `HIGH` finding (e.g.
   assume pip when Phase 1 already established Poetry from a lockfile).

Context gathering (1-3) does not vary by which group is weak; only the
requested output schema (4's "open questions" list, and the JSON schema
passed to the API) varies.

## Output Schema (Internal, Not Public)

The schema requested via `output_config.format` (or `client.messages.parse`
with a Pydantic model) is a **transient, internal-only** shape — it is
never exposed as a public envora type, and the model is never given a
`confidence` field to populate. Confidence is assigned by the orchestrator
after a valid response comes back, never self-reported by the model:

```python
class CommandGroupResponse(BaseModel):
    install: str
    install_reasoning: str
    dev: str
    dev_reasoning: str
    build: str
    build_reasoning: str

class PortsGroupResponse(BaseModel):
    ports: list[int]
    ports_reasoning: str
```

(Exact field nesting is an implementation detail for Task planning — the
binding requirement is: no `confidence` field anywhere in this schema, and
each `_reasoning` field is a separate string, not folded into the value.)

## Field Outcomes (applies independently to `install`, `dev`, `build`, and
to `ports`)

Four possible outcomes per field, in priority order:

1. **NOT_NEEDED** — this field's group was never triggered (nothing weak
   that maps to it).
   - `install`/`dev`/`build`: `Detection(value=None, confidence=Confidence.LOW, evidence=["AI step not needed: stack/package_manager/framework/runtime_version already confident"])`.
   - `ports`: Phase 1's existing list passes through **completely
     unmodified** — no note added, since AI was never in question for
     this field on this run.

2. **NOT_ATTEMPTED** — the group was triggered, but no `ANTHROPIC_API_KEY`
   is configured (or `--no-ai` was passed).
   - `install`/`dev`/`build`: `Detection(value=None, confidence=Confidence.LOW, evidence=["AI step not attempted: no ANTHROPIC_API_KEY configured (weak: <comma-joined weak field names>)"])`.
   - `ports`: Phase 1's single weak placeholder `Detection`, with this
     note appended to its `evidence` list (there is always exactly one
     entry to append to, by the weak-list definition above).

3. **ATTEMPTED_FAILED** — the group was triggered, a key was present, the
   call was attempted, and it never produced a valid, passing result
   (semantic validation exhausted its one retry, or the network/API retry
   budget of 2-3 attempts was exhausted).
   - `install`/`dev`/`build`: `Detection(value=None, confidence=Confidence.LOW, evidence=["AI inference attempted, failed validation twice: <last validation error>"])`
     (or the equivalent network-failure phrasing when that's what was
     exhausted).
   - `ports`: same append pattern as NOT_ATTEMPTED, with the
     attempted-and-failed note instead.

4. **SUCCESS** — a valid response passed all checks.
   - `install`/`dev`/`build`: `Detection(value=<model's value>, confidence=Confidence.MEDIUM, evidence=["AI inference: <model's reasoning>"])`.
   - `ports`: **full replacement** of Phase 1's placeholder — one
     `Detection` per port in the returned list, each
     `confidence=Confidence.MEDIUM`, each carrying the **same shared**
     `"AI inference: <reasoning>"` string (one reasoning explains the
     whole port list, not one per port).

This is a strict extension of Phase 1's own vocabulary: "evidence" always
means a literal, human-verifiable artifact; an AI-derived string is always
prefixed `"AI inference:"` so a report renderer can visually and
programmatically distinguish the two categories, and never claims a
confidence tier the model itself doesn't have standing to claim (`MEDIUM`
is the ceiling for anything AI-derived; only something outside the model's
own say-so — a manifest, or a later Phase 4 passing build — can earn
`HIGH`).

## Validation & Retry — Three Independent Failure Classes

1. **Malformed JSON / schema violation.** Structured outputs
   (`output_config.format` / `client.messages.parse`) guarantee
   schema-valid JSON at generation time — this should not happen. If it
   somehow does, it is a hard `AIResponseError`, raised internally and
   caught by the orchestrator as an immediate `ATTEMPTED_FAILED` (no
   retry budget spent on this class).

2. **Semantic validation** (schema-valid but content-invalid): port
   outside 1-65535, an empty command string, a command string containing
   an obviously dangerous pattern (e.g. `rm -rf`, `curl | sh`). Exactly
   **one** retry total per call, regardless of how many fields in the
   response failed validation: a fresh single-shot request (not a
   multi-turn conversation) with *every* validation failure found — not
   just the first — appended to the prompt (e.g. "Previous response had
   port 99999 (out of the valid 1-65535 range) and an empty `build`
   command — provide a corrected answer for both"). A second response
   that still fails any validation is `ATTEMPTED_FAILED`.

3. **Network/API failure** (timeout, rate limit, 5xx). Standard
   retry-with-backoff, 2-3 attempts, using its own counter — entirely
   independent of the semantic-retry counter above. Exhaustion is
   `ATTEMPTED_FAILED`.

No failure of any class ever raises out of `enrich()` to the CLI. This is
a direct, unconditional extension of Phase 1's own invariant ("no detector
ever raises for a repo it merely doesn't understand well") — Phase 2 must
never make the tool less reliable than Phase 1 alone.

## Model Choice

`claude-sonnet-5`, not Opus. This is bounded extraction over a pruned,
scoped context with a fixed output schema — not open-ended reasoning,
agentic tool use, or long-horizon planning, which is where Opus's
advantage over Sonnet actually shows up. Escalate to Opus only if Phase
2's own real-repo testing shows Sonnet genuinely struggling (monorepos,
unusual frameworks) — a decision made from measured evidence gathered
while building Phase 2, not assumed upfront. This choice is deliberately
inconsistent with generic Claude-usage defaults elsewhere, because the
task shape here doesn't call for Opus-tier judgment.

## Logging

One structured log line per `enrich()` invocation (including invocations
where nothing was weak):

```json
{"ai_invoked": false, "weak_fields": [], "reason": "no weak signals"}
{"ai_invoked": true, "weak_fields": ["runtime_version"], "reason": "command group weak"}
{"ai_invoked": true, "weak_fields": ["stack", "ports"], "reason": "command and ports groups weak"}
```

No persistent counter, log file, or aggregation state owned by envora
itself — it is a stateless CLI tool per Phase 1's own design, and adding
cross-invocation state solely to serve a reporting metric would be scope
creep against that, plus it raises a concurrent-invocation question
(shared file, multiple `envora analyze` processes) that has nothing to do
with the analyzer's actual job. The "invoked in X% of repos" statistic —
useful as a talking point precisely because Phase 2 is opt-out rather than
always-on — is computed externally by aggregating these structured log
lines across however many repos were analyzed; that aggregation is a
five-line script, not envora's job.

## Module Layout

```
src/envora/
  ai/
    __init__.py
    trigger.py        # find_weak_signals, WeakSignal
    prompt.py          # prompt/context assembly (tree pruning, config reads, ground-truth summary)
    client.py          # Claude API call wrapper, retry logic (semantic + network, separately counted)
    schema.py          # internal Pydantic response models (CommandGroupResponse, PortsGroupResponse)
    enrich.py          # enrich(repo_path, result, ai_enabled) -> AnalysisResult — orchestrates the above
```

Mirrors `analyzer/`'s existing pattern of splitting by responsibility
rather than one large file.

## CLI Integration

`envora analyze <repo-url>` calls `enrich()` automatically whenever
`find_weak_signals()` is non-empty and `ANTHROPIC_API_KEY` is set — this is
the default, not an opt-in. The trigger is already narrow (fires only on
genuine gaps), so "automatic" does not mean "always calls out to an API on
every run" — it means a normal `analyze` on a repo Phase 1 struggles with
gets the benefit Phase 2 exists to provide, without the user needing to
know in advance that a flag would help.

A `--no-ai` flag forces Phase-1-only behavior even when a key is present
and signals are weak — this is what integration tests use for
determinism (a real Claude call is not something a CI-style suite should
depend on), and what any user who wants zero AI involvement regardless of
gaps can reach for.

## Credentials

Standard `ANTHROPIC_API_KEY` environment variable, resolved however the
Anthropic SDK normally resolves it. If unset, `enrich()` treats every
triggered group as `NOT_ATTEMPTED` (see Field Outcomes) rather than
raising or silently skipping — the distinction between "AI tried and
couldn't help" and "AI was never configured to try" must be visible in
the output, mirroring Phase 1's own absent-file-vs-unparseable-file
distinction.

## Testing Strategy (sketch — detailed in the implementation plan)

- **Unit tests** for `find_weak_signals` (each of the 5 fields
  individually weak/not-weak; list-vs-placeholder edge cases for
  `stack`/`ports`), the group-mapping logic, the four Field Outcomes for
  both `install`-family and `ports`, and the three retry classes
  (mocking the Claude client — no real network calls in the unit suite).
- **Integration tests** (marked, excluded by default, same convention as
  Phase 1) against real repos: at least one repo where the command group
  fires and succeeds, one where it's not needed at all, and one exercised
  with `--no-ai` to confirm the flag actually suppresses the call.
