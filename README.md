# ICQA Analytics
Simulated Inventory Analysis to replicate a real world supply chain.
- Tracks inventory accuracy
- Detects cycle count discrepancies
- Measures shrinkage and defects
- Identifies risky SKUs, warehouses, regions, and suppliers
- Generates KPI dashboards

Demonstrates:
- extracting, cleaning, and manipulating data
- creating datasets
- creating databases
- SQL database
- KPI Analysis and calculations such as Inventory Accuracy, Defect Rate, Shrink Rate, and Variance Rate
- Detects anomalies and high risk SKUs
- Creates monthly and weekly inventory trends
- Root cause anlysis
- Actions to correct inaccuracies based on an items specific cause 
- Transforming raw warehouse data into structured analytics outputs, SQL tables, and datasets.

## Project Structure

*Made in Python 3.11*

*required libraries can be found in requirements.txt*

*pip install -r requirements.txt* or *python3.11 -m pip install -r requirements.txt* can be used to install them if needed (it's only numpy, openpyxl, it's only pandas)

**data/raw/inventory_dataset.csv** (original dataset)

**data/raw/cleaned_dataset.csv** (cleaned dataset)

**data/simulated/simulated_dataset** (simulated cycle counts)

**database/** (used for sql database)

**outputs/** (outputted csv files from kpi analysis. This includes csv summaries of different factors on inventory accuracy)

**powerbi/** (powerbi data files)

*Python files to run in order (these files generate the files that are already included)*

**python/01_data_cleaning.py** (cleans data)

**python/02_kpi_analysis.py** (contains all the calculations to determine inventory accuracy, and the root causes to inaccuracies (the data in the output folder))

**python/03_excel.py** (creates multiple pages in the excel file to display the data from the icqa kpi analysis)

**python/04_powerbi_data.py** (exports the data files to be inputed into power bi)

**reports** (powerbi, excel, and pdf of powerbi)
