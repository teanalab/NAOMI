from ollama import chat

class LlamaGuard3:
    def __init__(self, model_name='llama-guard3:1b'):
        self.model_name = model_name
        # MI Obesity context: S6 (Advice) and S11 (Self-Harm/Eating) 
        # often trigger false positives.
        self.ALLOW_LIST = ["S6", "S11"] 

    def check(self, user_text, assistant_text=None):
        """
        user_text: The user's prompt.
        assistant_text: The AI's response (None if checking user input).
        """
        if assistant_text is None:
            # --- INPUT GUARD (Checking User) ---
            messages = [{'role': 'user', 'content': user_text}]
        else:
            # --- OUTPUT GUARD (Checking Agent) ---
            # IMPORTANT: Documentation states both MUST be present for Agent assessment.
            messages = [
                {'role': 'user', 'content': user_text},
                {'role': 'assistant', 'content': assistant_text}
            ]

        response = chat(model=self.model_name, messages=messages)
        output = response.message.content.strip()
        
        is_safe = output.startswith("safe")
        category = output.replace("unsafe", "").strip() if not is_safe else None

        # Sensitivity Tuning for Obesity MI
        if not is_safe and category in self.ALLOW_LIST:
            # If it's medical advice or diet talk, we check for 'hard' harm keywords
            harm_keywords = ["starve", "purge", "laxative", "vomit", "pills"]
            check_text = assistant_text if assistant_text else user_text
            if not any(word in check_text.lower() for word in harm_keywords):
                return True, f"ALLOWED_{category}"
        
        return is_safe, category