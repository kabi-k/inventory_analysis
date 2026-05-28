# python/04_powerbi_data.py

import pandas as pd
import numpy as np
import sqlite3
import os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cycle_count = os.path.join(root, "data", "simulated", "simulated_dataset.csv")
powerbi = os.path.join(root, "powerbi")
os.makedirs(powerbi, exist_ok=True)
database = os.path.join(powerbi, "inventory.db")


df = pd.read_csv(cycle_count, parse_dates=["Date"])
df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
df["Quarter"] = df["Date"].dt.quarter


fact_cols = [
    "Date", "SKU_ID", "Warehouse_ID", "Supplier_ID", "Region",
    "Inventory_Level", "System_Count", "Physical_Count", "Variance",
    "Defect_Flag", "Shrink_Flag", "Accuracy_Flag", "Severity",
    "Supplier_Lead_Time_Days", "Reorder_Point", "Units_Sold",
    "Order_Quantity", "Unit_Cost", "Unit_Price", "Demand_Forecast",
    "Promotion_Flag", "YearMonth", "Week", "Quarter"
]
df[fact_cols].to_csv(os.path.join(powerbi, "inventory_fact_table.csv"), index=False)
print("Saved inventory_fact_table.csv")


# compute shrink value
df["Shrink_Value"] = np.where(df["Variance"] < 0, abs(df["Variance"]) * df["Unit_Cost"], 0)

# monthly trend 
monthly = (
    df.groupby("YearMonth")
    .agg(
        Avg_Inventory_Level=("Inventory_Level", "mean"),
        Total_Units_Sold=("Units_Sold", "sum"),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate_Pct=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Accuracy_Pct=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Shrink_Events=("Shrink_Flag", "sum"),
        Total_Shrink_Value=("Shrink_Value", "sum")
    )
    .reset_index()
)
monthly["Avg_Inventory_Level"] = monthly["Avg_Inventory_Level"].round(1)
monthly["Total_Shrink_Value"]  = monthly["Total_Shrink_Value"].round(2)
monthly.to_csv(os.path.join(powerbi, "monthly_trends.csv"), index=False)
print("Saved monthly_trends.csv")


# sku dimension
sku = (
    df.groupby("SKU_ID")
    .agg(
        Avg_Inventory=("Inventory_Level", "mean"),
        Avg_Units_Sold=("Units_Sold", "mean"),
        Defect_Rate_Pct=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Accuracy_Pct=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Total_Shrink_Value=("Shrink_Value", "sum"),
        Avg_Unit_Cost=("Unit_Cost", "mean"),
        Avg_Gross_Margin=("Unit_Price", "mean")
    )
    .reset_index()
)
sku["Avg_Inventory"] = sku["Avg_Inventory"].round(1)
sku["Avg_Units_Sold"] = sku["Avg_Units_Sold"].round(2)
sku["Total_Shrink_Value"] = sku["Total_Shrink_Value"].round(2)
sku["Avg_Unit_Cost"] = sku["Avg_Unit_Cost"].round(2)
sku["Avg_Gross_Margin"] = (sku["Avg_Gross_Margin"] - sku["Avg_Unit_Cost"]).round(2)
sku.to_csv(os.path.join(powerbi, "sku_dashboard.csv"), index=False)
print("Saved sku_dashboard.csv")


# warehouse
wh = (
    df.groupby("Warehouse_ID")
    .agg(
        Total_Records=("Variance", "count"),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate_Pct=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Avg_Accuracy_Pct=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Shrink_Events=("Shrink_Flag", "sum"),
        Total_Shrink_Value=("Shrink_Value", "sum")
    )
    .reset_index()
)
wh["Total_Shrink_Value"] = wh["Total_Shrink_Value"].round(2)
wh.to_csv(os.path.join(powerbi, "warehouse_dashboard.csv"), index=False)
print("Saved warehouse_dashboard.csv")


sup = (
    df.groupby("Supplier_ID")
    .agg(
        Avg_Lead_Time=("Supplier_Lead_Time_Days", "mean"),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate_Pct=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Avg_Accuracy_Pct=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2))
    )
    .reset_index()
)
sup["Avg_Lead_Time"] = sup["Avg_Lead_Time"].round(2)
sup.to_csv(os.path.join(powerbi, "supplier_dashboard.csv"), index=False)
print("Saved supplier_dashboard.csv")


# Region
regional = (
    df.groupby("Region")
    .agg(
        Total_Records=("Variance", "count"),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate_Pct=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Avg_Abs_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Total_Units_Sold=("Units_Sold", "sum"),
        Avg_Units_Sold=("Units_Sold", lambda x: round(x.mean(), 2))
    )
    .reset_index()
    .sort_values("Defect_Rate_Pct", ascending=False)
)

regional.to_csv(os.path.join(powerbi, "regional_dashboard.csv"), index=False)
print("Saved regional_dashboard.csv")

print(f"\nAll data to import into Power BI saved to: {powerbi}")