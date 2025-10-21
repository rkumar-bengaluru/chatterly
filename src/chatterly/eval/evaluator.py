import re
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence, RunnableMap, RunnableLambda
from chatterly.utils.log_exec_time import LogExecutionTime
import json 
class ConversationEvaluator:
    def __init__(self, llm):
        self.llm = llm
        self.prompt = PromptTemplate.from_template("""
You are a senior Go engineer conducting a technical interview. You’ve been given:

- A question asked by the agent
- An answer transcribed from the candidate’s voice recording using Faster-Whisper

Your task is to:
1. Analyze the answer in detail for relevance, correctness, and completeness.
2. Score the answer between 0 and 1:
   - 1.0 → Perfectly relevant, technically sound, and complete.
   - 0.5–0.9 → Partially relevant or incomplete, but shows understanding.
   - < 0.5 → Mostly irrelevant, incorrect, or off-topic.

Use your judgment as a Go expert. If the answer is off-topic (e.g., the question is about goroutines and the candidate talks about weather), assign a score of 0.

Respond **only** with a valid JSON object containing the following keys:
- "score": a float between 0 and 1
- "rationale": a concise 1–3 sentence explanation of your scoring
- "next_action": either "Ask a follow-up question to clarify or redirect." or "Accept the answer and proceed to the next question."
- "followup_question": based on the answer from user, provide a folow up question.

Do not include any other text, markdown, or formatting. Ensure the output is parseable JSON.

### Input:
Question: {question}

Transcribed Answer: {answer}

### Output (JSON):
""".strip())

        steps = [
            RunnableLambda(lambda x: {"question": x["question"], "answer": x["answer"]}),
            self.prompt,
            self.llm
        ]

        for i, step in enumerate(steps):
            print(f"[DEBUG] Step {i}: {type(step)} -> {step}")

        
        self.chain = (
            RunnableLambda(lambda x: {"question": x["question"], "answer": x["answer"]})
            | self.prompt
            | self.llm
        )
        

    @LogExecutionTime(label="Calling LLM")
    async def evaluate(self, question: str, answer: str) -> dict:
        response = await self.chain.ainvoke({"question": question, "answer": answer})
        print(f"llm response\n {response}")
        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        # Handle LangChain wrapper (e.g., Gemini returns .content)
        if hasattr(response, "content"):
            response = response.content

        # Strip Markdown code block if present
        response = response.strip()
        if response.startswith("```json"):
            response = re.sub(r"^```json\s*", "", response)
            response = re.sub(r"\s*```$", "", response)

        # Attempt to parse JSON
        try:
            parsed = json.loads(response)
            return {
                "score": parsed.get("score"),
                "rationale": parsed.get("rationale"),
                "next_action": parsed.get("next_action"),
                "followup_question": parsed.get("followup_question")
            }
        except json.JSONDecodeError as e:
            return {
                "score": None,
                "rationale": f"Failed to parse JSON: {e}",
                "next_action": "Fallback to manual review."
            }