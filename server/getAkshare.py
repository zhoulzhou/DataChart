import sys
import traceback

try:
    import pandas as pd
except Exception:
    pd = None

HAS_AKSHARE = False
try:
    import akshare as ak
    HAS_AKSHARE = True
except Exception:
    pass


def get_akshare_data(stock_code, start_year, end_year):
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