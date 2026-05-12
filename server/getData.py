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
START_YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
END_YEAR = int(sys.argv[3]) if len(sys.argv) > 3 else int(__import__('datetime').datetime.now().year)

AK_AVAILABLE = False
YF_AVAILABLE = False

try:
    from getAkshare import get_akshare_data, HAS_AKSHARE
    AK_AVAILABLE = HAS_AKSHARE
except Exception:
    def get_akshare_data(stock_code, start_year, end_year):
        return pd.DataFrame()

try:
    from getYfinance import get_yfinance_data, HAS_YFINANCE
    YF_AVAILABLE = HAS_YFINANCE
except Exception:
    def get_yfinance_data(stock_code, start_year, end_year):
        return pd.DataFrame()


def to_yi(val):
    try:
        n = pd.to_numeric(val, errors="coerce")
        if pd.isna(n):
            return 0
        return round(float(n) / 100000000, 1)
    except Exception:
        return 0


MONETARY_COLS = ["营业收入", "营业成本", "归母净利润", "存货", "应收账款",
                 "货币资金", "短期理财", "合同负债", "股东权益", "经营活动现金流净额"]


def to_yi_dataframe(df):
    df = df.loc[:, ~df.columns.duplicated()]
    for col in df.columns:
        if col in MONETARY_COLS:
            df[col] = df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)
    return df


def calc_index(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["现金总额(含短期理财)"] = df["货币资金"] + df["短期理财"].fillna(0)
    df["毛利"] = df["营业收入"] - df["营业成本"]
    df["毛利率(%)"] = (df["毛利"] / df["营业收入"].replace(0, pd.NA) * 100).fillna(0).round(1)
    df["净利率(%)"] = (df["归母净利润"] / df["营业收入"].replace(0, pd.NA) * 100).fillna(0).round(1)

    df["上期权益"] = df["股东权益"].shift(1)
    df["平均权益"] = (df["股东权益"] + df["上期权益"]) / 2
    df["ROE(%)"] = (df["归母净利润"] / df["平均权益"].replace(0, pd.NA) * 100).fillna(0).round(1)

    df["TTM_营业成本"] = df["营业成本"].rolling(4).sum()
    df["存货_去年同期"] = df["存货"].shift(4)
    df["平均存货"] = (df["存货"] + df["存货_去年同期"]) / 2
    df["存货周转天数"] = (df["平均存货"] * 365 / df["TTM_营业成本"].replace(0, pd.NA)).fillna(0).round(1)

    df["TTM_营业收入"] = df["营业收入"].rolling(4).sum()
    df["应收_去年同期"] = df["应收账款"].shift(4)
    df["平均应收"] = (df["应收账款"] + df["应收_去年同期"]) / 2
    df["应收周转天数"] = (df["平均应收"] * 365 / df["TTM_营业收入"].replace(0, pd.NA)).fillna(0).round(1)

    return df[[
        "报告期", "营业收入", "营业成本", "毛利", "毛利率(%)",
        "归母净利润", "净利率(%)", "ROE(%)",
        "货币资金", "短期理财", "现金总额(含短期理财)",
        "存货", "存货周转天数", "应收账款", "应收周转天数",
        "经营活动现金流净额", "合同负债", "股东权益"
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


def process_and_output(df, source_label):
    if df is None or df.empty:
        return False
    df = to_yi_dataframe(df)
    final = calc_index(df)
    records = df_to_records(final, source_label)
    print(f"[{source_label}] {len(records)}条", file=sys.stderr)
    print(json.dumps(records, ensure_ascii=False))
    return True


def main():
    print("=" * 70, file=sys.stderr)
    print(f" 股票:{STOCK_CODE}  {START_YEAR}-{END_YEAR}  ak={AK_AVAILABLE} yf={YF_AVAILABLE}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    print("\n### akshare", file=sys.stderr)
    ak_df = get_akshare_data(STOCK_CODE, START_YEAR, END_YEAR)
    if ak_df is not None and process_and_output(ak_df, "akshare"):
        return

    print("[akshare] 无数据, 尝试 yfinance", file=sys.stderr)
    print("\n### yfinance", file=sys.stderr)
    yf_df = get_yfinance_data(STOCK_CODE, START_YEAR, END_YEAR)
    if yf_df is not None and process_and_output(yf_df, "yfinance"):
        return

    print("[yfinance] 也无数据", file=sys.stderr)
    print(json.dumps([], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(json.dumps([], ensure_ascii=False))