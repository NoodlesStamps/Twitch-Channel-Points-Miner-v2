# TwitchChannelPointsMiner/log_analyzer.py
import re
from collections import defaultdict
from datetime import datetime
import logging

# Configure a logger for this module (optional, but good practice)
logger = logging.getLogger(__name__)

class BetPerformance:
    def __init__(self, timestamp, streamer, event_id, event_title, strategy, amount_bet, outcome, points_gained):
        self.timestamp = timestamp
        self.streamer = streamer
        self.event_id = event_id
        self.event_title = event_title
        self.strategy = strategy
        self.amount_bet = amount_bet
        self.outcome = outcome # "WIN", "LOSE", "REFUND"
        self.points_gained = points_gained # Can be negative for losses

    def __repr__(self):
        return (f"BetPerformance(ts={self.timestamp}, streamer={self.streamer}, event_id={self.event_id}, "
                f"strategy={self.strategy}, bet={self.amount_bet}, outcome={self.outcome}, gained={self.points_gained})")

class LogAnalyzer:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.parsed_bets = []

        # Timestamp: 29/07/24 10:00:00 or 29/07/2024 10:00:00
        self.timestamp_regex = r"\d{2}/\d{2}/\d{2,4} \d{2}:\d{2}:\d{2}"
        # Strategy: BetSettings(strategy=Strategy.SMART, ... or strategy=SMART
        self.strategy_log_regex = re.compile(
            r"BetSettings\(strategy=(?:Strategy\.([A-Z_0-9]+)|([A-Z_0-9]+))"
        )
        # Recap: EventPrediction(event_id=..., streamer=..., title=...) Bet(...) decision={'amount': ...} ... Result: TYPE, Action: (+/-)POINTS
        self.recap_log_regex = re.compile(
            r"EventPrediction\("
            r"event_id=([^,]+)\s*,\s*"
            r"streamer=Streamer\(username=([^,]+),.*\)\s*,\s*"
            r"title=([^)]+)\)\s*"
            r"Bet\(.*decision=.*'amount':\s*(\d+).*?\).*?" # amount before millify
            r"Result:\s*(WIN|LOSE|REFUND|CANCELLED|LOCKED)\s*,\s*"
            r"(?:Gained|Lost|Action|Refunded):\s*([+-]?[\d\.,kmbtKMGT]+)" # points_gained after millify
        )

        self.millify_re = re.compile(r'([+-]?[\d\.]+)([kKmMbBtTlLgG]?)') # Updated to include 'l' for "Lost", and sign

    def _parse_millify(self, value_str_signed):
        value_str_signed = str(value_str_signed).replace(',', '') # Remove commas for numbers like "1,000"
        match = self.millify_re.match(value_str_signed)

        if not match:
            try:
                return int(value_str_signed)
            except ValueError:
                logger.warning(f"Could not parse '{value_str_signed}' as int directly after millify regex failed.")
                raise ValueError(f"Invalid number format for millify: {value_str_signed}")

        num_str, suffix = match.groups()
        num = float(num_str)

        suffix = suffix.lower()

        if suffix == 'k':
            return int(num * 1000)
        elif suffix == 'm':
            return int(num * 1000**2)
        elif suffix == 'b' or suffix == 'g': # Billion/Giga
            return int(num * 1000**3)
        elif suffix == 't': # Trillion/Tera
            return int(num * 1000**4)
        elif suffix == 'l': # "Lost" if it's part of the number string, though unlikely with current regex
             return int(num) # Should already be handled by sign
        else: # Includes empty suffix
            return int(num)

    def parse_logs(self):
        self.parsed_bets = []
        current_strategy = None

        # Ensure file exists
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                log_content = f.readlines()
        except FileNotFoundError:
            logger.error(f"Log file not found: {self.log_file_path}")
            return [] # Return empty list if file not found

        for line_number, line in enumerate(log_content):
            line = line.strip()
            timestamp_match = re.search(self.timestamp_regex, line)
            ts = datetime.strptime(timestamp_match.group(0), "%d/%m/%y %H:%M:%S") if timestamp_match else                  (datetime.strptime(timestamp_match.group(0), "%d/%m/%Y %H:%M:%S") if timestamp_match and len(timestamp_match.group(0).split('/')[2].split(' ')[0]) == 4 else None)

            if not ts and timestamp_match: # Attempt parsing YYYY if YY failed
                 try:
                    ts = datetime.strptime(timestamp_match.group(0), "%d/%m/%Y %H:%M:%S")
                 except ValueError:
                    logger.warning(f"Could not parse timestamp on line {line_number+1}: {timestamp_match.group(0)}")
                    ts = datetime.now() # Fallback, or skip

            strategy_match = self.strategy_log_regex.search(line)
            if strategy_match:
                # Group 1 is Strategy.XXX, Group 2 is XXX
                current_strategy = strategy_match.group(1) or strategy_match.group(2)
                if current_strategy and '.' in current_strategy: # Handles Strategy.SMART
                    current_strategy = current_strategy.split('.')[-1]
                # This strategy applies to the next recap log
                continue

            recap_match = self.recap_log_regex.search(line)
            if recap_match and current_strategy:
                try:
                    event_id = recap_match.group(1).strip()
                    streamer = recap_match.group(2).strip()
                    event_title = recap_match.group(3).strip()
                    # Amount bet is from decision dict, pre-millify
                    amount_bet_str = recap_match.group(4).strip()
                    outcome_type = recap_match.group(5).strip().upper() # Ensure outcome is uppercase
                    points_gained_str = recap_match.group(6).strip()

                    amount_bet = int(amount_bet_str) # Amount bet is direct from decision, not millified
                    points_gained = self._parse_millify(points_gained_str)

                    # Points gained in log is net. If "LOSE, Lost: 1k", points_gained_str is "1k" -> 1000
                    # We need to ensure it's negative for losses.
                    # The regex `([+-]?[\d\.,kmbtKMGT]+)` captures the sign.
                    # If points_gained_str was "-1k", _parse_millify would return -1000.
                    # If it was "1k" for a loss, and outcome_type is LOSE, it should be made negative.
                    # However, the source `event.result['string']` is `f"{result_type}, {action}: {points['prefix']}{_millify(points['gained'])}"`
                    # And `points['gained']` = `won - placed`. So it is already correctly signed before millify.
                    # The _parse_millify should handle the prefix sign.

                    bet_perf = BetPerformance(
                        timestamp=ts if ts else datetime.now(), # Fallback timestamp
                        streamer=streamer,
                        event_id=event_id,
                        event_title=event_title,
                        strategy=current_strategy,
                        amount_bet=amount_bet,
                        outcome=outcome_type,
                        points_gained=points_gained
                    )
                    self.parsed_bets.append(bet_perf)

                except ValueError as e:
                    logger.warning(f"Could not parse numbers in line {line_number+1}: {line} - {e}")
                except Exception as e:
                    logger.error(f"Error parsing recap line {line_number+1}: {line} - {e}", exc_info=True)
                finally:
                    current_strategy = None # Reset strategy, critical for correct association
        return self.parsed_bets

    def analyze_performance(self, from_date=None, to_date=None):
        if not self.parsed_bets: # If called directly without parse_logs being called first or if parse_logs returned empty
            logger.info("No parsed bet data available. Running parse_logs first.")
            self.parse_logs()
            if not self.parsed_bets: # If still no data
                logger.info("No bets found in logs after parsing.")
                return {}


        filtered_bets = self.parsed_bets
        if from_date:
            filtered_bets = [b for b in filtered_bets if b.timestamp and b.timestamp >= from_date]
        if to_date:
            filtered_bets = [b for b in filtered_bets if b.timestamp and b.timestamp <= to_date]

        performance_by_strategy = defaultdict(lambda: {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "refunds": 0, # and other outcomes like CANCELLED
            "total_points_bet": 0,
            "total_points_gained": 0, # Net gain/loss
        })

        for bet in filtered_bets:
            stats = performance_by_strategy[bet.strategy]
            stats["total_bets"] += 1
            stats["total_points_bet"] += bet.amount_bet
            stats["total_points_gained"] += bet.points_gained

            if bet.outcome == "WIN":
                stats["wins"] += 1
            elif bet.outcome == "LOSE":
                stats["losses"] += 1
            elif bet.outcome == "REFUND" or bet.outcome == "CANCELLED": # Group refunds and cancelled
                stats["refunds"] += 1
            # Note: LOCKED events might not have points gained/lost in the same way.
            # For now, they are just counted in total_bets if they make it here.

        # Calculate further metrics
        for strategy, stats in performance_by_strategy.items():
            # Bettable outcomes are those that result in a win or loss.
            bettable_outcomes = stats["wins"] + stats["losses"]
            stats["win_rate"] = (stats["wins"] / bettable_outcomes) if bettable_outcomes > 0 else 0.0
            # ROI should be based on total points bet on outcomes that were not refunded/cancelled
            # For simplicity, current ROI includes all bets. Could be refined.
            stats["roi"] = (stats["total_points_gained"] / stats["total_points_bet"]) if stats["total_points_bet"] > 0 else 0.0

        return dict(performance_by_strategy) # Convert back to dict for easier use outside

# Example Usage (for testing, would be removed or in a __main__ block)
# if __name__ == '__main__':
#     # Configure basic logging for testing the analyzer
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#
#     # Create a dummy log file for testing
#     dummy_log_path = "dummy_miner.log"
#     with open(dummy_log_path, "w", encoding="utf-8") as f:
#         f.write("29/07/24 10:00:00 - INFO - MinerName - [funcName]: BetSettings(strategy=Strategy.SMART, percentage=5)
")
#         f.write("29/07/24 10:00:01 - INFO - MinerName - [funcName]: EventPrediction(event_id=event1, streamer=Streamer(username=test_streamer, channel_id=123), title=Will it blend?) Bet(total_users=10, total_points=1000, decision={'choice': 0, 'amount': 100, 'id': 'outcomeA'}) Result: WIN, Gained: +200
")
#         f.write("29/07/24 10:05:00 - INFO - MinerName - [funcName]: BetSettings(strategy=Strategy.HIGH_ODDS, max_points=1000)
")
#         f.write("29/07/24 10:05:01 - INFO - MinerName - [funcName]: EventPrediction(event_id=event2, streamer=Streamer(username=another_streamer, channel_id=456), title=Another bet?) Bet(total_users=5, total_points=500, decision={'choice': 1, 'amount': 50, 'id': 'outcomeB'}) Result: LOSE, Lost: -50
")
#         f.write("29/07/24 10:10:00 - INFO - MinerName - [funcName]: BetSettings(strategy=Strategy.SMART, percentage=10)
") # New SMART settings
#         f.write("29/07/24 10:10:01 - INFO - MinerName - [funcName]: EventPrediction(event_id=event3, streamer=Streamer(username=test_streamer, channel_id=123), title=Third time lucky?) Bet(total_users=20, total_points=2000, decision={'choice': 0, 'amount': 200, 'id': 'outcomeC'}) Result: LOSE, Lost: -200
")
#         f.write("29/07/24 10:15:00 - INFO - MinerName - [funcName]: BetSettings(strategy=Strategy.SMART, percentage=10)
")
#         f.write("29/07/24 10:15:01 - INFO - MinerName - [funcName]: EventPrediction(event_id=event4, streamer=Streamer(username=test_streamer, channel_id=123), title=Refund event) Bet(total_users=20, total_points=2000, decision={'choice': 0, 'amount': 50, 'id': 'outcomeD'}) Result: REFUND, Action: +0
")


#     analyzer = LogAnalyzer(dummy_log_path) # Use the dummy log
#     # analyzer = LogAnalyzer("path_to_your_actual_username.log") # For real testing
#
#     parsed_data = analyzer.parse_logs()
#     print("\n--- Parsed Bets ---")
#     for p_bet in parsed_data:
#         print(p_bet)
#
#     print("\n--- Performance Analysis ---")
#     performance = analyzer.analyze_performance()
#     for strategy_name, data_metrics in performance.items():
#         print(f"Strategy: {strategy_name}")
#         for stat, value in data_metrics.items():
#             print(f"  {stat}: {value}")

#     # Clean up dummy log file
#     import os
#     os.remove(dummy_log_path)
