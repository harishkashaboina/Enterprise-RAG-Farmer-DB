from typing import List, Dict, Any
from loguru import logger
from openai import OpenAI
import os 

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def validate_optimize_contexts(contexts: List[Dict], query: str) -> str:
        system_prompt = """
            You are an expert database analyst helping a Text-to-SQL system.

            Your task:
            - Keep only relevant views
            - Keep only relevant columns
            - Identify useful joins
            - Remove irrelevant context
            - Return concise optimized schema context only

            Rules:
            - Do not explain anything
            - Do not return JSON
            - Return clean optimized context only
        """

        user_prompt = f"""
            USER QUERY:
            {query}

            RETRIEVED CONTEXT:
            {contexts}
            """
        
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        #print('context_manager', response)
        return response.choices[0].message.content.strip()


