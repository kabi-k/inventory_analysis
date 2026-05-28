# python/01_data_cleaning.py

import pandas as pd
import os

# Creating and initializing data directories 
root_dir = os.path.dirname(os.path.dirname(__file__))
raw_csv_path = os.path.join(root_dir, "data", "raw", "inventory_dataset.csv")

# Loading data
df = pd.read_csv(raw_csv_path)

# converts date from text into datetime objects
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

print("Dataframe Head:")
print(df.head())

# CLEANING DATA

# initializing the required columns needed for accuracy/root cause analysis
required_columns = [
    "Date",
    "SKU_ID",
    "Warehouse_ID",
    "Supplier_ID",
    "Region",
    "Units_Sold",
    "Inventory_Level",
    "Supplier_Lead_Time_Days",
    "Reorder_Point",
    "Order_Quantity"
]


# Checking for missing columns
missing_columns = [c for c in required_columns if c not in df.columns]

if missing_columns:
    raise ValueError(f"Missing columns: {missing_columns}")

print(f"Total rows loaded: {len(df)}")

# Removing duplicate rows
initial_row_count = len(df)
df.drop_duplicates(inplace=True)
removed_duplicate_count = initial_row_count - len(df)

if removed_duplicate_count > 0: 
    print(f"Duplicate rows removed: {removed_duplicate_count}")
else:
    print("No duplicate rows found")

# Handling null values
df = df.dropna(subset=["Date", "SKU_ID"])

null_count = df.isnull().sum()
null_exists = null_count[null_count > 0]
for column in null_exists.index:
    if pd.api.types.is_numeric_dtype(df[column]):
        df[column] = df[column].fillna(df[column].median())
    else:
        df[column] = df[column].fillna("Unknown")



negative_inventory = df[df["Inventory_Level"] < 0]
print(f"Negative inventory rows: {len(negative_inventory)}")
impossible_sales = df[df["Units_Sold"] > df["Inventory_Level"]]
print(f"Impossible sales rows: {len(impossible_sales)}")

cleaned_dir = os.path.join(root_dir, "data", "cleaned")
os.makedirs(cleaned_dir, exist_ok=True)
df.to_csv(os.path.join(cleaned_dir, "cleaned_dataset.csv"), index=False)
print("Cleaned Data Saved")

