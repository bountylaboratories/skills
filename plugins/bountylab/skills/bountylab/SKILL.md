---
name: bountylab
description: >
  Search and research developers, repositories, professional profiles, emails, and DevRank scores
  using the Bounty Lab developer intelligence platform. Use when the user asks to "find developers",
  "search for candidates", "look up a GitHub user", "find repos", "get developer emails",
  "search professional profiles", "find engineers at <company>", "source candidates for <role>",
  "research a developer", "find contributors to <repo>", "get devrank scores",
  or any task involving developer sourcing, talent research, or technical recruiting.
allowed-tools: Bash(node *), Bash(python3 *), Read, Grep, Glob, Write, Task
---

# Bounty Lab Developer Intelligence

You have access to the `bountylab` CLI at `${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/bountylab.js`.
Run it with: `node ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/bountylab.js <command>`

For brevity in examples below, we write `bountylab` to mean the full path above.

## Authentication

**IMPORTANT: NEVER ask the user for an API key. Always use the browser login flow.**

Before any command, check if an API key exists:

```bash
cat ~/.bountylab/key 2>/dev/null
```

If no key exists, you MUST run the login command immediately — do NOT ask the user to provide or paste a key:

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/bountylab.js login --detached
```

The `--detached` flag starts a background server and exits immediately, printing a login URL. The output will look like:

```
Open this URL to log in:
https://app.bountylab.io/cli-auth?port=XXXXX&state=XXXXX
```

**You MUST show this URL to the user** so they can open it in their browser. Say something like: "Please open this link to log in to Bounty Lab: <url>". The background server waits up to 120 seconds for the user to complete login. Once they do, the key is saved automatically to `~/.bountylab/key`.

After showing the URL, **wait for the user to confirm they've logged in**, then verify by checking `cat ~/.bountylab/key 2>/dev/null` before continuing with the original task.

The only exception is if the user explicitly provides a key themselves (unprompted), in which case use:

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/bountylab.js login --key <their-key>
```

## Plan Your Search

Before making any API calls, **stop and plan your search strategy**.

### Step 1: Qualify with web search first

Use web search to build context BEFORE hitting the API. This saves wasted calls:
- **Company → industry mapping:** "What does Kikoff do?" → fintech/credit → now you know which industry filters to use
- **Industry → company list:** "Top fintech companies" → stripe, square, plaid, affirm, brex → use as filter values
- **Domain → terminology:** "What technologies are used in quantitative finance?" → helps you pick the right query terms and expertise filters

### Step 2: Decompose into filterable dimensions

Break the request into fields you can actually filter on. Each concept maps to a specific field:

| Concept | Field(s) | Operator |
|---------|----------|----------|
| Company (current) | `current_company` | `Eq`, `In` |
| Company (ever worked at) | `companies` | `Contains`, `ContainsAny` |
| Industry/sector | `industries` | `ContainsAny` |
| University/school | `campuses` | `ContainsAllTokens` (NOT Contains — values vary) |
| Degree/major | `majors` | `ContainsAllTokens` |
| Skills/expertise | `expertise` | `ContainsAny` or `ContainsAllTokens` |
| Job title | `current_title` or `headline` | `ContainsAllTokens` |
| Location | `city`, `state`, `country` | `Eq`, `In` |
| Seniority | `seniority_level` | `Eq`, `In` |
| Experience | `total_experience_years` | `Gte`, `Lte` |
| Has GitHub | `is_linked` | `Eq` |

**Do NOT put multiple concepts into a BM25 query.** "stanford fintech" as a query matches either word independently. Instead, use filters: `campuses ContainsAllTokens "stanford"` AND `industries ContainsAny ["fintech"]`.

### Step 3: Choose your starting point

**Default: `search li-users -i github`** — This is the right starting point 90% of the time. It gives you professional data (title, company, education, expertise) AND inline GitHub profiles with DevRank in a single call. Always include `-i github` unless you have a reason not to.

Only use other starting points when:
- `search users` — You specifically need GitHub-only data (bio, repos) and don't care about professional context
- `search repos` — You're looking for people via their projects (find repos → get contributors)
- `raw users` / `raw users-by-id` — You already have logins or IDs and need enrichment

### Step 4: Plan multiple search angles

A single search is never enough. Plan 2-4 complementary searches:
- **Filter variation:** Same education, different industry filters vs company-name filters (catches people whose industry field isn't set)
- **Different starting points:** li-users for professional data + repos for OSS contributors
- **Network expansion:** Find strong engineers first, then explore their followers/contributors

### Step 5: When to use subagents
- The research requires 10+ API calls
- There are independent search paths that can run in parallel
- You need to search across multiple dimensions (company, skills, location, repos)

## Command Quick Reference

| Command | Purpose |
|---------|---------|
| `bountylab search users [query]` | BM25 text search for GitHub users (query optional) |
| `bountylab search users-nl "<query>"` | AI-powered natural language user search |
| `bountylab search repos "<query>"` | Semantic vector search for repos |
| `bountylab search repos-nl "<query>"` | AI-powered natural language repo search |
| `bountylab search li-users [query]` | Professional profile BM25 search (query optional) |
| `bountylab raw users <login> [login2...]` | Look up GitHub users by login |
| `bountylab raw users-by-id <id> [id2...]` | Look up users by BountyLab ID or GitHub node ID |
| `bountylab raw repos <owner/name>` | Look up repos by full name |
| `bountylab raw user-count -f '<json>'` | Count users matching filters |
| `bountylab raw repo-count -f '<json>'` | Count repos matching filters |
| `bountylab email <login> [login2...]` | Get best email for GitHub users |

Common flags: `-j` (JSON output), `-n <N>` (max results), `-f '<json>'` (filters), `-i '<attrs>'` (include enrichment data), `--fields <fields>` (select specific fields in JSON output)

## Working with Results

- **Always use `-j`** for JSON output so you can process results programmatically
- **Use `--fields`** to select only the fields you need — keeps output clean and focused
  ```bash
  bountylab search li-users "ml" -j --fields full_name,current_title,current_company
  ```
- **Dot notation** works for nested objects (from `-i` enrichments):
  ```bash
  bountylab search li-users "ml" -j -i github --fields full_name,current_title,github.login,github.devrank.tier
  ```
- **DO NOT pipe through `jq`** — read the JSON output directly. You're an LLM; you parse JSON natively.
- **Save intermediate results** to `/tmp` files when you need to reference them across multiple steps.

## ID Types and Cross-Referencing

There are **four types of identifiers** across the system. Understanding them is critical for linking data between professional profiles and GitHub profiles.

### The Four ID Types

| ID Type | Format | Example | Where It Appears |
|---------|--------|---------|-----------------|
| **BountyLab ID** | 32-char hex | `9f0b8901cf1848298a60a60083b5aac0` | `id` field on GitHub users/repos; `bountylab_user_id` field on li-users |
| **GitHub Node ID** | Base64 string | `MDQ6VXNlcjE=` | `githubId` field on GitHub users/repos |
| **GitHub Login** | Username | `torvalds` | `login` field on GitHub users |
| **LinkedIn Profile ID** | Numeric string | `123456789` | `id` field on li-users (NOT the same as BountyLab ID) |

### Resolution Paths — How to Go From One ID Type to Another

```
Professional Profile (li-user)
  ├─ has `bountylab_user_id` (BountyLab ID) when is_linked=true
  └─ Pass to: `raw users-by-id <bountylab_user_id>` → GitHub profile

GitHub Profile (user)
  ├─ has `id` (BountyLab ID), `githubId` (GitHub Node ID), `login`
  └─ Pass to: `raw users -i professional` → linked professional profile

GitHub Login → GitHub Profile
  └─ `raw users <login>`

Any ID (BountyLab or GitHub Node) → GitHub Profile
  └─ `raw users-by-id <id>` (auto-detects format)
```

### Fastest Way: Use `-i github` on li-user search

Add `-i github` to your `search li-users` call. This inlines the linked GitHub profile (with DevRank) directly on each li-user result — no separate lookup needed:

```bash
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"stripe"}' -n 50 -j -i github --fields full_name,current_title,bountylab_user_id,github.login,github.devrank.tier
```

### Include Attributes Reference

**For `search li-users`:** `-i github` (inline GitHub profile + DevRank)

**For `raw users` / `raw users-by-id`:** `-i devrank,professional,followers:N,following:N,owns:N,stars:N,contributes:N`
- `devrank` — DevRank score (tier, crackedScore, etc.)
- `professional` — Linked professional/LinkedIn profile
- `followers:N` / `following:N` — First N followers/following
- `owns:N` / `stars:N` / `contributes:N` — First N repos

## Search Patterns

### Pattern 1: Company Team Mapping
Find engineers at a company with their GitHub profiles in one call:
```bash
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"stripe"}' -n 100 -j -i github --fields full_name,current_title,expertise,bountylab_user_id,github.login,github.devrank.tier
```
For deeper GitHub data (repos, followers), pass BountyLab IDs to raw lookups:
```bash
bountylab raw users-by-id <id1> <id2> -j -i 'owns:10,contributes:10,followers:20' --fields login,displayName,owns,contributes,followers
```

### Pattern 2: OSS Contributor Mining
Find repos in a domain, then extract their contributors:
```bash
bountylab search repos "payment processing API" -n 10 -j -i 'contributors:30' --fields name,ownerLogin,stargazerCount,language,contributors
```
Then look up the most interesting contributors for DevRank and professional context:
```bash
bountylab raw users contributor1 contributor2 contributor3 -j -i 'devrank,professional' --fields login,displayName,devrank.tier,devrank.crackedScore,professional
```

### Pattern 3: Targeted Talent Search
Combine text query with filters for precise sourcing:
```bash
bountylab search li-users "infrastructure platform kubernetes" -f '{"op":"And","filters":[{"field":"country","op":"Eq","value":"united states"},{"field":"total_experience_years","op":"Gte","value":5},{"field":"is_linked","op":"Eq","value":true}]}' -n 50 -j -i github --fields full_name,headline,current_company,total_experience_years,github.login,github.devrank.tier
```

### Pattern 4: Education + Industry Search
Find developers from a specific university in a specific industry. **Important:** Use `ContainsAllTokens` for `campuses` and `majors` — values are full institution names (e.g. "Stanford University School of Engineering") so exact-match operators like `Contains` will miss variants.
```bash
# Stanford grads in fintech — combine education filter with industry filter
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"industries","op":"ContainsAny","value":["financial services","fintech","banking","payments"]}]}' -n 100 -j -i github --fields full_name,headline,current_company,campuses,majors,industries,expertise,github.login,github.devrank.tier

# MIT grads who are currently at FAANG
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"mit"},{"field":"current_company","op":"In","value":["google","meta","apple","amazon","netflix"]}]}' -n 100 -j --fields full_name,current_title,current_company,campuses,majors
```

### Pattern 5: Network Exploration
Start from a known strong engineer and explore their network:
```bash
bountylab raw users strong-engineer -j -i 'followers:50,following:50,owns:10' --fields login,displayName,followers,following,owns
```
Then look up interesting people from their network for professional context.

## Worked Example: "Find Stanford developers in fintech"

Here's how to apply the planning framework:

**Step 1 — Web search:** Search "top fintech companies" → stripe, square, plaid, affirm, brex, coinbase, robinhood, etc. Search "fintech industry categories" → financial services, fintech, banking, payments, cryptocurrency.

**Step 2 — Decompose:** University=Stanford (`campuses ContainsAllTokens "stanford"`), Industry=fintech (`industries ContainsAny [...]`). Also need a company-name fallback since not everyone has industry tags.

**Step 3 — Starting point:** `search li-users -i github` — need education + professional data + DevRank.

**Step 4 — Plan searches:**
```bash
# Search A: Stanford + fintech industries
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"industries","op":"ContainsAny","value":["financial services","fintech","banking","payments","cryptocurrency"]}]}' -n 100 -j -i github --fields full_name,headline,current_company,campuses,expertise,industries,github.login,github.devrank.tier

# Search B: Stanford + known fintech companies (catches people without industry tags)
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"companies","op":"ContainsAny","value":["stripe","square","plaid","affirm","brex","coinbase","robinhood","sofi","chime"]}]}' -n 100 -j -i github --fields full_name,headline,current_company,companies,campuses,github.login,github.devrank.tier

# Search C: Stanford + fintech keywords in headline (catches edge cases)
bountylab search li-users "fintech payments blockchain" -f '{"field":"campuses","op":"ContainsAllTokens","value":"stanford"}' -n 50 -j -i github --fields full_name,headline,current_company,campuses,github.login,github.devrank.tier
```

**Step 5 — Merge, enrich, present:** Deduplicate across searches, get emails for top candidates.

## Using Subagents for Complex Research

For large research tasks (10+ API calls, independent search paths), use the `Task` tool to spawn subagents that work in parallel. Each subagent has full access to the bountylab CLI. Give each a clear task with specific commands. Have them return structured data (logins, IDs, names) that you can merge and deduplicate.

## Reference Documentation

- [cli-reference.md](references/cli-reference.md) — Complete CLI documentation with all options and response fields
- [filter-guide.md](references/filter-guide.md) — Filter syntax, operators, and all available fields
- [rankby-guide.md](references/rankby-guide.md) — Custom ranking expressions
- [research-playbooks.md](references/research-playbooks.md) — Step-by-step sourcing workflows

## Data Analysis & Visualization

You have Python visualization scripts at `${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/`. These produce publication-quality PNG charts that auto-embed in Slack threads.

**Usage pattern:** Fetch data with the CLI → transform to the script's input schema → pipe JSON to the script.

```bash
echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/<script>.py -o /home/claude/output/<name>.png
```

### Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `sankey.py` | Talent flow diagrams | "Where do Stripe engineers go?", company-to-company migration |
| `distribution.py` | Multi-panel demographics (bar, pie, histogram) | Team DNA analysis, skill/seniority/tier breakdowns |
| `network.py` | Network graphs | OSS ecosystem mapping, influence networks, contributor graphs |
| `scatter.py` | Labeled scatter plots | Talent arbitrage (DevRank vs experience), outlier discovery |
| `radar.py` | Radar/spider charts | Cohort comparison (Team A vs Team B across metrics) |
| `heatmap.py` | Heatmaps and matrices | Skill co-occurrence, technology overlap, company-skill matrices |

### Agentic Workflow Example

To create a talent flow chart for Stripe alumni:

1. **Fetch data:** `search li-users -f '{"field":"companies","op":"Contains","value":"stripe"}' -n 200 -j --fields full_name,current_company,past_companies`
2. **Transform:** Extract `past_companies` → `current_company` flows, count transitions
3. **Visualize:** Pipe the flow JSON to `sankey.py`

```bash
echo '{"title":"Stripe Alumni Flow","flows":[{"source":"Stripe","target":"Coinbase","value":12},{"source":"Stripe","target":"Plaid","value":8}]}' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/sankey.py -o /home/claude/output/stripe-flow.png
```

Files written to `/home/claude/output/` are automatically uploaded to the Slack thread. Images (PNG, JPG) embed inline as rich previews.

### Script Input Schemas

**sankey.py** — `{"title", "subtitle?", "flows": [{"source", "target", "value"}]}`

**distribution.py** — `{"title", "subtitle?", "panels": [{"name", "type": "bar"|"pie"|"histogram", "data": {...}|[...]}]}`

**network.py** — `{"title", "subtitle?", "nodes": [{"id", "label", "group?", "size?"}], "edges": [{"source", "target", "weight?"}], "layout?": "spring"|"circular"|"kamada_kawai"|"shell"}`

**scatter.py** — `{"title", "subtitle?", "x_label?", "y_label?", "points": [{"x", "y", "label", "group?", "size?"}], "zones?": [{"label", "x_min", "x_max", "y_min", "y_max", "color?"}]}`

**radar.py** — `{"title", "subtitle?", "axes": [...], "series": [{"name", "values": [...]}]}`

**heatmap.py** — `{"title", "subtitle?", "row_labels", "col_labels", "matrix": [[...]], "colormap?", "annotate?"}`

For detailed analysis playbooks, see [analysis-guide.md](references/analysis-guide.md).

## Output Formats

When presenting results to the user, format them clearly:

- **Candidate lists**: Table with name, login, location, key skills, DevRank tier
- **Company research**: Grouped by team/role with professional + GitHub data merged
- **Email results**: Table with login, email, profile type
- **Repo analysis**: Table with name, stars, language, description, top contributors

Always tell the user how many API calls you made and what you found at each step.
