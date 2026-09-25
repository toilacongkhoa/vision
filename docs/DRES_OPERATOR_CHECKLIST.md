# DRES operator checklist

## Before a task

- Before starting the backend, check whether port 8000 already serves the app. If it does, verify `/api/v1/health` and do not launch a second Uvicorn process; restart the existing process only when code or environment settings changed.
- The current `DRES_API_BASE_URL` is `https://eventretrieval.one` in the server `.env`. If organizers announce a different URL, change that one value and restart the existing backend. The endpoint must use HTTPS.
- For automatic login, set `DRES_USERNAME` and `DRES_PASSWORD` in the Git-ignored server `.env`, restart the existing backend, then click **Get session from .env** in the review dialog. This action is restricted to the local same-origin app; it returns only a sessionId to page memory, never the username/password. The standard username/password fields remain available for one-time manual login.
- Confirm the correct competition evaluation is `ACTIVE` after login. Do not select an old or unrelated evaluation.
- Start the matching task timer: Textual KIS 5 minutes, Video KIS 4 minutes, Q&A 5 minutes, or TRAKE 5 minutes.
- Keep every progressive clue in the active question. For TRAKE, enter all event descriptions in sequence before assigning results.

## Prepare and review

- Select exactly one answer. For TRAKE, include one video and one semantic keyframe for each event stage, in the correct order; a technical I-frame is not a semantic keyframe.
- For Q&A, check both the located video/time and the exact answer text.
- For Video KIS, describe the clip in natural language or draw a sketch. Do not record or capture it with an electronic device to provide it to a tool.
- In the review dialog, confirm task type, extensionless video ID, selected frame or ordered TRAKE frames, timestamp in milliseconds, exact Q&A answer, and serialized JSON.
- If a frame image does not load, use the displayed video ID, frame number, and timestamp to open/check the source video before deciding; do not treat a blank image as confirmation.
- A downloaded JSON file is only a local export; it has not been sent to DRES.

## Send and confirm

- Log in using organizer-provided credentials, select the correct `ACTIVE` evaluation, and submit only after reviewing the payload.
- The app stores the DRES session only in page memory; refreshing the page clears it. Environment credentials stay on the backend and are not returned to the browser or written to application logs. Credentials typed into the manual form are not saved by the app.
- Submission history uses green for `CORRECT`, red for `WRONG`, and amber for HTTP 412 (duplicate result or expired task time), 401 (session expired; log in again), and 404 (invalid Evaluation ID). HTTP 202 is shown as sent with no verdict yet. Other verdicts such as `INDETERMINATE` remain visible in the response details and are not guessed as accepted or rejected.
- If the same payload for the same query was already sent, the review dialog shows a warning, but you can still submit it again; every send may count as another DRES attempt. Corrected payloads are also available as new attempts. If an outcome is unknown, check DRES before retrying because the earlier request may already have been recorded.
- A rejected answer or uncertain location may cost points. Check the task's location and answer before submitting.

## Known checks for the first organizer rehearsal

- Confirm DRES's exact evaluation-list response shape and submit-response meaning.
- Confirm whether the evaluation accepts point timestamps encoded as `start == end` for KIS.
- Test login, evaluation selection and one submission using the organizers' actual evaluation before relying on the integration in competition.
