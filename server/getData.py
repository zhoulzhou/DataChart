import sys
import json
import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = 2026

FIELD_MAP = {
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

MONETARY = {
    "营业收入", "营业成本", "归母净利润", "存货", "应收账款",
    "货币资金", "短期理财", "合同负债", "股东权益", "经营现金流"
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


def get_yfinance_quarterly(stock_code, start_year, end_year):
    code = fix_code(stock_code)
    ticker = yf.Ticker(code)

    q_is = ticker.quarterly_financials
    q_bs = ticker.quarterly_balance_sheet
    q_cf = ticker.quarterly_cashflow

    if q_is.empty:
        return pd.DataFrame()

    q_is = q_is.T
    q_bs = q_bs.T if not q_bs.empty else pd.DataFrame()
    q_cf = q_cf.T if not q_cf.empty else pd.DataFrame()

    dfs = [q_is]
    if not q_bs.empty:
        dfs.append(q_bs)
    if not q_cf.empty:
        dfs.append(q_cf)

    df = pd.concat(dfs, axis=1)
    df = df.reset_index()
    df.rename(columns={"index": "报告期"}, inplace=True)

    df["报告期"] = pd.to_datetime(df["报告期"])
    df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]

    for eng, cn in FIELD_MAP.items():
        if eng in df.columns:
            df.rename(columns={eng: cn}, inplace=True)

    return df


def main():
    df = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)

    if df.empty:
        print(json.dumps({"source": "none", "records": []}))
        return

    for col in df.columns:
        if col in MONETARY:
            df[col] = df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)

    records = []
    for _, row in df.iterrows():
        dt = row["报告期"]
        r = {"year": int(dt.year), "quarter": (int(dt.month) - 1) // 3 + 1, "statDate": str(dt.date())}
        for col in df.columns:
            if col == "报告期":
                continue
            v = row[col]
            r[col] = 0 if pd.isna(v) else v
        records.append(r)

    print(json.dumps({"source": "yfinance", "records": records}, ensure_ascii=False))


if __name__ == "__main__":
    main()