# # MCP Agent Trust Verification with AgentOps Monitoring
#
# This example shows how to monitor an MCP-powered agent that verifies
# Solana wallet trustworthiness using the TWZRD Agent Intel MCP server.
#
# AgentOps traces every MCP tool call (score_agent, preflight_check)
# alongside the agent's decisions, giving you full observability over
# your trust-gating logic.
#
# Requirements:
# %pip install agentops mcp openai python-dotenv

import asyncio
import os
import agentops
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MCP_URL = "https://intel.twzrd.xyz/mcp"
TRUST_THRESHOLD = 0.5

agentops.init(
    api_key=os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key"),
    auto_start_session=False,
    trace_name="TWZRD MCP Trust Check",
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "your_openai_api_key"))


async def call_twzrd_mcp(tool_name: str, wallet: str) -> str:
    """Call a TWZRD Agent Intel MCP tool and return the result."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, {"wallet": wallet})
            return result.content[0].text


def verify_agent_wallet(wallet: str) -> dict:
    """
    Verify a Solana agent wallet using TWZRD Agent Intel.

    AgentOps records this function call as a span with the wallet address,
    trust score, and preflight decision — searchable in your dashboard.

    Args:
        wallet: Solana wallet address (base58)

    Returns:
        dict with trust_score, preflight_result, and approved flag
    """
    score_raw = asyncio.run(call_twzrd_mcp("score_agent", wallet))
    preflight_raw = asyncio.run(call_twzrd_mcp("preflight_check", wallet))

    # Parse score from response
    import re
    score_match = re.search(r"(\d+\.\d+|\d+)", score_raw)
    trust_score = float(score_match.group(1)) if score_match else 0.0

    approved = trust_score >= TRUST_THRESHOLD and "APPROVE" in preflight_raw.upper()

    return {
        "wallet": wallet,
        "trust_score": trust_score,
        "preflight_result": preflight_raw,
        "approved": approved,
    }


def run_trust_gated_agent(wallet: str, user_request: str) -> str:
    """
    An agent that gates responses behind TWZRD wallet trust verification.
    All steps are traced by AgentOps for monitoring and debugging.
    """
    tracer = agentops.start_trace(
        trace_name=f"trust_check_{wallet[:8]}",
        tags=["mcp", "twzrd", "solana", "trust-verification"],
    )

    try:
        # Step 1: Verify wallet trust
        print(f"Verifying wallet: {wallet}")
        trust_data = verify_agent_wallet(wallet)
        agentops.record(agentops.ActionEvent(
            action_type="trust_verification",
            params={"wallet": wallet},
            returns=trust_data,
        ))

        if not trust_data["approved"]:
            result = (
                f"Request rejected. Wallet {wallet[:8]}... has trust score "
                f"{trust_data['trust_score']:.2f} (threshold: {TRUST_THRESHOLD}). "
                f"Preflight: {trust_data['preflight_result']}"
            )
            agentops.end_trace(tracer, end_state="Rejected")
            return result

        # Step 2: Process verified request via OpenAI
        print(f"Wallet approved (score: {trust_data['trust_score']:.2f}). Processing request...")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant for verified Solana agents. "
                    f"The requesting agent wallet {wallet} has been verified "
                    f"with trust score {trust_data['trust_score']:.2f}."
                ),
            },
            {"role": "user", "content": user_request},
        ]
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=messages
        )
        result = response.choices[0].message.content

        agentops.end_trace(tracer, end_state="Success")
        return result

    except Exception as e:
        agentops.end_trace(tracer, end_state="Fail")
        raise


if __name__ == "__main__":
    # Example: high-trust wallet (many x402 payments on-chain)
    DEMO_WALLET = "D1QkbFJKiPsymJ65RKHhF6DFB8sPMfpBaFBzuHKfJGWi"
    REQUEST = "What Solana DeFi protocols offer the highest yields right now?"

    print("TWZRD Agent Trust Verification + AgentOps Monitoring")
    print("=" * 50)
    result = run_trust_gated_agent(DEMO_WALLET, REQUEST)
    print(f"\nResult: {result}")
    print("\nView traces at: https://app.agentops.ai")
