import sys
import json
import warnings
import traceback
warnings.filterwarnings("ignore")

try:
    import pandas as pd
except Exception as e:
    print(json.dumps([], ensure_ascii=False))
    sys.exit(0)

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = int(__import__('datetime').datetime.now().year)

HAS_BAOSTOCK = False
HAS_YFINANCE = False

try:
    import baostock as bs
    HAS_BAOSTOCK = True
except Exception:
    pass

try:
    import yfinance as yf
    HAS_YFINANCE = True
except Exception:
    pass


def safe_num(val, default=0):
    try:
        n = pd.to_numeric(val, errors="coerce")
        if pd.isna(n):
            return default
        return float(n)
    except Exception:
        return default


def to_yi(val):
    return round(safe_num(val) / 100000000, 1)


def to_quarter(df):
    if df.empty or len(df) == 0:
        return df
    df = df.sort_values("报告期").reset_index(drop=True)
    cols = ["营业收入", "营业成本", "归母净利润", "经营活动现金流净额"]
    for c in cols:
        if c in df.columns:
            orig = df[c].copy()
            df[c] = df[c].diff()
            df.loc[0, c] = orig.iloc[0]
    return df


def get_baostock_full(stock_code, start_year, end_year):
    if not HAS_BAOSTOCK:
        print("[BS] baostock未安装", file=sys.stderr)
        return pd.DataFrame()

    try:
        bs.login()
        code = f"sz.{stock_code}" if stock_code.startswith(("0", "3")) else f"sh.{stock_code}"
        rows = []

        for year in range(start_year, end_year + 1):
            for quarter in [1, 2, 3, 4]:
                try:
                    profit = bs.query_profit_data(code, year=year, quarter=quarter).get_data()
                    balance = bs.query_balance_data(code, year=year, quarter=quarter).get_data()
                    cashflow = bs.query_cash_flow_data(code, year=year, quarter=quarter).get_data()

                    if profit.empty:
                        continue

                    p = profit.iloc[0]
                    b = balance.iloc[0] if not balance.empty else None
                    c = cashflow.iloc[0] if not cashflow.empty else None

                    sd = str(p.get("statDate", p.get("reportDate", "")))
                    if not sd:
                        continue

                    row = {
                        "报告期": sd,
                        "营业收入": safe_num(p.get("totalOperatingRevenue", p.get("MBRevenue", 0))),
                        "营业成本": safe_num(p.get("totalOperatingCost", p.get("operatingCost", 0))),
                        "归母净利润": safe_num(p.get("netProfit", 0)),
                        "存货": safe_num(b.get("inventory", 0)) if b is not None else 0,
                        "应收账款": safe_num(b.get("accountsReceivable", 0)) if b is not None else 0,
                        "货币资金": safe_num(b.get("cashEquivalents", 0)) if b is not None else 0,
                        "短期理财": safe_num(b.get("tradingFinancialAssets", 0)) if b is not None else 0,
                        "合同负债": safe_num(b.get("contractLiability", 0)) if b is not None else 0,
                        "股东权益": safe_num(b.get("totalEquity", 0)) if b is not None else 0,
                        "经营活动现金流净额": safe_num(c.get("operateCashFlow", 0)) if c is not None else 0,
                    }
                    rows.append(row)
                except Exception:
                    continue

        bs.logout()

        if not rows:
            print("[BS] 无数据", file=sys.stderr)
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["报告期"] = pd.to_datetime(df["报告期"])
        df = df.drop_duplicates("报告期").sort_values("报告期").reset_index(drop=True)
        df = to_quarter(df)

        for _, row in df.iterrows():
            d = row["报告期"]
            vals = {c: round(row[c], 1) if pd.notna(row[c]) else 0 for c in df.columns if c != "报告期"}
            print(f"[BS] {d.strftime('%Y-%m-%d')}: {vals}", file=sys.stderr)

        return df
    except Exception as e:
        print(f"[BS] 异常: {e}", file=sys.stderr)
        try:
            bs.logout()
        except Exception:
            pass
        return pd.DataFrame()


def get_yfinance_quarterly(stock_code, start_year, end_year):
    if not HAS_YFINANCE:
        return pd.DataFrame()

    try:
        if stock_code.startswith(("0", "3")):
            code = f"{stock_code}.SZ"
        else:
            code = f"{stock_code}.SH"
        ticker = yf.Ticker(code)

        q_is = ticker.quarterly_financials
        if q_is.empty:
            return pd.DataFrame()

        q_bs = ticker.quarterly_balance_sheet
        q_cf = ticker.quarterly_cashflow

        q_is = q_is.T
        q_bs = q_bs.T if not q_bs.empty else pd.DataFrame()
        q_cf = q_cf.T if not q_cf.empty else pd.DataFrame()

        dfs = [q_is]
        if not q_bs.empty:
            dfs.append(q_bs)
        if not q_cf.empty:
            dfs.append(q_cf)

        df = pd.concat(dfs, axis=1).reset_index()
        df.rename(columns={"index": "报告期"}, inplace=True)
        df["报告期"] = pd.to_datetime(df["报告期"])
        df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]

        name_map = {
            "Total Revenue": "营业收入", "Cost Of Revenue": "营业成本",
            "Net Income": "归母净利润", "Inventory": "存货",
            "Accounts Receivable": "应收账款", "Cash And Cash Equivalents": "货币资金",
            "Short Term Investments": "短期理财", "Contract Liabilities": "合同负债",
            "Total Stockholder Equity": "股东权益", "Operating Cash Flow": "经营活动现金流净额"
        }
        for eng, cn in name_map.items():
            if eng in df.columns:
                df.rename(columns={eng: cn}, inplace=True)

        for cn in name_map.values():
            if cn not in df.columns:
                df[cn] = 0

        return df
    except Exception:
        return pd.DataFrame()


def calc_index(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["现金总额(含短期理财)"] = df["货币资金"] + df["短期理财"].fillna(0)
    df["毛利"] = df["营业收入"] - df["营业成本"]
    df["毛利率(%)"] = (df["毛利"] / df["营业收入"].replace(0, pd.NA) * 100).fillna(0).round(1)
    df["净利率(%)"] = (df["归母净利润"] / df["营业收入"].replace(0, pd.NA) * 100).fillna(0).round(1)

    df["上期存货"] = df["存货"].shift(1)
    df["上期应收"] = df["应收账款"].shift(1)
    df["上期权益"] = df["股东权益"].shift(1)

    df["平均存货"] = (df["存货"] + df["上期存货"]) / 2
    df["平均应收"] = (df["应收账款"] + df["上期应收"]) / 2
    df["平均权益"] = (df["股东权益"] + df["上期权益"]) / 2

    df["存货周转率"] = (df["营业成本"] / df["平均存货"].replace(0, pd.NA)).fillna(0).round(1)
    df["应收周转率"] = (df["营业收入"] / df["平均应收"].replace(0, pd.NA)).fillna(0).round(1)
    df["ROE(%)"] = (df["归母净利润"] / df["平均权益"].replace(0, pd.NA) * 100).fillna(0).round(1)

    return df[[
        "报告期", "营业收入", "营业成本", "毛利", "毛利率(%)",
        "归母净利润", "净利率(%)", "ROE(%)",
        "货币资金", "短期理财", "现金总额(含短期理财)",
        "存货", "存货周转率", "应收账款", "应收周转率",
        "经营活动现金流净额", "合同负债"
    ]]


def df_to_records(df, source):
    if df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        r = {}
        dt = row["报告期"]
        r["year"] = int(dt.year)
        r["quarter"] = (int(dt.month) - 1) // 3 + 1
        r["statDate"] = dt.strftime("%Y-%m-%d")
        r["source"] = source

        for col in df.columns:
            if col == "报告期":
                continue
            v = row[col]
            if pd.isna(v):
                r[col] = 0
            else:
                r[col] = round(float(v), 1)

        records.append(r)
    return records


def main():
    print("=" * 70, file=sys.stderr)
    print(f" 股票:{STOCK_CODE}  {START_YEAR}-{END_YEAR}  bs={HAS_BAOSTOCK} yf={HAS_YFINANCE}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    print("\n### 第1步: baostock", file=sys.stderr)
    bs_df = get_baostock_full(STOCK_CODE, START_YEAR, END_YEAR)

    if not bs_df.empty:
        bs_monetary = ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                        "货币资金", "短期理财", "合同负债", "股东权益", "经营活动现金流净额",
                        "毛利", "现金总额(含短期理财)"]
        for col in bs_df.columns:
            if col in bs_monetary:
                bs_df[col] = bs_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)

        bs_final = calc_index(bs_df)
        bs_records = df_to_records(bs_final, "baostock")
        print(f"[STEP1] baostock: {len(bs_records)}条", file=sys.stderr)
        print(json.dumps(bs_records, ensure_ascii=False))
        return

    print("[STEP1] baostock无数据, 尝试yfinance", file=sys.stderr)
    print("\n### 第2步: yfinance", file=sys.stderr)
    yf_df = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    if yf_df.empty:
        print("[STEP2] yfinance也无数据", file=sys.stderr)
        print(json.dumps([], ensure_ascii=False))
        return

    yf_monetary = ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                    "货币资金", "短期理财", "合同负债", "股东权益", "经营活动现金流净额"]
    for col in yf_df.columns:
        if col in yf_monetary:
            yf_df[col] = yf_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)

    yf_final = calc_index(yf_df)
    yf_records = df_to_records(yf_final, "yfinance")
    print(f"[STEP2] yfinance: {len(yf_records)}条", file=sys.stderr)
    print(json.dumps(yf_records, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(json.dumps([], ensure_ascii=False))