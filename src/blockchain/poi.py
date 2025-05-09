import hashlib
import random
import time
from epc import EPCKeyPair

class Insight:
    def __init__(self, author_pubkey, market_symbol, prediction, timestamp=None):
        self.author = author_pubkey
        self.market = market_symbol
        self.prediction = prediction  # Could be a price or directional signal
        self.timestamp = timestamp or time.time()
        self.signature = None

    def sign(self, epc_keypair):
        message = f"{self.author}:{self.market}:{self.prediction}:{self.timestamp}"
        self.signature = epc_keypair.sign(message)

    def verify(self):
        message = f"{self.author}:{self.market}:{self.prediction}:{self.timestamp}"
        return EPCKeyPair.verify(self.author, message, self.signature)

class ValidatorProfile:
    def __init__(self, pubkey):
        self.pubkey = pubkey
        self.reputation = 1.0
        self.insights = []

    def submit_insight(self, insight):
        if insight.verify():
            self.insights.append(insight)
        else:
            raise ValueError("Invalid insight signature")

    def update_reputation(self, accuracy_score):
        self.reputation = max(0.1, self.reputation * (0.9 + accuracy_score * 0.1))

class ProofOfInsight:
    def __init__(self):
        self.validators = {}

    def register_validator(self, pubkey):
        if pubkey not in self.validators:
            self.validators[pubkey] = ValidatorProfile(pubkey)

    def submit_insight(self, pubkey, insight):
        if pubkey in self.validators:
            self.validators[pubkey].submit_insight(insight)

    def evaluate_insights(self, market_data_fn):
        """
        Compares submitted insights with real market data using a scoring function.
        Updates validator reputations.
        """
        for profile in self.validators.values():
            total_score = 0
            for insight in profile.insights:
                actual = market_data_fn(insight.market, insight.timestamp)
                score = self.score_prediction(insight.prediction, actual)
                total_score += score
            if profile.insights:
                profile.update_reputation(total_score / len(profile.insights))
            profile.insights.clear()

    def score_prediction(self, prediction, actual_value):
        """
        Compares predicted vs actual (simplified version).
        """
        try:
            error = abs(prediction - actual_value) / max(0.0001, actual_value)
            return max(0.0, 1.0 - error)
        except Exception:
            return 0.0

    def select_validator(self):
        """
        Randomly selects a validator with probability weighted by reputation.
        """
        weighted_pool = []
        for profile in self.validators.values():
            weight = int(profile.reputation * 100)
            weighted_pool.extend([profile.pubkey] * weight)

        if not weighted_pool:
            return None

        return random.choice(weighted_pool)
