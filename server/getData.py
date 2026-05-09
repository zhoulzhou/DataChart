import sys
import json

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = 2026

def fetch_eastmoney(stock_code):
    import requests
    import pandas as pd
    url = (
        f"https://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php"
        f"?type=Q&token=70f12f2f4f091e4e90272a310c76c5e&st={stock_code}&sr=&p=1&ps=200"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": "https://eastmoney.com/"
    }
    res = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    res.encoding = "utf-8"
    df = pd.read_json(res.text)
    return df

def fetch_baostock(stock_code):
    import baostock as bs
    bs.login()

    if stock_code.startswith(("3", "0")):
        code = f"sz.{stock_code}"
    else:
        code = f"sh.{stock_code}"

    all_data = []
    for year in range(START_YEAR, END_YEAR + 1):
        for q in [1, 2, 3, 4]:
            rs = bs.query_finance_data(code=code, year=year, quarter=q)
            if rs.error_code != "0":
                continue
            while rs.next():
                all_data.append(rs.get_row_data())
    bs.logout()

    if not all_data:
        return None

    import pandas as pd
    df = pd.DataFrame(all_data, columns=rs.fields)
    df["reportDate"] = pd.to_datetime(df["reportDate"])
    return df

def main():
    df = None
    source = ""

    try:
        import baostock
        df = fetch_baostock(STOCK_CODE)
        source = "Baostock"
    except:
        pass

    if df is None or df.empty:
        try:
            df = fetch_eastmoney(STOCK_CODE)
            source = "Eastmoney"
        except:
            pass

    if df is None or df.empty:
        sys.exit(1)

    for _, row in df.iterrows():
        date = str(row.get("reportDate", row.get("reportdate", "")))
        biz = row.get("totalOperateIncome", row.get("businessincome", 0) or 0)
        cost = row.get("totalOperateCost", row.get("cost", 0) or 0)
        profit = row.get("netProfit", row.get("netprofit", 0) or 0)
        cf = row.get("operateCashFlow", row.get("operatecashflow", 0) or 0)
        inv = row.get("inventory", 0) or 0
        recv = row.get("accountsReceivable", row.get("receivable", 0) or 0)
        cash = row.get("cashEquivalents", row.get("moneyfunds", 0) or 0)
        trade = row.get("tradingFinancialAssets", row.get("tradingasset", 0) or 0)
        contract = row.get("contractLiability", row.get("contractliability", 0) or 0)
        equity = row.get("totalEquity", row.get("equity", 0) or 0)

        print(f"{date}\t{biz}\t{cost}\t{profit}\t{cf}\t{inv}\t{recv}\t{cash}\t{trade}\t{contract}\t{equity}")

if __name__ == "__main__":
    main()