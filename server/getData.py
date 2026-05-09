import sys
import json
import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = int(__import__('datetime').datetime.now().year)

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
    "Operating Cash Flow": "经营活动现金流净额"
}

MONETARY = {
    "营业收入", "营业成本", "归母净利润", "存货", "应收账款",
    "货币资金", "短期理财", "合同负债", "股东权益", "经营活动现金流净额"
}


def fix_code(code):
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith("6"):
        return f"{code}.SH"
    return code


def to_yi(val, divisor=100000000):
    try:
        n = float(val)
        if pd.isna(n):
            return 0
        return round(n / divisor, 1)
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


def get_baostock_quarterly(stock_code, start_year, end_year):
    try:
        import baostock as bs
    except ImportError:
        return pd.DataFrame()

    lg = bs.login()
    if lg.error_code != "0":
        bs.logout()
        return pd.DataFrame()

    if stock_code.startswith(("3", "0")):
        code = f"sz.{stock_code}"
    else:
        code = f"sh.{stock_code}"

    rows = []
    for year in range(start_year, end_year + 1):
        for q in [1, 2, 3, 4]:
            try:
                rs = bs.query_profit_data(code=code, year=year, quarter=q)
                if rs.error_code == "0":
                    pdf = rs.get_data()
                    if not pdf.empty:
                        r = pdf.iloc[0].to_dict()
                        rows.append({
                            "year": year, "quarter": q,
                            "statDate": str(r.get("statDate", "")),
                            "营业收入": to_yi(r.get("MBRevenue", 0), 100),
                            "营业成本": 0,
                            "归母净利润": to_yi(r.get("netProfit", 0), 10000),
                            "存货": 0, "应收账款": 0,
                            "货币资金": 0, "短期理财": 0,
                            "合同负债": 0, "股东权益": 0, "经营活动现金流净额": 0
                        })
                rs2 = bs.query_balance_data(code=code, year=year, quarter=q)
                if rs2.error_code == "0":
                    bdf = rs2.get_data()
                    if not bdf.empty and rows:
                        b = bdf.iloc[0].to_dict()
                        pass
                rs3 = bs.query_cash_flow_data(code=code, year=year, quarter=q)
                if rs3.error_code == "0":
                    cdf = rs3.get_data()
                    if not cdf.empty and rows:
                        pass
            except Exception:
                continue

    bs.logout()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def df_to_records(df):
    if df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        r = {}
        for col in df.columns:
            v = row[col]
            if pd.isna(v):
                r[col] = 0
            else:
                r[col] = v
        records.append(r)
    return records


def main():
    print("=" * 60, file=sys.stderr)
    print(f" 股票代码: {STOCK_CODE}  年份范围: {START_YEAR}-{END_YEAR}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    yf_df = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    bs_df = get_baostock_quarterly(STOCK_CODE, START_YEAR, END_YEAR)

    for col in yf_df.columns:
        if col in MONETARY:
            yf_df[col] = yf_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)

    if not bs_df.empty:
        for col in bs_df.columns:
            if col in MONETARY:
                bs_df[col] = bs_df[col].apply(lambda x: float(x) if pd.notna(x) else 0)

    yf_records = df_to_records(yf_df)
    bs_records = df_to_records(bs_df)

    key_fields = ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                   "货币资金", "短期理财", "合同负债", "经营活动现金流净额"]

    print("", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(" 数据对比 (单位: 亿)", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    all_periods = set()
    yf_map = {}
    bs_map = {}

    for r in yf_records:
        key = f"{r.get('year','')}Q{r.get('quarter','')}"
        all_periods.add(key)
        yf_map[key] = r

    for r in bs_records:
        key = f"{r.get('year','')}Q{r.get('quarter','')}"
        all_periods.add(key)
        bs_map[key] = r

    for period in sorted(all_periods):
        yf = yf_map.get(period, {})
        bs = bs_map.get(period, {})
        print(f"\n--- {period} ---", file=sys.stderr)
        print(f"{'字段':<16} {'Yahoo':>10} {'Baostock':>10} {'差异':>10}", file=sys.stderr)
        print("-" * 48, file=sys.stderr)
        for fld in key_fields:
            yv = yf.get(fld, 0)
            bv = bs.get(fld, 0)
            diff = round(yv - bv, 1) if yv and bv else "-"
            yvs = f"{yv:.1f}" if yv else "-"
            bvs = f"{bv:.1f}" if bv else "-"
            diffs = f"{diff:.1f}" if isinstance(diff, float) else diff
            print(f"{fld:<16} {yvs:>10} {bvs:>10} {diffs:>10}", file=sys.stderr)

    yf_count = len(yf_records)
    bs_count = len(bs_records)
    print(f"\nYahoo: {yf_count} 条  |  Baostock: {bs_count} 条", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    result = {
        "yfinance": {"records": yf_records},
        "baostock": {"records": bs_records}
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()