# Analysis & Visualization Guide

Step-by-step playbooks for common analysis tasks. Each playbook shows how to fetch data with the CLI, transform it, and produce a visualization.

## Talent Flow Analysis

**Goal:** Show where engineers move between companies (e.g., "Where do Stripe alumni go?")

### Steps

1. **Fetch profiles with company history:**
   ```bash
   bountylab search li-users -f '{"field":"companies","op":"Contains","value":"stripe"}' -n 200 -j -i github --fields full_name,current_company,past_companies,github.login,github.devrank.tier
   ```

2. **Transform:** For each person, extract transitions from `past_companies` to `current_company`. Count how many people made each source→target transition. Filter to the target company (e.g., people who left Stripe).

3. **Build flow JSON:**
   ```json
   {
     "title": "Stripe Alumni: Where They Went",
     "subtitle": "Based on 150 profiles",
     "flows": [
       {"source": "Stripe", "target": "Coinbase", "value": 12},
       {"source": "Stripe", "target": "Plaid", "value": 8},
       {"source": "Stripe", "target": "Own Startup", "value": 15}
     ]
   }
   ```

4. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/sankey.py -o /home/claude/output/stripe-flow.png
   ```

### Tips
- Use multiple searches: filter by `companies Contains "stripe"` AND by `current_company In [known companies]`
- Group small targets (<3 people) into "Other" before passing to the script
- The script auto-groups if there are >15 sources or targets


## Team DNA Analysis

**Goal:** Profile a team's demographics — DevRank distribution, languages, seniority, experience.

### Steps

1. **Fetch team profiles:**
   ```bash
   bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"stripe"}' -n 200 -j -i github --fields full_name,current_title,seniority_level,total_experience_years,expertise,github.login,github.devrank.tier,github.language
   ```

2. **Aggregate into panels:**
   - Count DevRank tiers → bar chart
   - Count top languages (from `github.language` or `expertise`) → bar chart
   - Count seniority levels → pie chart
   - Collect `total_experience_years` values → histogram

3. **Build distribution JSON:**
   ```json
   {
     "title": "Stripe Engineering Team DNA",
     "subtitle": "186 engineers analyzed",
     "panels": [
       {"name": "DevRank Tiers", "type": "bar", "data": {"cracked": 5, "legendary": 12, "elite": 30, "skilled": 40}},
       {"name": "Top Languages", "type": "bar", "data": {"Python": 45, "TypeScript": 38, "Go": 22}},
       {"name": "Seniority Mix", "type": "pie", "data": {"Senior": 40, "Staff": 25, "Mid": 20}},
       {"name": "Years of Experience", "type": "histogram", "data": [3, 5, 7, 8, 10, 12, 4]}
     ]
   }
   ```

4. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/distribution.py -o /home/claude/output/stripe-dna.png
   ```

### Tips
- The script auto-detects DevRank tier names and uses tier-specific colors
- Items beyond top 10 are grouped into "Other" automatically
- Panels auto-layout in a grid based on count


## OSS Ecosystem Mapping

**Goal:** Visualize the contributor network around a project or technology.

### Steps

1. **Find key repos:**
   ```bash
   bountylab search repos "react state management" -n 10 -j -i 'contributors:20' --fields name,ownerLogin,stargazerCount,contributors
   ```

2. **Build node/edge data:** Each contributor becomes a node. Edges connect contributors who work on the same repo. Node size = number of repos contributed to (or DevRank score). Group by primary repo.

3. **Enrich top contributors:**
   ```bash
   bountylab raw users contributor1 contributor2 -j -i 'devrank,professional' --fields login,displayName,devrank.tier,devrank.crackedScore
   ```

4. **Build network JSON:**
   ```json
   {
     "title": "React State Management Ecosystem",
     "subtitle": "Contributors across Redux, Zustand, Jotai, Recoil",
     "nodes": [
       {"id": "user1", "label": "Dan Abramov", "group": "Redux", "size": 30},
       {"id": "user2", "label": "Daishi Kato", "group": "Zustand", "size": 25}
     ],
     "edges": [
       {"source": "user1", "target": "user2", "weight": 3}
     ],
     "layout": "spring"
   }
   ```

5. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/network.py -o /home/claude/output/react-ecosystem.png
   ```

### Tips
- Use `layout: "spring"` for organic clusters, `"circular"` for cleaner structure
- For large networks (>50 nodes), only the top 20 by size get labeled
- Edge weight can represent: shared repos, mutual follows, or collaboration frequency


## Talent Arbitrage Discovery

**Goal:** Find undervalued engineers — high DevRank but low seniority/title, or at smaller companies.

### Steps

1. **Fetch candidates with both DevRank and professional data:**
   ```bash
   bountylab search li-users -f '{"op":"And","filters":[{"field":"is_linked","op":"Eq","value":true},{"field":"expertise","op":"ContainsAny","value":["python","machine learning"]}]}' -n 200 -j -i github --fields full_name,current_company,current_title,seniority_level,total_experience_years,github.login,github.devrank.crackedScore
   ```

2. **Build scatter data:** X-axis = years of experience, Y-axis = DevRank score. Group by seniority or company tier. Define "arbitrage zone" = high DevRank + low experience.

3. **Build scatter JSON:**
   ```json
   {
     "title": "Talent Arbitrage: ML Engineers",
     "subtitle": "DevRank vs Experience — undervalued candidates in green zone",
     "x_label": "Years of Experience",
     "y_label": "DevRank Cracked Score",
     "points": [
       {"x": 3, "y": 85, "label": "alice", "group": "undervalued"},
       {"x": 12, "y": 60, "label": "bob", "group": "expected"}
     ],
     "zones": [
       {"label": "Arbitrage Zone", "x_min": 0, "x_max": 7, "y_min": 70, "y_max": 100, "color": "#10B98133"}
     ]
   }
   ```

4. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/scatter.py -o /home/claude/output/ml-arbitrage.png
   ```

### Tips
- Classification logic: if DevRank > 70 and experience < 7 → "undervalued"
- Use `adjustText` labels to avoid overlap (handled by the script)
- Zones are semi-transparent rectangles — use hex color with alpha (e.g., `#10B98133`)


## Cohort Comparison

**Goal:** Compare two teams or groups across multiple dimensions using a radar chart.

### Steps

1. **Fetch both cohorts:**
   ```bash
   # Cohort A
   bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"stripe"}' -n 100 -j -i github --fields github.devrank.crackedScore,total_experience_years,github.followerCount,github.publicRepoCount
   # Cohort B
   bountylab search li-users -f '{"field":"current_company","op":"Eq","value":"coinbase"}' -n 100 -j -i github --fields github.devrank.crackedScore,total_experience_years,github.followerCount,github.publicRepoCount
   ```

2. **Compute metrics:** For each cohort, calculate averages/medians for each axis. Normalize to 0-100 scale.

3. **Build radar JSON:**
   ```json
   {
     "title": "Stripe vs Coinbase Engineering",
     "subtitle": "Normalized scores (0-100)",
     "axes": ["DevRank", "Experience", "OSS Activity", "Network Size", "Specialization"],
     "series": [
       {"name": "Stripe", "values": [85, 75, 90, 70, 60]},
       {"name": "Coinbase", "values": [70, 80, 65, 85, 75]}
     ]
   }
   ```

4. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/radar.py -o /home/claude/output/stripe-vs-coinbase.png
   ```

### Tips
- Normalize all axes to the same scale (0-100) for fair comparison
- Need at least 3 axes (script will error otherwise)
- Support up to 6 series (cohorts) per chart


## Skill Co-occurrence Analysis

**Goal:** Discover which skills frequently appear together on profiles.

### Steps

1. **Fetch profiles with expertise:**
   ```bash
   bountylab search li-users -f '{"field":"expertise","op":"ContainsAny","value":["python","typescript","go","rust","java","kubernetes","docker","aws","react","node.js"]}' -n 500 -j --fields full_name,expertise
   ```

2. **Build co-occurrence matrix:** For each pair of skills, count how many profiles have both. Normalize by dividing by total profiles (to get frequency 0-1).

3. **Build heatmap JSON:**
   ```json
   {
     "title": "Skill Co-occurrence Matrix",
     "subtitle": "500 engineer profiles — how often skills appear together",
     "row_labels": ["Python", "TypeScript", "Go", "Rust", "Java"],
     "col_labels": ["Python", "TypeScript", "Go", "Rust", "Java"],
     "matrix": [
       [1.0, 0.35, 0.28, 0.15, 0.22],
       [0.35, 1.0, 0.18, 0.12, 0.20],
       [0.28, 0.18, 1.0, 0.25, 0.30],
       [0.15, 0.12, 0.25, 1.0, 0.10],
       [0.22, 0.20, 0.30, 0.10, 1.0]
     ],
     "annotate": true
   }
   ```

4. **Visualize:**
   ```bash
   echo '<json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/bountylab/scripts/viz/heatmap.py -o /home/claude/output/skill-cooccurrence.png
   ```

### Tips
- The script auto-detects symmetric matrices and masks the upper triangle
- For non-symmetric use cases (e.g., company × skill), provide different `row_labels` and `col_labels`
- Default colormap is `YlOrRd`; override with `"colormap": "Blues"` etc.
