import random

class RandomGenerator:
    CATEGORIES = ['ExtendedFamily', 'Self', 'NearFamily', 'MD', 'General']

    @staticmethod
    def get_random_category():
        """Selects a random category from the predefined list."""
       # return random.choice(RandomGenerator.CATEGORIES)
        return "MD"

    @staticmethod
    def get_random_prompt_count(min_val=1, max_val=2):
        """Generates a random number between min_val and max_val inclusive."""
        return random.randint(min_val, max_val)

