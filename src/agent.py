"""
AI Agent Module - CloudWalk Operations Intelligence

This module implements the Natural Language to SQL (NL2SQL) agent
using Groq's Llama 3 model. The agent converts user questions
into SQL queries and executes them against the SQLite database.

Author: Gabriel Milhardo
"""

import os
import re
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from groq import Groq

from src.database import Database
from src.prompts import SYSTEM_PROMPT

# Load environment variables
load_dotenv()


class CloudWalkAgent:
    """
    AI Agent for CloudWalk Operations Intelligence.

    This agent:
    1. Receives natural language questions
    2. Generates SQL queries using Llama 3
    3. Executes queries against SQLite
    4. Returns formatted results

    Attributes:
        db: Database instance
        client: Groq client
        model: LLM model name
        conversation_history: List of messages for context
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        model: str = "llama-3.3-70b-versatile"
    ):
        """
        Initialize the AI Agent.

        Args:
            db: Database instance (creates new if not provided)
            model: Groq model to use
        """
        # Initialize database
        if db is None:
            self.db = Database()
            self.db.load_csv_to_db()
        else:
            self.db = db

        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=api_key)
        self.model = model

        # Conversation history for context
        self.conversation_history = []

        print(f"[Agent] Initialized with model: {model}")

    def _extract_sql(self, text: str) -> Optional[str]:
        """
        Extract SQL query from LLM response.

        Args:
            text: LLM response text

        Returns:
            Extracted SQL query or None
        """
        # Try to find SQL in code blocks
        patterns = [
            r"```sql\n(.*?)```",  # ```sql ... ```
            r"```\n(.*?)```",      # ``` ... ```
            r"SELECT.*?(?:;|$)",   # Direct SELECT statement
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1) if "```" in pattern else match.group(0)
                sql = sql.strip()
                if sql.upper().startswith("SELECT"):
                    return sql

        return None

    def _generate_response(self, user_question: str) -> str:
        """
        Generate LLM response for user question.

        Args:
            user_question: User's natural language question

        Returns:
            LLM response text
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history,
            {"role": "user", "content": user_question}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # Low temperature for consistent SQL
            max_tokens=2000
        )

        return response.choices[0].message.content

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question and return results.

        Args:
            question: User's question in natural language

        Returns:
            Dictionary with:
                - question: Original question
                - sql: Generated SQL query
                - data: Query results as list of dicts
                - answer: Formatted answer text
                - error: Error message if any
        """
        result = {
            "question": question,
            "sql": None,
            "data": None,
            "answer": None,
            "error": None
        }

        try:
            # Generate response with SQL
            llm_response = self._generate_response(question)

            # Extract SQL from response
            sql = self._extract_sql(llm_response)

            if sql:
                result["sql"] = sql

                # Execute query
                try:
                    df = self.db.execute_query(sql)
                    result["data"] = df.to_dict(orient="records")

                    # Format the answer
                    if len(df) == 0:
                        result["answer"] = "No data found for this query."
                    elif len(df) == 1 and len(df.columns) == 1:
                        # Single value result
                        value = df.iloc[0, 0]
                        if isinstance(value, float):
                            result["answer"] = f"R$ {value:,.2f}"
                        else:
                            result["answer"] = str(value)
                    else:
                        # Table result - include in response
                        result["answer"] = llm_response

                except Exception as e:
                    result["error"] = f"SQL execution error: {str(e)}"
                    result["answer"] = f"I generated a query but it failed: {str(e)}"
            else:
                # No SQL found - might be a clarification or general response
                result["answer"] = llm_response

            # Add to conversation history (keep last 10 exchanges)
            self.conversation_history.append({"role": "user", "content": question})
            self.conversation_history.append({"role": "assistant", "content": llm_response})
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

        except Exception as e:
            result["error"] = str(e)
            result["answer"] = f"Error processing question: {str(e)}"

        return result

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print("[Agent] Conversation history cleared")

    def get_quick_stats(self) -> Dict[str, Any]:
        """
        Get quick statistics for dashboard display.

        Returns:
            Dictionary with key metrics
        """
        stats = {}

        # Total TPV
        result = self.db.execute_query(
            "SELECT ROUND(SUM(amount_transacted), 2) as tpv FROM transactions"
        )
        stats["total_tpv"] = result["tpv"].iloc[0]

        # Total transactions
        result = self.db.execute_query(
            "SELECT SUM(quantity_transactions) as txns FROM transactions"
        )
        stats["total_transactions"] = int(result["txns"].iloc[0])

        # Average ticket
        stats["avg_ticket"] = stats["total_tpv"] / stats["total_transactions"]

        # Date range
        result = self.db.execute_query(
            "SELECT MIN(day) as min_date, MAX(day) as max_date FROM transactions"
        )
        stats["date_range"] = {
            "start": result["min_date"].iloc[0],
            "end": result["max_date"].iloc[0]
        }

        # Latest day TPV
        result = self.db.execute_query("""
            SELECT day, ROUND(SUM(amount_transacted), 2) as tpv
            FROM transactions
            WHERE day = (SELECT MAX(day) FROM transactions)
            GROUP BY day
        """)
        stats["latest_day"] = {
            "date": result["day"].iloc[0],
            "tpv": result["tpv"].iloc[0]
        }

        return stats


# Convenience function for quick setup
def create_agent() -> CloudWalkAgent:
    """
    Create and initialize the CloudWalk Agent.

    Returns:
        Configured CloudWalkAgent instance
    """
    return CloudWalkAgent()


# For direct testing
if __name__ == "__main__":
    print("=" * 60)
    print("CLOUDWALK AI AGENT TEST")
    print("=" * 60)

    # Create agent
    agent = create_agent()

    # Test questions
    test_questions = [
        "What is the total TPV?",
        "Which product has the highest TPV?",
        "What was the TPV yesterday?",
        "Compare credit vs debit transactions",
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print("-" * 60)

        result = agent.ask(question)

        if result["sql"]:
            print(f"SQL: {result['sql'][:100]}...")

        if result["error"]:
            print(f"Error: {result['error']}")
        else:
            print(f"Answer: {result['answer'][:200]}..." if result["answer"] and len(result["answer"]) > 200 else f"Answer: {result['answer']}")

    # Test quick stats
    print(f"\n{'='*60}")
    print("QUICK STATS:")
    print("-" * 60)
    stats = agent.get_quick_stats()
    print(f"Total TPV: R$ {stats['total_tpv']:,.2f}")
    print(f"Total Transactions: {stats['total_transactions']:,}")
    print(f"Average Ticket: R$ {stats['avg_ticket']:,.2f}")
    print(f"Date Range: {stats['date_range']['start']} to {stats['date_range']['end']}")

    print("\n[OK] Agent test completed!")
