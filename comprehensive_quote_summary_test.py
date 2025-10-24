"""
Comprehensive test script for yahooquery quote summary functionality
Tests all properties that use _quote_summary to identify inconsistent response structures
Uses rate-limited execution to avoid API limits and saves string response examples
"""
import yahooquery as yq
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

def test_single_ticker_all_properties(ticker, description, quote_summary_properties, string_examples_data=None):
    """
    Test all quote summary properties for a single ticker using individual API calls
    """
    try:
        # Extract string_examples dict and lock if provided
        string_examples = None
        string_examples_lock = None
        if string_examples_data:
            string_examples, string_examples_lock = string_examples_data
        
        # Add delay to avoid hitting rate limits
        time.sleep(0.1)  # 100ms delay between tickers (reduced since we're doing individual calls)
        
        ticker_obj = yq.Ticker(ticker)
        
        # Map property names to their actual property methods
        property_methods = {
            'asset_profile': 'asset_profile',
            'calendar_events': 'calendar_events',
            'earnings': 'earnings',
            'earnings_trend': 'earnings_trend',
            'esg_scores': 'esg_scores',
            'financial_data': 'financial_data',
            'index_trend': 'index_trend',
            'industry_trend': 'industry_trend',
            'key_stats': 'key_stats',
            'major_holders': 'major_holders',
            'page_views': 'page_views',
            'price': 'price',
            'quote_type': 'quote_type',
            'share_purchase_activity': 'share_purchase_activity',
            'summary_detail': 'summary_detail',
            'summary_profile': 'summary_profile',
            'technical_insights': 'technical_insights'
        }
        
        results = []
        
        # Process each property with individual API calls
        for prop_name in quote_summary_properties:
            if prop_name not in property_methods:
                continue
                
            try:
                # Make individual property call
                method_name = property_methods[prop_name]
                property_data = getattr(ticker_obj, method_name)
                
                # Find the ticker-specific data
                ticker_key = None
                for key in property_data.keys():
                    if key.upper() == ticker.upper():
                        ticker_key = key
                        break
                
                if ticker_key is None:
                    result = {
                        "ticker": ticker,
                        "property": prop_name,
                        "status": "error",
                        "issue": "Ticker not found in response",
                        "available_keys": list(property_data.keys())
                    }
                    results.append(result)
                    continue
                
                # Extract the ticker-specific data
                module_data = property_data[ticker_key]
                
                # Analyze the module response
                if isinstance(module_data, str):
                    result = {
                        "ticker": ticker,
                        "property": prop_name,
                        "status": "string_response",
                        "message": module_data,
                        "issue": "Returned string instead of structured data",
                        "full_response": {ticker_key: module_data}
                    }
                    
                    # Save string response example (thread-safe)
                    if string_examples is not None and string_examples_lock is not None:
                        example_key = f"{prop_name}_{ticker}"
                        with string_examples_lock:
                            string_examples[example_key] = {
                                "ticker": ticker,
                                "property": prop_name,
                                "description": description,
                                "string_message": module_data,
                                "full_response": {ticker_key: module_data},
                                "timestamp": datetime.now().isoformat()
                            }
                        
                elif isinstance(module_data, dict):
                    if module_data.get("error"):
                        result = {
                            "ticker": ticker,
                            "property": prop_name,
                            "status": "structured_error",
                            "error_info": module_data.get("error"),
                            "keys": list(module_data.keys())
                        }
                    else:
                        result = {
                            "ticker": ticker,
                            "property": prop_name,
                            "status": "valid_data",
                            "key_count": len(module_data),
                            "sample_keys": list(module_data.keys())[:5]
                        }
                elif module_data is None:
                    result = {
                        "ticker": ticker,
                        "property": prop_name,
                        "status": "null_value"
                    }
                else:
                    result = {
                        "ticker": ticker,
                        "property": prop_name,
                        "status": "unexpected_type",
                        "type": type(module_data).__name__,
                        "value": str(module_data)[:100]
                    }
                
                results.append(result)
                
                # Small delay between individual property calls
                time.sleep(0.05)  # 50ms between properties to avoid rate limits
                
            except Exception as prop_error:
                result = {
                    "ticker": ticker,
                    "property": prop_name,
                    "status": "exception",
                    "error": str(prop_error)
                }
                results.append(result)
        
        return results
        
    except Exception as e:
        # Return error results for all properties
        return [{
            "ticker": ticker,
            "property": prop_name,
            "status": "exception",
            "error": str(e)
        } for prop_name in quote_summary_properties]

def analyze_ticker_patterns(detailed_results):
    """
    Analyze patterns across tickers to identify which types cause most issues
    """
    ticker_string_counts = {}
    ticker_total_counts = {}
    
    # Count string responses per ticker across all properties
    for prop_name, prop_data in detailed_results.items():
        for ticker, ticker_data in prop_data["test_cases"].items():
            if ticker not in ticker_string_counts:
                ticker_string_counts[ticker] = 0
                ticker_total_counts[ticker] = 0
            
            ticker_total_counts[ticker] += 1
            if ticker_data.get("status") == "string_response":
                ticker_string_counts[ticker] += 1
    
    # Calculate string response rates per ticker
    ticker_rates = {}
    for ticker in ticker_total_counts:
        if ticker_total_counts[ticker] > 0:
            ticker_rates[ticker] = ticker_string_counts[ticker] / ticker_total_counts[ticker]
    
    # Sort tickers by problematic-ness
    most_problematic = sorted(ticker_rates.items(), key=lambda x: x[1], reverse=True)[:10]
    most_reliable = sorted(ticker_rates.items(), key=lambda x: x[1])[:10]
    
    # Categorize tickers
    categories = {
        "Major Tech Stocks": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"],
        "Financial Stocks": ["JPM", "BAC", "GS", "MS", "WFC"],
        "ETFs": ["SPY", "QQQ", "IWM"],
        "International/ADR": ["BABA", "ASML", "TSM", "NVO", "UL"],
        "Energy & Resources": ["APA", "XOM", "F", "DD"],
        "Consumer & Retail": ["BALL", "BBY", "CCL", "CL", "COST", "DIS", "HD", "KO", "NKE", "PG", "WMT", "YUM"],
        "Healthcare & Pharma": ["JNJ", "UNH"],
        "Industrial & Defense": ["AON", "EMR", "FDX", "GE", "LMT", "MMM", "NOC", "RTX"],
        "Technology Services": ["IBM", "T", "TXN", "V"],
        "Small/Micro Cap": ["EAI", "ZYXI", "ACRX", "BTCS", "ACHR", "ACEL", "EARN", "MLI", "NINE", "SAFE", "TUYA", "WEAV"],
        "OTC/Penny Stocks": ["GVSI", "OZSC"],
        "Cryptocurrencies": ["BTC-USD", "ETH-USD", "BTCUSD=X"],
        "Market Indices": ["^GSPC", "^DJI", "^IXIC", "^VIX"],
        "Forex": ["EURUSD=X", "GBPUSD=X"],
        "Commodities": ["GC=F", "CL=F"],
        "Invalid Tickers": ["INVALID123", "NOTREAL999", "FAKE_SYMBOL", ""]
    }
    
    category_analysis = {}
    for category, tickers in categories.items():
        total_rate = 0
        count = 0
        for ticker in tickers:
            if ticker in ticker_rates:
                total_rate += ticker_rates[ticker]
                count += 1
        category_analysis[category] = total_rate / count if count > 0 else 0
    
    return {
        "most_problematic": most_problematic,
        "most_reliable": most_reliable,
        "category_analysis": category_analysis,
        "ticker_rates": ticker_rates
    }

def create_examples_report(string_examples):
    """
    Create a markdown report with string response examples for the bug report
    """
    if not string_examples:
        return
    
    report_content = """# String Response Examples

This file contains examples of string responses that demonstrate the inconsistent behavior
described in the bug report. These examples were automatically collected during testing.

## Examples

"""
    
    # Group examples by property
    properties = {}
    for key, example in string_examples.items():
        prop = example["property"]
        if prop not in properties:
            properties[prop] = []
        properties[prop].append(example)
    
    # Create sections for each property that had string responses
    for prop_name, examples in properties.items():
        report_content += f"### Property: `{prop_name}`\n\n"
        
        for example in examples[:3]:  # Limit to first 3 examples per property
            report_content += f"**Ticker:** `{example['ticker']}` ({example['description']})\n\n"
            report_content += f"**String Message:** `{example['string_message']}`\n\n"
            report_content += f"**Full Response:**\n```json\n{json.dumps(example['full_response'], indent=2)}\n```\n\n"
            report_content += f"**Timestamp:** {example['timestamp']}\n\n"
            report_content += "---\n\n"
    
    # Save the report
    with open("string_response_examples_report.md", "w") as f:
        f.write(report_content)
    
    print(f"📄 String response examples report saved to: string_response_examples_report.md")

def update_bug_report_with_examples(bug_examples, string_examples):
    """
    Update the bug report with concrete examples from the test run
    """
    bug_report_path = "BUG_yahooquery_asset_profile_inconsistent_response.md"
    
    if not os.path.exists(bug_report_path):
        print(f"⚠️  Bug report file not found: {bug_report_path}")
        return
    
    # Read the current bug report
    with open(bug_report_path, "r") as f:
        content = f.read()
    
    # Find the examples section
    examples_start = content.find("Observed outputs (examples)")
    if examples_start == -1:
        print("⚠️  Could not find examples section in bug report")
        return
    
    # Find the end of the examples section
    examples_end = content.find("Why this is a bug", examples_start)
    if examples_end == -1:
        examples_end = len(content)
    
    # Create new examples section with actual data
    new_examples = "Observed outputs (examples)\n---------------------------\n"
    
    # Add the AAPL example (expected structure)
    if "AAPL" in bug_examples and bug_examples["AAPL"]["issue_type"] == "valid_data":
        aapl_data = bug_examples["AAPL"]["ticker_data"]
        # Get a few sample fields for the example
        sample_data = {k: v for k, v in list(aapl_data.items())[:5]}
        new_examples += f"- Expected (normal) — nested dict for `AAPL` (collected {datetime.now().strftime('%Y-%m-%d')}):\n\n"
        new_examples += f"```json\n{json.dumps({'AAPL': sample_data}, indent=2)}\n```\n\n"
    
    # Add string response examples
    if string_examples:
        # Find asset_profile examples specifically
        asset_profile_examples = {k: v for k, v in string_examples.items() if v["property"] == "asset_profile"}
        if asset_profile_examples:
            example = list(asset_profile_examples.values())[0]
            new_examples += f"- Unexpected for `{example['ticker']}` — string message inside dict (collected {datetime.now().strftime('%Y-%m-%d')}):\n\n"
            new_examples += f"```json\n{json.dumps(example['full_response'], indent=2)}\n```\n\n"
    
    # Add information about other properties with similar issues
    if string_examples:
        affected_properties = set(example["property"] for example in string_examples.values())
        if len(affected_properties) > 1:
            new_examples += f"- **Additional affected properties:** {', '.join(f'`{prop}`' for prop in sorted(affected_properties))}\n\n"
            new_examples += f"- **Total examples collected:** {len(string_examples)} string responses across {len(affected_properties)} properties\n\n"
    
    new_examples += f"**Test execution details:**\n"
    new_examples += f"- Collected on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    new_examples += f"- Examples saved to: `string_response_examples.json`\n"
    new_examples += f"- Detailed report: `string_response_examples_report.md`\n\n"
    
    # Replace the examples section
    updated_content = (content[:examples_start] + 
                      new_examples + 
                      content[examples_end:])
    
    # Create a backup of the original
    backup_path = f"{bug_report_path}.backup"
    with open(backup_path, "w") as f:
        f.write(content)
    
    # Write the updated content
    with open(bug_report_path, "w") as f:
        f.write(updated_content)
    
    print(f"📝 Bug report updated with collected examples")
    print(f"📁 Original backed up to: {backup_path}")

def test_quote_summary_consistency():
    """
    Test all quote summary properties for response consistency.
    
    This script identifies properties that return string error messages instead of
    structured data, which causes the inconsistency documented in the bug report.
    """
    
    # All properties that use _quote_summary
    quote_summary_properties = [
        'asset_profile',
        'calendar_events', 
        'earnings',
        'earnings_trend',
        'esg_scores',
        'financial_data',
        'index_trend',
        'industry_trend',
        'key_stats',
        'major_holders',
        'page_views',
        'price',
        'quote_type',
        'share_purchase_activity',
        'summary_detail',
        'summary_profile',
        'technical_insights'
    ]
    
    # Expanded test cases to cover a broader range of scenarios
    test_cases = [
        # Major tech stocks (should have full data)
        ("AAPL", "Apple - Major tech stock", "should_have_data"),
        ("MSFT", "Microsoft - Major tech stock", "should_have_data"),
        ("GOOGL", "Google - Major tech stock", "should_have_data"),
        ("TSLA", "Tesla - Major growth stock", "should_have_data"),
        ("NVDA", "NVIDIA - Major AI/GPU stock", "should_have_data"),
        ("META", "Meta Platforms - Social media giant", "should_have_data"),
        ("AMZN", "Amazon - E-commerce giant", "should_have_data"),
        
        # Financial stocks
        ("JPM", "JPMorgan Chase - Major bank", "should_have_data"),
        ("BAC", "Bank of America - Major bank", "should_have_data"),
        ("GS", "Goldman Sachs - Investment bank", "should_have_data"),
        ("MS", "Morgan Stanley - Investment bank", "should_have_data"),
        ("WFC", "Wells Fargo - Major bank", "should_have_data"),
        
        # Different exchanges and types
        ("BRK-B", "Berkshire Hathaway - Class B shares", "should_have_data"),
        ("SPY", "SPDR S&P 500 ETF", "should_have_data"),
        ("QQQ", "Invesco QQQ Trust ETF", "should_have_data"),
        ("IWM", "iShares Russell 2000 ETF", "should_have_data"),
        
        # International/ADR stocks
        ("BABA", "Alibaba - Chinese ADR", "should_have_data"),
        ("ASML", "ASML - European ADR", "should_have_data"),
        ("TSM", "Taiwan Semiconductor - Asian ADR", "should_have_data"),
        ("NVO", "Novo Nordisk - Danish ADR", "should_have_data"),
        ("UL", "Unilever - British ADR", "should_have_data"),
        
        # Energy sector (A range)
        ("APA", "APA Corporation - Oil & gas", "should_have_data"),
        ("AON", "Aon PLC - Insurance services", "should_have_data"),
        
        # Consumer goods (B-C range)
        ("BALL", "Ball Corporation - Packaging", "should_have_data"),
        ("BBY", "Best Buy - Electronics retail", "should_have_data"),
        ("CCL", "Carnival Corporation - Cruise lines", "should_have_data"),
        ("CL", "Colgate-Palmolive - Consumer goods", "should_have_data"),
        ("COST", "Costco - Retail warehouse", "should_have_data"),
        
        # Diverse sectors (D-F range)
        ("DD", "DuPont - Chemicals", "should_have_data"),
        ("DIS", "Disney - Entertainment", "should_have_data"),
        ("EMR", "Emerson Electric - Industrial", "should_have_data"),
        ("F", "Ford Motor Company - Automotive", "should_have_data"),
        ("FDX", "FedEx - Logistics", "should_have_data"),
        
        # Healthcare & pharma (G-J range)
        ("GE", "General Electric - Industrial conglomerate", "should_have_data"),
        ("HD", "Home Depot - Home improvement retail", "should_have_data"),
        ("IBM", "IBM - Technology services", "should_have_data"),
        ("JNJ", "Johnson & Johnson - Healthcare", "should_have_data"),
        
        # Mid-range alphabet (K-O range)
        ("KO", "Coca-Cola - Beverages", "should_have_data"),
        ("LMT", "Lockheed Martin - Defense", "should_have_data"),
        ("MMM", "3M Company - Industrial conglomerate", "should_have_data"),
        ("NKE", "Nike - Sportswear", "should_have_data"),
        ("NOC", "Northrop Grumman - Defense", "should_have_data"),
        
        # Later alphabet (P-T range)
        ("PG", "Procter & Gamble - Consumer goods", "should_have_data"),
        ("RTX", "Raytheon Technologies - Aerospace", "should_have_data"),
        ("T", "AT&T - Telecommunications", "should_have_data"),
        ("TXN", "Texas Instruments - Semiconductors", "should_have_data"),
        
        # End of alphabet (U-Z range)
        ("UNH", "UnitedHealth Group - Healthcare", "should_have_data"),
        ("V", "Visa - Payment processing", "should_have_data"),
        ("WMT", "Walmart - Retail", "should_have_data"),
        ("XOM", "Exxon Mobil - Oil & gas", "should_have_data"),
        ("YUM", "Yum! Brands - Restaurants", "should_have_data"),
        
        # Small/micro cap stocks (more likely to have issues)
        ("EAI", "Known problematic ticker", "may_have_string_errors"),
        ("ZYXI", "Small biotech company", "may_have_string_errors"),
        ("ACRX", "Small pharmaceutical", "may_have_string_errors"),
        ("BTCS", "Small blockchain company", "may_have_string_errors"),
        ("ACHR", "Archer Aviation - Small aerospace", "may_have_string_errors"),
        ("ACEL", "Accel Entertainment - Gaming", "may_have_string_errors"),
        ("EARN", "Ellington Residential - Small REIT", "may_have_string_errors"),
        ("MLI", "Mueller Industries - Small industrial", "may_have_string_errors"),
        ("NINE", "Nine Energy Service - Small energy", "may_have_string_errors"),
        ("SAFE", "Safehold Inc - Small REIT", "may_have_string_errors"),
        ("TUYA", "Tuya Inc - Small tech", "may_have_string_errors"),
        ("WEAV", "Weave Communications - Small software", "may_have_string_errors"),
        
        # Penny stocks and OTC
        ("GVSI", "OTC penny stock", "may_have_string_errors"),
        ("OZSC", "OTC energy company", "may_have_string_errors"),

        
        # Market indices
        ("^GSPC", "S&P 500 Index", "may_have_string_errors"),
        ("^DJI", "Dow Jones Industrial Average", "may_have_string_errors"),
        ("^IXIC", "NASDAQ Composite", "may_have_string_errors"),
        ("^VIX", "CBOE Volatility Index", "may_have_string_errors"),
        
        # Forex pairs
        ("EURUSD=X", "Euro/USD currency pair", "may_have_string_errors"),
        ("GBPUSD=X", "GBP/USD currency pair", "may_have_string_errors"),
        
        # Commodities
        ("GC=F", "Gold futures", "may_have_string_errors"),
        ("CL=F", "Crude oil futures", "may_have_string_errors"),
    ]
    
    print("=" * 80)
    print("YAHOOQUERY QUOTE SUMMARY CONSISTENCY TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = {
        "test_metadata": {
            "test_date": datetime.now().isoformat(),
            "total_tests": len(quote_summary_properties) * len(test_cases),
            "total_tickers": len(test_cases),
            "total_properties": len(quote_summary_properties),
            "batched_execution": False,
            "max_workers": 2,
            "individual_calls": True
        },
        "test_summary": {
            "total_properties": len(quote_summary_properties),
            "total_test_cases": len(test_cases),
            "properties_with_string_responses": [],
            "consistent_properties": [],
            "properties_with_mixed_behavior": []
        },
        "detailed_results": {}
    }
    
    # Calculate total tests for progress tracking
    total_tests = len(quote_summary_properties) * len(test_cases)
    print(f"Total property-ticker combinations to test: {total_tests}")
    print(f"Using individual API calls: {total_tests} API requests (one per property-ticker combo)")
    print(f"This ensures accurate detection of string response inconsistencies!")
    print(f"Using rate-limited execution with up to 4 threads (to avoid API limits)...")
    
    # String examples collection (thread-safe)
    string_examples = {}  # Dict for collecting string response examples
    string_examples_lock = threading.Lock()  # Lock for thread-safe access
    
    print(f"\nStarting individual property testing...")
    start_time = time.time()
    
    # Run tests using individual API calls (one call per property-ticker combo)
    all_results = []
    with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced workers to avoid rate limits with individual calls
        # Submit one test per ticker (individual property calls)
        future_to_ticker = {
            executor.submit(
                test_single_ticker_all_properties, 
                ticker, description, quote_summary_properties, (string_examples, string_examples_lock)
            ): (ticker, description)
            for ticker, description, expected in test_cases
        }
        
        # Collect results as they complete
        completed_tickers = 0
        for future in as_completed(future_to_ticker):
            ticker_results = future.result()  # This returns a list of results for all properties
            all_results.extend(ticker_results)
            completed_tickers += 1
            if completed_tickers % 5 == 0:  # Print every 5 tickers
                print(f"Progress: {completed_tickers}/{len(test_cases)} tickers completed ({completed_tickers/len(test_cases)*100:.1f}%)")
    
    execution_time = time.time() - start_time
    print(f"\n✅ Individual property testing completed in {execution_time:.2f} seconds")
    print(f"Average time per ticker: {execution_time/len(test_cases):.3f} seconds")
    print(f"Average time per property-ticker test: {execution_time/total_tests:.3f} seconds")
    
    # Add execution stats to results
    results["test_metadata"]["execution_time"] = execution_time
    results["test_metadata"]["api_calls_made"] = total_tests
    results["test_metadata"]["tests_per_second"] = total_tests / execution_time
    results["test_metadata"]["batching_enabled"] = False
    
    # Organize results by property
    for prop_name in quote_summary_properties:
        prop_results = {
            "has_string_responses": False,
            "has_dict_responses": False, 
            "test_cases": {}
        }
        
        # Filter results for this property
        prop_test_results = [r for r in all_results if r["property"] == prop_name]
        
        print(f"\nProperty: {prop_name} - {len(prop_test_results)} tests")
        
        for result in prop_test_results:
            ticker = result["ticker"]
            status = result["status"]
            
            # Copy result data (excluding ticker and property keys)
            test_case_data = {k: v for k, v in result.items() 
                            if k not in ["ticker", "property"]}
            prop_results["test_cases"][ticker] = test_case_data
            
            # Track response types
            if status == "string_response":
                prop_results["has_string_responses"] = True
                print(f"  ⚠️  {ticker}: STRING_RESPONSE")
            elif status in ["structured_error", "valid_data"]:
                prop_results["has_dict_responses"] = True
                print(f"  ✅ {ticker}: {status.upper()}")
            elif status == "exception":
                print(f"  💥 {ticker}: EXCEPTION - {result.get('error', '')[:50]}...")
            else:
                print(f"  ? {ticker}: {status.upper()}")
        
        # Categorize this property
        if prop_results["has_string_responses"] and prop_results["has_dict_responses"]:
            results["test_summary"]["properties_with_mixed_behavior"].append(prop_name)
        elif prop_results["has_string_responses"]:
            results["test_summary"]["properties_with_string_responses"].append(prop_name)
        else:
            results["test_summary"]["consistent_properties"].append(prop_name)
        
        results["detailed_results"][prop_name] = prop_results
    
    # Analyze ticker-level patterns
    ticker_analysis = analyze_ticker_patterns(results["detailed_results"])
    results["ticker_analysis"] = ticker_analysis
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    summary = results["test_summary"]
    
    print(f"Total properties tested: {summary['total_properties']}")
    print(f"Total tickers tested: {summary['total_test_cases']}")
    print(f"Total individual tests: {total_tests}")
    print(f"API calls made: {results['test_metadata']['api_calls_made']} (individual)")
    print(f"Individual calls ensure accurate string response detection")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Tests per second: {total_tests/execution_time:.1f}")
    print(f"Properties with string responses: {len(summary['properties_with_string_responses'])}")
    print(f"Properties with consistent behavior: {len(summary['consistent_properties'])}")
    print(f"Properties with mixed behavior: {len(summary['properties_with_mixed_behavior'])}")
    
    # Show ticker-level patterns
    print(f"\n📊 TICKER-LEVEL ANALYSIS:")
    print(f"Tickers causing most string responses: {ticker_analysis['most_problematic'][:5]}")
    print(f"Tickers with most consistent responses: {ticker_analysis['most_reliable'][:5]}")
    print(f"String response rate by ticker category:")
    for category, rate in ticker_analysis['category_analysis'].items():
        print(f"   {category}: {rate:.1%}")
    
    if summary["properties_with_string_responses"]:
        print(f"\n🔍 PROPERTIES WITH STRING RESPONSE ISSUES:")
        for prop in summary["properties_with_string_responses"]:
            print(f"   - {prop}")
    
    if summary["properties_with_mixed_behavior"]:
        print(f"\n⚠️  PROPERTIES WITH MIXED BEHAVIOR:")
        for prop in summary["properties_with_mixed_behavior"]:
            print(f"   - {prop}")
    
    if summary["consistent_properties"]:
        print(f"\n✅ PROPERTIES WITH CONSISTENT BEHAVIOR:")
        for prop in summary["consistent_properties"]:
            print(f"   - {prop}")
    
    # Save detailed results to file
    with open("quote_summary_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save string response examples to separate file
    if string_examples:
        with open("string_response_examples.json", "w") as f:
            json.dump(string_examples, f, indent=2)
        print(f"\n📁 String response examples saved to: string_response_examples.json")
        
        # Create a markdown report of examples for the bug report
        create_examples_report(string_examples)
    
    print(f"\n📁 Detailed results saved to: quote_summary_test_results.json")
    
    return results

def analyze_specific_issue():
    """
    Demonstrate the specific issue described in the bug report and save examples
    """
    print("\n" + "=" * 80)
    print("DEMONSTRATING THE SPECIFIC BUG FROM THE REPORT")
    print("=" * 80)
    
    bug_examples = {}
    
    for ticker in ("AAPL", "EAI"):
        print(f"\nTicker: {ticker}")
        print("-" * 40)
        
        # Add delay to avoid rate limits
        time.sleep(0.2)
        
        ticker_obj = yq.Ticker(ticker)
        asset_profile = ticker_obj.asset_profile
        
        print(f"Response type: {type(asset_profile)}")
        print(f"Keys: {list(asset_profile.keys())}")
        
        # Get the ticker-specific data
        ticker_data = asset_profile.get(ticker) or asset_profile.get(ticker.upper())
        
        print(f"Ticker data type: {type(ticker_data)}")
        
        # Save the example for the bug report
        bug_examples[ticker] = {
            "ticker": ticker,
            "response_type": type(ticker_data).__name__,
            "full_response": asset_profile,
            "ticker_data": ticker_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if isinstance(ticker_data, str):
            print(f"❌ STRING RESPONSE: {ticker_data}")
            bug_examples[ticker]["issue_type"] = "string_response"
            bug_examples[ticker]["string_message"] = ticker_data
        elif isinstance(ticker_data, dict):
            if ticker_data.get("error"):
                print(f"✅ STRUCTURED ERROR: {ticker_data}")
                bug_examples[ticker]["issue_type"] = "structured_error"
            else:
                print(f"✅ VALID DATA: {len(ticker_data)} fields")
                sample_keys = list(ticker_data.keys())[:5]
                print(f"   Sample keys: {sample_keys}")
                bug_examples[ticker]["issue_type"] = "valid_data"
                bug_examples[ticker]["field_count"] = len(ticker_data)
                bug_examples[ticker]["sample_keys"] = sample_keys
    
    # Save bug demonstration examples
    with open("bug_demonstration_examples.json", "w") as f:
        json.dump(bug_examples, f, indent=2)
    
    print(f"\n📁 Bug demonstration examples saved to: bug_demonstration_examples.json")
    
    return bug_examples

if __name__ == "__main__":
    try:
        # Run the comprehensive test
        results = test_quote_summary_consistency()
        
        # Demonstrate the specific bug and get examples
        bug_examples = analyze_specific_issue()
        
        # Update the bug report with collected examples
        if hasattr(results, 'string_examples'):
            update_bug_report_with_examples(bug_examples, results.string_examples)
        else:
            # Get string examples from the detailed results
            all_string_examples = {}
            for prop_name, prop_data in results["detailed_results"].items():
                for ticker, ticker_data in prop_data["test_cases"].items():
                    if ticker_data.get("status") == "string_response" and "full_response" in ticker_data:
                        example_key = f"{prop_name}_{ticker}"
                        all_string_examples[example_key] = {
                            "ticker": ticker,
                            "property": prop_name,
                            "string_message": ticker_data.get("message", ""),
                            "full_response": ticker_data["full_response"],
                            "timestamp": datetime.now().isoformat()
                        }
            
            if all_string_examples:
                update_bug_report_with_examples(bug_examples, all_string_examples)
        
        # Print final assessment
        print("\n" + "=" * 80)
        print("FINAL ASSESSMENT")
        print("=" * 80)
        
        problematic_count = len(results["test_summary"]["properties_with_string_responses"])
        mixed_count = len(results["test_summary"]["properties_with_mixed_behavior"])
        
        if problematic_count > 0 or mixed_count > 0:
            print(f"❌ BUG CONFIRMED: {problematic_count + mixed_count} properties have inconsistent responses")
            print("   This matches the behavior described in the bug report.")
        else:
            print("✅ BUG RESOLVED: All properties now have consistent response structures")
        
    except Exception as e:
        print(f"\n💥 TEST FAILED: {e}")
        print("This may indicate a more serious issue with the yahooquery installation.")