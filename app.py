import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# Set page config
st.set_page_config(
    page_title="Stock Data Analyzer",
    page_icon="📈",
    layout="wide"
)

# Function to get stock data
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_stock_data(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get historical data
        hist = stock.history(period=period)
        
        # Calculate technical indicators
        # Moving Averages
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        hist['MA200'] = hist['Close'].rolling(window=200).mean()
        
        # RSI (Relative Strength Index)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD (Moving Average Convergence Divergence)
        hist['EMA12'] = hist['Close'].ewm(span=12, adjust=False).mean()
        hist['EMA26'] = hist['Close'].ewm(span=26, adjust=False).mean()
        hist['MACD'] = hist['EMA12'] - hist['EMA26']
        hist['Signal_Line'] = hist['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        hist['Middle_Band'] = hist['Close'].rolling(window=20).mean()
        std = hist['Close'].rolling(window=20).std()
        hist['Upper_Band'] = hist['Middle_Band'] + (std * 2)
        hist['Lower_Band'] = hist['Middle_Band'] - (std * 2)
        
        return hist, info
    except Exception as e:
        st.error(f"Error retrieving data for {ticker}: {e}")
        return None, None

# Function to create interactive chart
def create_stock_chart(data, ticker):
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    ))
    
    # Add Moving Averages
    fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], mode='lines', name='MA 20', line=dict(color='blue', width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], mode='lines', name='MA 50', line=dict(color='orange', width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], mode='lines', name='MA 200', line=dict(color='green', width=1)))
    
    # Configure layout
    fig.update_layout(
        title=f'{ticker} Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=True,
        height=600,
        template='plotly_white'
    )
    
    return fig

# Function to create technical indicators chart
def create_technical_chart(data, indicator):
    fig = go.Figure()
    
    if indicator == 'RSI':
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], mode='lines', name='RSI'))
        fig.add_shape(type="line", x0=data.index[0], y0=70, x1=data.index[-1], y1=70,
                      line=dict(color="red", width=1, dash="dash"))
        fig.add_shape(type="line", x0=data.index[0], y0=30, x1=data.index[-1], y1=30,
                      line=dict(color="green", width=1, dash="dash"))
        fig.update_layout(
            title='Relative Strength Index (RSI)',
            yaxis_title='RSI',
            height=300
        )
    
    elif indicator == 'MACD':
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], mode='lines', name='MACD'))
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal_Line'], mode='lines', name='Signal Line'))
        
        # Add MACD histogram
        colors = ['green' if val >= 0 else 'red' for val in (data['MACD'] - data['Signal_Line'])]
        fig.add_trace(go.Bar(
            x=data.index, 
            y=data['MACD'] - data['Signal_Line'],
            name='Histogram',
            marker_color=colors
        ))
        
        fig.update_layout(
            title='Moving Average Convergence Divergence (MACD)',
            yaxis_title='Value',
            height=300
        )
    
    elif indicator == 'Bollinger':
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close Price'))
        fig.add_trace(go.Scatter(x=data.index, y=data['Upper_Band'], mode='lines', name='Upper Band', line=dict(width=1)))
        fig.add_trace(go.Scatter(x=data.index, y=data['Middle_Band'], mode='lines', name='Middle Band', line=dict(width=1)))
        fig.add_trace(go.Scatter(x=data.index, y=data['Lower_Band'], mode='lines', name='Lower Band', line=dict(width=1)))
        
        fig.update_layout(
            title='Bollinger Bands',
            yaxis_title='Price',
            height=300
        )
    
    return fig

# Format currency values
def format_currency(value):
    if pd.isna(value):
        return "N/A"
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:.2f}"

# Format percentage values
def format_percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"

# Main app
st.title("📈 Stock & Crypto Data Analyzer")

# User input
st.sidebar.header("Enter Symbol")
ticker_input = st.sidebar.text_input("Stock/Crypto Symbol (e.g., AAPL, MSFT, BTC-USD, ETH-USD)", "AAPL")
ticker = ticker_input.upper().strip()

# Asset type
asset_type = st.sidebar.radio("Asset Type", ["Stock", "Cryptocurrency"])

# Time period selection
period_options = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "Year to Date": "ytd",
    "1 Year": "1y",
    "5 Years": "5y",
    "Max": "max"
}
selected_period = st.sidebar.selectbox("Select Time Period", list(period_options.keys()))
period = period_options[selected_period]

# Technical indicators selection
tech_indicators = st.sidebar.multiselect(
    "Select Technical Indicators",
    ["RSI", "MACD", "Bollinger"],
    default=["RSI"]
)

# Fetch data button
button_label = "Fetch Data" if asset_type == "Cryptocurrency" else "Fetch Stock Data"
if st.sidebar.button(button_label):
    # Show loading spinner
    with st.spinner(f"Fetching data for {ticker}..."):
        # Get data
        hist_data, stock_info = get_stock_data(ticker, period)
        
        if hist_data is not None and stock_info is not None:
            # Success message
            st.sidebar.success(f"Data fetched successfully for {ticker}")
            
            # Asset info
            asset_name = stock_info.get('shortName', ticker)
            st.header(f"{asset_name} ({ticker})")
            
            # Description
            description_label = "Description" if asset_type == "Cryptocurrency" else "Company Description"
            with st.expander(description_label):
                st.write(stock_info.get('longBusinessSummary', 'No description available'))
            
            # Key metrics
            st.subheader("Key Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Current Price", format_currency(stock_info.get('currentPrice', None)))
                
            with col2:
                previous_close = stock_info.get('previousClose', None)
                current_price = stock_info.get('currentPrice', None)
                
                if previous_close is not None and current_price is not None:
                    daily_change = ((current_price - previous_close) / previous_close) * 100
                    st.metric("Daily Change", format_percent(daily_change), format_percent(daily_change))
                else:
                    st.metric("Daily Change", "N/A")
                
            with col3:
                market_cap = stock_info.get('marketCap', None)
                st.metric("Market Cap", format_currency(market_cap) if market_cap else "N/A")
                
            with col4:
                volume = stock_info.get('volume', None)
                if volume:
                    if volume >= 1e9:
                        volume_str = f"{volume/1e9:.2f}B"
                    elif volume >= 1e6:
                        volume_str = f"{volume/1e6:.2f}M"
                    else:
                        volume_str = f"{volume}"
                    st.metric("Volume", volume_str)
                else:
                    st.metric("Volume", "N/A")
            
            # Additional metrics
            col1, col2, col3, col4 = st.columns(4)
            
            if asset_type == "Cryptocurrency":
                with col1:
                    market_cap_rank = stock_info.get('marketCapRank', None)
                    st.metric("Market Cap Rank", f"#{market_cap_rank}" if market_cap_rank else "N/A")
                
                with col2:
                    circulating_supply = stock_info.get('circulatingSupply', None)
                    if circulating_supply:
                        if circulating_supply >= 1e9:
                            supply_str = f"{circulating_supply/1e9:.2f}B"
                        elif circulating_supply >= 1e6:
                            supply_str = f"{circulating_supply/1e6:.2f}M"
                        else:
                            supply_str = f"{circulating_supply:.0f}"
                        st.metric("Circulating Supply", supply_str)
                    else:
                        st.metric("Circulating Supply", "N/A")
                
                with col3:
                    total_supply = stock_info.get('totalSupply', None)
                    if total_supply:
                        if total_supply >= 1e9:
                            supply_str = f"{total_supply/1e9:.2f}B"
                        elif total_supply >= 1e6:
                            supply_str = f"{total_supply/1e6:.2f}M"
                        else:
                            supply_str = f"{total_supply:.0f}"
                        st.metric("Total Supply", supply_str)
                    else:
                        st.metric("Total Supply", "N/A")
                
                with col4:
                    max_supply = stock_info.get('maxSupply', None)
                    if max_supply:
                        if max_supply >= 1e9:
                            supply_str = f"{max_supply/1e9:.2f}B"
                        elif max_supply >= 1e6:
                            supply_str = f"{max_supply/1e6:.2f}M"
                        else:
                            supply_str = f"{max_supply:.0f}"
                        st.metric("Max Supply", supply_str)
                    else:
                        st.metric("Max Supply", "N/A")
            else:
                with col1:
                    pe_ratio = stock_info.get('trailingPE', None)
                    st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
                    
                with col2:
                    dividend_yield = stock_info.get('dividendYield', None)
                    if dividend_yield:
                        dividend_yield *= 100  # Convert to percentage
                    st.metric("Dividend Yield", format_percent(dividend_yield) if dividend_yield else "N/A")
                    
                with col3:
                    eps = stock_info.get('trailingEps', None)
                    st.metric("EPS (TTM)", format_currency(eps) if eps else "N/A")
                    
                with col4:
                    target_price = stock_info.get('targetMeanPrice', None)
                    st.metric("Target Price", format_currency(target_price) if target_price else "N/A")
            
            # Price chart
            st.subheader("Price History")
            price_chart = create_stock_chart(hist_data, ticker)
            st.plotly_chart(price_chart, use_container_width=True)
            
            # Technical indicators
            if tech_indicators:
                st.subheader("Technical Indicators")
                for indicator in tech_indicators:
                    tech_chart = create_technical_chart(hist_data, indicator)
                    st.plotly_chart(tech_chart, use_container_width=True)
            
            # Data table
            st.subheader("Historical Data")
            
            # Prepare data table
            table_data = hist_data.copy()
            # Format columns to 2 decimal places
            for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'MA20', 'MA50', 'MA200', 'RSI', 'MACD', 'Signal_Line']:
                if col in table_data.columns:
                    if col == 'Volume':
                        # Format volume as integers
                        table_data[col] = table_data[col].astype(int)
                    else:
                        # Format prices with 2 decimal places
                        table_data[col] = table_data[col].round(2)
            
            # Reset index to make Date a column
            table_data = table_data.reset_index()
            
            # Convert Date to string format
            table_data['Date'] = table_data['Date'].dt.strftime('%Y-%m-%d')
            
            # Display table
            st.dataframe(table_data, use_container_width=True)
            
            # Download button for CSV
            csv = table_data.to_csv(index=False)
            file_prefix = "crypto" if asset_type == "Cryptocurrency" else "stock"
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{ticker}_{file_prefix}_data.csv",
                mime="text/csv",
            )
        else:
            asset_type_label = "cryptocurrency" if asset_type == "Cryptocurrency" else "stock"
            st.error(f"Could not fetch data for {ticker}. Please check the {asset_type_label} symbol and try again.")

# Initial instructions
if "ticker_input" not in locals() or not ticker_input:
    st.info("👈 Enter a stock or cryptocurrency symbol in the sidebar and click 'Fetch Data' to begin analysis.")
    
# Footer
st.markdown("---")
st.markdown("Data provided by Yahoo Finance. Powered by Streamlit.")
