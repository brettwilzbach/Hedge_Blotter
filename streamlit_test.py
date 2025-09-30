import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Streamlit Test App",
    page_icon="🧪",
    layout="wide"
)

# Header
st.title("🧪 Streamlit Test Application")
st.caption("A simple test to verify Streamlit functionality")

# Sidebar
st.sidebar.header("Test Controls")
test_option = st.sidebar.selectbox(
    "Select Test Feature",
    ["Basic Elements", "Data Display", "Charts", "Input Forms", "Layouts"]
)

# Generate sample data
@st.cache_data
def generate_sample_data(rows=100):
    dates = pd.date_range(start=datetime.now() - timedelta(days=rows), periods=rows, freq='D')
    data = {
        'date': dates,
        'value': np.random.randn(rows).cumsum(),
        'category': np.random.choice(['A', 'B', 'C'], size=rows),
        'metric': np.random.randint(1, 100, size=rows)
    }
    return pd.DataFrame(data)

sample_df = generate_sample_data()

# Basic Elements Test
if test_option == "Basic Elements":
    st.header("Basic UI Elements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Text Elements")
        st.text("This is plain text")
        st.markdown("**This is bold markdown** and *this is italic*")
        st.code("print('Hello, Streamlit!')", language="python")
        st.latex(r'''
            a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} = \sum_{k=0}^{n-1} ar^k = a \frac{1-r^{n}}{1-r}
            ''')
    
    with col2:
        st.subheader("Alert Elements")
        st.info("This is an info box")
        st.success("This is a success box")
        st.warning("This is a warning box")
        st.error("This is an error box")
        
        with st.expander("Click to expand"):
            st.write("This content is hidden in an expander")
    
    st.divider()
    
    st.subheader("Progress Indicators")
    progress_bar = st.progress(0)
    for i in range(101):
        # Update progress bar
        progress_bar.progress(i)
    
    st.metric(label="Temperature", value="70 °F", delta="1.2 °F")

# Data Display Test
elif test_option == "Data Display":
    st.header("Data Display Features")
    
    st.subheader("Sample DataFrame")
    st.dataframe(sample_df, use_container_width=True)
    
    st.subheader("Table View")
    st.table(sample_df.head())
    
    st.subheader("JSON Display")
    st.json({
        "name": "Streamlit Test",
        "version": "1.0",
        "features": ["charts", "data", "widgets"],
        "config": {
            "debug": True,
            "theme": "light"
        }
    })

# Charts Test
elif test_option == "Charts":
    st.header("Chart Types")
    
    st.subheader("Line Chart")
    chart_data = sample_df[['date', 'value']].rename(columns={'value': 'Stock Price'})
    line_chart = alt.Chart(chart_data).mark_line().encode(
        x='date:T',
        y='Stock Price:Q',
        tooltip=['date:T', 'Stock Price:Q']
    ).properties(
        width=700,
        height=400,
        title='Sample Stock Price Over Time'
    )
    st.altair_chart(line_chart, use_container_width=True)
    
    st.subheader("Bar Chart")
    category_counts = sample_df['category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    bar_chart = alt.Chart(category_counts).mark_bar().encode(
        x='Category:N',
        y='Count:Q',
        color='Category:N',
        tooltip=['Category:N', 'Count:Q']
    ).properties(
        width=500,
        height=300,
        title='Category Distribution'
    )
    st.altair_chart(bar_chart, use_container_width=True)
    
    st.subheader("Scatter Plot")
    scatter_data = sample_df[['value', 'metric', 'category']].sample(50)
    scatter_chart = alt.Chart(scatter_data).mark_circle(size=60).encode(
        x='value:Q',
        y='metric:Q',
        color='category:N',
        tooltip=['value:Q', 'metric:Q', 'category:N']
    ).properties(
        width=600,
        height=400,
        title='Value vs Metric by Category'
    )
    st.altair_chart(scatter_chart, use_container_width=True)

# Input Forms Test
elif test_option == "Input Forms":
    st.header("Input Forms & Widgets")
    
    with st.form("test_form"):
        st.subheader("Sample Form")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name")
            email = st.text_input("Email")
            date = st.date_input("Date")
        
        with col2:
            category = st.selectbox("Category", ["Option A", "Option B", "Option C"])
            value = st.slider("Value", 0, 100, 50)
            files = st.file_uploader("Upload File", accept_multiple_files=True)
        
        notes = st.text_area("Notes")
        agree = st.checkbox("I agree to the terms")
        
        submitted = st.form_submit_button("Submit Form")
        
        if submitted:
            st.success("Form submitted successfully!")
            st.write({
                "Name": name,
                "Email": email,
                "Date": date,
                "Category": category,
                "Value": value,
                "Notes": notes,
                "Agreed": agree,
                "Files": [f.name for f in files] if files else []
            })
    
    st.divider()
    
    st.subheader("Other Input Widgets")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.number_input("Number Input", min_value=0, max_value=10, value=5)
        st.radio("Radio Options", ["Option 1", "Option 2", "Option 3"])
    
    with col2:
        st.multiselect("Multiselect", ["Item 1", "Item 2", "Item 3", "Item 4"])
        st.color_picker("Pick a color")
    
    with col3:
        st.time_input("Set a time")
        st.button("Click Me", help="This is a button")

# Layouts Test
elif test_option == "Layouts":
    st.header("Layout Options")
    
    st.subheader("Columns Layout")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Column 1**")
        st.info("This is the first column")
        st.metric("Value A", 123, 10.5)
    
    with col2:
        st.write("**Column 2**")
        st.warning("This is the second column")
        st.metric("Value B", 456, -5.4)
    
    with col3:
        st.write("**Column 3**")
        st.success("This is the third column")
        st.metric("Value C", 789, 0)
    
    st.divider()
    
    st.subheader("Tabs Layout")
    tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
    
    with tab1:
        st.write("**Tab 1 Content**")
        st.bar_chart(sample_df[['value']].head(10))
    
    with tab2:
        st.write("**Tab 2 Content**")
        st.line_chart(sample_df[['value']].head(20))
    
    with tab3:
        st.write("**Tab 3 Content**")
        st.dataframe(sample_df.head())
    
    st.divider()
    
    st.subheader("Expanders")
    with st.expander("Expander 1"):
        st.write("This content is hidden until you expand it")
        st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=200)
    
    with st.expander("Expander 2"):
        st.write("Another expandable section")
        st.code("""
        def hello_world():
            print("Hello, Streamlit!")
        """)

# Footer
st.divider()
st.caption("Streamlit Test App - Created for testing purposes")
