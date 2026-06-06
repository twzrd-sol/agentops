# MCP Agent Trust Verification + AgentOps Monitoring

An example showing how to monitor an MCP-powered Solana agent trust
verification workflow using [AgentOps](https://agentops.ai).

## What It Does

1. Calls the [TWZRD Agent Intel](https://intel.twzrd.xyz) MCP server to score
   a Solana wallet (`score_agent`) and run a preflight check (`preflight_check`)
2. Gates downstream requests to OpenAI behind the trust check (wallets with
   score ≥ 0.5 and `APPROVE` preflight proceed; others are rejected)
3. Records every step as an AgentOps span — trust score, preflight decision,
   and OpenAI response — searchable in the AgentOps dashboard

## Setup

```bash
pip install agentops mcp openai python-dotenv
```

```bash
export AGENTOPS_API_KEY=your_key   # from app.agentops.ai
export OPENAI_API_KEY=your_key
```

## Run

```bash
python mcp_trust_verification.py
```

View traces at [app.agentops.ai](https://app.agentops.ai).

## MCP Server

| Tool | Description | Cost |
|------|-------------|------|
| `score_agent` | Trust score (0–1) + x402 payment history | Free |
| `preflight_check` | APPROVE/REJECT with reasoning | Free |
| `get_trust_receipt` | Signed on-chain trust receipt | HTTP 402 |

```json
{
  "mcpServers": {
    "twzrd-agent-intel": {
      "url": "https://intel.twzrd.xyz/mcp"
    }
  }
}
```

## AgentOps Dashboard

The example creates tagged traces with `mcp`, `twzrd`, `solana`, and
`trust-verification` tags. Each trace includes:

- `trust_verification` action with wallet address, score, and preflight result
- Downstream OpenAI call (if wallet is approved)
- End state: `Success` (approved + responded) or `Rejected` (low trust score)
