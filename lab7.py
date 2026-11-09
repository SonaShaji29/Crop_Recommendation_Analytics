import io
import traceback

import pandas as pd
import plotly.express as px
import streamlit as st
from packaging.version import Version

# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Crop Recommendation Analytics",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Newer Streamlit uses width="stretch"; older versions use
# use_container_width=True. Pick whichever this install supports.
try:
    if Version(st.__version__) >= Version("1.50.0"):
        WIDTH = {"width": "stretch"}
    else:
        WIDTH = {"use_container_width": True}
except Exception:
    WIDTH = {"use_container_width": True}

# =====================================================
# 2. CUSTOM CSS
# =====================================================

st.markdown("""
<style>
    .stApp {
        background-color: #f7faf7;
    }

    h1 {
        color: #176b3a;
    }

    h2, h3 {
        color: #247447;
    }

    [data-testid="stMetric"] {
        background-color: #e8f5e9;
        border: 1px solid #c8e6c9;
        padding: 16px;
        border-radius: 12px;
    }

    .main-title {
        color: #176b3a;
        font-size: 35px;
        font-weight: bold;
    }

    .subtitle {
        color: #526b58;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 3. APPLICATION TITLE
# =====================================================

st.markdown(
    '<p class="main-title">🌱 Crop Recommendation & '
    'Management Analytics</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="subtitle">Explore agricultural data, '
    'soil nutrients and environmental conditions '
    'through interactive visualizations.</p>',
    unsafe_allow_html=True
)

st.divider()

# =====================================================
# 4. DATASET LOADING
# =====================================================

DATA_FILE = "Crop_recommendation.csv"


@st.cache_data
def load_local_data():
    return pd.read_csv(DATA_FILE)


@st.cache_data
def load_uploaded_data(file_bytes):
    return pd.read_csv(io.BytesIO(file_bytes))


st.sidebar.title("🌾 Data Source")

uploaded_file = st.sidebar.file_uploader(
    "Upload Crop Dataset (CSV)",
    type=["csv"]
)

try:
    if uploaded_file is not None:
        df = load_uploaded_data(uploaded_file.getvalue())
    else:
        df = load_local_data()

except FileNotFoundError:
    st.error(
        "Dataset not found! Place Crop_recommendation.csv "
        "in the same folder as app.py or upload it using "
        "the sidebar."
    )
    st.stop()

except Exception as e:
    st.error(f"Unable to load dataset: {e}")
    st.stop()

# =====================================================
# 5. DATA VALIDATION AND CLEANING
# =====================================================

required_columns = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
    "label"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(
        f"Dataset is missing required columns: "
        f"{missing_columns}"
    )
    st.stop()

df = df[required_columns].copy()

# Convert numerical columns into numeric values
numeric_columns = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove missing and invalid observations first
df = df.dropna(subset=required_columns).copy()

# Clean crop names as plain Python strings
df["label"] = df["label"].astype(str).str.strip()
df = df[df["label"] != ""].copy()

if df.empty:
    st.error("No valid records found in the dataset.")
    st.stop()

# =====================================================
# 6. SIDEBAR FILTERS
# =====================================================

st.sidebar.divider()

st.sidebar.header("🔍 Explore & Filter Data")

crop_options = sorted(df["label"].unique().tolist())

selected_crops = st.sidebar.multiselect(
    "Select Crop Categories",
    options=crop_options,
    default=crop_options
)


def create_range_filter(column, title):
    minimum = float(df[column].min())
    maximum = float(df[column].max())

    # A slider needs min < max
    if minimum == maximum:
        st.sidebar.caption(f"{title}: all values are {minimum}")
        return (minimum, maximum)

    return st.sidebar.slider(
        title,
        min_value=minimum,
        max_value=maximum,
        value=(minimum, maximum),
        help=f"Filter data by {title.lower()}."
    )


temp_range = create_range_filter("temperature", "Temperature (°C)")
rain_range = create_range_filter("rainfall", "Rainfall (mm)")
ph_range = create_range_filter("ph", "Soil pH")
humidity_range = create_range_filter("humidity", "Humidity (%)")

st.sidebar.divider()

st.sidebar.caption(
    "Select different crops and adjust the sliders "
    "to explore agricultural patterns."
)

# =====================================================
# 7. FILTER THE DATASET
# =====================================================

filtered_df = df[
    (df["label"].isin(selected_crops)) &
    (df["temperature"].between(*temp_range)) &
    (df["rainfall"].between(*rain_range)) &
    (df["ph"].between(*ph_range)) &
    (df["humidity"].between(*humidity_range))
].copy()


def safe_run(render_function):
    """Run one tab's code; show any error inside that tab only."""
    try:
        render_function()
    except Exception as e:
        st.error(f"This tab hit an error: {e}")
        st.code(traceback.format_exc())


# =====================================================
# 8. TAB CONTENT
# =====================================================

def render_dashboard():

    st.header("📈 Agricultural Dashboard")

    st.write(
        "Key Performance Indicators based on "
        "the currently selected filters."
    )

    if filtered_df.empty:
        st.warning(
            "No records match your filters. "
            "Please change the sidebar selections."
        )
        return

    total_records = len(filtered_df)
    total_crops = filtered_df["label"].nunique()
    total_rainfall = filtered_df["rainfall"].sum()
    avg_rainfall = filtered_df["rainfall"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Records", f"{total_records:,}")
    col2.metric("Crop Categories", f"{total_crops}")
    col3.metric("Total Rainfall", f"{total_rainfall:,.2f} mm")
    col4.metric("Average Rainfall", f"{avg_rainfall:.2f} mm")

    # NPK SUM AND AVERAGE
    st.subheader("🌿 Soil Nutrient Analysis")

    nutrient_columns = st.columns(3)

    for i, nutrient in enumerate(["N", "P", "K"]):

        total_value = filtered_df[nutrient].sum()
        average_value = filtered_df[nutrient].mean()

        with nutrient_columns[i]:
            st.metric(f"Total {nutrient}", f"{total_value:,.2f}")
            st.metric(f"Average {nutrient}", f"{average_value:.2f}")

    st.divider()

    # CROP DISTRIBUTION
    st.subheader("Crop-wise Record Distribution")

    crop_counts = (
        filtered_df.groupby("label")
        .size()
        .reset_index(name="Records")
        .sort_values("Records", ascending=False)
    )

    fig = px.bar(
        crop_counts,
        x="label",
        y="Records",
        color="label",
        text="Records",
        title="Number of Observations for Each Crop",
        labels={
            "label": "Crop Category",
            "Records": "Number of Records"
        }
    )

    fig.update_layout(xaxis_tickangle=-45, showlegend=False)

    st.plotly_chart(fig, **WIDTH)

    st.caption(
        "This chart displays the number of observations "
        "available for each selected crop."
    )


def render_dataset_overview():

    st.header("📋 Dataset Overview")

    if filtered_df.empty:
        st.warning("No records available for the selected filters.")
        return

    # DATASET PREVIEW
    st.subheader("Dataset Preview")

    st.write(f"Displaying {len(filtered_df)} filtered records.")

    st.dataframe(filtered_df, height=300, **WIDTH)

    # STATISTICAL SUMMARY
    st.subheader("Statistical Summary")

    summary = filtered_df[numeric_columns].describe()

    st.dataframe(summary, **WIDTH)

    # GROUP BY ANALYSIS
    st.subheader("Crop-wise Statistical Analysis")

    crop_summary = (
        filtered_df.groupby("label")
        .agg(
            Total_Records=("label", "count"),
            Average_N=("N", "mean"),
            Average_P=("P", "mean"),
            Average_K=("K", "mean"),
            Average_Temperature=("temperature", "mean"),
            Average_Humidity=("humidity", "mean"),
            Average_Rainfall=("rainfall", "mean"),
            Average_pH=("ph", "mean")
        )
        .round(2)
        .reset_index()
    )

    st.dataframe(crop_summary, **WIDTH)

    # EXPANDER
    with st.expander("🔎 View Additional Dataset Information"):

        st.write("Original dataset shape:", df.shape)
        st.write("Filtered dataset shape:", filtered_df.shape)
        st.write("Dataset columns:", list(df.columns))

        st.write("Data types:")
        st.write(df.dtypes.astype(str))

        st.write("Missing values in cleaned dataset:")
        st.write(df.isnull().sum())

    # DOWNLOAD OPTION
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Filtered Dataset",
        data=csv_data,
        file_name="filtered_crop_dataset.csv",
        mime="text/csv"
    )


def render_visualizations():

    st.header("📊 Data Visualization and Analysis")

    if filtered_df.empty:
        st.warning("No data available. Please adjust the sidebar filters.")
        return

    # ---------------- BAR CHART ----------------
    st.subheader("1. Bar Chart - Crop Distribution")

    bar_data = (
        filtered_df.groupby("label")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    fig1 = px.bar(
        bar_data,
        x="label",
        y="Count",
        color="label",
        text="Count",
        title="Distribution of Different Crop Categories",
        labels={
            "label": "Crop Name",
            "Count": "Number of Observations"
        }
    )

    fig1.update_layout(xaxis_tickangle=-45, showlegend=False)

    st.plotly_chart(fig1, **WIDTH)

    st.info(
        "Interpretation: The bar chart compares the "
        "number of records belonging to different crops. "
        "Higher bars represent more observations."
    )

    st.divider()

    # ---------------- LINE CHART ----------------
    st.subheader("2. Line Chart - Average Rainfall")

    line_data = (
        filtered_df.groupby("label")["rainfall"]
        .mean()
        .reset_index()
        .sort_values("rainfall")
    )

    fig2 = px.line(
        line_data,
        x="label",
        y="rainfall",
        markers=True,
        title="Average Rainfall Across Crop Categories",
        labels={
            "label": "Crop Category",
            "rainfall": "Average Rainfall (mm)"
        }
    )

    fig2.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig2, **WIDTH)

    st.info(
        "Interpretation: This line chart compares the "
        "average rainfall values across crop categories. "
        "It helps identify differences in rainfall "
        "requirements represented in the dataset."
    )

    st.divider()

    # ---------------- SCATTER PLOT ----------------
    st.subheader("3. Scatter Plot - Variable Relationship")

    col1, col2 = st.columns(2)

    with col1:
        x_axis = st.selectbox(
            "Select X-axis variable",
            numeric_columns,
            index=numeric_columns.index("rainfall"),
            key="scatter_x"
        )

    with col2:
        y_axis = st.selectbox(
            "Select Y-axis variable",
            numeric_columns,
            index=numeric_columns.index("humidity"),
            key="scatter_y"
        )

    if x_axis == y_axis:
        st.warning("Please select two different numerical variables.")
    else:
        fig3 = px.scatter(
            filtered_df,
            x=x_axis,
            y=y_axis,
            color="label",
            title=f"Relationship Between {x_axis} and {y_axis}",
            labels={
                x_axis: x_axis.capitalize(),
                y_axis: y_axis.capitalize()
            },
            hover_data=["label"],
            opacity=0.7
        )

        st.plotly_chart(fig3, **WIDTH)

        st.info(
            "Interpretation: The scatter plot shows how "
            "two numerical variables are related. Different "
            "colours represent different crop categories. "
            "It can help identify clusters and outliers."
        )


def render_insights():

    st.header("💡 Agricultural Insights")

    if filtered_df.empty:
        st.warning("No records available. Change the selected filters.")
        return

    # CROP DISTRIBUTION INSIGHTS
    st.subheader("Most Frequently Represented Crop")

    crop_counts = filtered_df["label"].value_counts()
    most_common_crop = crop_counts.idxmax()

    st.success(
        f"{most_common_crop} has the highest number "
        f"of observations in the filtered dataset "
        f"({crop_counts.max()} records)."
    )

    # ENVIRONMENTAL ANALYSIS
    st.subheader("Environmental Conditions")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Average Temperature",
            f"{filtered_df['temperature'].mean():.2f} °C"
        )
        st.metric(
            "Average Humidity",
            f"{filtered_df['humidity'].mean():.2f} %"
        )

    with col2:
        st.metric(
            "Average Soil pH",
            f"{filtered_df['ph'].mean():.2f}"
        )
        st.metric(
            "Average Rainfall",
            f"{filtered_df['rainfall'].mean():.2f} mm"
        )

    st.divider()

    # NUTRIENT COMPARISON
    st.subheader("Crop-wise Nutrient Requirements")

    nutrient_data = (
        filtered_df.groupby("label")[["N", "P", "K"]]
        .mean()
        .round(2)
        .reset_index()
    )

    nutrient_melted = nutrient_data.melt(
        id_vars="label",
        var_name="Nutrient",
        value_name="Average Value"
    )

    fig4 = px.bar(
        nutrient_melted,
        x="label",
        y="Average Value",
        color="Nutrient",
        barmode="group",
        title="Average NPK Values for Different Crops",
        labels={
            "label": "Crop Category",
            "Average Value": "Average Nutrient Value"
        }
    )

    fig4.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig4, **WIDTH)

    # ADDITIONAL OBSERVATIONS
    with st.expander("📖 Detailed Agricultural Observations"):

        st.write(
            "**1. Nitrogen:** Nitrogen is important "
            "for plant growth and leaf development."
        )
        st.write(
            "**2. Phosphorus:** Phosphorus supports "
            "root development and energy transfer."
        )
        st.write(
            "**3. Potassium:** Potassium helps plants "
            "regulate water and supports overall growth."
        )
        st.write(
            "**4. Temperature:** Temperature influences "
            "plant growth and crop suitability."
        )
        st.write(
            "**5. Humidity:** Humidity affects plant "
            "water loss and environmental conditions."
        )
        st.write(
            "**6. Soil pH:** Soil pH influences nutrient "
            "availability to plants."
        )
        st.write(
            "**7. Rainfall:** Different crops have "
            "different water requirements."
        )

    st.warning(
        "Note: These are descriptive observations from "
        "the dataset. They are not guaranteed crop "
        "recommendations or substitutes for local "
        "agricultural advice."
    )


# =====================================================
# 9. NAVIGATION TABS
# =====================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Dashboard",
    "📋 Dataset Overview",
    "📊 Visualizations",
    "💡 Agricultural Insights"
])

with tab1:
    safe_run(render_dashboard)

with tab2:
    safe_run(render_dataset_overview)

with tab3:
    safe_run(render_visualizations)

with tab4:
    safe_run(render_insights)

# =====================================================
# 10. FOOTER
# =====================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:gray;">
        🌱 Crop Recommendation & Management Analytics
        <br>
        Developed using Python, Streamlit, Pandas and Plotly
        <br>
        Q8 - Interactive Data Analytics Dashboard
    </div>
    """,
    unsafe_allow_html=True
)