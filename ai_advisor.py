"""
AI Portfolio Advisor using Claude API
Provides intelligent portfolio analysis and recommendations
"""

import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Check if Anthropic API is available
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
AI_ENABLED = ANTHROPIC_API_KEY is not None

if AI_ENABLED:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        AI_ENABLED = False
        print("Warning: anthropic package not installed. Install with: pip install anthropic")


def analyze_portfolio(tickers, weights, metrics, portfolio_name="Portfolio"):
    """
    Analyze portfolio using Claude AI and provide recommendations.

    Args:
        tickers: List of ticker symbols
        weights: List of weights (percentages)
        metrics: Dict with performance metrics
        portfolio_name: Name of the portfolio

    Returns:
        Dict with analysis results or None if AI is disabled
    """
    if not AI_ENABLED:
        return {
            'success': False,
            'error': 'AI advisor is not configured. Please add ANTHROPIC_API_KEY to .env file.',
            'setup_instructions': 'Get your API key from https://console.anthropic.com/'
        }

    try:
        # Build portfolio summary
        portfolio_summary = f"""
Portfolio Name: {portfolio_name}
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}

Holdings:
"""
        for ticker, weight in zip(tickers, weights):
            portfolio_summary += f"- {ticker}: {weight:.1f}%\n"

        portfolio_summary += f"""
Performance Metrics:
- Total Return: {metrics.get('Total Return', 'N/A')}
- Annualized Return: {metrics.get('Annualized Return', 'N/A')}
- Annualized Volatility: {metrics.get('Annualized Volatility', 'N/A')}
- Max Drawdown: {metrics.get('Max Drawdown', 'N/A')}
- Period: {metrics.get('Period', 'N/A')}
"""

        # Create the prompt for Claude
        prompt = f"""You are an expert financial advisor analyzing a portfolio. Please provide a comprehensive analysis of this portfolio.

{portfolio_summary}

Please provide:

1. **Performance Summary** (2-3 sentences)
   - Overall assessment of the returns and risk
   - How this compares to typical market performance

2. **Strengths** (2-3 bullet points)
   - What is this portfolio doing well?
   - Positive aspects of the allocation or performance

3. **Weaknesses** (2-3 bullet points)
   - What concerns should the investor be aware of?
   - Areas that could be improved

4. **Risk Assessment**
   - Rate the overall risk level (Low/Medium/High) with brief explanation
   - Key risk factors to monitor

5. **Recommendations** (3-4 actionable suggestions)
   - Specific, practical advice for improving the portfolio
   - Consider diversification, allocation, and risk management

Keep the tone professional but accessible. Use plain language, not financial jargon. Be honest about both positives and negatives."""

        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the response
        analysis_text = message.content[0].text

        return {
            'success': True,
            'analysis': analysis_text,
            'portfolio_summary': portfolio_summary,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tokens_used': message.usage.input_tokens + message.usage.output_tokens
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'AI analysis failed: {str(e)}',
            'details': 'Check your API key and internet connection'
        }


def get_quick_insights(metrics):
    """
    Provide quick rule-based insights without AI (fallback option).

    Args:
        metrics: Dict with performance metrics

    Returns:
        String with basic insights
    """
    insights = []

    # Parse metrics
    try:
        total_return = float(metrics.get('Total Return', '0%').strip('%'))
        volatility = float(metrics.get('Annualized Volatility', '0%').strip('%'))
        max_dd = float(metrics.get('Max Drawdown', '0%').strip('%'))
    except:
        return "Unable to analyze metrics - invalid format"

    # Return assessment
    if total_return > 15:
        insights.append("✓ Strong returns - outperforming typical portfolios")
    elif total_return > 8:
        insights.append("✓ Moderate returns - reasonable performance")
    elif total_return > 0:
        insights.append("⚠ Below-average returns - consider optimization")
    else:
        insights.append("⚠ Negative returns - portfolio underperforming")

    # Volatility assessment
    if volatility < 10:
        insights.append("✓ Low volatility - conservative portfolio")
    elif volatility < 20:
        insights.append("○ Moderate volatility - balanced risk")
    else:
        insights.append("⚠ High volatility - aggressive portfolio")

    # Drawdown assessment
    if abs(max_dd) < 10:
        insights.append("✓ Small drawdowns - good downside protection")
    elif abs(max_dd) < 25:
        insights.append("○ Moderate drawdowns - typical for stock portfolios")
    else:
        insights.append("⚠ Large drawdowns - high risk exposure")

    return "\n".join(insights)


def check_ai_status():
    """
    Check if AI advisor is properly configured.

    Returns:
        Dict with status information
    """
    if not AI_ENABLED:
        return {
            'enabled': False,
            'reason': 'API key not found',
            'instructions': 'Add ANTHROPIC_API_KEY to your .env file'
        }

    try:
        # Test API connection with minimal request
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Hi"}
            ]
        )
        return {
            'enabled': True,
            'model': 'claude-3-5-sonnet-20241022',
            'status': 'Connected'
        }
    except Exception as e:
        return {
            'enabled': False,
            'reason': f'API error: {str(e)}',
            'instructions': 'Check your API key and internet connection'
        }
