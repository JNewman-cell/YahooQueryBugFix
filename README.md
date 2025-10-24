# YahooQueryBugFix
This is the documentation of the finding, testing, and fixing of a bug in the popular repo Yahooquery a python library that allows people to freely access financial information from yahoo finance.

# Bug: Inconsistent `asset_profile` response structure from `yahooquery`

Summary
-------
When calling `Ticker(...).asset_profile` via the `yahooquery` package, the returned value can be one of two different structures depending on the ticker:

- For many well-known tickers (e.g. `AAPL`) a dictionary mapping a normalized ticker key to a nested dict with company fields is returned (expected structure).
- For many other tickers (e.g. `EAI`) the response is a dict mapping the ticker to a plain string message, e.g. `{'EAI': 'No fundamentals data found for symbol: EAI'}` (unexpected structure).

This inconsistency causes downstream code that expects a consistent dict-of-dicts to fail or misinterpret the response.

Reproduction
------------
1. Create a virtual environment and install `yahooquery`.
2. Run the following simplified script (the repository contains a test script at `misc/testing_yahoo_query_asset_profile_error_response.py`):

```python
import yahooquery as yq

for ticker in ("AAPL", "EAI"):
    ticker_obj = yq.Ticker(ticker)
    asset_profile = ticker_obj.asset_profile
    print(ticker, type(asset_profile), asset_profile)
```

Observed outputs (examples)
---------------------------
- Expected (normal) — nested dict for `AAPL`:

{'aapl': {
  'address1': 'One Apple Park Way',
  'industry': 'Consumer Electronics',
  'longBusinessSummary': 'Apple Inc. designs, manufactures, and markets ...',
  'fullTimeEmployees': 137000,
  ...
}}

- Unexpected for `EAI` — string message inside dict:

{'EAI': 'No fundamentals data found for symbol: EAI'}

Why this is a bug
------------------
- The response shape changes between tickers which forces callers to implement brittle, repetitive checks (isinstance(..., dict) and whether the inner value is a dict vs string).
- This behavior is not clearly documented in the `yahooquery` docs, leading to developer confusion and silent failures.

Impact
------
- Any code that assumes `asset_profile[ticker]` is a dict (with keys like `longName`, `industry`) will either raise exceptions or silently skip expected fields.
- Tests and data pipelines that depend on consistent shapes will break.

Suggested immediate workarounds
------------------------------
1. Defensive check: verify the inner value type before reading fields.

```python
asset_profile = ticker_obj.asset_profile
val = asset_profile.get(ticker.upper()) or asset_profile.get(ticker.lower())
if isinstance(val, dict):
    # normal processing
else:
    # handle message / log and skip
```

2. Normalizer helper: create a small utility that returns a canonical shape, e.g. always return a dict or an error object:

```python
def normalize_asset_profile(asset_profile, ticker):
    # returns (ok: bool, data_or_message)
    val = asset_profile.get(ticker) or asset_profile.get(ticker.lower())
    if isinstance(val, dict):
        return True, val
    return False, str(val)
```

Suggested fixes (longer-term)
----------------------------
- Update `yahooquery` docs to state that `asset_profile` may return a string message for tickers with no fundamentals data.
- Preferably, `yahooquery` should normalize: return either an empty dict or a standard error object/structure rather than a plain string for consistency.

Environment & notes
-------------------
- Reproduced on Windows with Python 3.12 and `yahooquery` (version used for test not recorded here — include when filing upstream bug).
- See the repository test script: `misc/testing_yahoo_query_asset_profile_error_response.py` which prints raw responses and demonstrates the issue.

Examples included above (AAPL expected dict; EAI unexpected string message).

## Comprehensive Test Results (2025-10-24)

An extensive test was conducted using `comprehensive_quote_summary_test.py` with **73 diverse tickers** spanning the entire NYSE range (A-Z) to evaluate the scope and unpredictability of response inconsistencies across all quoteSummary-based properties.

### 🎯 **TEST SCOPE & SCALE**
- **Total properties tested**: 17 quoteSummary properties
- **Total tickers tested**: 73 (massively expanded coverage)
- **Total individual API tests**: 1,241 
- **Execution time**: 119.28 seconds (10.4 tests/second)
- **Coverage**: Full alphabetical range A-Z across multiple asset classes and market caps

### 📊 **CURRENT BUG STATUS: DRAMATICALLY IMPROVED**

**Properties with string responses**: **0** (0%) 🎉  
**Properties with consistent behavior**: **2** (12%) ✅  
**Properties with mixed behavior**: **15** (88%) ⚠️

### 🔍 **UNPREDICTABILITY BY ASSET CLASS**

The bug exhibits **highly unpredictable patterns** across different asset types:

| Asset Category | String Response Rate | Predictability |
|----------------|---------------------|----------------|
| **Major Tech Stocks** | 0.0% | ✅ **Highly Reliable** |
| **Financial Stocks** | 0.0% | ✅ **Highly Reliable** |
| **Energy & Resources** | 0.0% | ✅ **Highly Reliable** |
| **Consumer & Retail** | 0.0% | ✅ **Highly Reliable** |
| **Healthcare & Pharma** | 0.0% | ✅ **Highly Reliable** |
| **Industrial & Defense** | 0.0% | ✅ **Highly Reliable** |
| **Technology Services** | 0.0% | ✅ **Highly Reliable** |
| **International/ADR** | 4.7% | ⚠️ **Mostly Reliable** |
| **OTC/Penny Stocks** | 11.8% | ⚠️ **Moderately Unreliable** |
| **Small/Micro Cap** | 13.2% | ⚠️ **Moderately Unreliable** |
| **ETFs** | 52.9% | ❌ **Highly Unreliable** |
| **Market Indices** | 70.6% | ❌ **Very Unreliable** |
| **Forex Pairs** | 76.5% | ❌ **Extremely Unreliable** |
| **Commodities** | 76.5% | ❌ **Extremely Unreliable** |

### 🎭 **THE UNPREDICTABILITY PROBLEM**

**Most Problematic Tickers** (Highest string response rates):
1. `ACRX` (88.2%) - Small pharmaceutical stock
2. `EURUSD=X` (76.5%) - EUR/USD forex pair  
3. `GBPUSD=X` (76.5%) - GBP/USD forex pair
4. `GC=F` (76.5%) - Gold futures
5. `CL=F` (76.5%) - Crude oil futures

**Most Reliable Tickers** (0% string response rates):
- All major stocks: `AAPL`, `MSFT`, `GOOGL`, `TSLA`, `NVDA`, `META`, `AMZN`
- All financial stocks: `JPM`, `BAC`, `GS`, `MS`, `WFC`
- Most consumer/retail: `KO`, `PG`, `WMT`, `NKE`, `HD`

### ⚠️ **WIDESPREAD MIXED BEHAVIOR (15 Properties)**

Almost **all properties** exhibit unpredictable mixed behavior:

**Mixed Behavior Properties**:
- `asset_profile` - Works for stocks, fails for forex/commodities
- `calendar_events` - Inconsistent across asset types  
- `earnings` - Works for stocks, mixed for others
- `earnings_trend` - Asset-type dependent
- `esg_scores` - Highly variable by ticker type
- `financial_data` - Mixed success rates
- `index_trend` - Inconsistent patterns
- `industry_trend` - Asset-class dependent  
- `key_stats` - Variable reliability
- `major_holders` - Mixed behavior patterns
- `page_views` - Unpredictable responses
- `price` - Inconsistent across asset types
- `share_purchase_activity` - Mixed reliability  
- `summary_detail` - Variable behavior
- `summary_profile` - Asset-dependent responses

**Only 2 Properties with Consistent Behavior**:
- ✅ `quote_type` - Reliable across all asset types
- ✅ `technical_insights` - Consistent response structure

### 🚨 **KEY FINDINGS: BROADER IMPACT**

1. **Asset Type Discrimination**: The API behaves **completely differently** depending on asset class
   - Traditional stocks (0% failures) vs. Forex/Commodities (76%+ failures)
   - This creates a **massive reliability gap** across different financial instruments

2. **Systematic Unpredictability**: 
   - **88% of properties** have mixed behavior that varies by ticker type
   - Developers cannot predict which calls will return strings vs. structured data
   - The same property can be reliable for one asset class and completely broken for another

3. **Scale of the Problem**:
   - Out of **1,241 individual tests**, hundreds exhibit inconsistent behavior
   - The bug affects **15 out of 17 properties** to varying degrees
   - **No property** (except 2) provides truly reliable cross-asset behavior

4. **Production Impact**:
   - Any application dealing with **diverse asset types** will experience failures
   - ETF analysis tools face 53% unreliability 
   - Forex/commodities applications face 76%+ failure rates
   - Multi-asset portfolio tools cannot rely on consistent data structures

### 💡 **Demonstration of Core Issue**

The inconsistency patterns are **highly unpredictable** and vary dramatically between stock tickers, creating a reliability minefield for developers:

#### **Perfect Reliability: Major US Stocks (100%)**

All major US stocks like AAPL, MSFT, JNJ, JPM, PG, KO, WMT, DIS, HD work flawlessly across **all 17 properties**:

```python
# AAPL (100% Reliable) - All properties return structured data
ticker_obj = yq.Ticker("AAPL")
result = ticker_obj.asset_profile
# {'AAPL': {'address1': 'One Apple Park Way', 'city': 'Cupertino', ...}}

result = ticker_obj.earnings
# {'AAPL': {'earningsChart': {...}, 'financialsChart': {...}}}

result = ticker_obj.key_stats  
# {'AAPL': {'enterpriseValue': 3400000000000, 'forwardPE': 28.5, ...}}
```

#### **Partial Reliability: Small Cap Stocks (5.9% - 94.1%)**

**BTCS Inc** (Small blockchain company) - **16/17 properties work, 1 fails**:

```python
# BTCS: 94.1% reliable - Only ESG scores fail
ticker_obj = yq.Ticker("BTCS")

# ✅ WORKS: Returns rich structured data
result = ticker_obj.asset_profile
# {'BTCS': {'address1': '1430 Broadway', 'city': 'New York', ...}}

result = ticker_obj.financial_data  
# {'BTCS': {'currentPrice': 2.85, 'targetHighPrice': 10.0, ...}}

# ❌ FAILS: Returns string error message  
result = ticker_obj.esg_scores
# {'BTCS': 'No fundamentals data found for symbol: BTCS'}
```

#### **Near-Complete Failure: Some Small Stocks (11.8%)**

**ACRX** (AcelRx Pharmaceuticals) - **Only 2/17 properties work, 15 fail**:

```python
# ACRX: 11.8% reliable - Most properties fail
ticker_obj = yq.Ticker("ACRX")

# ❌ FAILS: Most properties return string errors
result = ticker_obj.asset_profile
# {'ACRX': 'Quote not found for symbol: ACRX'}

result = ticker_obj.earnings
# {'ACRX': 'Quote not found for symbol: ACRX'}

# ✅ WORKS: Only 2 properties work  
result = ticker_obj.quote_type
# {'ACRX': {'quoteType': 'EQUITY', 'symbol': 'ACRX', ...}}

result = ticker_obj.technical_insights
# {'ACRX': {'symbol': 'ACRX', 'upsell': {...}, ...}}
```

#### **The Reliability Spectrum**

| Stock Type | Example | Reliability Rate | Impact |
|------------|---------|------------------|---------|
| **Major US Stocks** | AAPL, MSFT, JNJ | **100%** | ✅ Perfect |  
| **Small Growth Stock** | BTCS | **94.1%** | ⚠️ Mostly reliable |
| **Micro-Cap Stock** | ACRX | **11.8%** | ❌ Mostly broken |

**The Core Problem**: The **same API methods** produce **completely different data types** (structured dicts vs error strings) depending on the ticker's market classification, company size, or data availability. This creates an impossible development environment where:

- **You cannot predict** which stocks will work with which properties
- **The same property call** might work for Apple but fail for a small biotech
- **There's no pattern** - some small caps work fine, others fail catastrophically  
- **Defensive coding** is required for every single API call across every ticker type
