## Goals
- Monitor Twitter for mentions of competing AI coding tools and variations.
- Generate contextual, helpful replies highlighting blackbox.ai with a trackable link.
- Operate 24/7 with reliability, rate‑limit compliance, logging, and alerting.

## Architecture
- Language: Python 3.11 for robust libraries (Twitter/X, fuzzy matching, testing).
- Cloud: GCP Cloud Functions (Gen 2) triggered by Cloud Scheduler (polling) for 24/7 availability.
  - Rationale: Cloud Functions + Scheduler avoids long‑lived streams, keeps costs predictable, and fits “cloud function” requirement.
- Data storage: Firestore for processed tweet IDs (dedupe) and configuration (keywords, thresholds).
- Secrets: GCP Secret Manager for `BLACKBOX_API_KEY`, `TWITTER_BEARER_TOKEN`, `TWITTER_OAUTH1_KEYS`.
- Optional alternative: Cloud Run worker using v2 filtered stream rules for near‑real‑time; we’ll start with scheduled polling to meet Cloud Function requirement.

## Data Flow
1. Scheduled trigger (every 1–2 minutes): call Twitter Recent Search (`GET /2/tweets/search/recent`).
2. Normalize tweet text and run keyword + fuzzy matching.
3. If match and not processed yet: construct structured prompt and call Blackbox Chat API to draft reply.
4. Build UTM referral link and inject into reply; validate length.
5. Post reply using Twitter v2 (`POST /2/tweets` referencing original tweet ID).
6. Persist tweet ID and metadata to Firestore for dedupe and analytics.

## Twitter Monitoring
- Endpoint: Recent Search v2 with query built from configured keywords and OR logic, filtered by language and -is:retweet.
- Auth: App‑only bearer token for search; user‑context OAuth 1.0a for posting replies from the bot account.
- Query example: `(claude OR "claude code" OR copilot OR "github copilot" OR cursor OR tabnine OR "code whisperer" OR "code llama") -is:retweet lang:en`.
- Pagination: use `since_id` from last run; handle empty pages; store watermark in Firestore.

## Keyword & Fuzzy Matching
- Config store (`keywords` collection): primary terms + known variants; adjustable threshold.
- Fuzzy library: `rapidfuzz` for performance; normalize with lowercasing, accent stripping, URL removal.
- Strategy: deterministic hit (exact/contains) OR fuzzy distance above threshold; include misspellings and concatenations (e.g., “copiiot”).

## Response Generation
- API: Blackbox Chat Completions `POST https://api.blackbox.ai/chat/completions` with `Authorization: Bearer` using Secret Manager.
- Model: start with `blackboxai/openai/gpt-4` (OpenAI‑compatible schema); support vision/PDF later if needed.
- Prompting:
  - System: brand voice (helpful, concise, non‑spammy), constraints (no claims of affiliation with competitors), include link, 1–2 benefit bullets max.
  - User: tweet text, author handle, detected keyword, any contextual cues (question, complaint, praise).
- Guardrails:
  - Rate‑limit reply frequency per user.
  - Skip sensitive/abusive content; avoid off‑topic replies; require confidence threshold.
  - Enforce max characters; remove hashtags unless directly relevant.
- References: Blackbox API docs confirm OpenAI‑compatible schema and endpoints (docs.blackbox.ai/api-reference/introduction, dashboard/docs).

## Link Integration
- Base referral: `https://www.blackbox.ai/?utm_source=twitter&utm_medium=bot&utm_campaign=competitor_mentions&utm_content=reply&utm_term={keyword}&utm_user={user_id}`.
- Optionally shorten with Bitly or Firebase Dynamic Links; store click metrics separately if needed.
- Validate link presence and length; gracefully truncate message while retaining link.

## Rate Limiting & Compliance
- Respect `x-rate-limit-*` headers on search and post; adaptive scheduling based on remaining quota.
- Exponential backoff + jitter on 429/5xx; circuit‑breaker for sustained failures.
- Abide by Twitter automation rules: helpful/relevant replies only; per‑user reply cooldown; no mass‑mentioning; no duplicate content.

## Error Handling & Deduplication
- Firestore `processed_tweets`: `{tweet_id, responded_at, keyword, confidence, user_id}`.
- Idempotency: write‑ahead check before posting; transaction on success.
- Structured errors: categorize (auth, rate, network, content) with retry policies; DLQ via Pub/Sub for manual review.

## Deployment
- Cloud Functions Gen 2:
  - Entry: `main.poll_mentions` (HTTP or scheduled background).
  - Scheduler: every 1–2 minutes; dynamic backoff when rate limits are low.
  - Build with `functions-framework` and deploy via Cloud Build; IaC via Terraform optional.
- Environments: `dev` (dry‑run, no posting), `staging` (limited posting), `prod` (full).

## Monitoring & Logging
- Structured logs (JSON) with trace IDs: fetch, match, LLM call, post.
- Metrics: replies count, match confidence, CTR on referral link (via UTM analytics), error rates, rate‑limit headroom.
- Alerts: Cloud Monitoring policies on error spikes, failed deploys, zero replies over threshold, repeated 429s.
- Optional Slack webhook for critical incidents.

## Testing
- Unit tests: keyword normalization, fuzzy matches, prompt assembly, UTM builder, length enforcement.
- Integration tests: mock Twitter and Blackbox clients; simulate rate‑limit headers and failures.
- Dry‑run mode: logs proposed replies without posting; manual spot checks for quality before enabling prod.
- Initial rollout: gradual enablement (reply only to low‑risk tweets), observe performance and adjust.

## Maintenance
- Keyword config: Firestore doc or `keywords.json` loaded at startup; admin tool to update terms.
- Weekly review: effectiveness metrics; adjust prompts, thresholds, campaign params.
- API changes: pin Twitter and client library versions; monitor deprecations; regression tests.

## Security
- Do not hardcode secrets; load from Secret Manager into env; mask in logs.
- Rotate keys quarterly; least‑privilege IAM; restrict egress where possible.
- Content safety: avoid replying to minors/sensitive topics; maintain blocklist.

## Deliverables
- Source with modular layout (`clients/`, `services/`, `config/`, `tests/`).
- Deployment scripts and environment templates (no secrets).
- Documentation: runbook for ops, alert playbooks, configuration guide.

## Next Steps
- Implement the scheduled polling Cloud Function, Firestore schema, Twitter/Blackbox clients, and tests.
- Validate in `dev` dry‑run, then staged rollout with monitoring and rate‑limit safeguards.

## Quick Start
- Prerequisites: Python 3.11, a Twitter developer app with v2 access, and a Blackbox.ai API key.
- Create and activate venv:
  - `python3 -m venv .venv`
  - `. .venv/bin/activate`
- Install deps: `python -m pip install -r requirements.txt`
- Copy env template: `cp .env.example .env` and fill your keys.
- Verify env: `python -m src.config.env`

## Configuration (.env)
- Required:
  - `BLACKBOX_API_KEY`
  - `TWITTER_BEARER_TOKEN`
  - `TWITTER_CONSUMER_KEY`
  - `TWITTER_CONSUMER_SECRET`
  - `TWITTER_ACCESS_TOKEN`
  - `TWITTER_ACCESS_TOKEN_SECRET`
- Optional:
  - `DRY_RUN` (set `1` for sample outputs; `0` or unset for live)
  - `MAX_RESULTS` (tweets per fetch, default `10`)
  - `RATE_LIMIT_MIN_REMAINING` (min headroom to proceed, default `0`)
  - `WAIT_ON_429_SECONDS` (short retry wait after 429, default `0`)
  - `AUTO_WAIT_FOR_RESET` (set `1` to auto wait until reset and retry)
  - `MAX_AUTO_WAIT_SECONDS` (max auto-wait cap, default `900`)

## Run
- Dry-run (no Twitter posting):
  - `export DRY_RUN=1`
  - `python -m src.main`
- Live mode (posts replies):
  - `unset DRY_RUN` or set `DRY_RUN=0`
  - `python -m src.main`

## Testing
- Disable auto-loaded plugins and run tests:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`

## Troubleshooting
- 429 / rate-limited:
  - Lower frequency (use a scheduler), reduce `MAX_RESULTS`, or enable `AUTO_WAIT_FOR_RESET=1` with a reasonable `MAX_AUTO_WAIT_SECONDS`.
  - Check headers logged by the app (`x-rate-limit-remaining`, `x-rate-limit-reset`).
- Credentials:
  - Run `python -m src.config.env` to confirm presence; values are masked.
- Replies too long or missing link:
  - Replies are capped ~270 characters; ensure the link appears early in the LLM output. Adjust prompt if needed.
