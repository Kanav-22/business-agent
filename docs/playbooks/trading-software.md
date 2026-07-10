# Playbook: Trading Software Business

Sell tools TO traders — analytics, journaling, alerts, backtesting. The reliable
business is the shovel store, not the gold mine: this playbook is explicitly NOT
about running trading capital or selling signals.

## Best niche examples
- Trade journaling + performance analytics for retail options/F&O traders.
- Backtesting UI for a specific broker's API users.
- Alert/scanner tools for one strategy community (breakouts, momentum).
- Broker-account P&L consolidation and tax reports.

## Ideal customer profile
Active retail traders (>10 trades/month) on a specific broker/platform, already
paying for data or tools, present in trading Discords/Telegrams/YouTube audiences.
They churn when they stop trading — expect structurally higher churn than normal
SaaS.

## MVP
One workflow on one broker integration: e.g. "auto-import your Zerodha trades,
see your real win-rate and cost of mistakes in 5 minutes." Read-only API access
only — never touch order placement in v1 (risk and compliance jump massively).

## Pricing model
$15–50 / ₹500–2,000 per month, free trial limited by history depth (e.g. last 30
days free, full history paid). Annual discount matters — it hedges their
trading-activity churn. Avoid revenue-share/performance pricing: it drags you
toward advice territory.

## Sales channels
Trading communities (Discord/Telegram/subreddits) where the broker's users gather,
YouTube trading educators (affiliate 20–30%), broker app marketplaces where they
exist.

## Marketing channels
Free calculators/scanners as top-of-funnel, SEO on "broker-name + journal/
backtest/tax", transparent build-in-public content (traders respect live P&L
honesty), educator partnerships.

## Tech stack
Broker APIs (read-only scopes), Python/pandas backend for analytics, Next.js
front-end, Postgres, a job queue for nightly imports. Charting: TradingView
widgets or lightweight-charts. Market data costs money at scale — cache
aggressively.

## First 10 customers strategy
Join 3 communities of the target broker's users → post one genuinely useful free
analysis (e.g. "I analyzed 500 trades; here's where retail loses money") → DM the
people who engage; onboard them personally, importing their real history on a call
→ founding-member pricing locked for life.

## 30-day launch plan
- **Week 1:** broker API access + import pipeline for one broker; compute 5 core
  stats (win rate, expectancy, fee drag, drawdown, revenge-trading flag).
- **Week 2:** dashboard UI; onboard 5 community members free; fix data-quality
  issues (there will be many).
- **Week 3:** payment + trial gate; publish the free analysis post; educator
  outreach (3 affiliates).
- **Week 4:** public launch in communities; 10 paying target; collect testimonial
  screenshots (with permission).

## Common mistakes
Building signal/advice features (regulatory line-crossing); supporting 5 brokers
at launch (each import pipeline is its own product); underestimating data-quality
work (splits, corporate actions, fee structures); marketing "make money" instead
of "know your numbers"; ignoring the churn structure (traders quit trading).

## Risks
**Regulatory:** anything resembling investment advice may require registration
(e.g. SEBI RIA/RA in India, similar elsewhere) — stay strictly on analytics of the
user's own data; have a lawyer review marketing copy. **Platform:** broker API
policy changes. **Market cyclicality:** churn spikes in bear markets — annual
plans and multi-broker coverage hedge it. **Liability:** a data bug that
misstates P&L destroys trust — reconcile against broker statements automatically.

## KPIs
Trial→paid conversion (target 5–10%), churn (expect 6–10%/mo; watch the trend not
the level), MRR, import success rate (>99%), weekly active usage on trading days,
affiliate-sourced share of signups.

## Scaling path
One broker → adjacent brokers (shared UI, new pipelines) → team/prop-desk tier →
tax-season reports as an upsell spike → API access for power users. Resist the
pull toward managing money or selling signals — different business, different
license, different risk.
