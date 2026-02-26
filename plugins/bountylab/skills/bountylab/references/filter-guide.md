# Filter & Operator Reference

Filters are JSON objects passed via `-f '<json>'`. All string values are **auto-lowercased** before matching.

## Critical Rule: Default to ContainsAllTokens

**Almost every string/text filter should use `ContainsAllTokens`, not `Eq`.** The data in our indexes is messy, inconsistent, and varies in format. `Eq` requires an EXACT match against the stored value — if the stored value is even slightly different from what you pass, you get zero results.

**Why `Eq` fails in practice:**
- Company names vary: `"Google"`, `"Google LLC"`, `"Google Inc."`, `"Alphabet/Google"` — `Eq "google"` misses most of these
- Titles vary: `"Senior Software Engineer"`, `"Sr. Software Engineer"`, `"Senior SWE"` — `Eq` only matches one
- Campuses vary: `"Stanford University"`, `"Stanford University School of Engineering"`, `"Stanford"` — `Eq "stanford university"` misses the others
- Locations vary: `"San Francisco, CA"`, `"San Francisco"`, `"SF Bay Area"` — `Eq` is useless here

**`ContainsAllTokens` handles all of this.** It tokenizes both the filter value and field content, then checks that every token appears somewhere. `"google"` matches `"Google LLC"`. `"stanford"` matches `"Stanford University School of Engineering"`. `"senior engineer"` matches `"Senior Software Engineer"`.

**When `Eq` IS appropriate:**
- Enum-like fields with known exact values: `seniority_level` (values: `"Entry"`, `"Senior"`, `"Manager"`, `"Director"`, `"VP"`)
- ID lookups: `githubId`, `linkedin_url`, `bountylab_user_id`
- `language` on repos (exact values like `"Rust"`, `"Go"`, `"TypeScript"`)

**When `IGlob` IS appropriate:**
- **Location fields** (`city`, `state`, `country`): Data is stored with mixed casing (e.g. `"San Francisco"`, `"United States"`). `Eq` is case-sensitive and will miss results. Use `IGlob` for case-insensitive exact matching: `{"field":"city","op":"IGlob","value":"san francisco"}`
- Non-FTS fields where you need case-insensitive matching

---

## Data Structure (Turbopuffer Schema)

Understanding how data is stored is essential for choosing the right operator. Fields have two key properties from the schema:

- **`filterable: true`** — supports Eq, NotEq, In, NotIn, Glob, IGlob, Contains, etc.
- **`full_text_search: true`** — supports `ContainsAllTokens` (tokenized matching)
- Fields can be both, one, or neither

Field types:
- `string` — single string value
- `uint` — unsigned integer
- `bool` — boolean
- `[]string` — array of strings (e.g. a person's list of past companies)
- `[]uint` — array of unsigned integers
- `datetime` — timestamp (not filterable)

### How ContainsAllTokens works on arrays (`[]string`)

For array fields like `companies`, `campuses`, `titles`, etc., `ContainsAllTokens` tokenizes the filter value and checks if all tokens appear across ANY element in the array. This is far more flexible than `Contains` (which requires an exact full-string match against a single array element).

Example: `campuses` might contain `["Stanford University School of Engineering", "MIT"]`
- `Contains "stanford university"` — **MISS** (no element is exactly `"stanford university"`)
- `ContainsAllTokens "stanford"` — **HIT** (token `"stanford"` appears in the first element)
- `ContainsAllTokens "stanford engineering"` — **HIT** (both tokens appear in the first element)

---

## Filter Structure

**Field filter:**
```json
{ "field": "<fieldName>", "op": "<operator>", "value": <value> }
```

**Composite filter (And / Or):**
```json
{
  "op": "And",
  "filters": [
    { "field": "field1", "op": "ContainsAllTokens", "value": "some query" },
    { "field": "field2", "op": "Gte", "value": 100 }
  ]
}
```

---

## Operators Quick Reference

### Text Matching (use these for strings)

| Operator | When to use | Value type |
|----------|-------------|------------|
| `ContainsAllTokens` | **DEFAULT for all text fields.** Tokenized matching — all tokens must appear in any order. | string |
| `Eq` | Only for exact-value fields (booleans, enums, IDs, `country`, `language`) | string, number, bool |
| `In` | Same as Eq but matching one of several exact values | string[], number[] |

### Numeric

| Operator | Description |
|----------|-------------|
| `Gte` / `Gt` | Greater than or equal / greater than |
| `Lte` / `Lt` | Less than or equal / less than |

### Negation

| Operator | Description |
|----------|-------------|
| `NotEq` | Not equal (exact) |
| `NotIn` | Not one of (exact) |
| `NotContains` | Array does not contain exact value |
| `NotContainsAny` | Array contains none of exact values |

### Array (for `[]string` and `[]uint` fields)

| Operator | When to use |
|----------|-------------|
| `Contains` | Only when you know the EXACT stored string in the array |
| `ContainsAny` | Only when you know the EXACT stored strings and want to match any |
| `ContainsAllTokens` | **DEFAULT for array text fields.** Tokenized matching across all elements. |

### Rarely Needed

| Operator | When to use |
|----------|-------------|
| `Glob` / `IGlob` | Wildcard patterns on non-FTS filterable fields. Almost never needed. |
| `Regex` | Complex patterns. Almost never needed. |

---

## GitHub User Fields

Schema: `TurbopufferUserSchema` in `packages/turbopuffer/src/schema.ts`

| Field | Type | filterable | FTS | Best operator |
|-------|------|------------|-----|---------------|
| `githubId` | string | yes | no | Eq, In |
| `login` | string | yes | yes | ContainsAllTokens |
| `displayName` | string | yes | yes | ContainsAllTokens |
| `bio` | string | yes | yes | ContainsAllTokens |
| `company` | string | yes | yes | ContainsAllTokens |
| `location` | string | yes | yes | ContainsAllTokens |
| `emails` | string | yes | yes | ContainsAllTokens |
| `resolvedCountry` | string | yes | yes | Eq or In (known enum values) |
| `resolvedState` | string | yes | yes | Eq or In (known enum values) |
| `resolvedCity` | string | yes | yes | ContainsAllTokens (city names vary) |

### User filter examples

```bash
# Find users by company (ContainsAllTokens handles "Google LLC", "Google Inc", etc.)
bountylab search users -f '{"field":"company","op":"ContainsAllTokens","value":"google"}' -n 50 -j

# Text search + country filter (country is an enum-like field, Eq is fine)
bountylab search users "rust developer" -f '{"field":"resolvedCountry","op":"Eq","value":"united states"}' -n 50 -j

# Users in multiple countries
bountylab search users "frontend" -f '{"field":"resolvedCountry","op":"In","value":["united states","canada","united kingdom"]}' -n 50 -j

# Count users in a country
bountylab raw user-count -f '{"field":"resolvedCountry","op":"Eq","value":"germany"}'
```

---

## Repository Fields

Schema: `TurbopufferRepoSchema` in `packages/turbopuffer/src/schema.ts`

| Field | Type | filterable | FTS | Best operator |
|-------|------|------------|-----|---------------|
| `githubId` | string | yes | no | Eq, In |
| `ownerLogin` | string | yes | no | Eq, In |
| `name` | string | yes | no | Eq, In |
| `stargazerCount` | uint | yes | no | Gte, Lte, Gt, Lt |
| `language` | string | yes | no | Eq, In (known enum: `"Rust"`, `"Go"`, etc.) |
| `totalIssuesCount` | uint | yes | no | Gte, Lte |
| `totalIssuesOpen` | uint | yes | no | Gte, Lte |
| `totalIssuesClosed` | uint | yes | no | Gte, Lte |
| `ownerLocation` | string | yes | yes | ContainsAllTokens |
| `lastContributorLocations` | []string | yes | yes | ContainsAllTokens |
| `description` | string | **no** | yes | FTS/BM25 query only (not filterable) |
| `readmePreview` | string | **no** | yes | FTS/BM25 query only (not filterable) |

### Repo filter examples

```bash
# Rust repos with 1000+ stars
bountylab search repos "web framework" -f '{"op":"And","filters":[{"field":"language","op":"Eq","value":"rust"},{"field":"stargazerCount","op":"Gte","value":1000}]}' -n 20 -j

# All repos by an owner
bountylab search repos null -f '{"field":"ownerLogin","op":"Eq","value":"vercel"}' -n 50 -j

# Multiple languages
bountylab search repos "game engine" -f '{"field":"language","op":"In","value":["C++","Rust","C"]}' -n 20 -j

# Repos with contributors in a location
bountylab search repos "database" -f '{"field":"lastContributorLocations","op":"ContainsAllTokens","value":"san francisco"}' -n 20 -j
```

---

## Professional Profile (li-users) Fields

Schema: `TurbopufferLiUserSchema` in `packages/turbopuffer/src/schema.ts`

### FTS Fields (support ContainsAllTokens — use this operator for all of these)

| Field | Type | filterable | Best operator |
|-------|------|------------|---------------|
| `full_name` | string | yes | ContainsAllTokens |
| `headline` | string | **no** | ContainsAllTokens only |
| `current_title` | string | yes | ContainsAllTokens |
| `current_titles` | []string | **no** | ContainsAllTokens only |
| `current_title_at_company` | []string | yes | ContainsAllTokens |
| `titles` | []string | **no** | ContainsAllTokens only |
| `title_at_company` | []string | yes | ContainsAllTokens |
| `past_title_at_company` | []string | yes | ContainsAllTokens |
| `campuses` | []string | yes | ContainsAllTokens |
| `majors` | []string | yes | ContainsAllTokens |
| `major_at_campus` | []string | **no** | ContainsAllTokens only |
| `expertise` | []string | yes | ContainsAllTokens |
| `certifications` | []string | yes | ContainsAllTokens |

### Enum/Exact-Value Fields (Eq or In is appropriate)

| Field | Type | Notes |
|-------|------|-------|
| `linkedin_url` | string | ID field — Eq only |
| `city` | string | **IGlob** — data has mixed casing, Eq will fail |
| `state` | string | **IGlob** — data has mixed casing, Eq will fail |
| `country` | string | **IGlob** — data has mixed casing, Eq will fail |
| `seniority_level` | string | Eq, In — values: `"Entry"`, `"Senior"`, `"Manager"`, `"Director"`, `"VP"`, etc. |
| `current_company` | string | **Use ContainsAllTokens** — company names vary! This is filterable but NOT FTS, so use IGlob `"*stripe*"` as fallback if ContainsAllTokens isn't available. Actually, this field lacks FTS — use Eq only if you know the exact value, otherwise filter on `current_title_at_company` with ContainsAllTokens. |
| `bountylab_user_id` | string | ID field — Eq only |

### Numeric Fields (Gte, Lte, Gt, Lt)

| Field | Type |
|-------|------|
| `connections_count` | uint |
| `follower_count` | uint |
| `current_tenure_months` | uint |
| `total_experience_years` | uint |
| `num_positions` | uint |
| `max_company_employees` | uint |

### Boolean Fields (Eq only)

| Field |
|-------|
| `is_currently_employed` |
| `has_patents` |
| `has_publications` |
| `is_linked` |

### Array Fields (filterable, no FTS — use Contains/ContainsAny with exact values)

| Field | Type | Notes |
|-------|------|-------|
| `current_companies` | []string | Exact company names |
| `companies` | []string | All companies ever worked at |
| `past_companies` | []string | Previous companies |
| `tenure_buckets` | []string | Tenure ranges |
| `industries` | []string | Industry labels |
| `graduation_years` | []uint | Graduation years |
| `emails` | []string | Email addresses |
| `email_domains` | []string | Email domains |
| `languages` | []string | Spoken languages |

**Important about `companies`, `current_companies`, `past_companies`:** These are filterable but NOT FTS-enabled, so `ContainsAllTokens` is NOT available on them. You must use `Contains` or `ContainsAny` with exact company name strings. If you don't know the exact stored name, use `current_title_at_company` or `title_at_company` with `ContainsAllTokens` instead — those fields ARE FTS-enabled and contain both the title and company name.

### Professional profile filter examples

```bash
# Find engineers by title (ContainsAllTokens — handles all title variations)
bountylab search li-users -f '{"field":"headline","op":"ContainsAllTokens","value":"senior software engineer"}' -n 100 -j

# Find people at a specific company via title_at_company (FTS-enabled, handles name variations)
bountylab search li-users -f '{"field":"current_title_at_company","op":"ContainsAllTokens","value":"stripe"}' -n 100 -j

# Find staff+ engineers at a company
bountylab search li-users -f '{"field":"current_title_at_company","op":"ContainsAllTokens","value":"staff engineer google"}' -n 50 -j

# Senior+ engineers in San Francisco
bountylab search li-users "software engineer" -f '{"op":"And","filters":[{"field":"city","op":"IGlob","value":"san francisco"},{"field":"seniority_level","op":"In","value":["Senior","Manager","Director","VP"]}]}' -n 100 -j

# Stanford grads in CS (ContainsAllTokens handles campus/major name variations)
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"majors","op":"ContainsAllTokens","value":"computer science"},{"field":"is_linked","op":"Eq","value":true}]}' -n 50 -j

# ML engineers with 8+ years experience
bountylab search li-users -f '{"op":"And","filters":[{"field":"headline","op":"ContainsAllTokens","value":"machine learning engineer"},{"field":"total_experience_years","op":"Gte","value":8}]}' -n 50 -j

# Ex-FAANG via title_at_company (handles company name variations)
bountylab search li-users -f '{"op":"Or","filters":[{"field":"title_at_company","op":"ContainsAllTokens","value":"google"},{"field":"title_at_company","op":"ContainsAllTokens","value":"meta"},{"field":"title_at_company","op":"ContainsAllTokens","value":"apple"},{"field":"title_at_company","op":"ContainsAllTokens","value":"amazon"}]}' -n 100 -j

# People with specific expertise
bountylab search li-users -f '{"field":"expertise","op":"ContainsAllTokens","value":"kubernetes"}' -n 100 -j

# Experienced, currently employed with high connections
bountylab search li-users -f '{"op":"And","filters":[{"field":"headline","op":"ContainsAllTokens","value":"engineer"},{"field":"total_experience_years","op":"Gte","value":8},{"field":"is_currently_employed","op":"Eq","value":true},{"field":"connections_count","op":"Gte","value":500}]}' -n 50 -j

# Exclude specific companies (companies field is NOT FTS — must use exact Contains)
bountylab search li-users "software engineer" -f '{"op":"And","filters":[{"field":"city","op":"IGlob","value":"san francisco"},{"field":"current_companies","op":"NotContainsAny","value":["Google","Meta","Apple"]}]}' -n 100 -j

# People who graduated in specific years
bountylab search li-users -f '{"op":"And","filters":[{"field":"graduation_years","op":"ContainsAny","value":[2020,2021,2022]},{"field":"majors","op":"ContainsAllTokens","value":"computer science"}]}' -n 50 -j
```

---

## Operator Decision Tree

1. **Is the field a boolean?** → `Eq`
2. **Is the field a number?** → `Gte`, `Lte`, `Gt`, `Lt` (or `Eq` for exact number)
3. **Is the field an ID or enum with known exact values?** (githubId, linkedin_url, country, state, language, seniority_level) → `Eq` or `In`
4. **Is the field FTS-enabled?** (check schema — `full_text_search: true`) → **`ContainsAllTokens`**
5. **Is the field a `[]string` without FTS?** (companies, industries, etc.) → `Contains` / `ContainsAny` with exact values. If you don't know the exact value, find an FTS-enabled field that contains similar data (e.g. use `title_at_company` instead of `companies`).
6. **Is the field a filterable string without FTS?** → `Eq` / `In` if you know exact values, or `IGlob` with wildcards as last resort.
