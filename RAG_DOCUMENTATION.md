# RAG Integration with Gemini Live

This document explains how the Retrieval-Augmented Generation (RAG) system integrates with the Gemini Live API to provide grounded, context-aware responses based on a local knowledge base.

## Integration via Function Calling

The core of the integration lies in Gemini's function calling (or "tool use") capability. The voice agent does not simply pass the user's raw transcript to the language model. Instead, it prompts the model to use a specific tool whenever the user asks a question that can be answered by the knowledge base.

In `agent.py`, we define a tool named `lookup_company_info`. The system prompt given to Gemini explicitly instructs it to use this function for any queries related to company policies, product information, or other topics covered in the FAQ document.

This approach forces the model to ground its answers in the data we provide, preventing it from improvising or "hallucinating" answers to policy-related questions.

## Retrieval Mechanism

The retrieval process happens inside the `rag.py` module and is triggered when Gemini calls the `lookup_company_info` tool.

1.  **Embedding:** The knowledge base, a collection of question-answer pairs in `data/ecommerce.json`, is processed by a sentence transformer model (`all-MiniLM-L6-v2`) to create 384-dimensional vector embeddings for each question. These embeddings, along with the original text, are stored locally in the `embeddings_cache/` directory for fast access.

2.  **Search:** When a user asks a question (e.g., "How do I send something back?"), the following occurs:
    a. The user's query is converted into a vector embedding using the same model.
    b. A FAISS (Facebook AI Similarity Search) index is used to perform an efficient similarity search, finding the top 5 questions from the knowledge base that are closest to the user's query in vector space (L2 distance).
    c. **Hybrid Re-ranking:** These 5 candidates are then re-ranked using a hybrid score that combines three factors:
        - **Semantic Score (60% weight):** The cosine similarity between the query and the candidate question.
        - **Lexical Score (25% weight):** The simple text similarity ratio (using Python's `difflib.SequenceMatcher`).
        - **Token Overlap (15% weight):** The proportion of words from the query that also appear in the candidate question and answer.
    d. The top-scoring candidate(s) are selected. If no candidate meets a predefined relevance threshold, a keyword-based fallback search is performed to find a "best effort" match.

3.  **Formatting:** The selected question-answer pair(s) are formatted into a clean string and returned to the Gemini model as the result of the `lookup_company_info` tool call.

## Example Walkthrough

Here is a step-by-step example of the system in action:

1.  **User Speaks:** "I need to send an item back, what's the process?"

2.  **Gemini Transcribes & Plans:** The Gemini Live API transcribes the audio in real-time. Based on its system prompt, it recognizes that this is a policy-related question and decides to call the `lookup_company_info` tool. It makes the following tool call:
    ```json
    {
      "functionCall": {
        "name": "lookup_company_info",
        "args": {
          "query": "return process"
        }
      }
    }
    ```

3.  **RAG Module Executes:** The `agent.py` worker receives this instruction and calls `rag.search(query="return process")`.
    - The RAG module finds the most relevant entry in `data/ecommerce.json`, which is:
      > **Q:** How do I initiate a return?
      > **A:** To initiate a return, please visit our returns portal at [link] and enter your order number and email address. Follow the on-screen instructions to select the items you wish to return and generate a prepaid shipping label.

4.  **Context is Returned to Gemini:** The RAG module formats this Q&A pair into a string and sends it back to the Gemini API as the result of the tool call.

5.  **Gemini Synthesizes and Responds:** The Gemini model now has the grounded context it needs. It will not invent a process. Instead, it will synthesize a helpful, natural-sounding response based *only* on the text provided by the tool. It then generates the audio for the response and streams it back to the user through LiveKit.
    > **Agent (Audio):** "To initiate a return, you'll need to go to our returns portal. There, you can enter your order number and email to get started and print a prepaid shipping label."
