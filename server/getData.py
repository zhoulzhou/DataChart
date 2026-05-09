import sys
import requests
import pandas as pd
import baostock as bs
import warnings
warnings.filterwarnings("ignore")

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = 2026


def get_eastmoney_quarter_data(stock_code):
    url = (
        f"https://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get_cwgx.php"
        f"?type=Q&token=70f12f2f4f091e4e90272a310c76c5e&st={stock_code}&sr=&p=1&ps=200"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": "https://eastmoney.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        res.encoding = "utf-8"
        json_str = res.text.strip("var hq_str_cwgx=").rstrip(";")
        df = pd.read_json(json_str)

        df = df.rename(columns={
            "reportdate": "reportDate",
            "businessincome": "totalOperateIncome",
            "cost": "totalOperateCost",
            "netprofit": "netProfit",
            "operatecashflow": "operateCashFlow",
            "inventory": "inventory",
            "receivable": "accountsReceivable",
            "moneyfunds": "cashEquivalents",
            "contractliability": "contractLiability",
            "equity": "totalEquity",
            "tradingasset": "tradingFinancialAssets"
        })

        keep_cols = [
            "reportDate","totalOperateIncome","totalOperateCost","netProfit",
            "operateCashFlow","inventory","accountsReceivable","cashEquivalents",
            "tradingFinancialAssets","contractLiability","totalEquity"
        ]
        df = df[keep_cols].copy()
        df["reportDate"] = pd.to_datetime(df["reportDate"])
        df = df.sort_values("reportDate").reset_index(drop=True)
        return df
    except Exception as e:
        print("东财接口异常：", e, file=sys.stderr)
        return None


def get_baostock_quarter_data(stock_code, start_year, end_year):
    bs.login()

    if stock_code.startswith(("3", "0")):
        code = f"sz.{stock_code}"
    else:
        code = f"sh.{stock_code}"

    all_data = []
    for year in range(start_year, end_year + 1):
        for q in [1, 2, 3, 4]:
            rs = bs.query_finance_data(code=code, year=year, quarter=q)
            if rs.error_code != "0":
                continue
            while rs.next():
                all_data.append(rs.get_row_data())
    bs.logout()

    if not all_data:
        return None

    df = pd.DataFrame(all_data, columns=rs.fields)
    df["reportDate"] = pd.to_datetime(df["reportDate"])
    num_cols = [
        "totalOperateIncome","totalOperateCost","netProfit","operateCashFlow",
        "inventory","accountsReceivable","cashEquivalents","tradingFinancialAssets",
        "contractLiability","totalEquity"
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("reportDate").reset_index(drop=True)
    return df


def get_stock_all_finance(stock_code):
    df = get_baostock_quarter_data(stock_code, START_YEAR, END_YEAR)
    if df is not None and not df.empty:
        print("bao", file=sys.stderr)
    else:
        print("east", file=sys.stderr)
        df = get_eastmoney_quarter_data(stock_code)

    if df is None or df.empty:
        return None
    return df


def main():
    df = get_stock_all_finance(STOCK_CODE)
    if df is None or df.empty:
        sys.exit(1)

    for _, row in df.iterrows():
        date = str(row["reportDate"])[:10]
        def v(col):
            val = row.get(col, 0)
            n = float(val) if pd.notna(val) else 0
            return round(n, 1)
        print(f"{date}\t{v('totalOperateIncome')}\t{v('totalOperateCost')}\t{v('netProfit')}\t{v('operateCashFlow')}\t{v('inventory')}\t{v('accountsReceivable')}\t{v('cashEquivalents')}\t{v('tradingFinancialAssets')}\t{v('contractLiability')}")

if __name__ == "__main__":
    main()