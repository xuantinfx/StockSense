import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import re

# Set page configuration
st.set_page_config(
    page_title="Stock Data Analyzer",
    page_icon="📈",
    layout="wide"
)

# Function to validate stock symbol
def is_valid_stock_symbol(symbol):
    # Basic validation: alphanumeric with optional dots or hyphens
    pattern = re.compile(r'^[A-Za-z0-9\.\-]+$')
    return bool(pattern.match(symbol))

# Function to get stock data
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def get_stock_data(symbol, period="1y"):
    try:
        # Get stock info
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Get historical data
        hist = stock.history(period=period)
        
        if hist.empty:
            return None, None, f"No data available for {symbol}"
        
        return stock, hist, None
    except Exception as e:
        return None, None, f"Error retrieving data for {symbol}: {str(e)}"

# Function to calculate technical indicators
def calculate_technical_indicators(df):
    # Calculate 20-day and 50-day moving averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    
    # Calculate Relative Strength Index (RSI)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Calculate MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df

# Function to format currency
def format_currency(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"

# Function to format large numbers
def format_number(value):
    if value is None or pd.isna(value):
        return "N/A"
    
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value/1_000:.2f}K"
    else:
        return f"{value:.2f}"

# Function to format percentage
def format_percentage(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"

# App title and description
st.title("📈 Stock Data Analyzer")
st.markdown("Retrieve and analyze stock data from Yahoo Finance")

# Input for stock symbol
col1, col2 = st.columns([3, 1])
with col1:
    symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, MSFT, GOOGL)", "AAPL").upper()
with col2:
    period = st.selectbox(
        "Select Time Period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        index=3
    )

# Validate and fetch data only when a valid symbol is entered
if symbol:
    if not is_valid_stock_symbol(symbol):
        st.error("Invalid stock symbol. Please enter a valid symbol.")
    else:
        with st.spinner(f"Loading data for {symbol}..."):
            stock, hist_data, error = get_stock_data(symbol, period)
            
            if error:
                st.error(error)
            elif stock and hist_data is not None:
                # Get company info
                info = stock.info
                
                # Display company header
                col1, col2 = st.columns([3, 1])
                with col1:
                    company_name = info.get('longName', symbol)
                    st.header(f"{company_name} ({symbol})")
                    exchange = info.get('exchange', 'N/A')
                    sector = info.get('sector', 'N/A')
                    st.markdown(f"**Exchange:** {exchange} | **Sector:** {sector}")
                
                with col2:
                    # Current price and daily change
                    if not hist_data.empty:
                        current_price = hist_data['Close'].iloc[-1]
                        prev_close = info.get('previousClose', hist_data['Close'].iloc[-2] if len(hist_data) > 1 else current_price)
                        price_change = current_price - prev_close
                        price_change_percent = (price_change / prev_close) * 100 if prev_close else 0
                        
                        price_color = "green" if price_change >= 0 else "red"
                        change_icon = "▲" if price_change >= 0 else "▼"
                        
                        st.markdown(f"<h2 style='margin-bottom:0px'>{format_currency(current_price)}</h2>", unsafe_allow_html=True)
                        st.markdown(
                            f"<p style='color:{price_color};font-size:1.2rem;margin-top:0px'>{change_icon} {format_currency(abs(price_change))} ({price_change_percent:.2f}%)</p>",
                            unsafe_allow_html=True
                        )
                
                # Key metrics
                st.subheader("Key Financial Metrics")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    market_cap = info.get('marketCap', None)
                    st.metric("Market Cap", format_number(market_cap))
                    
                    volume = info.get('volume', None)
                    st.metric("Volume", format_number(volume))
                
                with col2:
                    pe_ratio = info.get('trailingPE', None)
                    st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio and not pd.isna(pe_ratio) else "N/A")
                    
                    eps = info.get('trailingEps', None)
                    st.metric("EPS", format_currency(eps) if eps else "N/A")
                
                with col3:
                    dividend_yield = info.get('dividendYield', None)
                    if dividend_yield and not pd.isna(dividend_yield):
                        dividend_yield = dividend_yield * 100  # Convert to percentage
                    st.metric("Dividend Yield", format_percentage(dividend_yield) if dividend_yield else "N/A")
                    
                    beta = info.get('beta', None)
                    st.metric("Beta", f"{beta:.2f}" if beta and not pd.isna(beta) else "N/A")
                
                with col4:
                    fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
                    st.metric("52 Week High", format_currency(fifty_two_week_high))
                    
                    fifty_two_week_low = info.get('fiftyTwoWeekLow', None)
                    st.metric("52 Week Low", format_currency(fifty_two_week_low))
                
                # Calculate technical indicators
                if not hist_data.empty:
                    tech_data = calculate_technical_indicators(hist_data.copy())
                    
                    # Interactive Price Chart
                    st.subheader("Price History and Technical Indicators")
                    
                    # Chart type and indicator selection
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        chart_type = st.selectbox(
                            "Chart Type",
                            options=["Line", "Candlestick"],
                            index=0
                        )
                    
                    with col2:
                        indicators = st.multiselect(
                            "Technical Indicators",
                            options=["Moving Averages", "RSI", "MACD"],
                            default=["Moving Averages"]
                        )
                    
                    # Create figure
                    fig = go.Figure()
                    
                    if chart_type == "Line":
                        fig.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["Close"],
                                mode="lines",
                                name="Close Price",
                                line=dict(color="#1f77b4", width=2)
                            )
                        )
                    else:  # Candlestick
                        fig.add_trace(
                            go.Candlestick(
                                x=tech_data.index,
                                open=tech_data["Open"],
                                high=tech_data["High"],
                                low=tech_data["Low"],
                                close=tech_data["Close"],
                                name="Price"
                            )
                        )
                    
                    # Add technical indicators
                    if "Moving Averages" in indicators:
                        fig.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["MA20"],
                                mode="lines",
                                name="20-day MA",
                                line=dict(color="orange", width=1.5)
                            )
                        )
                        fig.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["MA50"],
                                mode="lines",
                                name="50-day MA",
                                line=dict(color="red", width=1.5)
                            )
                        )
                    
                    # Configure layout
                    fig.update_layout(
                        title=f"{symbol} Price History",
                        xaxis_title="Date",
                        yaxis_title="Price (USD)",
                        hovermode="x unified",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    # Display main chart
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display additional indicators in separate charts if selected
                    if "RSI" in indicators:
                        # RSI Chart
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["RSI"],
                                mode="lines",
                                name="RSI",
                                line=dict(color="purple", width=1.5)
                            )
                        )
                        
                        # Add overbought/oversold lines
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                        
                        fig_rsi.update_layout(
                            title="Relative Strength Index (RSI)",
                            xaxis_title="Date",
                            yaxis_title="RSI",
                            yaxis=dict(range=[0, 100])
                        )
                        
                        st.plotly_chart(fig_rsi, use_container_width=True)
                    
                    if "MACD" in indicators:
                        # MACD Chart
                        fig_macd = go.Figure()
                        fig_macd.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["MACD"],
                                mode="lines",
                                name="MACD",
                                line=dict(color="blue", width=1.5)
                            )
                        )
                        fig_macd.add_trace(
                            go.Scatter(
                                x=tech_data.index,
                                y=tech_data["Signal"],
                                mode="lines",
                                name="Signal",
                                line=dict(color="red", width=1.5)
                            )
                        )
                        
                        # Add MACD histogram
                        fig_macd.add_trace(
                            go.Bar(
                                x=tech_data.index,
                                y=tech_data["MACD"] - tech_data["Signal"],
                                name="Histogram",
                                marker_color=np.where(
                                    tech_data["MACD"] - tech_data["Signal"] >= 0,
                                    "green",
                                    "red"
                                )
                            )
                        )
                        
                        fig_macd.update_layout(
                            title="Moving Average Convergence Divergence (MACD)",
                            xaxis_title="Date",
                            yaxis_title="MACD"
                        )
                        
                        st.plotly_chart(fig_macd, use_container_width=True)
                    
                    # Historical Data Table
                    st.subheader("Historical Data")
                    
                    # Prepare data for display
                    display_data = hist_data.copy()
                    display_data = display_data.sort_index(ascending=False)  # Show most recent first
                    display_data.index = display_data.index.strftime('%Y-%m-%d')
                    display_data = display_data.round(2)
                    
                    # Show the table
                    st.dataframe(display_data, use_container_width=True)
                    
                    # Download button for CSV
                    csv = display_data.to_csv()
                    st.download_button(
                        label="Download data as CSV",
                        data=csv,
                        file_name=f"{symbol}_historical_data.csv",
                        mime="text/csv",
                    )
                    
                    # Summary and description
                    st.subheader("Company Summary")
                    business_summary = info.get('longBusinessSummary', 'No business summary available.')
                    st.write(business_summary)
            else:
                st.error(f"No data available for {symbol}")

# Footer
st.markdown("---")
st.markdown("Data provided by Yahoo Finance through yfinance")
