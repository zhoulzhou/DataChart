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

COLUMN_RENAME = {
    "营业总收入": "营业收入",
    "营业总成本": "营业成本",
    "净利润": "归母净利润",
    "归属于母公司所有者的净利润": "归母净利润",
    "归属于上市公司股东的扣除非经常性损益的净利润": "归母净利润",
    "交易性金融资产": "短期理财",
    "所有者权益(或股东权益)合计": "股东权益",
    "经营活动产生的现金流量净额": "经营活动现金流净额",
}

NEED_COLS = ["报告期", "营业收入", "营业成本", "归母净利润",
             "存货", "应收账款", "货币资金", "短期理财", "合同负债",
             "股东权益", "经营活动现金流净额",
             "短期借款", "一年内到期的非流动负债", "长期借款", "应付债券",
             "利息支出"]

FLOW_COLS = ["营业收入", "营业成本", "归母净利润", "经营活动现金流净额", "利息支出"]


def to_quarter(df):
    """将财务指标累计值转换为单季度值"""
    if pd is None:
        return df
    df = df.sort_values("报告期").reset_index(drop=True)
    for col in FLOW_COLS:
        if col in df.columns:
            df[col] = df.groupby(df["报告期"].dt.year)[col].diff().fillna(df[col])
    return df


def _normalize_date_col(df, label):
    if df.empty:
        print(f"[AK] {label} 为空", file=sys.stderr)
        return df
    for col in df.columns:
        if col in ("报告日", "日期", "报告期"):
            df.rename(columns={col: "报告期"}, inplace=True)
            return df
    print(f"[AK] {label} 无日期列, 列名: {list(df.columns[:6])}", file=sys.stderr)
    return df


def _rename_and_trim(df, label):
    df = _normalize_date_col(df, label)
    if df.empty or "报告期" not in df.columns:
        return df
    if "归属于母公司所有者的净利润" in df.columns and "净利润" in df.columns:
        df = df.drop(columns=["净利润"])
    for old_name, new_name in COLUMN_RENAME.items():
        if old_name in df.columns and new_name in df.columns:
            df = df.drop(columns=[old_name])
    df = df.rename(columns=COLUMN_RENAME)
    df = df.loc[:, ~df.columns.duplicated()]
    keep = [c for c in dict.fromkeys(NEED_COLS) if c in df.columns]
    if "报告期" not in keep:
        keep.insert(0, "报告期")
    print(f"[AK] {label} rename后列: {keep}", file=sys.stderr)
    return df[keep]


def get_akshare_data(stock_code, start_year, end_year):
    if pd is None:
        print("[AK] pandas未安装", file=sys.stderr)
        return None
    if not HAS_AKSHARE:
        print("[AK] akshare未安装", file=sys.stderr)
        return pd.DataFrame()

    try:
        profit = ak.stock_financial_report_sina(stock=stock_code, symbol="利润表")
        balance = ak.stock_financial_report_sina(stock=stock_code, symbol="资产负债表")
        cashflow = ak.stock_financial_report_sina(stock=stock_code, symbol="现金流量表")

        profit = _rename_and_trim(profit, "利润表")
        balance = _rename_and_trim(balance, "资产负债表")
        cashflow = _rename_and_trim(cashflow, "现金流量表")

        if profit.empty or "报告期" not in profit.columns:
            print("[AK] 利润表无报告期列", file=sys.stderr)
            return pd.DataFrame()

        df = profit
        if not balance.empty and "报告期" in balance.columns:
            df = df.merge(balance, on="报告期", how="inner", suffixes=("", "_drop"))
            df = df[[c for c in df.columns if not c.endswith("_drop")]]
        else:
            print("[AK] 资产负债表跳过", file=sys.stderr)
        if not cashflow.empty and "报告期" in cashflow.columns:
            df = df.merge(cashflow, on="报告期", how="inner", suffixes=("", "_drop"))
            df = df[[c for c in df.columns if not c.endswith("_drop")]]
        else:
            print("[AK] 现金流量表跳过", file=sys.stderr)

        df["报告期"] = pd.to_datetime(df["报告期"], errors="coerce")
        df = df[df["报告期"].dt.year.between(start_year, end_year)]

        if df.empty:
            print("[AK] 日期筛选后无数据", file=sys.stderr)
            return pd.DataFrame()

        for c in NEED_COLS:
            if c == "报告期":
                continue
            if c not in df.columns:
                df[c] = 0
            else:
                col_data = df[c]
                if isinstance(col_data, pd.DataFrame):
                    col_data = col_data.iloc[:, 0]
                df[c] = pd.to_numeric(col_data, errors="coerce").fillna(0)

        df = to_quarter(df)

        for _, row in df.iterrows():
            d = row["报告期"]
            vals = {}
            for c in NEED_COLS:
                if c == "报告期":
                    continue
                v = row[c]
                try:
                    if isinstance(v, pd.Series):
                        v = v.iloc[0]
                    vals[c] = round(float(v), 1) if pd.notna(v) else 0
                except Exception:
                    vals[c] = 0
            print(f"[AK] {d.strftime('%Y-%m-%d')}: {vals}", file=sys.stderr)

        return df[NEED_COLS]
    except Exception as e:
        print(f"[AK] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return pd.DataFrame()