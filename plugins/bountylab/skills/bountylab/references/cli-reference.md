# Bounty Lab CLI Complete Reference

## Authentication

### `bountylab login --key <api-key>`
Save an API key directly. Always use this method from a skill context.

### `bountylab logout`
Remove the saved API key from `~/.bountylab/key`.

---

## Search Commands

### `bountylab search users [query]`
BM25 full-text search across GitHub user profiles.

**Query is optional.** When provided, results are ranked by BM25 relevance across FTS fields. When omitted, returns filter-matched results ordered by recency.

**FTS fields searched** (weighted): login, displayName, bio, company, location, emails, resolvedCountry, resolvedState, resolvedCity

**Options:**
- `-n, --max-results <N>` — Max results (default: 20, max: 1000)
- `-f, --filters <json>` — JSON filter expression (see [filter-guide.md](filter-guide.md))
- `-j, --json` — Raw JSON output (use this for programmatic access)
- `--fields <fields>` — Comma-separated fields to include in JSON output (supports dot notation)

**Examples:**
```bash
# Text search with selected fields
bountylab search users "kubernetes golang" -n 30 -j --fields login,displayName,location,bio

# Filter-only (no text query)
bountylab search users -f '{"field":"resolvedCountry","op":"Eq","value":"germany"}' -n 50 -j --fields login,displayName,location

# Text + filter
bountylab search users "rust developer" -f '{"field":"resolvedCountry","op":"Eq","value":"united states"}' -n 50 -j --fields login,displayName,location,bio
```

**Response fields (JSON):**
```json
{
  "count": 30,
  "users": [{
    "id": "bl_xxx",
    "githubId": "MDQ6VXNlcjE=",
    "login": "username",
    "displayName": "Full Name",
    "bio": "Software engineer...",
    "company": "ACME Corp",
    "location": "San Francisco, CA",
    "resolvedCity": "San Francisco",
    "resolvedState": "California",
    "resolvedCountry": "United States",
    "emails": ["user@example.com"],
    "websiteUrl": "https://...",
    "socialAccounts": [{"provider": "twitter", "url": "..."}],
    "score": 0.123,
    "createdAt": "2020-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }]
}
```

### `bountylab search users-nl <query>`
AI-powered natural language user search. The query is interpreted by an AI model that generates an optimized BM25 query.

**Options:**
- `-n, --max-results <N>` — Max results (default: 20)
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output

**Example:**
```bash
bountylab search users-nl "senior rust developers in Germany who work on embedded systems" -n 20 -j --fields login,displayName,location,bio
```

**Response includes `searchQuery` showing what the AI generated:**
```json
{
  "count": 15,
  "searchQuery": "rust embedded systems firmware",
  "users": [...]
}
```

### `bountylab search repos <query>`
Semantic search using vector embeddings across repository READMEs and descriptions.

**Query modes:** `"text"` for semantic search, `null` for filter-only.

**Options:**
- `-n, --max-results <N>` — Max results (default: 20, max: 1000)
- `-f, --filters <json>` — JSON filter expression
- `-i, --include <attrs>` — Graph attributes: `owner,contributors:N,starrers:N`
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output (supports dot notation)

**Example:**
```bash
bountylab search repos "real-time collaborative text editor CRDT" -n 10 -j -i 'owner,contributors:10' --fields name,ownerLogin,stargazerCount,language,description,contributors
```

**Response fields (JSON):**
```json
{
  "count": 10,
  "repositories": [{
    "id": "bl_xxx",
    "githubId": "MDEwOlJlcG9zaXRvcnkx",
    "name": "repo-name",
    "ownerLogin": "owner",
    "stargazerCount": 5000,
    "language": "TypeScript",
    "description": "A real-time collaborative editor...",
    "readmePreview": "First 500 chars of README...",
    "totalIssuesOpen": 42,
    "totalIssuesClosed": 300,
    "totalIssuesCount": 342,
    "score": 0.15,
    "owner": { "login": "owner", "displayName": "...", ... },
    "contributors": {
      "edges": [{ "login": "...", "displayName": "...", ... }],
      "pageInfo": { "hasNextPage": true, "endCursor": "abc123" }
    },
    "starrers": {
      "edges": [{ "login": "...", ... }],
      "pageInfo": { "hasNextPage": true, "endCursor": "def456" }
    }
  }]
}
```

### `bountylab search repos-nl <query>`
Natural language repo search (AI-powered).

**Options:**
- `-n, --max-results <N>` — Max results (default: 20)
- `-i, --include <attrs>` — Graph attributes
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output

**Example:**
```bash
bountylab search repos-nl "open source alternatives to Datadog for monitoring Kubernetes clusters" -n 10 -j --fields name,ownerLogin,stargazerCount,description
```

### `bountylab search li-users [query]`
Professional profile BM25 search across LinkedIn-sourced data.

**Query is optional.** When provided, results are ranked by BM25 relevance. When omitted, use filters for targeted lookups (results ordered by connections_count).

**FTS fields searched** (weighted): full_name (5x), headline (4x), current_title (3x), expertise (3x), current_title_at_company (2x), titles (1.5x), campuses (1.5x), majors (1x)

**Options:**
- `-n, --max-results <N>` — Max results (default: 20, max: 1000)
- `-f, --filters <json>` — JSON filter expression (see [filter-guide.md](filter-guide.md))
- `-r, --rank-by <json>` — Custom rankBy expression (see [rankby-guide.md](rankby-guide.md))
- `-i, --include <attrs>` — Include attributes: `github` (inline linked GitHub profile + DevRank)
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output (supports dot notation)
- `--paginate` — Enable cursor pagination
- `--after <cursor>` — Continue from cursor

**Examples:**
```bash
# Text search with selected fields
bountylab search li-users "machine learning engineer" -n 50 -j --fields full_name,headline,current_company,expertise

# Text + filter with inline GitHub profiles (RECOMMENDED for cross-referencing)
bountylab search li-users "machine learning engineer" -f '{"field":"current_company","op":"Eq","value":"meta"}' -n 50 -j -i github --fields full_name,current_title,github.login,github.devrank.tier

# Filter-only (no text query)
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"stripe"}' -n 100 -j --fields full_name,current_title,seniority_level,expertise

# ContainsAllTokens on headline (powerful fuzzy matching)
bountylab search li-users -f '{"field":"headline","op":"ContainsAllTokens","value":"senior staff engineer infrastructure"}' -n 50 -j --fields full_name,headline,current_company
```

**Key fields for cross-referencing:**
- `bountylab_user_id` — BountyLab ID (32-char hex) linking to GitHub profile. Pass to `raw users-by-id` for graph data.
- `is_linked` — `true` if this person has a linked GitHub account in BountyLab
- `github` — (when `-i github` is used) Full GitHub profile with DevRank, including `login`, `bio`, `location`, `devrank`, etc.

**Professional profile response fields (with `-i github`):**
```json
{
  "count": 50,
  "liUsers": [{
    "id": "123456",
    "linkedin_url": "https://...",
    "full_name": "Jane Doe",
    "headline": "Senior ML Engineer at Meta",
    "city": "Menlo Park",
    "state": "California",
    "country": "United States",
    "current_title": "Senior ML Engineer",
    "current_company": "Meta",
    "total_experience_years": 8,
    "expertise": ["Machine Learning", "PyTorch", "NLP"],
    "campuses": ["Stanford University"],
    "majors": ["Computer Science"],
    "bountylab_user_id": "9f0b8901cf1848298a60a60083b5aac0",
    "is_linked": true,
    "score": 12.5,
    "github": {
      "id": "9f0b8901cf1848298a60a60083b5aac0",
      "githubId": "MDQ6VXNlcjU4MzIzMQ==",
      "login": "janedoe",
      "displayName": "Jane Doe",
      "bio": "ML Engineer @Meta. Stanford CS '16.",
      "location": "Menlo Park, CA",
      "devrank": {
        "tier": "DIAMOND",
        "crackedScore": 4500.0
      }
    }
  }],
  "pageInfo": { "hasNextPage": true, "endCursor": "cursor_abc123" }
}
```

**Note:** The `github` field is only present for li-users where `is_linked=true`. For unlinked profiles, it will be absent.

---

## Raw Lookup Commands

### `bountylab raw users <login1> [login2...]`
Batch lookup GitHub users by login (1-100 at a time).

**Options:**
- `-i, --include <attrs>` — Graph/enrichment: `devrank,professional,followers:N,following:N,owns:N,stars:N,contributes:N`
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output (supports dot notation)

**Include attributes explained:**
- `devrank` — Attach DevRank score (tier, crackedScore, trust, etc.)
- `professional` — Attach linked professional/LinkedIn profile data
- `followers:N` / `following:N` — First N followers/following with full profile
- `owns:N` / `stars:N` / `contributes:N` — First N owned/starred/contributed repos

**Example:**
```bash
bountylab raw users torvalds gvanrossum -j -i 'devrank,owns:5,followers:10' --fields login,displayName,devrank,owns,followers
```

### `bountylab raw users-by-id <id1> [id2...]`
Batch lookup by ID. **Accepts both GitHub node IDs (e.g. `MDQ6VXNlcjE=`) and BountyLab IDs (32-char hex).** You can mix ID types in a single call. Same options as `raw users`.

**This is the primary way to look up GitHub profiles from professional profile results.** Professional profiles (`search li-users`) return a `bountylab_user_id` field — pass that directly to this command.

```bash
bountylab raw users-by-id a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4 -j -i 'devrank,professional,owns:10' --fields login,displayName,devrank.tier,devrank.crackedScore,professional,owns
```

### `bountylab raw repos <owner/name> [owner2/name2...]`
Batch lookup repos by full name (1-100 at a time).

**Options:**
- `-i, --include <attrs>` — Graph: `owner,contributors:N,starrers:N`
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output (supports dot notation)

**Example:**
```bash
bountylab raw repos facebook/react vercel/next.js -j -i 'owner,contributors:20' --fields name,ownerLogin,stargazerCount,owner,contributors
```

### `bountylab raw repos-by-id <id1> [id2...]`
Batch lookup by ID. **Accepts both GitHub node IDs and BountyLab IDs (32-char hex).** Same options as `raw repos`.

### `bountylab raw user-count -f '<json>'`
Count GitHub users matching filters. Filter is required.

**Example:**
```bash
bountylab raw user-count -f '{"field":"resolvedCountry","op":"Eq","value":"japan"}'
# Output: Found 234,567 users matching filters
```

### `bountylab raw repo-count -f '<json>'`
Count repos matching filters. Filter is required.

**Example:**
```bash
bountylab raw repo-count -f '{"op":"And","filters":[{"field":"language","op":"Eq","value":"rust"},{"field":"stargazerCount","op":"Gte","value":100}]}'
# Output: Found 4,521 repos matching filters
```

---

## Email Commands

### `bountylab email <login1> [login2...]`
Get best email for GitHub users by login (1-100 at a time).

**Options:**
- `-p, --profile <type>` — `work`, `personal`, or `school` (default: work)
- `-j, --json` — Raw JSON output
- `--fields <fields>` — Comma-separated fields to include in JSON output

**Example:**
```bash
bountylab email octocat torvalds -p work -j --fields login,bestEmail,profile
```

### `bountylab email-by-id <id1> [id2...]`
Get best email by GitHub node ID. Same options.

---

## DevRank Scores

DevRank is accessed via the `-i devrank` include attribute on `raw users` or `raw users-by-id`, **not** as a separate command.

```bash
# Get DevRank for users by login
bountylab raw users torvalds gvanrossum -j -i 'devrank' --fields login,devrank.tier,devrank.crackedScore

# Get DevRank for users by ID (BountyLab IDs from li-user search)
bountylab raw users-by-id a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4 -j -i 'devrank' --fields login,devrank
```

**DevRank fields** (returned under `.devrank` on each user):
- `tier` — PLATINUM, EMERALD, DIAMOND, GOLD, SILVER, BRONZE, IRON
- `crackedScore` — Numeric score (higher = better)
- `rawScore`, `trust`, `pc`, `followersIn`, `followingOut`, `community`
