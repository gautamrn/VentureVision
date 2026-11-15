# Screenshot specs

Three screenshots, matching the demo script's strongest moments. All three use demo mode, so they need no API keys and are reproducible.

**Common setup for all three:**

- **Build:** production build (`npm run build && npm start` in `frontend/`), so the Next.js dev badge is not visible.
- **Window:** 1440×900 at 100% zoom, light system theme.
- **Profile:** a fresh browser profile, so pitch history is empty.
- **Output:** PNG, saved under `docs/screenshots/`.
- **Crop:** to the content column (the pages are `max-w-2xl` or `max-w-4xl` and centered). Leave about 32 px of background on each side, and no browser chrome.
- **Content:** no cursor, no hover states, no selection highlight.

## 1. `replay.png`: the agents at work

- **URL:** `/demo/flakeguard`
- **State:** load the page, wait about 4 seconds (the replay runs at 4× speed and finishes in about 9 s), and capture while the timeline shows Planner done, Scout or Critic active, and Writer waiting. If the timing is hard to hit, use the browser's devtools to pause JavaScript at the right moment.
- **Must be visible:**
  - The header labels "Investment Memo", "Pitch Lab", and "Dev-tools SaaS", and the title "Flakeguard: Detects and quarantines flaky tests before they block a merge."
  - The line "Replaying a real pipeline run recorded 2026-11-15 (40s of live web research, shown at 4× speed)."
  - The full four-step agent timeline.
- **Must not be visible:** the **Skip to memo** button being hovered.
- **Alt text:** "Agent timeline replaying a recorded VentureVision run: planner done, scout and critic looping, writer waiting."
- **Why this shot:** it shows that the memo comes from a multi-step research process, not one prompt.

## 2. `annotations.png`: claim verdicts with citations

- **URL:** `/demo/pantry`
- **State:**
  - Click **Skip to memo**, then scroll so **How an Investor Reads Your Pitch** sits at the top of the viewport.
  - Click the **[1]** marker on the first (Supported) annotation, so its quote "The average American spends more than $762 per year on food that ends up wasted." and its source line (copiaresources.com, Retrieved 2026-11-15) are expanded.
  - Do not click the feedback controls; leave **Verdict right? ✓ ✕** in its idle state.
- **Must be visible, top to bottom:**
  - The highlighted pitch paragraph.
  - The Supported annotation with its expanded quote.
  - The Unsubstantiated annotation.
  - At least one annotation showing "Downgraded from Supported: no verifiable citation in the evidence."
- **Alt text:** "A pitch annotated claim by claim: one supported claim with its verbatim source quote, others downgraded for missing citations, each with a correct / wrong feedback control."
- **Why this shot:** it shows the grounding rule and its honest failure mode on one screen.

## 3. `evals.png`: measured, with the gaps labeled

- **URL:** `/evals`
- **State:** scroll so the page heading **Evals** is at the top. Capture down through **Latest scores** and the CI gate note. If it fits in 900 px, include the first rows of **Heuristic baseline misses**.
- **Must be visible:**
  - The Dataset card: "venturevision-claims v1", "updated 2026-11-15", "36" cases, labels 12/12/12, origin "seed-real 14" and "seed-constructed 22", "0 user-feedback candidates awaiting review".
  - The **Heuristic baseline** row: 83.3% (30/36) with per-label scores.
  - The **LLM verifier** row reading "Not run yet".
  - The CI note: "CI fails a pull request if heuristic accuracy drops more than 3 points below the stored baseline (83.3% on v1)."
- **Alt text:** "Eval page: 36-case hand-labeled dataset, heuristic baseline at 83.3%, LLM verifier marked not run yet, and the CI regression gate."
- **Why this shot:** it shows the numbers labeled exactly as what they are, including the one that does not exist yet.
- **Retake when:** the LLM verifier has been run with `--publish`. The row will then show a real score, and the caption should change to match.

## README wiring

Once the files exist, replace the commented-out Screenshots block in `README.md` with:

```markdown
| Agents at work | Claim verdicts with citations | Evals |
|---|---|---|
| ![Agent timeline replaying a recorded run](docs/screenshots/replay.png) | ![Pitch annotated claim by claim with source quotes](docs/screenshots/annotations.png) | ![Eval page with baseline and gaps labeled](docs/screenshots/evals.png) |
```
