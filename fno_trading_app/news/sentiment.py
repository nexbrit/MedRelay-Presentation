"""
Sentiment Analysis for market news and social media
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter
import requests


class SentimentAnalyzer:
    """
    Analyze market sentiment from news and social media

    Uses simple keyword-based sentiment analysis
    Can be extended with ML models or APIs

    Sentiment as contrarian indicator:
    - Extreme bullishness (>90%) = Consider selling
    - Extreme bearishness (<10%) = Consider buying
    """

    def __init__(self):
        """Initialize sentiment analyzer"""
        # Positive keywords
        self.positive_keywords = {
            'bullish', 'rally', 'surge', 'jump', 'soar', 'gain', 'rise',
            'up', 'high', 'strong', 'boost', 'positive', 'optimistic',
            'breakout', 'buying', 'support', 'uptrend', 'momentum',
            'green', 'profit', 'bull', 'buy', 'long'
        }

        # Negative keywords
        self.negative_keywords = {
            'bearish', 'crash', 'plunge', 'fall', 'drop', 'decline', 'down',
            'low', 'weak', 'negative', 'pessimistic', 'breakdown', 'selling',
            'resistance', 'downtrend', 'red', 'loss', 'bear', 'sell', 'short',
            'fear', 'panic', 'dump'
        }

        self.sentiment_history = []

    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis
        """
        if not text:
            return {'sentiment': 'neutral', 'score': 0, 'confidence': 0}

        text_lower = text.lower()

        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text_lower)

        # Count positive and negative words
        positive_count = sum(1 for word in words if word in self.positive_keywords)
        negative_count = sum(1 for word in words if word in self.negative_keywords)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            return {
                'sentiment': 'neutral',
                'score': 0,
                'confidence': 0,
                'positive_count': 0,
                'negative_count': 0
            }

        # Calculate sentiment score (-1 to 1)
        score = (positive_count - negative_count) / total_sentiment_words

        # Calculate confidence (0 to 1)
        confidence = min(total_sentiment_words / len(words), 1.0) if len(words) > 0 else 0

        # Determine sentiment label
        if score > 0.2:
            sentiment = 'bullish'
        elif score < -0.2:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'score': round(score, 3),
            'confidence': round(confidence, 3),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'total_words': len(words)
        }

    def analyze_headlines(self, headlines: List[str]) -> Dict:
        """
        Analyze sentiment across multiple headlines

        Args:
            headlines: List of news headlines

        Returns:
            Aggregated sentiment analysis
        """
        if not headlines:
            return {
                'overall_sentiment': 'neutral',
                'bullish_pct': 0,
                'bearish_pct': 0,
                'neutral_pct': 0
            }

        sentiments = []
        scores = []

        for headline in headlines:
            analysis = self.analyze_text(headline)
            sentiments.append(analysis['sentiment'])
            scores.append(analysis['score'])

        # Count sentiment distribution
        sentiment_counts = Counter(sentiments)
        total = len(sentiments)

        bullish_pct = (sentiment_counts.get('bullish', 0) / total) * 100
        bearish_pct = (sentiment_counts.get('bearish', 0) / total) * 100
        neutral_pct = (sentiment_counts.get('neutral', 0) / total) * 100

        # Calculate average score
        avg_score = sum(scores) / len(scores) if scores else 0

        # Determine overall sentiment
        if bullish_pct > 50:
            overall = 'bullish'
        elif bearish_pct > 50:
            overall = 'bearish'
        else:
            overall = 'neutral'

        result = {
            'overall_sentiment': overall,
            'avg_score': round(avg_score, 3),
            'bullish_pct': round(bullish_pct, 2),
            'bearish_pct': round(bearish_pct, 2),
            'neutral_pct': round(neutral_pct, 2),
            'total_headlines': total,
            'timestamp': datetime.now()
        }

        # Save to history
        self.sentiment_history.append(result)

        return result

    def get_market_sentiment_indicator(
        self,
        headlines: List[str]
    ) -> Dict:
        """
        Get market sentiment as a contrarian indicator

        Args:
            headlines: List of news headlines

        Returns:
            Trading signal based on extreme sentiment
        """
        analysis = self.analyze_headlines(headlines)

        bullish_pct = analysis['bullish_pct']
        bearish_pct = analysis['bearish_pct']

        # Contrarian signals
        if bullish_pct >= 90:
            signal = 'EXTREME_BULLISH_SELL_SIGNAL'
            message = "Extreme bullishness detected (>90%). Consider taking profits or shorting."
            action = 'SELL'
        elif bullish_pct >= 75:
            signal = 'HIGH_BULLISH_CAUTION'
            message = "High bullishness (>75%). Be cautious with longs."
            action = 'CAUTION'
        elif bearish_pct >= 90:
            signal = 'EXTREME_BEARISH_BUY_SIGNAL'
            message = "Extreme bearishness detected (>90%). Consider buying opportunity."
            action = 'BUY'
        elif bearish_pct >= 75:
            signal = 'HIGH_BEARISH_OPPORTUNITY'
            message = "High bearishness (>75%). Look for long opportunities."
            action = 'WATCH_FOR_LONG'
        else:
            signal = 'NEUTRAL'
            message = "Balanced sentiment. No extreme readings."
            action = 'NEUTRAL'

        return {
            **analysis,
            'contrarian_signal': signal,
            'message': message,
            'action': action
        }

    def track_sentiment_over_time(
        self,
        days: int = 7
    ) -> Optional[List[Dict]]:
        """
        Get sentiment history over time

        Args:
            days: Number of days to look back

        Returns:
            List of sentiment snapshots
        """
        if not self.sentiment_history:
            return None

        cutoff_date = datetime.now() - timedelta(days=days)

        recent_history = [
            snapshot for snapshot in self.sentiment_history
            if snapshot['timestamp'] >= cutoff_date
        ]

        return recent_history

    def detect_sentiment_shift(self) -> Optional[Dict]:
        """
        Detect significant shifts in sentiment

        Returns:
            Dictionary with shift details if detected
        """
        if len(self.sentiment_history) < 2:
            return None

        latest = self.sentiment_history[-1]
        previous = self.sentiment_history[-2]

        bullish_change = latest['bullish_pct'] - previous['bullish_pct']
        bearish_change = latest['bearish_pct'] - previous['bearish_pct']

        # Detect significant shifts (>20% change)
        if abs(bullish_change) > 20 or abs(bearish_change) > 20:
            return {
                'shift_detected': True,
                'from_sentiment': previous['overall_sentiment'],
                'to_sentiment': latest['overall_sentiment'],
                'bullish_change': round(bullish_change, 2),
                'bearish_change': round(bearish_change, 2),
                'timestamp': latest['timestamp']
            }

        return None

    def get_simple_sentiment_score(
        self,
        instrument: str,
        sample_headlines: List[str] = None
    ) -> int:
        """
        Get simple sentiment score for quick reference

        Args:
            instrument: Trading instrument
            sample_headlines: Headlines to analyze

        Returns:
            Sentiment score from 0 (extreme bearish) to 100 (extreme bullish)
        """
        if not sample_headlines:
            # If no headlines provided, return neutral
            return 50

        analysis = self.analyze_headlines(sample_headlines)

        # Convert to 0-100 scale
        # bearish_pct maps to 0, neutral to 50, bullish to 100
        score = analysis['bullish_pct']

        return int(round(score))

    def print_sentiment_report(self, headlines: List[str]):
        """Print formatted sentiment report"""
        if not headlines:
            print("\nNo headlines to analyze")
            return

        analysis = self.get_market_sentiment_indicator(headlines)

        print("\n" + "=" * 60)
        print("MARKET SENTIMENT ANALYSIS")
        print("=" * 60)

        print(f"\nTotal Headlines Analyzed: {analysis['total_headlines']}")
        print(f"\nSentiment Distribution:")
        print(f"  🟢 Bullish:  {analysis['bullish_pct']:.1f}%")
        print(f"  🔴 Bearish:  {analysis['bearish_pct']:.1f}%")
        print(f"  ⚪ Neutral:  {analysis['neutral_pct']:.1f}%")

        print(f"\nOverall Sentiment: {analysis['overall_sentiment'].upper()}")
        print(f"Average Score: {analysis['avg_score']:.3f} (-1 to 1)")

        print(f"\n🎯 CONTRARIAN SIGNAL: {analysis['contrarian_signal']}")
        print(f"Action: {analysis['action']}")
        print(f"Message: {analysis['message']}")

        print("=" * 60)

    def add_custom_keywords(
        self,
        positive: List[str] = None,
        negative: List[str] = None
    ):
        """
        Add custom sentiment keywords

        Args:
            positive: List of positive keywords to add
            negative: List of negative keywords to add
        """
        if positive:
            self.positive_keywords.update(set(positive))

        if negative:
            self.negative_keywords.update(set(negative))

    def reset_history(self):
        """Clear sentiment history"""
        self.sentiment_history = []


# Example usage
if __name__ == "__main__":
    # Demo sentiment analysis
    analyzer = SentimentAnalyzer()

    sample_headlines = [
        "Nifty surges 200 points on strong buying",
        "Market crashes amid global selloff",
        "Sensex jumps to new all-time high",
        "Banking stocks plunge on RBI concerns",
        "Bulls dominate as IT stocks rally",
        "Bears in control, market falls sharply",
    ]

    analyzer.print_sentiment_report(sample_headlines)
