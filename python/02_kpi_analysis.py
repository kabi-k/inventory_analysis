# python/02_kpi_analysis.py

import pandas as pd
import numpy as np
import sqlite3
import os

# Creating and initializing data directories 
root_dir = os.path.dirname(os.path.dirname(__file__))
cleaned_csv_path = os.path.join(root_dir, "data", "cleaned", "cleaned_dataset.csv")

# Creating directory for saving exported outputs
output_dir = os.path.join(root_dir, "outputs")
os.makedirs(output_dir, exist_ok=True)

# directory for SQL database
database_dir = os.path.join(root_dir, "database")
os.makedirs(database_dir, exist_ok=True)

database_path = os.path.join(database_dir, "inventory.db")

# Loading data
df = pd.read_csv(cleaned_csv_path, parse_dates=["Date"])

# SIMULATING CYCLE COUNT AUDITING
print("Simulating cycle count...")
np.random.seed(42)

# noise for simulating inventory errors
np.random.seed(42)

# setting a reasonable scale of random rows to get an error
error_mask = np.random.random(size=len(df)) < 0.05
variance_values = np.where(
    error_mask,
    np.random.randint(-20, 20, size=len(df)), 0
)

df["System_Count"] = df["Inventory_Level"]
df["Physical_Count"] = df["Inventory_Level"] + variance_values
df["Variance"] = df["Physical_Count"] - df["System_Count"]


# Marks as accuracte if the physical inventory matches the system inventory
df["Accuracy_Flag"]  = np.where(df["Variance"] == 0, "Accurate", "Inaccurate")

# Larger inaccuracies are marked as defects
df["Defect_Flag"] = np.where(abs(df["Variance"]) > 5, 1, 0)

# Inaccuracies caused by less physical stock than system stock
df["Shrink_Flag"] = np.where(df["Variance"] < 0, 1, 0)

# Sections for how severe the inaccuracies are
conditions = [
    df["Variance"] == 0,
    abs(df["Variance"]) <= 5,
    abs(df["Variance"]) <= 15,
    abs(df["Variance"]) > 15
]

df["Severity"] = np.select(conditions, ["Accurate", "Minor", "Moderate", "Critical"], default="Unknown")

# Saving the cycle count csv
simulated_cycle_count_dir = os.path.join(root_dir, "data", "simulated")
os.makedirs(simulated_cycle_count_dir, exist_ok=True)
df.to_csv(os.path.join(simulated_cycle_count_dir, "simulated_dataset.csv"), index=False)
print(f"Simulated cycle count CSV saved to: {simulated_cycle_count_dir}")


# Date Breakdown
df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
df["Month"] = df["Date"].dt.month
df["Quarter"] = df["Date"].dt.quarter
df["Month_Name"] = df["Date"].dt.month_name()



df["Out_Of_Stock_Risk"] = (df["Inventory_Level"] < df["Reorder_Point"]).astype(int)

# The amount of days inventory can last based on demand
df["Days_of_Inventory"] = np.where(df["Units_Sold"] > 0, df["Inventory_Level"] / df["Units_Sold"], np.nan)

# Using standard deviation to determine SKU anomalies
sku_stats = df.groupby("SKU_ID")["Inventory_Level"].agg(["mean", "std"]).reset_index()

sku_stats.columns = [
    "SKU_ID",
    "SKU_Mean",
    "SKU_STD"
]

df = df.merge(sku_stats, on="SKU_ID", how="left")

df["Inventory_Anomaly"] = np.where(df["SKU_STD"] > 0, (np.abs(df["Inventory_Level"] - df["SKU_Mean"]) > (2 * df["SKU_STD"])), 0).astype(int)
# Current stock compared to stock that has to be maintained
df["Inventory_Variance"] = df["Inventory_Level"] - df["Reorder_Point"]

# Checks the accuracy percentage of an inventory record 
df["Row_Accuracy"] = np.clip(1 - (np.abs(df["Inventory_Variance"]) / df["Reorder_Point"].replace(0, np.nan)), 0, 1) * 100

# Price margins for each unit
df["Price_Margin"] = df["Unit_Price"] - df["Unit_Cost"]

df["Shrink_Value"] = np.where(df["Variance"] < 0, abs(df["Variance"]) * df["Unit_Cost"], 0)



# SQLITE
print("Creating SQL database")
conn = sqlite3.connect(database_path)
df.to_sql("inventory_fact", conn, if_exists="replace", index=False)
db_count = pd.read_sql("SELECT COUNT(*) AS count FROM inventory_fact", conn).iloc[0, 0]

# KPI Calculations (using pandas and SQL to demonstrate both methods)

# Overall accuracy

total_inventory = df["Inventory_Level"].sum()
total_inventory = total_inventory if total_inventory != 0 else np.nan
inventory_accuracy = round((df["Variance"] == 0).mean() * 100, 2)
defect_rate = round(df["Defect_Flag"].mean() * 100, 2)
shrink_units = abs(df[df["Variance"] < 0]["Variance"].sum())
shrink_rate = round((shrink_units / total_inventory) * 100 if total_inventory else 0, 2)
variance_rate = round((abs(df["Variance"]).sum() / total_inventory) * 100 if total_inventory else 0, 2)

overall_accuracy = pd.DataFrame({
    "KPI": [
        "Inventory Accuracy %",
        "Defect Rate %",
        "Shrink Rate %",
        "Variance Rate %",
        "Total Records",
        "Total Anomalies",
        "Total Shrink Value ($)"
    ],
    "Value": [
        inventory_accuracy,
        defect_rate,
        shrink_rate,
        variance_rate,
        len(df),
        int(df["Inventory_Anomaly"].sum()),
        round(df["Shrink_Value"].sum(), 2)
    ]
})

# monthly trend
monthly_trend = (
    df.groupby("YearMonth").agg(
        Avg_Accuracy=("Row_Accuracy", "mean"),
        Inventory_Accuracy=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Out_Of_Stock_Rate=("Out_Of_Stock_Risk", lambda x: round(x.mean() * 100, 2)),
        Defect_Count=("Defect_Flag", "sum"),
        Shrink_Events=("Shrink_Flag", "sum"),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Total_Units_Sold=("Units_Sold", "sum"),
        Total_Shrink_Value=("Shrink_Value", "sum")
    )
    .reset_index()
)
monthly_trend["Avg_Accuracy"] = monthly_trend["Avg_Accuracy"].round(2)
monthly_trend["Total_Shrink_Value"] = monthly_trend["Total_Shrink_Value"].round(2)

# weekly trend
week_order = df[["Week", "YearMonth"]].drop_duplicates().sort_values("Week")
weekly_kpi = (df.groupby("Week").agg(
        Records=("Variance", "count"),
        Inventory_Accuracy=("Variance", lambda x: round((x == 0).mean() * 100, 2)),
        Defect_Count=("Defect_Flag", "sum"),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Out_Of_Stock_Risk_Count=("Out_Of_Stock_Risk", "sum")
    )
    .reset_index()
)

# SKU out of stock analysis
out_of_stock_from_sku = pd.read_sql("""
    SELECT
        SKU_ID,
        COUNT(*) AS Total_Records,
        SUM(Defect_Flag) AS Defect_Count,
        ROUND(100.0 * SUM(Defect_Flag) / COUNT(*), 2) AS Defect_Rate,
        SUM(Shrink_Flag) AS Shrink_Events,
        ROUND(100.0 * SUM(Shrink_Flag) / COUNT(*), 2) AS Shrink_Rate,
        ROUND(AVG(ABS(Variance)), 2) AS Avg_Abs_Variance,
        SUM(CASE WHEN Variance = 0 THEN 0 ELSE 1 END) AS Mismatch_Count,
        ROUND(100.0 * SUM(CASE WHEN Variance = 0 THEN 1 END) / COUNT(*), 2) AS Accuracy,
        ROUND(AVG(Row_Accuracy), 2) AS Avg_Row_Accuracy,
        ROUND(SUM(Shrink_Value), 2) AS Total_Shrink_Value
    FROM inventory_fact
    GROUP BY SKU_ID
    ORDER BY Defect_Rate DESC
""", conn)

# warehouse analysis
warehouse_analysis = pd.read_sql("""
    SELECT
        Warehouse_ID,
        COUNT(*) AS Total_Records,
        SUM(Defect_Flag) AS Defect_Count,
        ROUND(100.0 * SUM(Defect_Flag) / COUNT(*), 2) AS Defect_Rate,
        SUM(Shrink_Flag) AS Shrink_Events,
        ROUND(AVG(ABS(Variance)), 2) AS Avg_Abs_Variance,
        ROUND(AVG(Row_Accuracy), 2) AS Avg_Accuracy,
        SUM(Inventory_Anomaly) AS Anomaly_Count,
        ROUND(SUM(Shrink_Value), 2) AS Total_Shrink_Value
    FROM inventory_fact
    GROUP BY Warehouse_ID
    ORDER BY Defect_Rate DESC
""", conn)


# supplier analysis
supplier_analysis = pd.read_sql("""
    SELECT
        Supplier_ID,
        ROUND(AVG(Supplier_Lead_Time_Days), 2) AS Avg_Lead_Time,
        MAX(Supplier_Lead_Time_Days) AS Max_Lead_Time,
        MIN(Supplier_Lead_Time_Days) AS Min_Lead_Time,
        SUM(Defect_Flag) AS Defect_Count,
        ROUND(100.0 * SUM(Defect_Flag) / COUNT(*), 2) AS Defect_Rate,
        ROUND(AVG(Row_Accuracy), 2) AS Avg_Accuracy,
        ROUND(AVG(ABS(Variance)), 2) AS Avg_Abs_Variance,
        COUNT(*) AS Total_Records
    FROM inventory_fact
    GROUP BY Supplier_ID
    ORDER BY Avg_Lead_Time DESC
""", conn)


# regional analysis
region_kpi = (
    df.groupby("Region")
    .agg(
        Total_Records=("Variance", "count"),
        Avg_Accuracy=("Row_Accuracy", lambda x: round(x.mean(), 2)),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Shrink_Events=("Shrink_Flag", "sum"),
        Avg_Days_of_Inventory=("Days_of_Inventory", lambda x: round(x.mean(), 2)),
        Total_Shrink_Value=("Shrink_Value", lambda x: round(x.sum(), 2))
    )
    .reset_index()
    .sort_values("Defect_Rate", ascending=False)
)


# severity summary
severity_summary = (df["Severity"].value_counts().reset_index())
severity_summary.columns = ["Severity", "Count"]
severity_summary["Percentage_of_Total"] = round(severity_summary["Count"] / len(df) * 100, 2)

# High risk SKUs with filtering
high_risk_skus = (df.groupby("SKU_ID").agg({
        "Inventory_Anomaly": "sum",
        "Out_Of_Stock_Risk": "sum",
        "Defect_Flag": "sum",
        "Row_Accuracy": "mean"
    }).reset_index()
)
high_risk_skus.columns = ["SKU_ID", "Total_Anomalies", "Out_Of_Stock_Events", "Defect_Count", "Avg_Accuracy"]
high_risk_skus = high_risk_skus[
    (high_risk_skus["Total_Anomalies"] >= 3) |
    (high_risk_skus["Out_Of_Stock_Events"] >= 3) |
    (high_risk_skus["Defect_Count"] >= 5)
]



# root cause (top problematic SKU and warehouse combos)
top_problematic_SKU = pd.read_sql("""
    SELECT
        SKU_ID,
        Warehouse_ID,
        Supplier_ID,
        COUNT(*) AS Records,
        SUM(Defect_Flag) AS Defect_Count,
        ROUND(100.0 * SUM(Defect_Flag) / COUNT(*), 2) AS Defect_Rate,
        ROUND(AVG(ABS(Variance)), 2) AS Avg_Abs_Variance,
        SUM(Shrink_Flag) AS Shrink_Events,
        ROUND(SUM(Shrink_Value), 2) AS Total_Shrink_Value,
        ROUND(AVG(Supplier_Lead_Time_Days), 1) AS Avg_Lead_Time
    FROM inventory_fact
    GROUP BY SKU_ID, Warehouse_ID
    ORDER BY Defect_Rate DESC
    LIMIT 20
""", conn)


# promotion impact on defects
promo_impact = (
    df.groupby("Promotion_Flag")
    .agg(
        Records=("Defect_Flag", "count"),
        Defect_Count=("Defect_Flag", "sum"),
        Defect_Rate=("Defect_Flag", lambda x: round(x.mean() * 100, 2)),
        Avg_Variance=("Variance", lambda x: round(abs(x).mean(), 2)),
        Avg_Units_Sold=("Units_Sold", "mean")
    )
    .reset_index()
)

promo_impact["Promotion_Flag"] = promo_impact["Promotion_Flag"].map({0: "No Promo", 1: "Promotion Active"})
promo_impact["Avg_Units_Sold"] = promo_impact["Avg_Units_Sold"].round(2)


# lead time impact on defects
lead_time_defects = pd.read_sql("""
    SELECT
        Supplier_Lead_Time_Days,
        COUNT(*) AS Records,
        SUM(Defect_Flag) AS Defect_Count,
        ROUND(100.0 * SUM(Defect_Flag) / COUNT(*), 2) AS Defect_Rate,
        ROUND(AVG(ABS(Variance)), 2) AS Avg_Abs_Variance
    FROM inventory_fact
    GROUP BY Supplier_Lead_Time_Days
    ORDER BY Supplier_Lead_Time_Days
""", conn)
 
# Corrective suggestions summary
corrective_suggestions = []

# flag warehouse defects within the threshold
avg_defect_rate = warehouse_analysis["Defect_Rate"].mean()

for _, warehouse in warehouse_analysis.iterrows():
    if warehouse["Defect_Rate"] > avg_defect_rate * 1.05:
        corrective_suggestions.append({
            "Issue": f"High defect rate in {warehouse['Warehouse_ID']} ({warehouse['Defect_Rate']}%)",
            "Root_Cause": "Variance is above average in physical counts: potentially a scanner misconfiguration",
            "Action": "Re-calibrate handheld RF scanners; verify correct counting procedures",
            "Priority": "High",
            "Owner": "Warehouse Manager"
        })
    
# flag shrink losses if they're impactful
# flag ALL shrink losses above threshold
high_shrink_skus = out_of_stock_from_sku[out_of_stock_from_sku["Shrink_Rate"] > 2.3].sort_values("Shrink_Rate", ascending=False)

for _, sku in high_shrink_skus.iterrows():
    corrective_suggestions.append({
        "Issue": f"High shrink rate for {sku['SKU_ID']} ({sku['Shrink_Rate']}%)",
        "Root_Cause": "Higher cost SKUs have increased shrink rates",
        "Action": "Increase cycle count frequency for this SKU",
        "Priority": "High",
        "Owner": "ICQA Lead"
    })

# flag promomotions if promotional eriods increase defect rates
promo_rates = promo_impact.set_index("Promotion_Flag")["Defect_Rate"]
if "Promotion Active" in promo_rates and "No Promo" in promo_rates:
    if promo_rates["Promotion Active"] > promo_rates["No Promo"] * 1.1:
        corrective_suggestions.append({
            "Issue": "Promotion periods result in higher defect rates",
            "Root_Cause": "Faster item picking during promotional periods cause an increase in miscount probability",
            "Action": "Have additional counters during promotional periods and review the picking process to prevent rushes",
            "Priority": "Medium",
            "Owner": "Operations Supervisor"
        })


lead_time_correlation = lead_time_defects["Avg_Abs_Variance"].corr(lead_time_defects["Supplier_Lead_Time_Days"])
# Only flag if correlation is significant
if abs(lead_time_correlation) > 0.3:
    # Calculate expected defect rate based on lead time trend
    avg_defect_by_lead_time = lead_time_defects.groupby("Supplier_Lead_Time_Days")["Defect_Rate"].mean().to_dict()

    for _, supplier in supplier_analysis.iterrows():
        expected_rate = avg_defect_by_lead_time.get(round(supplier["Avg_Lead_Time"]), supplier_analysis["Defect_Rate"].mean())
            
        # Flag if actual defect rate is significantly higher than expected for that lead time
        if supplier["Defect_Rate"] > expected_rate * 1.15:  # 15% higher than expected
            corrective_suggestions.append({
                "Issue": f"Supplier {supplier['Supplier_ID']} has {supplier['Defect_Rate']}% defect rate vs expected {expected_rate:.2f}% for {supplier['Avg_Lead_Time']} day lead time",
                "Root_Cause": "This supplier performs worse than others with similar lead times",
                "Action": "Audit supplier receiving process; investigate root cause of discrepancies",
                "Priority": "Medium",
                "Owner": "Inventory Control"
            })

corrective_suggestions = pd.DataFrame(corrective_suggestions)


print(f"Database rows: {db_count:,}")
print(f"Database match: {'Yes' if db_count == len(df) else 'No'}")


conn.close()

# exporting data
exports = {
    "kpi_summary.csv": overall_accuracy,
    "monthly_accuracy.csv": monthly_trend,
    "weekly_kpi.csv": weekly_kpi,
    "sku_error_analysis.csv": out_of_stock_from_sku,
    "warehouse_defects_analysis.csv": warehouse_analysis,
    "supplier_performance.csv": supplier_analysis,
    "regional_analysis.csv": region_kpi,
    "variance_severity.csv": severity_summary,
    "kpi_high_risk_skus.csv": high_risk_skus,
    "top_problematic_SKU.csv": top_problematic_SKU,
    "promotion_impact.csv": promo_impact,
    "lead_time_defects.csv": lead_time_defects,
    "corrective_actions.csv": corrective_suggestions,
}


for file, data in exports.items():
    data.to_csv(os.path.join(output_dir, file), index=False)

print(f"All outputs saved to: {output_dir}")

