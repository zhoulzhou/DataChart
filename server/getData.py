import sys
import json
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
            "reportdate": "statDate",
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
        df["statDate"] = pd.to_datetime(df["statDate"]).astype(str)
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

    profit_rows = []
    balance_rows = []
    cash_rows = []

    for year in range(start_year, end_year + 1):
        for q in [1, 2, 3, 4]:
            try:
                profit_rs = bs.query_profit_data(code=code, year=year, quarter=q)
                balance_rs = bs.query_balance_data(code=code, year=year, quarter=q)
                cash_rs = bs.query_cash_flow_data(code=code, year=year, quarter=q)

                if profit_rs.error_code == "0":
                    pdf = profit_rs.get_data()
                    if not pdf.empty:
                        p_row = {k: safe_float(v) for k, v in pdf.iloc[0].to_dict().items()}
                        p_row["year"] = year
                        p_row["quarter"] = q
                        if 'netProfit' in p_row:
                            p_row['netProfit'] = round(p_row['netProfit'] / 10000, 1)
                        if 'MBRevenue' in p_row:
                            p_row['MBRevenue'] = round(p_row['MBRevenue'] / 100, 1)
                        profit_rows.append(p_row)

                if balance_rs.error_code == "0":
                    bdf = balance_rs.get_data()
                    if not bdf.empty:
                        b_row = {k: safe_float(v) for k, v in bdf.iloc[0].to_dict().items()}
                        b_row["year"] = year
                        b_row["quarter"] = q
                        balance_rows.append(b_row)

                if cash_rs.error_code == "0":
                    cdf = cash_rs.get_data()
                    if not cdf.empty:
                        c_row = {k: safe_float(v) for k, v in cdf.iloc[0].to_dict().items()}
                        c_row["year"] = year
                        c_row["quarter"] = q
                        cash_rows.append(c_row)

            except Exception as e:
                print(f"Baostock {year}Q{q} 异常:", e, file=sys.stderr)
                continue

    bs.logout()

    if not profit_rows:
        return None

    return {
        "profit": profit_rows,
        "balance": balance_rows,
        "cash_flow": cash_rows
    }


def get_eastmoney_all(stock_code):
    df = get_eastmoney_quarter_data(stock_code)
    if df is None or df.empty:
        return None

    profit_rows = []
    balance_rows = []
    cash_rows = []

    for _, row in df.iterrows():
        sd = str(row["statDate"])[:10]
        y = int(sd[:4])
        m = int(sd[5:7])
        q = (m - 1) // 3 + 1

        def sv(key):
            return to_yi(row.get(key, 0), 100000000)

        profit_rows.append({
            "statDate": sd, "year": y, "quarter": q,
            "totalOperateIncome": sv("totalOperateIncome"),
            "totalOperateCost": sv("totalOperateCost"),
            "netProfit": sv("netProfit"),
            "totalEquity": sv("totalEquity")
        })

        balance_rows.append({
            "statDate": sd, "year": y, "quarter": q,
            "inventory": sv("inventory"),
            "accountsReceivable": sv("accountsReceivable"),
            "cashEquivalents": sv("cashEquivalents"),
            "tradingFinancialAssets": sv("tradingFinancialAssets"),
            "contractLiability": sv("contractLiability"),
            "totalEquity": sv("totalEquity")
        })

        cash_rows.append({
            "statDate": sd, "year": y, "quarter": q,
            "operateCashFlow": sv("operateCashFlow")
        })

    return {
        "profit": profit_rows,
        "balance": balance_rows,
        "cash_flow": cash_rows
    }


def safe_float(val):
    try:
        n = float(val)
        if pd.isna(n):
            return 0
        return n
    except (ValueError, TypeError):
        return 0


def to_yi(val, divisor):
    try:
        n = float(val)
        if pd.isna(n):
            return 0
        return round(n / divisor, 1)
    except (ValueError, TypeError):
        return 0


def get_stock_all_finance(stock_code):
    result = get_baostock_quarter_data(stock_code, START_YEAR, END_YEAR)
    if result is not None and result["profit"]:
        print("bao", file=sys.stderr)
        return result
    else:
        print("east", file=sys.stderr)
        return get_eastmoney_all(stock_code)


def main():
    result = get_stock_all_finance(STOCK_CODE)
    if result is None:
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()