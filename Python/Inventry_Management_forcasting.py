import pandas as pd
from prophet import Prophet

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv(r"c:\Users\esvxxxi\Downloads\inventory-analytics-demand-forecasting\final_inventory_dataset.csv")

# Convert data types
df['sale_date'] = pd.to_datetime(df['sale_date'])
df['StockCode'] = df['StockCode'].astype(str).str.strip()   # 🔥 FIX (IMPORTANT)

# -----------------------------
# BASIC VALIDATION
# -----------------------------
if 'daily_units_sold' not in df.columns:
    raise ValueError("❌ daily_units_sold column missing!")

# Remove invalid data
df = df[df['daily_units_sold'] >= 0]
df = df.dropna(subset=['sale_date', 'daily_units_sold'])

# -----------------------------
# SKU FILTERING (TOP SKUs ONLY)
# -----------------------------
active_skus = (
    df.groupby('StockCode')['daily_units_sold']
    .sum()
    .nlargest(30)   # 🔥 LIMIT
    .index
)

df = df[df['StockCode'].isin(active_skus)]

print(f"✅ Total SKUs after filtering: {len(active_skus)}")

# -----------------------------
# FORECAST LOOP
# -----------------------------
final_list = []

for sku in active_skus:

    sku_df = df[df['StockCode'] == sku].copy()

    # Skip small data
    if len(sku_df) < 10:
        continue

    # -----------------------------
    # PREPARE DATA
    # -----------------------------
    sku_df = sku_df[['sale_date', 'daily_units_sold']]
    sku_df.columns = ['ds', 'y']

    # -----------------------------
    # WEEKLY AGGREGATION
    # -----------------------------
    sku_df = sku_df.set_index('ds').resample('W').sum().reset_index()

    # Fill missing values
    sku_df['y'] = sku_df['y'].fillna(0)

    # -----------------------------
    # SMOOTHING
    # -----------------------------
    sku_df['y'] = sku_df['y'].rolling(2, min_periods=1).mean()

    # -----------------------------
    # OUTLIER HANDLING
    # -----------------------------
    upper_limit = sku_df['y'].quantile(0.95)
    sku_df['y'] = sku_df['y'].clip(upper=upper_limit)

    # -----------------------------
    # REMOVE FLAT SERIES
    # -----------------------------
    if sku_df['y'].sum() == 0:
        continue

    # -----------------------------
    # MODEL TRAINING
    # -----------------------------
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False
    )

    model.fit(sku_df)

    # -----------------------------
    # FORECAST
    # -----------------------------
    future = model.make_future_dataframe(periods=30, freq='W')
    forecast = model.predict(future)

    # -----------------------------
    # ACTUAL DATA
    # -----------------------------
    actual_df = sku_df.copy()
    actual_df['type'] = 'Actual'

    last_actual_date = sku_df['ds'].max()

    # -----------------------------
    # FORECAST DATA
    # -----------------------------
    forecast_df = forecast[['ds', 'yhat']].copy()
    forecast_df.columns = ['ds', 'y']

    # Keep only future
    forecast_df = forecast_df[forecast_df['ds'] > last_actual_date]

    # Remove negatives
    forecast_df['y'] = forecast_df['y'].clip(lower=0)

    forecast_df['type'] = 'Forecast'

    # Add last actual point (smooth connection)
    last_actual_row = actual_df[actual_df['ds'] == last_actual_date].copy()
    last_actual_row['type'] = 'Forecast'

    forecast_df = pd.concat([last_actual_row, forecast_df])

    # -----------------------------
    # COMBINE
    # -----------------------------
    combined = pd.concat([actual_df, forecast_df])
    combined['StockCode'] = str(sku)   # 🔥 ENSURE STRING

    final_list.append(combined)

# -----------------------------
# FINAL DATASET
# -----------------------------
final_df = pd.concat(final_list)

# Sort properly
final_df = final_df.sort_values(['StockCode', 'ds'])

# 🔥 FINAL SAFETY (IMPORTANT)
# -----------------------------
# FINAL CLEANING (VERY IMPORTANT)
# -----------------------------

# Fix StockCode
final_df['StockCode'] = final_df['StockCode'].astype(str).str.strip()

# Remove bad StockCodes
final_df = final_df[final_df['StockCode'].notna()]
final_df = final_df[final_df['StockCode'] != '']
final_df = final_df[final_df['StockCode'] != 'nan']

# Fix Date
final_df['ds'] = pd.to_datetime(final_df['ds'], errors='coerce')

# Remove bad dates
final_df = final_df[final_df['ds'].notna()]

# Fix y column
final_df['y'] = pd.to_numeric(final_df['y'], errors='coerce')

# Remove bad values
final_df = final_df[final_df['y'].notna()]

# -----------------------------
# SAVE OUTPUT
# -----------------------------
output_path = r"c:\Users\esvxxxi\Downloads\inventory-analytics-demand-forecasting\final_forecast_dataset.csv"
final_df.to_csv(
    output_path,
    index=False,
    encoding='utf-8',
    date_format='%Y-%m-%d'
)

print("✅ Final Forecast Dataset Ready")
print(f"📁 Saved at: {output_path}")
