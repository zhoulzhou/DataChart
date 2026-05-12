import sys, traceback
sys.path.insert(0, 'server')

print("importing akshare...")
try:
    import akshare as ak
    print("akshare version:", ak.__version__)
except Exception as e:
    print("import error:", e)
    sys.exit(1)

print("fetching profit...")
try:
    profit = ak.stock_financial_report_sina(stock="300308", symbol="利润表")
    print(f"profit: {len(profit)} rows, cols: {list(profit.columns[:10])}")
    if not profit.empty:
        print(profit.head(2).to_string())
except Exception as e:
    traceback.print_exc()

print("fetching balance...")
try:
    balance = ak.stock_financial_report_sina(stock="300308", symbol="资产负债表")
    print(f"balance: {len(balance)} rows, cols: {list(balance.columns[:10])}")
except Exception as e:
    traceback.print_exc()

print("fetching cashflow...")
try:
    cashflow = ak.stock_financial_report_sina(stock="300308", symbol="现金流量表")
    print(f"cashflow: {len(cashflow)} rows, cols: {list(cashflow.columns[:10])}")
except Exception as e:
    traceback.print_exc()