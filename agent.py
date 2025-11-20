import logging
import asyncio
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import function_tool
from livekit.plugins import google
import rag  # Import your specific knowledge

load_dotenv()
logger = logging.getLogger("gemini-agent")

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 1. DEFINE THE MODEL (The "General" Brain)
    model = google.beta.realtime.RealtimeModel(
        model="gemini-live-2.5-flash-preview",
        voice="Fenrir",
    )

    # 2. DEFINE THE AGENT (The "Personality")
    # The 'instructions' are the Rules of Engagement.
    agent = Agent(
        instructions=(
            "You are a helpful e-commerce FAQ assistant. Your role is to answer general questions about "
            "company policies and procedures using the FAQ database.\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. You ONLY have access to general FAQ information - you CANNOT access specific customer data, "
            "order details, account information, or any personal/transactional data.\n"
            "2. ALWAYS use the lookup_company_info tool to answer questions about policies, procedures, and general topics.\n"
            "3. If a user asks about their specific order, account, tracking number, or personal information, "
            "politely explain: 'I can help with general questions about our policies and procedures, but I don't have "
            "access to specific customer or order information. For account-specific questions, please contact our "
            "support team directly.'\n"
            "4. NEVER ask for order numbers, shipping addresses, account details, or any personal information - "
            "you cannot process or look up this information.\n"
            "5. Focus on answering general questions like: shipping times, return policies, payment methods, "
            "how to place orders, general procedures, etc.\n"
            "6. If the FAQ doesn't have the answer, say: 'I don't have that information in my FAQ database. "
            "Please contact our support team for more specific help.'\n"
            "\n"
            "Keep responses concise, friendly, and always direct users to support for specific/personal queries."
        ),
    )

    # 3. DEFINE THE TOOL (The "Bridge")
    # The description below is what Gemini reads to decide if it needs this tool.
    @function_tool
    async def lookup_company_info(query: str):
        """
        Searches the company's FAQ database for information about orders, shipping, returns, payments, 
        tracking, accounts, policies, and all other e-commerce topics.
        
        Use this tool for ANY question related to:
        - Ordering (phone orders, guest checkout, bulk orders, etc.)
        - Shipping (times, costs, international, tracking, etc.)
        - Returns and refunds
        - Payments (methods, security, gift cards, etc.)
        - Account management
        - Products (availability, reviews, etc.)
        - Customer support contact methods
        - Any other company policy or procedure
        
        Args:
            query: The user's question or keywords to search for
        """
        logger.info(f"Tool called with query: {query}")
        return rag.search(query)

    # 4. START THE SESSION
    session = AgentSession(
        llm=model,
    )

    await session.start(agent, room=ctx.room)
    
    # 5. GREETING
    await asyncio.sleep(1)
    session.generate_reply(instructions="Greet the user, and introduce yourself mentioning you can help with E-commerce related questions.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))