import copy
from enum import Enum, auto
from random import uniform

from millify import millify

#from TwitchChannelPointsMiner.utils import char_decision_as_index, float_round
from TwitchChannelPointsMiner.utils import float_round


class Strategy(Enum):
    MOST_VOTED = auto()
    HIGH_ODDS = auto()
    PERCENTAGE = auto()
    SMART_MONEY = auto()
    SMART = auto()
    NUMBER_1 = auto()
    NUMBER_2 = auto()
    NUMBER_3 = auto()
    NUMBER_4 = auto()
    NUMBER_5 = auto()
    NUMBER_6 = auto()
    NUMBER_7 = auto()
    NUMBER_8 = auto()
    KELLY_CRITERION = auto() # New Strategy

    def __str__(self):
        return self.name

class KellyProbabilitySource(Enum):
    ODDS_PERCENTAGE = auto()
    USER_PERCENTAGE = auto()

    def __str__(self):
        return self.name


class Condition(Enum):
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()

    def __str__(self):
        return self.name


class OutcomeKeys(object):
    # Real key on Bet dict ['']
    PERCENTAGE_USERS = "percentage_users"
    ODDS_PERCENTAGE = "odds_percentage"
    ODDS = "odds"
    TOP_POINTS = "top_points"
    # Real key on Bet dict [''] - Sum()
    TOTAL_USERS = "total_users"
    TOTAL_POINTS = "total_points"
    # This key does not exist
    DECISION_USERS = "decision_users"
    DECISION_POINTS = "decision_points"


class DelayMode(Enum):
    FROM_START = auto()
    FROM_END = auto()
    PERCENTAGE = auto()

    def __str__(self):
        return self.name


class FilterCondition(object):
    __slots__ = [
        "by",
        "where",
        "value",
    ]

    def __init__(self, by=None, where=None, value=None, decision=None):
        self.by = by
        self.where = where
        self.value = value

    def __repr__(self):
        return f"FilterCondition(by={self.by.upper()}, where={self.where}, value={self.value})"


class BetSettings(object):
    __slots__ = [
        "strategy",
        "percentage",
        "percentage_gap",
        "max_points",
        "minimum_points",
        "stealth_mode",
        "filter_condition",
        "delay",
        "delay_mode",
        "kelly_fraction",
        "kelly_probability_source",
    ]

    def __init__(
        self,
        strategy: Strategy = None,
        percentage: int = None,
        percentage_gap: int = None,
        max_points: int = None,
        minimum_points: int = None,
        stealth_mode: bool = None,
        filter_condition: FilterCondition = None,
        delay: float = None,
        delay_mode: DelayMode = None,
        kelly_fraction: float = None,
        kelly_probability_source: KellyProbabilitySource = None,
    ):
        self.strategy = strategy
        self.percentage = percentage
        self.percentage_gap = percentage_gap
        self.max_points = max_points
        self.minimum_points = minimum_points
        self.stealth_mode = stealth_mode
        self.filter_condition = filter_condition
        self.delay = delay
        self.delay_mode = delay_mode
        self.kelly_fraction = kelly_fraction
        self.kelly_probability_source = kelly_probability_source

    def default(self):
        self.strategy = self.strategy if self.strategy is not None else Strategy.SMART
        self.percentage = self.percentage if self.percentage is not None else 5
        self.percentage_gap = (
            self.percentage_gap if self.percentage_gap is not None else 20
        )
        self.max_points = self.max_points if self.max_points is not None else 50000
        self.minimum_points = (
            self.minimum_points if self.minimum_points is not None else 0
        )
        self.stealth_mode = (
            self.stealth_mode if self.stealth_mode is not None else False
        )
        self.delay = self.delay if self.delay is not None else 6
        self.delay_mode = (
            self.delay_mode if self.delay_mode is not None else DelayMode.FROM_END
        )
        self.kelly_fraction = self.kelly_fraction if self.kelly_fraction is not None else 0.5
        self.kelly_probability_source = (
            self.kelly_probability_source if self.kelly_probability_source is not None
            else KellyProbabilitySource.ODDS_PERCENTAGE
        )

    def __repr__(self):
        base_repr = (f"BetSettings(strategy={self.strategy}, percentage={self.percentage}, percentage_gap={self.percentage_gap}, "
                     f"max_points={self.max_points}, minimum_points={self.minimum_points}, stealth_mode={self.stealth_mode}, "
                     f"delay={self.delay}, delay_mode={self.delay_mode}")
        if self.strategy == Strategy.KELLY_CRITERION: # Check for actual enum member
            base_repr += f", kelly_fraction={self.kelly_fraction}, kelly_probability_source={self.kelly_probability_source.name if self.kelly_probability_source else None}"
        base_repr += ")"
        return base_repr


class Bet(object):
    __slots__ = ["outcomes", "decision", "total_users", "total_points", "settings"]

    def __init__(self, outcomes: list, settings: BetSettings):
        self.outcomes = outcomes
        self.__clear_outcomes()
        self.decision: dict = {}
        self.total_users = 0
        self.total_points = 0
        self.settings = settings

    def update_outcomes(self, outcomes):
        for index in range(0, len(self.outcomes)):
            self.outcomes[index][OutcomeKeys.TOTAL_USERS] = int(
                outcomes[index][OutcomeKeys.TOTAL_USERS]
            )
            self.outcomes[index][OutcomeKeys.TOTAL_POINTS] = int(
                outcomes[index][OutcomeKeys.TOTAL_POINTS]
            )
            if outcomes[index]["top_predictors"] != []:
                # Sort by points placed by other users
                outcomes[index]["top_predictors"] = sorted(
                    outcomes[index]["top_predictors"],
                    key=lambda x: x["points"],
                    reverse=True,
                )
                # Get the first elements (most placed)
                top_points = outcomes[index]["top_predictors"][0]["points"]
                self.outcomes[index][OutcomeKeys.TOP_POINTS] = top_points

        # Inefficient, but otherwise outcomekeys are represented wrong
        self.total_points = 0
        self.total_users = 0
        for index in range(0, len(self.outcomes)):
            self.total_users += self.outcomes[index][OutcomeKeys.TOTAL_USERS]
            self.total_points += self.outcomes[index][OutcomeKeys.TOTAL_POINTS]

        if (
            self.total_users > 0
            and self.total_points > 0
        ):
            for index in range(0, len(self.outcomes)):
                self.outcomes[index][OutcomeKeys.PERCENTAGE_USERS] = float_round(
                    (100 * self.outcomes[index][OutcomeKeys.TOTAL_USERS]) / self.total_users
                )
                self.outcomes[index][OutcomeKeys.ODDS] = float_round(
                    #self.total_points / max(self.outcomes[index][OutcomeKeys.TOTAL_POINTS], 1)
                    0
                    if self.outcomes[index][OutcomeKeys.TOTAL_POINTS] == 0
                    else self.total_points / self.outcomes[index][OutcomeKeys.TOTAL_POINTS]
                )
                self.outcomes[index][OutcomeKeys.ODDS_PERCENTAGE] = float_round(
                    #100 / max(self.outcomes[index][OutcomeKeys.ODDS], 1)
                    0
                    if self.outcomes[index][OutcomeKeys.ODDS] == 0
                    else 100 / self.outcomes[index][OutcomeKeys.ODDS]
                )

        self.__clear_outcomes()

    def __repr__(self):
        return f"Bet(total_users={millify(self.total_users)}, total_points={millify(self.total_points)}), decision={self.decision})\n\t\tOutcome A({self.get_outcome(0)})\n\t\tOutcome B({self.get_outcome(1)})"

    def get_decision(self, parsed=False):
        #decision = self.outcomes[0 if self.decision["choice"] == "A" else 1]
        decision = self.outcomes[self.decision["choice"]]
        return decision if parsed is False else Bet.__parse_outcome(decision)

    @staticmethod
    def __parse_outcome(outcome):
        return f"{outcome['title']} ({outcome['color']}), Points: {millify(outcome[OutcomeKeys.TOTAL_POINTS])}, Users: {millify(outcome[OutcomeKeys.TOTAL_USERS])} ({outcome[OutcomeKeys.PERCENTAGE_USERS]}%), Odds: {outcome[OutcomeKeys.ODDS]} ({outcome[OutcomeKeys.ODDS_PERCENTAGE]}%)"

    def get_outcome(self, index):
        return Bet.__parse_outcome(self.outcomes[index])

    def __clear_outcomes(self):
        for index in range(0, len(self.outcomes)):
            keys = copy.deepcopy(list(self.outcomes[index].keys()))
            for key in keys:
                if key not in [
                    OutcomeKeys.TOTAL_USERS,
                    OutcomeKeys.TOTAL_POINTS,
                    OutcomeKeys.TOP_POINTS,
                    OutcomeKeys.PERCENTAGE_USERS,
                    OutcomeKeys.ODDS,
                    OutcomeKeys.ODDS_PERCENTAGE,
                    "title",
                    "color",
                    "id",
                ]:
                    del self.outcomes[index][key]
            for key in [
                OutcomeKeys.PERCENTAGE_USERS,
                OutcomeKeys.ODDS,
                OutcomeKeys.ODDS_PERCENTAGE,
                OutcomeKeys.TOP_POINTS,
            ]:
                if key not in self.outcomes[index]:
                    self.outcomes[index][key] = 0

    '''def __return_choice(self, key) -> str:
        return "A" if self.outcomes[0][key] > self.outcomes[1][key] else "B"'''

    def __return_choice(self, key) -> int:
        largest=0
        for index in range(0, len(self.outcomes)):
            if self.outcomes[index][key] > self.outcomes[largest][key]:
                largest = index
        return largest

    def __return_number_choice(self, number) -> int:
        if (len(self.outcomes) > number):
            return number
        else:
            return 0

    def skip(self) -> bool:
        if self.settings.filter_condition is not None:
            # key == by , condition == where
            key = self.settings.filter_condition.by
            condition = self.settings.filter_condition.where
            value = self.settings.filter_condition.value

            fixed_key = (
                key
                if key not in [OutcomeKeys.DECISION_USERS, OutcomeKeys.DECISION_POINTS]
                else key.replace("decision", "total")
            )
            if key in [OutcomeKeys.TOTAL_USERS, OutcomeKeys.TOTAL_POINTS]:
                compared_value = (
                    self.outcomes[0][fixed_key] + self.outcomes[1][fixed_key]
                )
            else:
                #outcome_index = char_decision_as_index(self.decision["choice"])
                outcome_index = self.decision["choice"]
                compared_value = self.outcomes[outcome_index][fixed_key]

            # Check if condition is satisfied
            if condition == Condition.GT:
                if compared_value > value:
                    return False, compared_value
            elif condition == Condition.LT:
                if compared_value < value:
                    return False, compared_value
            elif condition == Condition.GTE:
                if compared_value >= value:
                    return False, compared_value
            elif condition == Condition.LTE:
                if compared_value <= value:
                    return False, compared_value
            return True, compared_value  # Else skip the bet
        else:
            return False, 0  # Default don't skip the bet

    def calculate(self, balance: int) -> dict:
        self.decision = {"choice": None, "amount": 0, "id": None}
        if self.settings.strategy == Strategy.MOST_VOTED:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.TOTAL_USERS)
        elif self.settings.strategy == Strategy.HIGH_ODDS:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.ODDS)
        elif self.settings.strategy == Strategy.PERCENTAGE:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.ODDS_PERCENTAGE)
        elif self.settings.strategy == Strategy.SMART_MONEY:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.TOP_POINTS)
        elif self.settings.strategy == Strategy.NUMBER_1:
            self.decision["choice"] = self.__return_number_choice(0)
        elif self.settings.strategy == Strategy.NUMBER_2:
            self.decision["choice"] = self.__return_number_choice(1)
        elif self.settings.strategy == Strategy.NUMBER_3:
            self.decision["choice"] = self.__return_number_choice(2)
        elif self.settings.strategy == Strategy.NUMBER_4:
            self.decision["choice"] = self.__return_number_choice(3)
        elif self.settings.strategy == Strategy.NUMBER_5:
            self.decision["choice"] = self.__return_number_choice(4)
        elif self.settings.strategy == Strategy.NUMBER_6:
            self.decision["choice"] = self.__return_number_choice(5)
        elif self.settings.strategy == Strategy.NUMBER_7:
            self.decision["choice"] = self.__return_number_choice(6)
        elif self.settings.strategy == Strategy.NUMBER_8:
            self.decision["choice"] = self.__return_number_choice(7)
        elif self.settings.strategy == Strategy.SMART:
            difference = abs(
                self.outcomes[0][OutcomeKeys.PERCENTAGE_USERS]
                - self.outcomes[1][OutcomeKeys.PERCENTAGE_USERS]
            )
            self.decision["choice"] = (
                self.__return_choice(OutcomeKeys.ODDS)
                if difference < self.settings.percentage_gap
                else self.__return_choice(OutcomeKeys.TOTAL_USERS)
            )
        elif self.settings.strategy == Strategy.KELLY_CRITERION:
            best_f_star = -float('inf')
            chosen_outcome_index = None
            calculated_amount_for_chosen_outcome = 0

            for i, outcome_data in enumerate(self.outcomes):
                p_key = (
                    OutcomeKeys.ODDS_PERCENTAGE
                    if self.settings.kelly_probability_source == KellyProbabilitySource.ODDS_PERCENTAGE
                    else OutcomeKeys.PERCENTAGE_USERS
                )
                p = outcome_data.get(p_key, 0.0) / 100.0 # Probabilities should be 0-1
                if p == 0.0:
                    continue

                q = 1.0 - p

                # Odds 'b' are net odds (payout multiplier - 1)
                # E.g., if Twitch odds are 2.5 (you get 2.5x your bet back), b = 1.5
                raw_odds = outcome_data.get(OutcomeKeys.ODDS, 0.0)
                if raw_odds <= 1.0: # Must win more than staked
                    continue
                b = raw_odds - 1.0

                value_check = (b * p) - q
                if value_check > 0 and b > 0:
                    f_star = value_check / b
                    if f_star > best_f_star:
                        best_f_star = f_star
                        chosen_outcome_index = i
                        calculated_amount_for_chosen_outcome = balance * f_star * self.settings.kelly_fraction

            if chosen_outcome_index is not None:
                self.decision["choice"] = chosen_outcome_index
                self.decision["id"] = self.outcomes[chosen_outcome_index]["id"]
                final_amount = int(calculated_amount_for_chosen_outcome)
                final_amount = min(final_amount, self.settings.max_points) # Apply max_points cap
                self.decision["amount"] = final_amount

                # Populate kelly_details
                chosen_outcome_data = self.outcomes[chosen_outcome_index]
                p_chosen = 0.0
                if self.settings.kelly_probability_source == KellyProbabilitySource.ODDS_PERCENTAGE:
                    p_chosen = chosen_outcome_data.get(OutcomeKeys.ODDS_PERCENTAGE, 0) / 100.0
                elif self.settings.kelly_probability_source == KellyProbabilitySource.USER_PERCENTAGE:
                    p_chosen = chosen_outcome_data.get(OutcomeKeys.PERCENTAGE_USERS, 0) / 100.0

                b_chosen = chosen_outcome_data.get(OutcomeKeys.ODDS, 0) - 1.0

                self.decision["kelly_details"] = {
                    "p": p_chosen,
                    "b": b_chosen,
                    "f_star_raw": best_f_star, # best_f_star is already (value_check / b)
                    "kelly_fraction_applied": self.settings.kelly_fraction
                }

        # Finalize decision and amount for all strategies
        if self.decision["choice"] is not None:
            # Ensure 'id' is set if not already (e.g. by non-Kelly strategies not setting it directly)
            if self.decision.get("id") is None: # Ensure id is set
                 self.decision["id"] = self.outcomes[self.decision["choice"]]["id"]

            # Amount finalization for non-Kelly strategies (if they didn't set it fully or need stealth)
            if self.settings.strategy != Strategy.KELLY_CRITERION:
                # If amount wasn't set by a specific non-Kelly strategy block, calculate it generally
                if self.decision.get("amount") is None or self.decision.get("amount") == 0:
                    self.decision["amount"] = min(
                        int(balance * (self.settings.percentage / 100)),
                        self.settings.max_points,
                    )

                # Apply stealth mode for non-Kelly strategies
                chosen_outcome_details = self.outcomes[self.decision["choice"]]
                top_points_on_chosen = chosen_outcome_details.get(OutcomeKeys.TOP_POINTS, float('inf'))

                if (
                    self.settings.stealth_mode is True
                    and self.decision["amount"] >= top_points_on_chosen
                    and top_points_on_chosen > 0 # only if top_points is meaningful
                ):
                    # from random import uniform # Already imported at the top
                    reduce_amount = uniform(1, 5)
                    self.decision["amount"] = int(top_points_on_chosen - reduce_amount)

            # Universal final adjustments for amount (applies to Kelly as well after its specific calculation)
            self.decision["amount"] = int(self.decision["amount"]) # Ensure integer

            # Apply minimum_points constraint if amount is positive
            if self.decision["amount"] > 0 and self.settings.minimum_points > 0:
                 # Only apply minimum_points if current amount is less than minimum_points
                 # and also ensure it doesn't exceed max_points or balance
                if self.decision["amount"] < self.settings.minimum_points:
                    self.decision["amount"] = min(self.settings.minimum_points, self.settings.max_points, balance)

            if self.decision["amount"] < 0: # Safety: amount should not be negative
                self.decision["amount"] = 0
        else: # If no choice was made by any strategy
            self.decision["amount"] = 0 # Ensure amount is zero

        return self.decision
