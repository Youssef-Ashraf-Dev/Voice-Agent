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
import rag

load_dotenv()
logger = logging.getLogger("gemini-agent")

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 1. DEFINE THE MODEL (The "General" Brain)
    model = google.beta.realtime.RealtimeModel(
        model="gemini-live-2.5-flash-preview",
        voice="Fenrir",
    )

    # 2. DEFINE THE TOOL (The "Bridge")
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

    # 3. DEFINE THE AGENT (The "Personality")
    # The 'instructions' are the Rules of Engagement.
    agent = Agent(
        instructions=(
            "You are a helpful e-commerce FAQ assistant. Your role is to answer general questions about "
            "company policies and procedures using ONLY the FAQ database.\n"
            "\n"
            "CRITICAL RULES - READ CAREFULLY:\n"
            "1. You ONLY have access to general FAQ information - you CANNOT access specific customer data, "
            "order details, account information, or any personal/transactional data.\n"
            "\n"
            "2. ALWAYS use the lookup_company_info tool for ANY question about company policies or procedures.\n"
            "\n"
            "3. ANSWER ONLY WITH INFORMATION FROM THE RETRIEVED FAQ DATA:\n"
            "   - DO NOT use your training data or general knowledge\n"
            "   - DO NOT improvise or add information not in the FAQ results\n"
            "   - DO NOT infer or assume anything beyond what's explicitly stated in the FAQ\n"
            "   - If the FAQ says 'credit cards, debit cards, and PayPal', say EXACTLY that - don't add other payment methods\n"
            "   - If the FAQ says '30 days', say '30 days' - don't say '30 or 60 days'\n"
            "\n"
            "4. If the lookup_company_info tool returns 'No relevant information found in the FAQ database', "
            "you MUST respond: 'I don't have that information in my FAQ database. Please contact our support team for help.'\n"
            "\n"
            "5. If a user asks about their specific order, account, tracking number, or personal information, "
            "politely explain: 'I can help with general questions about our policies and procedures, but I don't have "
            "access to specific customer or order information. For account-specific questions, please contact our "
            "support team directly.'\n"
            "\n"
            "6. NEVER ask for order numbers, shipping addresses, account details, or any personal information - "
            "you cannot process or look up this information.\n"
            "\n"
            "7. If a question is completely unrelated to e-commerce (weather, jokes, general knowledge), "
            "respond: 'I can only help with questions about our e-commerce policies and procedures. Is there "
            "anything related to orders, shipping, returns, or payments I can help you with?'\n"
            "\n"
            "REMEMBER: You are a STRICT FAQ assistant. Only repeat information from the FAQ database. "
            "Never add, infer, or improvise information from your training data."
        ),
        tools=[lookup_company_info],
    )

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