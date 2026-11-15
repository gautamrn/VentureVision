# 60-second demo script

**Setup:**

- Use a production build (`npm run build && npm start` in `frontend/`) so the Next.js dev badge is not on screen, with the backend running.
- Browser window 1440×900 at 100% zoom, with a fresh profile so pitch history is empty.
- Start on `/`.
- No API keys are needed: the demo replays recorded runs.

**Story:**

- It researches a real pitch on the web.
- It shows where the evidence is thin.
- One of its own verdicts is wrong, and the system is built to catch exactly that.

| Time | Screen | Exact action | Voiceover (one line) |
|---|---|---|---|
| 0:00 | `/` landing | Hold on the hero and the three **Try the demo** cards. | "VentureVision reads a startup pitch, researches it on the live web, and writes an investment memo." |
| 0:05 | `/` | Click the **Pantry** card (**View memo →**). | "This is a recorded run of the real pipeline, no API keys." |
| 0:07 | `/demo/pantry` replay | Do nothing; let the agent timeline play (about 9 s at 7× speed). | "A planner writes searches, a scout runs them, a critic sends it back until the evidence holds up." |
| 0:17 | Memo top | Point the cursor at the **Groundedness** line: "2 of 8 claims cited · 2 downgraded". | "Every 'supported' claim needs a verbatim quote from a retrieved page, or it gets downgraded." |
| 0:22 | Memo | Scroll to **How an Investor Reads Your Pitch**. | "Here is the founder's own pitch, claim by claim." |
| 0:25 | First annotation, **Supported** | Click the **[1]** citation marker after "…roughly $1,500 a year." to expand the quote. | "The model called this supported, citing $762 a year per American." |
| 0:31 | Same annotation | Click the **✕** next to **Verdict right?** and hold on "Recorded: you marked this verdict wrong." | "But per person isn't per household; that verdict is wrong, and readers can say so." |
| 0:37 | Fourth annotation | Scroll down to the traction claim and point at "Downgraded from Supported: no verifiable citation in the evidence." | "Private traction numbers can't be found on the web, so the system refuses to call them supported." |
| 0:42 | Memo top | Click **← VentureVision**, then scroll to and click **How often are the verdicts right? See the evals →**. | "So how often are the verdicts right?" |
| 0:47 | `/evals` | Hold on the Dataset card (v1, 36 cases) and **Latest scores**: Heuristic baseline 83.3%, LLM verifier "Not run yet". | "36 hand-labeled cases; the baseline is 83%, and the model's own score is marked not run yet, not guessed." |
| 0:53 | `/evals` | Scroll to **Heuristic baseline misses** and click **uns-05**. | "That same household claim is in the eval set, with the evidence that makes it ambiguous." |
| 0:58 | `/evals` expanded case | Hold. End. | "Feedback becomes candidate eval cases; nothing reaches the golden set without review." |

**Notes:**

- The ✕ click at 0:31 writes a real row to the feedback table, marked `unverified demo memo`. After recording, reject the take's rows on `/admin` (**Verdict feedback → Reject**), or record against a local backend.
- If the replay is still playing at 0:17, wait. Do not click **Skip to memo**: the timeline is half the story.
- Everything quoted on screen is from `frontend/src/data/demo/pantry.json` and `frontend/src/data/evals/summary.json`. If either is re-recorded, re-check the numbers in the voiceover.
