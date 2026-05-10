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

HAS_AKSHARE = False
HAS_YFINANCE = False

try:
    import akshare as ak
    HAS_AKSHARE = True
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


def get_akshare_full(stock_code, start_year, end_year):
    if not HAS_AKSHARE:
        print("[AK] akshare未安装", file=sys.stderr)
        return pd.DataFrame()

    try:
        pro = ak.stock_financial_report_sina(stock=stock_code, symbol="利润表")
        bal = ak.stock_financial_report_sina(stock=stock_code, symbol="资产负债表")
        cas = ak.stock_financial_report_sina(stock=stock_code, symbol="现金流量表")

        if pro.empty:
            print("[AK] 利润表无数据", file=sys.stderr)
            return pd.DataFrame()

        df = pro.merge(bal, on="报告期", how="left").merge(cas, on="报告期", how="left")

        df = df.rename(columns={
            "营业总收入": "营业收入",
            "营业总成本": "营业成本",
            "净利润": "归母净利润",
            "交易性金融资产": "短期理财",
            "经营活动产生的现金流量净额": "经营活动现金流净额",
        })

        for col in df.columns:
            if "所有者权益" in col and "少数股东" not in col:
                df.rename(columns={col: "股东权益"}, inplace=True)
                break

        df["报告期"] = pd.to_datetime(df["报告期"])
        df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]

        if df.empty:
            print("[AK] 日期筛选后无数据", file=sys.stderr)
            return pd.DataFrame()

        need = ["报告期", "营业收入", "营业成本", "归母净利润",
                "存货", "应收账款", "货币资金", "短期理财", "合同负债",
                "股东权益", "经营活动现金流净额"]
        for c in need:
            if c not in df.columns:
                df[c] = 0
            else:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df = df.sort_values("报告期").reset_index(drop=True)

        flow_cols = ["营业收入", "营业成本", "归母净利润", "经营活动现金流净额"]
        for c in flow_cols:
            if c in df.columns and len(df) > 0:
                orig = df[c].copy()
                df[c] = df[c].diff()
                df.loc[0, c] = orig.iloc[0]

        for _, row in df.iterrows():
            d = row["报告期"]
            vals = {c: round(row[c], 1) if pd.notna(row[c]) else 0 for c in need if c != "报告期"}
            print(f"[AK] {d.strftime('%Y-%m-%d')}: {vals}", file=sys.stderr)

        return df[need]
    except Exception as e:
        print(f"[AK] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
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
    print(f" 股票:{STOCK_CODE}  {START_YEAR}-{END_YEAR}  ak={HAS_AKSHARE} yf={HAS_YFINANCE}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    print("\n### 第1步: akshare", file=sys.stderr)
    ak_df = get_akshare_full(STOCK_CODE, START_YEAR, END_YEAR)

    if not ak_df.empty:
        monetary = ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                     "货币资金", "短期理财", "合同负债", "股东权益", "经营活动现金流净额"]
        for col in ak_df.columns:
            if col in monetary:
                ak_df[col] = ak_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)

        ak_final = calc_index(ak_df)
        ak_records = df_to_records(ak_final, "akshare")
        print(f"[STEP1] akshare: {len(ak_records)}条", file=sys.stderr)
        print(json.dumps(ak_records, ensure_ascii=False))
        return

    print("[STEP1] akshare无数据, 尝试yfinance", file=sys.stderr)
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