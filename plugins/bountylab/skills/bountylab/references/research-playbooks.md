# Research Playbooks

Strategy-focused workflows for common sourcing and research tasks. Each playbook describes the approach, then gives concrete commands with `--fields` to keep output focused.

**For complex research with 10+ API calls, use subagents** (the `Task` tool) to parallelize independent searches. See "Subagent Workflows" at the bottom.

---

## Playbook 1: Source Candidates for a Company Role

**Scenario:** "Find backend engineers for Kikoff" or "Source ML engineers for Anthropic"

**Strategy:** Map the company's current team via professional profiles with inline GitHub data. Identify strong engineers, then mine their repo contributor networks and follower graphs for similar talent. Score candidates with DevRank, get emails for outreach.

### Phase 1: Map the company team (one call with -i github)
```bash
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"kikoff"}' -n 100 -j -i github --fields full_name,current_title,expertise,bountylab_user_id,is_linked,github.login,github.devrank.tier
```

### Phase 2: Deep-dive repos and networks for strong engineers
```bash
bountylab raw users-by-id <bountylab_id_1> <bountylab_id_2> -j -i 'owns:10,contributes:10,followers:20' --fields login,displayName,owns,contributes,followers
```

### Phase 3: Mine contributor networks from notable repos
```bash
bountylab raw repos owner/notable-repo -j -i 'contributors:100' --fields name,ownerLogin,stargazerCount,contributors
```

### Phase 4: Search for similar profiles
```bash
bountylab search users-nl "senior backend engineer fintech payments experience" -n 50 -j --fields login,displayName,location,bio
```

### Phase 5: Score and prioritize with DevRank
```bash
bountylab raw users candidate1 candidate2 candidate3 -j -i 'devrank' --fields login,devrank.tier,devrank.crackedScore
```

### Phase 6: Get emails for top candidates
```bash
bountylab email candidate1 candidate2 candidate3 -j --fields login,bestEmail,profile
```

---

## Playbook 2: Research a Specific Developer

**Scenario:** "Tell me everything about @torvalds" or "Research this GitHub user"

**Strategy:** Single raw lookup with all enrichments, then find their professional profile and email.

```bash
# Full profile with DevRank, repos, and network
bountylab raw users torvalds -j -i 'devrank,professional,owns:20,contributes:20,followers:50,following:50,stars:20'

# Email
bountylab email torvalds -j --fields login,bestEmail

# Professional profile (if not found via -i professional)
bountylab search li-users "Linus Torvalds" -f '{"field":"is_linked","op":"Eq","value":true}' -n 5 -j --fields full_name,headline,current_company,expertise,bountylab_user_id
```

---

## Playbook 3: Find OSS Contributors in a Domain

**Scenario:** "Find the best Rust async runtime contributors" or "Who are the top Kubernetes contributors?"

**Strategy:** Find key repos in the domain, extract contributors, batch look up profiles with DevRank, then get professional context.

```bash
# 1. Find repos in the domain
bountylab search repos "async runtime" -f '{"field":"language","op":"Eq","value":"rust"}' -n 20 -j --fields name,ownerLogin,stargazerCount,language

# 2. Get contributors for top repos
bountylab raw repos tokio-rs/tokio async-rs/async-std -j -i 'contributors:100' --fields name,ownerLogin,contributors

# 3. Look up contributor profiles with DevRank (batch up to 100)
bountylab raw users contributor1 contributor2 contributor3 -j -i 'devrank' --fields login,displayName,location,devrank.tier,devrank.crackedScore

# 4. Get emails for top candidates
bountylab email contributor1 contributor2 contributor3 -j --fields login,bestEmail
```

---

## Playbook 4: Company Engineering Team Analysis

**Scenario:** "Analyze Vercel's engineering team" or "What does Stripe's team look like?"

**Strategy:** Pull all employees via professional profiles, then segment by role, location, seniority, and previous companies. Cross-reference with GitHub for OSS activity.

```bash
# 1. Get all employees
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"vercel"}' -n 200 --paginate -j --fields full_name,current_title,seniority_level,city,country,expertise,past_companies,is_linked,bountylab_user_id

# 2. Find their public repos
bountylab search repos "vercel" -f '{"field":"ownerLogin","op":"Eq","value":"vercel"}' -n 50 -j --fields name,ownerLogin,stargazerCount,language,description

# 3. Get contributors for top repos
bountylab raw repos vercel/next.js vercel/turbo vercel/swr -j -i 'contributors:50' --fields name,ownerLogin,contributors
```

Analyze the JSON output to segment by role, location, seniority, and previous companies. Cross-reference contributor logins with employee bountylab_user_ids to identify which contributors are employees.

---

## Playbook 5: Find Developers by Technology Stack

**Scenario:** "Find developers who know both Rust and WebAssembly"

**Strategy:** Attack from multiple angles — repos, GitHub users, NL search, and professional profiles — then merge and deduplicate.

```bash
# 1. Find active projects to identify contributors
bountylab search repos "WebAssembly runtime" -f '{"field":"language","op":"Eq","value":"rust"}' -n 20 -j -i 'contributors:30' --fields name,ownerLogin,stargazerCount,contributors

# 2. Direct user search
bountylab search users "rust wasm webassembly" -n 50 -j --fields login,displayName,location,bio

# 3. Natural language search
bountylab search users-nl "developers who build WebAssembly tools and runtimes in Rust" -n 30 -j --fields login,displayName,location,bio

# 4. Professional profiles with matching expertise
bountylab search li-users -f '{"field":"expertise","op":"ContainsAny","value":["rust","webassembly","wasm"]}' -n 100 -j --fields full_name,headline,current_company,expertise,bountylab_user_id,is_linked

# 5. Score with DevRank
bountylab raw users user1 user2 user3 -j -i 'devrank' --fields login,devrank.tier,devrank.crackedScore

# 6. Get emails
bountylab email user1 user2 user3 -j --fields login,bestEmail
```

---

## Playbook 6: Find Developers by Education + Industry

**Scenario:** "Find Stanford developers in fintech" or "MIT grads working in AI"

**Strategy:** Use `ContainsAllTokens` on `campuses` (NOT `Contains` — campus values vary: "Stanford University", "Stanford University School of Engineering", etc.). Combine with industry or company filters to narrow to the target sector. Use `-i github` for inline DevRank.

```bash
# 1. Stanford + fintech (industries filter)
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"industries","op":"ContainsAny","value":["financial services","fintech","banking","payments"]}]}' -n 100 -j -i github --fields full_name,headline,current_company,campuses,majors,industries,expertise,bountylab_user_id,github.login,github.devrank.tier

# 2. Broaden: Stanford + fintech company names (catches people whose industry field isn't set)
bountylab search li-users -f '{"op":"And","filters":[{"field":"campuses","op":"ContainsAllTokens","value":"stanford"},{"field":"companies","op":"ContainsAny","value":["stripe","square","plaid","affirm","brex","robinhood","coinbase","ripple"]}]}' -n 100 -j -i github --fields full_name,headline,current_company,companies,campuses,github.login,github.devrank.tier

# 3. Get DevRank and emails for top candidates
bountylab raw users candidate1 candidate2 candidate3 -j -i 'devrank' --fields login,devrank.tier,devrank.crackedScore
bountylab email candidate1 candidate2 candidate3 -j --fields login,bestEmail
```

---

## Playbook 7: Competitive Intelligence — Who's Hiring?

**Scenario:** "What engineers has Anthropic hired recently?" or "Where are ex-Google engineers going?"

**Strategy:** Pull all employees, analyze tenure for recent hires, look at past companies for hiring patterns.

```bash
# 1. Find all current employees
bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"anthropic"}' -n 200 --paginate -j --fields full_name,current_title,current_tenure_months,past_companies,seniority_level,expertise

# 2. Find ex-Google engineers (who left)
bountylab search li-users "engineer" -f '{"op":"And","filters":[{"field":"past_companies","op":"Contains","value":"google"},{"field":"current_company","op":"NotEq","value":"google"}]}' -n 100 -j --fields full_name,current_title,current_company,past_companies
```

Analyze the JSON to identify recent hires (short tenure), common source companies, and hiring patterns.

---

## Subagent Workflows

For complex research, spawn subagents with the `Task` tool to parallelize independent work. Each subagent has full access to the bountylab CLI.

### When to parallelize
- Independent search dimensions (company search, repo search, profile search)
- Multiple companies or domains to map
- Research + enrichment that don't depend on each other

### Decomposition pattern
1. **Split** the research into independent search paths
2. **Spawn** one subagent per path with clear instructions and specific commands
3. **Collect** structured results (logins, IDs, names) from each subagent
4. **Merge** and deduplicate in the main agent
5. **Enrich** the merged set (DevRank, emails) in the main agent

### Example: "Find best ML engineers in fintech"

**Subagent A** — Search professional profiles:
```bash
bountylab search li-users "machine learning" -f '{"op":"And","filters":[{"field":"industries","op":"ContainsAny","value":["financial services","fintech"]},{"field":"is_linked","op":"Eq","value":true}]}' -n 100 -j -i github --fields full_name,current_title,current_company,bountylab_user_id,github.login,github.devrank.tier
```

**Subagent B** — Find ML repos in fintech, extract contributors:
```bash
bountylab search repos "machine learning fraud detection credit scoring" -n 20 -j -i 'contributors:30' --fields name,ownerLogin,stargazerCount,contributors
```

**Subagent C** — Find recently unemployed ML engineers from fintech:
```bash
bountylab search li-users -f '{"op":"And","filters":[{"field":"past_companies","op":"ContainsAny","value":["stripe","square","plaid","affirm","brex","robinhood"]},{"field":"expertise","op":"ContainsAny","value":["machine learning","deep learning","data science"]},{"field":"is_currently_employed","op":"Eq","value":false}]}' -n 100 -j --fields full_name,headline,past_companies,expertise,bountylab_user_id,is_linked
```

**Main agent** — Merge results, deduplicate by bountylab_user_id/login, get DevRank scores and emails for top candidates.

---

## General Tips

1. **Always use `-j --fields`** to get clean, focused JSON output
2. **Save intermediate results** to `/tmp` files so you can reference them across steps
3. **Batch lookups** — `raw users` and `email` accept up to 100 items per call
4. **Cross-reference** — use `bountylab_user_id` from li-user results with `raw users-by-id`
5. **Follow the graph** — the best candidates are often 1-2 hops from known strong engineers
6. **Use DevRank** — add `-i devrank` to `raw users` calls to quantify developer quality
7. **Try multiple angles** — keyword search, NL search, repo contributors, follower networks, professional filters
8. **Use ContainsAllTokens** for fuzzy matching on headlines, titles, expertise
9. **Use subagents** for 10+ call workflows to parallelize
10. **Present results** as structured tables with clear sourcing attribution
