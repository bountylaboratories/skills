# RankBy Expressions Guide

RankBy lets you define custom scoring/ranking formulas as JSON AST expressions. They control how search results are ordered beyond simple BM25 relevance.

## When to Use RankBy

- **Default behavior is usually fine.** Each search type has sensible defaults.
- Use custom `rankBy` when you need to weight results differently — e.g., prioritize people with more connections, or boost results from specific fields.
- The `search li-users` CLI command supports `--rank-by <json>` for custom ranking expressions.

## How It Works

For **users** and **li-users** searches:
- The text query is converted to BM25 expressions that score against FTS fields
- RankBy is the actual scoring formula sent to Turbopuffer
- If you provide a query but no rankBy, the default BM25 formula is used
- If you provide neither query nor rankBy, results are ordered by a default field

For **repos** searches:
- The query generates a vector embedding for semantic (ANN) search
- RankBy is evaluated client-side to combine ANN score with attribute-based scoring
- Default: `0.7 * ANN + 0.2 * log_norm(stars, 500K) + 0.1 * log_norm(issues_closed, 200K)`

## Default Formulas

### GitHub Users (when query is provided)
```
3 × BM25(emails, query)
+ 3 × BM25(bio, query)
+ 2 × BM25(location, query)
+ 1 × BM25(login, query)
+ 1 × BM25(company, query)
```

### Professional Profiles / li-users (when query is provided)
```
5   × BM25(full_name, query)
+ 4   × BM25(headline, query)
+ 3   × BM25(current_title, query)
+ 3   × BM25(expertise, query)
+ 2   × BM25(current_title_at_company, query)
+ 1.5 × BM25(titles, query)
+ 1.5 × BM25(campuses, query)
+ 1   × BM25(majors, query)
```

### Repositories (default)
```
0.7 × ANN_score + 0.2 × log_norm(stars, 500K) + 0.1 × log_norm(issues_closed, 200K)
```

## Expression Types

| Type | Description | JSON |
|------|-------------|------|
| `BM25` | Full-text search scoring on a field | `{"type":"BM25","field":"headline","query":"ml engineer"}` |
| `Attr` | Reference a document attribute | `{"type":"Attr","name":"connections_count"}` |
| `Const` | Constant number | `{"type":"Const","value":0.5}` |
| `Sum` | Sum of expressions | `{"type":"Sum","exprs":[...]}` |
| `Mult` | Product of two expressions | `{"type":"Mult","exprs":[expr1, expr2]}` |
| `Div` | Division of two expressions | `{"type":"Div","exprs":[expr1, expr2]}` |
| `Max` | Maximum of expressions | `{"type":"Max","exprs":[...]}` |
| `Min` | Minimum of expressions | `{"type":"Min","exprs":[...]}` |
| `Log` | Logarithm | `{"type":"Log","base":10,"expr":...}` |
| `Saturate` | Sigmoid-like saturation to [0,1) | `{"type":"Saturate","expr":...,"midpoint":1000}` |

**Note:** For Turbopuffer-native conversion (users/li-users), only `Sum`, `Mult(Const, expr)`, `Max`, and `BM25` are supported. `Attr`, `Saturate`, `Div`, `Min`, `Log` are evaluated client-side (repos only).

## Available Column Names for li-users

These are the attribute names you can use in `Attr` expressions for li-user searches:

| Column | Type | Description |
|--------|------|-------------|
| `connections_count` | uint | LinkedIn connections |
| `follower_count` | uint | LinkedIn followers |
| `current_tenure_months` | uint | Months at current company |
| `total_experience_years` | uint | Total years of experience |
| `num_positions` | uint | Number of positions held |
| `max_company_employees` | uint | Largest company size worked at |

## Examples

### Custom li-user BM25 with different weights
Weight expertise and title higher, ignore name matching:
```json
{
  "type": "Sum",
  "exprs": [
    {"type": "Mult", "exprs": [{"type": "Const", "value": 5}, {"type": "BM25", "field": "expertise", "query": "kubernetes docker terraform"}]},
    {"type": "Mult", "exprs": [{"type": "Const", "value": 4}, {"type": "BM25", "field": "headline", "query": "infrastructure platform engineer"}]},
    {"type": "Mult", "exprs": [{"type": "Const", "value": 3}, {"type": "BM25", "field": "current_title", "query": "platform engineer sre"}]},
    {"type": "Mult", "exprs": [{"type": "Const", "value": 2}, {"type": "BM25", "field": "certifications", "query": "aws gcp azure"}]}
  ]
}
```

### Search multiple distinct terms across different fields
Find people who are ML engineers AND went to top schools:
```json
{
  "type": "Sum",
  "exprs": [
    {"type": "Mult", "exprs": [{"type": "Const", "value": 5}, {"type": "BM25", "field": "headline", "query": "machine learning ai deep learning"}]},
    {"type": "Mult", "exprs": [{"type": "Const", "value": 3}, {"type": "BM25", "field": "current_title", "query": "machine learning engineer researcher"}]},
    {"type": "Mult", "exprs": [{"type": "Const", "value": 2}, {"type": "BM25", "field": "campuses", "query": "stanford mit berkeley cmu carnegie"}]}
  ]
}
```
