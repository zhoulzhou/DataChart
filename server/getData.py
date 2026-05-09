import sys
import json
import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = 2026

MONETARY_FIELDS = {
    "营业收入", "营业成本", "毛利", "归母净利润", "存货", "应收账款",
    "货币资金", "短期理财", "现金总额(含短期理财)", "合同负债", "股东权益", "经营现金流"
}


def fix_code(code):
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith("6"):
        return f"{code}.SH"
    return code


def to_yi(val):
    try:
        n = float(val)
        if pd.isna(n):
            return 0
        return round(n / 100000000, 1)
    except (ValueError, TypeError):
        return 0


def safe_float(val):
    try:
        n = float(val)
        if pd.isna(n):
            return 0
        return round(n, 1)
    except (ValueError, TypeError):
        return 0


def get_yfinance_quarterly(stock_code, start_year, end_year):
    code = fix_code(stock_code)
    ticker = yf.Ticker(code)

    q_is = ticker.quarterly_financials
    q_bs = ticker.quarterly_balance_sheet
    q_cf = ticker.quarterly_cashflow

    if q_is.empty or q_bs.empty:
        return pd.DataFrame()

    q_is = q_is.T
    q_bs = q_bs.T
    q_cf = q_cf.T

    df = pd.concat([q_is, q_bs, q_cf], axis=1)
    df = df.reset_index()
    df.rename(columns={"index": "报告期"}, inplace=True)

    df["报告期"] = pd.to_datetime(df["报告期"])
    df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]

    map_cols = {
        "Total Revenue": "营业收入",
        "Cost Of Revenue": "营业成本",
        "Net Income": "归母净利润",
        "Inventory": "存货",
        "Accounts Receivable": "应收账款",
        "Cash And Cash Equivalents": "货币资金",
        "Short Term Investments": "短期理财",
        "Contract Liabilities": "合同负债",
        "Total Stockholder Equity": "股东权益",
        "Operating Cash Flow": "经营现金流"
    }
    df = df.rename(columns=map_cols)

    for col in ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                 "货币资金", "短期理财", "合同负债", "股东权益", "经营现金流"]:
        if col not in df.columns:
            df[col] = None

    return df


def calc_index(df):
    df["短期理财"] = df["短期理财"].fillna(0)
    df["现金总额(含短期理财)"] = df["货币资金"] + df["短期理财"]
    df["毛利"] = df["营业收入"] - df["营业成本"]
    df["毛利率(%)"] = (df["毛利"] / df["营业收入"] * 100).round(1)
    df["净利率(%)"] = (df["归母净利润"] / df["营业收入"] * 100).round(1)

    df["上期存货"] = df["存货"].shift(1)
    df["上期应收"] = df["应收账款"].shift(1)
    df["上期权益"] = df["股东权益"].shift(1)

    df["平均存货"] = (df["存货"] + df["上期存货"]) / 2
    df["平均应收"] = (df["应收账款"] + df["上期应收"]) / 2
    df["平均权益"] = (df["股东权益"] + df["上期权益"]) / 2

    df["存货周转率"] = (df["营业成本"] / df["平均存货"]).round(1)
    df["应收周转率"] = (df["营业收入"] / df["平均应收"]).round(1)
    df["ROE(%)"] = (df["归母净利润"] / df["平均权益"] * 100).round(1)

    return df[[
        "报告期", "营业收入", "营业成本", "毛利", "毛利率(%)",
        "归母净利润", "净利率(%)", "ROE(%)",
        "货币资金", "短期理财", "现金总额(含短期理财)",
        "存货", "存货周转率", "应收账款", "应收周转率",
        "经营现金流", "合同负债"
    ]]


def main():
    try:
        import baostock as bs
        bs.login()
        has_baostock = True
        bs.logout()
    except Exception:
        has_baostock = False

    df = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    source = "yfinance"

    if df.empty and has_baostock:
        source, df = baostock_fallback(STOCK_CODE, START_YEAR, END_YEAR)

    if df is None or df.empty:
        print(json.dumps({"source": "none", "records": []}))
        return

    if source == "yfinance":
        final = calc_index(df)

        for col in final.columns:
            if col in MONETARY_FIELDS:
                final[col] = final[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)
            elif col != "报告期":
                final[col] = final[col].apply(lambda x: safe_float(x) if pd.notna(x) else 0)

        records = []
        for _, row in final.iterrows():
            dt = row["报告期"]
            r = {"year": int(dt.year), "quarter": (int(dt.month) - 1) // 3 + 1, "statDate": str(dt.date())}
            for col in final.columns:
                if col == "报告期":
                    continue
                v = row[col]
                r[col] = 0 if pd.isna(v) else v
            records.append(r)

        print(json.dumps({"source": source, "records": records}, ensure_ascii=False))
    else:
        print(json.dumps({"source": source, "profit": df.get("profit", []),
                           "balance": df.get("balance", []), "cash_flow": df.get("cash_flow", [])},
                          ensure_ascii=False))


def baostock_fallback(stock_code, start_year, end_year):
    import baostock as bs
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

            except Exception:
                continue

    bs.logout()

    if not profit_rows:
        return "none", pd.DataFrame()

    return "baostock", {"profit": profit_rows, "balance": balance_rows, "cash_flow": cash_rows}


if __name__ == "__main__":
    main()