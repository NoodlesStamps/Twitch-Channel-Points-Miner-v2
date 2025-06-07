# TwitchChannelPointsMiner/tests/test_bet_logic.py
import unittest
from TwitchChannelPointsMiner.classes.entities.Bet import (
    Bet, BetSettings, Strategy, KellyProbabilitySource, OutcomeKeys
)
# Make sure BetSettings and Strategy enums are correctly imported/accessible
# For local testing, you might need to adjust Python's path if running tests directly
# e.g. by adding the project root to sys.path

class TestBetKellyCriterion(unittest.TestCase):

    def _create_mock_outcomes(self, outcome1_props, outcome2_props=None):
        outcomes = []

        def process_props(props, oc_id, oc_title, oc_color):
            if not props: return None # If props is None, skip this outcome

            # Basic structure from Bet.__init__ and Bet.update_outcomes
            outcome_template = {
                "id": oc_id, "title": oc_title, "color": oc_color,
                OutcomeKeys.TOTAL_USERS: 0, OutcomeKeys.TOTAL_POINTS: 0,
                OutcomeKeys.TOP_POINTS: 0, OutcomeKeys.PERCENTAGE_USERS: 0,
                OutcomeKeys.ODDS: 0, OutcomeKeys.ODDS_PERCENTAGE: 0
            }

            # Apply provided properties
            if props.get("odds") is not None:
                outcome_template[OutcomeKeys.ODDS] = props["odds"]
            if props.get("odds_p") is not None:
                outcome_template[OutcomeKeys.ODDS_PERCENTAGE] = props["odds_p"]
            if props.get("user_p") is not None:
                outcome_template[OutcomeKeys.PERCENTAGE_USERS] = props["user_p"]
            if props.get("points") is not None:
                outcome_template[OutcomeKeys.TOTAL_POINTS] = props["points"]
            if props.get("users") is not None:
                outcome_template[OutcomeKeys.TOTAL_USERS] = props["users"]
            if props.get("top_points") is not None:
                outcome_template[OutcomeKeys.TOP_POINTS] = props["top_points"]

            return outcome_template

        o1 = process_props(outcome1_props, "o1", "Outcome 1", "blue")
        if o1: outcomes.append(o1)

        o2 = process_props(outcome2_props, "o2", "Outcome 2", "pink")
        if o2: outcomes.append(o2)

        # Simulate the __clear_outcomes and initial calculations in Bet constructor/update_outcomes
        # For Kelly, explicit 'p' (from odds_p or user_p) and 'b' (from odds) are most important.
        # The Bet object's update_outcomes method would normally derive some of these.
        # Here, we provide them directly as they would be *after* such processing if needed by Kelly.
        return outcomes

    def test_kelly_positive_ev_odds_percentage(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=0.5,
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE,
            max_points=10000, minimum_points=10
        )
        # p=0.6, b=1 (odds=2.0). f* = (1*0.6 - 0.4) / 1 = 0.2. Bet = 1000 * 0.2 * 0.5 = 100.
        # p=0.4, b=2 (odds=3.0). f* = (2*0.4 - 0.6) / 2 = 0.2 / 2 = 0.1.
        outcomes_data = self._create_mock_outcomes(
            {"odds": 2.0, "odds_p": 60},
            {"odds": 3.0, "odds_p": 40}
        )
        bet_obj = Bet(outcomes_data, settings) # Bet constructor calls self.__clear_outcomes and self.update_outcomes
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 100)
        self.assertIn("kelly_details", decision)
        self.assertAlmostEqual(decision["kelly_details"]["f_star_raw"], 0.2, places=5)
        self.assertAlmostEqual(decision["kelly_details"]["p"], 0.6, places=5)
        self.assertAlmostEqual(decision["kelly_details"]["b"], 1.0, places=5)

    def test_kelly_positive_ev_user_percentage(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=1.0,
            kelly_probability_source=KellyProbabilitySource.USER_PERCENTAGE,
            max_points=10000, minimum_points=10
        )
        # p=0.7, b=1 (odds=2.0). f* = (1*0.7 - 0.3) / 1 = 0.4. Bet = 1000 * 0.4 * 1.0 = 400.
        outcomes_data = self._create_mock_outcomes(
            {"odds": 2.0, "user_p": 70},
            {"odds": 2.0, "user_p": 30}  # p=0.3, b=1. f* = (1*0.3-0.7)/1 = -0.4
        )
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 400)
        self.assertIn("kelly_details", decision)
        self.assertAlmostEqual(decision["kelly_details"]["f_star_raw"], 0.4, places=5)
        self.assertAlmostEqual(decision["kelly_details"]["p"], 0.7, places=5)

    def test_kelly_negative_ev_no_bet(self):
        settings = BetSettings(strategy=Strategy.KELLY_CRITERION, kelly_fraction=0.5, kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE, minimum_points=10)
        # p=0.4, b=1 (odds=2.0). f* = (1*0.4 - 0.6) / 1 = -0.2. No bet.
        outcomes_data = self._create_mock_outcomes({"odds": 2.0, "odds_p": 40})
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertIsNone(decision["choice"])
        self.assertEqual(decision["amount"], 0)

    def test_kelly_b_is_zero_or_less_no_bet(self):
        settings = BetSettings(strategy=Strategy.KELLY_CRITERION, kelly_fraction=0.5, kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE, minimum_points=10)

        outcomes_data_b_zero = self._create_mock_outcomes({"odds": 1.0, "odds_p": 60}) # b=0
        bet_obj_b_zero = Bet(outcomes_data_b_zero, settings)
        decision_b_zero = bet_obj_b_zero.calculate(balance=1000)
        self.assertIsNone(decision_b_zero["choice"])
        self.assertEqual(decision_b_zero["amount"], 0)

        outcomes_data_b_neg = self._create_mock_outcomes({"odds": 0.5, "odds_p": 60}) # b=-0.5
        bet_obj_b_neg = Bet(outcomes_data_b_neg, settings)
        decision_b_neg = bet_obj_b_neg.calculate(balance=1000)
        self.assertIsNone(decision_b_neg["choice"])
        self.assertEqual(decision_b_neg["amount"], 0)

    def test_kelly_p_is_zero_no_bet(self):
        settings = BetSettings(strategy=Strategy.KELLY_CRITERION, kelly_fraction=0.5, kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE, minimum_points=10)
        outcomes_data = self._create_mock_outcomes({"odds": 2.0, "odds_p": 0}) # p=0
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)
        self.assertIsNone(decision["choice"])
        self.assertEqual(decision["amount"], 0)

    def test_kelly_max_points_cap(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=1.0,
            max_points=50,
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE,
            minimum_points=10
        )
        # p=0.7, b=1 (odds=2.0) => f*=0.4. Bet=1000*0.4*1=400. Capped at 50.
        outcomes_data = self._create_mock_outcomes({"odds": 2.0, "odds_p": 70})
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 50)

    def test_kelly_respects_minimum_points(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=0.01,
            max_points=10000,
            minimum_points=20,
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE
        )
        # p=0.6, b=1 (odds=2.0) => f_star_raw=0.2. Bet = 1000 * 0.2 * 0.01 = 2.
        # Should be raised to minimum_points (20).
        outcomes_data = self._create_mock_outcomes({"odds": 2.0, "odds_p": 60})
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 20)

    def test_kelly_amount_less_than_min_points_setting_and_less_than_10(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=0.01, # Results in calculated amount of 2
            max_points=10000,
            minimum_points=0, # Min points setting is 0
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE
        )
        # p=0.6, b=1 (odds=2.0) => f_star_raw=0.2. Bet = 1000 * 0.2 * 0.01 = 2.
        # Min_points is 0, so amount should remain 2. Twitch.py will prevent bet if < 10.
        outcomes_data = self._create_mock_outcomes({"odds": 2.0, "odds_p": 60})
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 2)

    def test_kelly_chooses_higher_f_star(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=1.0,
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE,
            max_points=10000, minimum_points=10
        )
        # Outcome 1: p=0.5, b=1.5 (odds=2.5) => f* = (1.5*0.5-0.5)/1.5 approx 0.166666
        # Outcome 2: p=0.2, b=5.0 (odds=6.0) => f* = (5.0*0.2-0.8)/5.0 = 0.2/5.0 = 0.04
        outcomes_data = self._create_mock_outcomes(
            {"odds": 2.5, "odds_p": 50},
            {"odds": 6.0, "odds_p": 20}
        )
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)

        self.assertEqual(decision["choice"], 0)
        self.assertEqual(decision["amount"], 166) # 1000 * 0.16666... * 1.0 = 166
        self.assertIn("kelly_details", decision)
        self.assertAlmostEqual(decision["kelly_details"]["f_star_raw"], (1.5*0.5-0.5)/1.5, places=5)

    def test_kelly_no_valid_outcome_due_to_p_or_b(self):
        settings = BetSettings(
            strategy=Strategy.KELLY_CRITERION,
            kelly_fraction=0.5,
            kelly_probability_source=KellyProbabilitySource.ODDS_PERCENTAGE,
            max_points=10000, minimum_points=10
        )
        outcomes_data = self._create_mock_outcomes(
            {"odds": 2.0, "odds_p": 0},    # p=0
            {"odds": 1.0, "odds_p": 50}    # b=0
        )
        bet_obj = Bet(outcomes_data, settings)
        decision = bet_obj.calculate(balance=1000)
        self.assertIsNone(decision["choice"])
        self.assertEqual(decision["amount"], 0)

if __name__ == '__main__':
    unittest.main()
