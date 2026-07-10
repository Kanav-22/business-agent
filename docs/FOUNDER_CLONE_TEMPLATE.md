# Founder Clone Template

A structured profile of YOU that makes every recommendation founder-specific
instead of generic. Stored in the `founder_profile` table (key/value), edited via
the Venture Studio page or `PUT /api/founder`, and automatically prepended to
venture workflow briefs and router decisions.

Fill every field honestly — especially the uncomfortable ones (weaknesses,
decision flaws, distractions). The agents can only challenge you as well as you
let them know you.

## The 16 fields

| Key | What to write | Example |
|-----|---------------|---------|
| `skills` | What you're genuinely good at, with evidence | "Python (3 yrs), basic web scraping, writing; sold ₹40k of freelance work" |
| `weaknesses` | What you're bad at or avoid | "Cold calling, design, finishing the last 10%" |
| `working_style` | How you actually work best | "Deep-work mornings, hate meetings, ship better with weekly public deadlines" |
| `risk_tolerance` | low / medium / high + what that means for you | "Medium — can lose ₹50k without stress, cannot go without income >4 months" |
| `budget_range` | Capital actually available for the next venture | "₹50,000 total, ₹10k/month sustainable" |
| `long_term_goals` | Where this is supposed to lead in 3–5 years | "₹3L/month owner income from products, location-independent, no employees before ₹1L MRR" |
| `current_assets` | What you already have: audience, network, tools, IP | "800 LinkedIn followers, 2 potential clinic contacts, a half-built scraper" |
| `coding_ability` | Honest level — agents scope MVPs to this | "Basic: can glue APIs and ship a Flask app; cannot build real-time systems" |
| `business_interests` | Domains that hold your attention | "Healthcare ops, developer tools, trading analytics" |
| `communication_style` | How you want agents to talk to you | "Blunt, numbers first, no cheerleading, short answers" |
| `decision_flaws` | Your known failure modes in decisions | "Overweight novelty, underweight distribution, quit at the boring middle" |
| `how_to_challenge` | What agents should push back on and how | "Ask 'where will customer #1 come from' on every idea; make me pre-sell before building" |
| `how_to_focus` | What keeps you on one thing | "Public commitments, weekly metrics review, a written kill-list of parked ideas" |
| `distracting_ideas` | The shiny things that derail you | "New AI model demos, crypto tools, anything needing a mobile app" |
| `avoid` | Hard constraints — never recommend these | "Businesses needing >₹2L capital, pure content grind, anything requiring sales headcount" |
| `double_down` | Where past evidence says to lean in | "B2B automation for clinics — only niche where prospects replied fast" |

## How agents use it

- **Router** (`/api/route`): appends a founder-fit note — budget vs.
  `budget_range`, request vs. `distracting_ideas` and `avoid`, risk level vs.
  `risk_tolerance`.
- **Venture workflows** (debate, failure sim, interviews, scoring): the profile
  is prepended to every task brief, so the CFO attacks *your* budget math, the
  COO plans around *your* hours and skills, and the scorer's `founder_fit`
  category is scored against this file instead of guessed.
- **CEO / COO in debates**: `how_to_challenge`, `decision_flaws`, and
  `communication_style` shape the tone — a founder who wrote "make me pre-sell
  before building" will see that objection every time, on purpose.
- **Idea scoring**: `avoid` matches can cap the verdict at Test-First; `double_down`
  matches are noted but never inflate scores (the engine stays strict).

## Maintenance

Review monthly and after every postmortem. When a `financial_assumption` or
`lesson_learned` memory contradicts a field (e.g. risk tolerance proved lower
than claimed), update the field — the clone is only useful while it's true.

## Privacy

The profile lives in your local SQLite database and is injected only into your
own agents' briefs. Don't put credentials or anything you wouldn't paste into a
prompt in it.
