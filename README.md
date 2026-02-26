# Bounty Lab Skills

Official [Claude Code](https://claude.ai/claude-code) plugin marketplace for [Bounty Lab](https://bountylab.io) developer intelligence.

## Installation

```bash
# 1. Add the marketplace
/plugin marketplace add bountylaboratories/skills

# 2. Install the bountylab plugin
/plugin install bountylab@bountylab-skills
```

## Setup

After installing, set your Bounty Lab API key:

```
bountylab login --key <your-api-key>
```

Or ask Claude: "Log me in to Bounty Lab" and provide your key when prompted.

## What's included

### `bountylab` plugin

Gives Claude access to the full Bounty Lab developer intelligence platform:

| Capability | Description |
|-----------|-------------|
| **GitHub User Search** | BM25 full-text + AI-powered natural language search |
| **Repository Search** | Semantic vector search + AI-powered natural language |
| **Professional Search** | BM25 search with 40+ filterable fields |
| **Raw Lookups** | Batch user/repo lookup with graph expansion (followers, contributors, starrers) |
| **Email Discovery** | Best email for GitHub users (work, personal, school) |
| **DevRank** | Developer quality scores and global leaderboard |

## Example prompts

- "Find senior Rust engineers in Berlin"
- "Source ML engineer candidates for Anthropic"
- "Research the engineering team at Stripe"
- "Find contributors to the tokio project and get their emails"
- "Who are the top DevRank developers?"
- "Find all engineers at Kikoff, look up their GitHub, and find similar candidates"
- "Compare the engineering teams at Vercel vs Netlify"

## Updating

```
/plugin marketplace update bountylab-skills
```
