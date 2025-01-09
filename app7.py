import streamlit as st
import requests
import datetime
from dotenv import load_dotenv
load_dotenv(override=True)
#from langchain.agents import initialize_agent, Tool
from langchain_core.tools import initialize_agent, Tool
from langchain.llms import OpenAI  # Replace with your preferred LLM
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import yfinance as yf  # Import yahoo_fin for Yahoo Finance data

## call the gemini models
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash",
                             verbose=True,
                             temperature=0.5,
                             google_api_key=os.getenv("GOOGLE_API_KEY"))

# Google Custom Search API endpoint
GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

# Your Google API key and Custom Search Engine ID (CSE ID)
API_KEY = "AIzaSyDdpotx35hkI77KEeFkIS4jncgDnhgThBg"
CSE_ID = "8445a0f9b645945cf"

def get_ticker(user_input):
    yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    params = {"q": user_input, "quotes_count": 1, "country": "United States"}

    try:
        res = requests.get(url=yfinance, params=params, headers={'User-Agent': user_agent})
        res.raise_for_status()  # Raise an exception for HTTP errors
        data = res.json()

        if 'quotes' in data and len(data['quotes']) > 0:
            company_code = data['quotes'][0]['symbol']
            return company_code
        else:
            return None  # In case no results found
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"


def get_balance_sheet(ticker):
    try:
        # Fetch the data using yfinance
        stock = yf.Ticker(ticker)
        balance_sheet = stock.balance_sheet  # Fetch balance sheet data
        income_statement = stock.financials
        #info = stock.info
        fin_data = {
            'balance sheet': balance_sheet,
            'income_statement': income_statement
        }

        if balance_sheet.empty:
            return "Balance sheet data is not available for this ticker."
        else:
            return fin_data
    except Exception as e:
        return f"Error retrieving balance sheet: {str(e)}"

# Function to get news articles within the last 3 months
def get_recent_news(query, API_KEY, CSE_ID, num_results=10):
    params = {
        'q': f"{query} site:news.google.com",  # Adding the site restriction for Google News
        'key': API_KEY,  # Google API key
        'cx': CSE_ID,  # Custom Search Engine ID
        'num': num_results,  # Number of results to fetch
        'dateRestrict': 'y[2]',  # Restrict results to the last year (approximately)
    }

    try:
        response = requests.get(GOOGLE_SEARCH_API_URL, params=params)
        response.raise_for_status()
        results = response.json()

        search_results = []
        if 'items' in results:
            for item in results['items']:
                search_results.append({
                    'title': item['title'],
                    'link': item['link'],
                    'snippet': item['snippet'],
                    'date': item.get('pagemap', {}).get('metatags', [{}])[0].get('date', 'N/A')
                })
        return search_results

    except requests.exceptions.RequestException as e:
        st.error(f"Error during search: {e}")
        return []

# Function to fetch financial data from Yahoo Finance


# Define agent prompts
investment_decision_prompt = """
Read the provided news articles about the company. 

Based on the information in the articles and financial data provided, determine and suggest the overall sentiment about the company from the news articles and 
analyse the following factors to decide whether investment should be made in the company or not. Suggest your decision to the user in output.
Also, pass the financial data from last 5 years in a tabular form to "Investment Decision". Also consider the following factors while taking investment decision:
1. Company has been investing in R&D, or acquiring new business, or is in organic growth phase or declining phase.
2. Compare financial numbers and ratios with competitors to decide if the company is doing better as compared to competitors.
3. Determine whether overall sentiments regarding the company from the new articles are positive or negative.
4. Consider the financial data of the company:
   - Live stock price: {live_price}
   - Market Cap: {market_cap}
   - P/E Ratio: {pe_ratio}

Articles:
{articles}

Investment Decision: 
"""

# Define a simple tool class
class SimpleTool(Tool):
    def _run(self, query: str):
        return query  # Just return the query for now

    def _arun(self, query: str):
        return query  # This can be asynchronous; for now, just return the query

# Initialize agent with a simple tool
investment_decision_agent = initialize_agent(
    tools=[SimpleTool(name="simple_tool", func=lambda x: x, description="Simple tool for testing")],
    agent_type="zero-shot-react-description",
    llm=llm,
    verbose=True,
    handle_parsing_errors=True
)

def main():
    st.title("Investment Analysis App")

    user_input = st.text_input("Enter company name or ISIN code:")

    if user_input:
        # Get news articles
        news_articles = get_recent_news(user_input, API_KEY, CSE_ID)

        # Get Yahoo Finance data
        company_code = get_ticker(user_input)
        fin_data = get_balance_sheet(company_code)

        # Make investment decision
        if news_articles and fin_data:
            # Combine company name and articles into a single input for the agent
            articles_text = "\n\n".join(
                [f"Title: {article['title']}\nSnippet: {article['snippet']}\nLink: {article['link']}" for article in news_articles])

            # Format the input as a single string
            input_text = f"Company: {user_input}\nArticles:\n{articles_text}\n\n" \
                         f"Financial Data:\n" \
                         f"Live Stock Price: {fin_data}\n"

            # Run the agent with the formatted input
            investment_decision = investment_decision_agent.run({"input": input_text})

            st.write(
                f"Investment Decision: {investment_decision} \n" \
                f"Financial Data:\n" \
                "(Disclaimer: This is not financial advice. Please consult a professional before making any investment decisions.)")
        else:
            st.write(f"No relevant news articles or financial data found for {user_input}.")

if __name__ == "__main__":
    main()
