class ValidationRubric:
    def __init__(self):
        self.categories = {
            "VL 1": {"description": "Active listening and engagement. Therapist is present and attentive.", "markers": ["engagement", "non-judgmental", "observational"]},
            "VL 2": {"description": "Accurate reflection of the client's feelings or thoughts.", "markers": ["reflection", "similar language", "empathy"]},
            "VL 3": {"description": "Accurate verbalization of unspoken thoughts or feelings (mind reading).", "markers": ["mind reading", "attunement", "insight"]},
            "VL 4": {"description": "Normalization of thoughts/feelings using specific events or causes.", "markers": ["normalization", "explanation", "context"]},
            "VL 5": {"description": "Justification of emotions, thoughts, or behaviors within the current context.", "markers": ["justification", "reasonableness", "meaning"]},
            "VL 6": {"description": "Deep validation and genuine understanding, like a close friend.", "markers": ["genuine", "authentic", "empathy", "care"]}
        }

    def evaluate_response(self, response):
        scores = {key: 0 for key in self.categories.keys()}
        for category, details in self.categories.items():
            for marker in details["markers"]:
                if marker in response.lower():  
                    scores[category] += 1
        best_category = max(scores, key=scores.get)
        return best_category, scores

    def get_category_description(self, category):
        return self.categories.get(category, {}).get("description", "Unknown category.")
