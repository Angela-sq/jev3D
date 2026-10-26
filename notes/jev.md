# Jev notes (from docs.typesafe.ai, read 2026-10-23)

## What Jev is
- TypeSafe's "System One" model. It answers typed questions about a `state` and returns structured answers with probabilities.
- Jev does not write text, code, or actions. It labels and judges.
- Same weights for every account; no per-customer fine-tuning.

## Call
- `POST https://api.typesafe.ai/v1/systemone`, header `Authorization: Bearer $TYPESAFE_API_KEY`.
- Python: `pip install typesafe-sdk` → `TypeSafeClient().system_one(state=..., questions=...)`.
- Body: `state` (string / JSON / array), `questions` (name → question), optional `assets` (images), `model`.
- Models: `jev-latest` = `jev-1.13.0`; `jev-preview` = `jev-1.14.0`.

## Question types
- `choice`: pick one of up to 255 named options → `choice`, `confidence`, `probabilities`.
- `score`: 1–10 ordered levels → `score` (can be fractional), `probabilities`.
- `noul`: yes/no statement → `noul` (0–1).
- `box`: find a thing in an image → `top/bottom/left/right` (0–1 fractions). Needs `jev-preview`.

## Images (preview)
- Header `TypeSafe-Danger-Zone-Images: true`.
- PNG/JPEG still images, ≤16 MiB, each side 280–1568 px. No video: send single frames.
- Docs say images and box are "not yet up to our standards" for production.

## Cost and limits
- $0.042 per million input tokens; output is free. $5 ≈ 119M input tokens.
- Image token count per frame is not documented: measure from `usage.input_tokens`.
- Context 64k per request, 32k per question (262k with the long-context header).
- Rate limits are per org, shown at https://console.typesafe.ai/rate-limits. 429/529 → back off.
- Latency is not documented: measure it.

## Weak spots (Jev 1.13)
- Counting and numbers are unreliable. Leans toward the first choice option.
- Accuracy drops with long, noisy state. Reads instructions literally.

## Nothing documented about
- Games, Minecraft, 3D, actions, trajectories, or training data.

## Use in this project (idea, untested)
- Jev cannot play by itself. Jev can see: "where is the mob" (box), "is the mob in reach" (noul), "what is on screen" (choice).
- A simple script turns those answers into keys and mouse moves.
- The script logs every screenshot with its action, which becomes training data for a small student model (`tools/mcbench/src/mcbench/agents/policy_stub.py`).
