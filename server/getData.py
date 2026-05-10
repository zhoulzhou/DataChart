import sys
import json
import warnings
import traceback
warnings.filterwarnings("ignore")

try:
    import pandas as pd
except Exception as e:
    print("[FATAL] pandas 未安装", file=sys.stderr)
    print(json.dumps({"yfinance": {"records": [], "msg": f"pandas未安装:{e}"}, "baostock": {"records": [], "msg": ""}}, ensure_ascii=False))
    sys.exit(0)

STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else "300308"
START_YEAR = 2024
END_YEAR = int(__import__('datetime').datetime.now().year)

FIELD_ALIAS_MAP = {
    "营业收入": ["Total Revenue", "Total Revenues", "Revenue", "Operating Revenue", "Revenues"],
    "营业成本": ["Cost Of Revenue", "Cost of Revenue", "Cost Of Sales", "Cost of Goods Sold", "Operating Expense", "Operating Expenses"],
    "归母净利润": ["Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operations", "Net Profit"],
    "存货": ["Inventory", "Inventories", "Inventory Net"],
    "应收账款": ["Accounts Receivable", "Receivables", "Trade And Other Receivables", "Accounts Receivables"],
    "货币资金": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash", "Cash & Equivalents"],
    "短期理财": ["Short Term Investments", "Short-term Investments", "Marketable Securities", "Current Investments"],
    "合同负债": ["Contract Liabilities", "Contract Liability", "Deferred Revenue", "Current Deferred Revenue"],
    "股东权益": ["Total Stockholder Equity", "Total Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"],
    "经营活动现金流净额": ["Operating Cash Flow", "Cash From Operating Activities", "Operating Cashflows", "Net Cash From Operating Activities"]
}

MONETARY = set(FIELD_ALIAS_MAP.keys())

HAS_YFINANCE = False
HAS_BAOSTOCK = False

print("[INIT] 导入 yfinance...", file=sys.stderr)
try:
    import yfinance as yf
    HAS_YFINANCE = True
    print("[INIT] yfinance OK", file=sys.stderr)
except Exception as e:
    print(f"[INIT] yfinance 失败: {e}", file=sys.stderr)

print("[INIT] 导入 baostock...", file=sys.stderr)
try:
    import baostock as bs
    HAS_BAOSTOCK = True
    print("[INIT] baostock OK", file=sys.stderr)
except Exception as e:
    print(f"[INIT] baostock 失败: {e}", file=sys.stderr)


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


def safe_val(v):
    if v is None:
        return 0
    if pd.isna(v):
        return 0
    if isinstance(v, (pd.Timestamp,)):
        return str(v)
    if isinstance(v, float):
        return v
    try:
        return float(v)
    except (ValueError, TypeError):
        return str(v)


def map_fields(df):
    found = {}
    missing = []
    for cn, candidates in FIELD_ALIAS_MAP.items():
        matched = None
        for eng in candidates:
            if eng in df.columns:
                matched = eng
                break
        if matched:
            found[matched] = cn
        else:
            missing.append(f"{cn}({'|'.join(candidates[:3])})")

    if missing:
        print(f"[MAP] 未匹配字段: {missing}", file=sys.stderr)
        print(f"[MAP] 可用字段: {list(df.columns)}", file=sys.stderr)

    df = df.rename(columns=found)
    for cn in FIELD_ALIAS_MAP:
        if cn not in df.columns:
            df[cn] = 0
    return df


def get_yfinance_quarterly(stock_code, start_year, end_year):
    if not HAS_YFINANCE:
        return pd.DataFrame(), "yfinance未安装"

    try:
        code = fix_code(stock_code)
        print(f"[YF] 代码: {code}", file=sys.stderr)
        ticker = yf.Ticker(code)

        print("[YF] 取 quarterly_financials...", file=sys.stderr)
        q_is = ticker.quarterly_financials
        print(f"[YF]   shape={q_is.shape} empty={q_is.empty}", file=sys.stderr)
        if q_is.empty:
            print("[YF] 无利润表，退出", file=sys.stderr)
            return pd.DataFrame(), "无利润表"

        print("[YF] 取 quarterly_balance_sheet...", file=sys.stderr)
        q_bs = ticker.quarterly_balance_sheet
        print(f"[YF]   shape={q_bs.shape} empty={q_bs.empty}", file=sys.stderr)

        print("[YF] 取 quarterly_cashflow...", file=sys.stderr)
        q_cf = ticker.quarterly_cashflow
        print(f"[YF]   shape={q_cf.shape} empty={q_cf.empty}", file=sys.stderr)

        q_is = q_is.T
        q_bs = q_bs.T if not q_bs.empty else pd.DataFrame()
        q_cf = q_cf.T if not q_cf.empty else pd.DataFrame()

        dfs = [q_is]
        if not q_bs.empty:
            dfs.append(q_bs)
        if not q_cf.empty:
            dfs.append(q_cf)

        df = pd.concat(dfs, axis=1)
        print(f"[YF] 合并 shape={df.shape}", file=sys.stderr)
        df = df.reset_index()
        df.rename(columns={"index": "报告期"}, inplace=True)

        df["报告期"] = pd.to_datetime(df["报告期"])
        df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]
        print(f"[YF] 筛选后 {len(df)}行: {list(df['报告期'].dt.strftime('%Y-%m-%d').values)}", file=sys.stderr)

        df = map_fields(df)

        for _, row in df.iterrows():
            dt = row["报告期"]
            vals = {cn: safe_val(row[cn]) for cn in FIELD_ALIAS_MAP if cn in df.columns}
            print(f"[YF] {dt.strftime('%Y-%m-%d')}: {vals}", file=sys.stderr)

        return df, "ok"
    except Exception as e:
        print(f"[YF] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return pd.DataFrame(), str(e)[:100]


def get_baostock_quarterly(stock_code, start_year, end_year):
    if not HAS_BAOSTOCK:
        return pd.DataFrame(), "baostock未安装"

    try:
        print("[BS] 登录...", file=sys.stderr)
        lg = bs.login()
        print(f"[BS] {lg.error_code} {lg.error_msg}", file=sys.stderr)
        if lg.error_code != "0":
            bs.logout()
            return pd.DataFrame(), f"登录失败:{lg.error_msg}"

        if stock_code.startswith(("3", "0")):
            code = f"sz.{stock_code}"
        else:
            code = f"sh.{stock_code}"

        rows = []
        for year in range(start_year, end_year + 1):
            for q in [1, 2, 3, 4]:
                try:
                    rs = bs.query_profit_data(code=code, year=year, quarter=q)
                    print(f"[BS] {year}Q{q} query: {rs.error_code} {rs.error_msg}", file=sys.stderr)
                    if rs.error_code == "0":
                        pdf = rs.get_data()
                        if not pdf.empty:
                            r = pdf.iloc[0].to_dict()
                            print(f"[BS] {year}Q{q} 原始: {r}", file=sys.stderr)
                            mr = safe_val(r.get("MBRevenue", 0))
                            np_val = safe_val(r.get("netProfit", 0))
                            row = {
                                "year": year, "quarter": q,
                                "statDate": str(r.get("statDate", "")),
                                "营业收入": to_yi(mr, 100),
                                "营业成本": 0,
                                "归母净利润": to_yi(np_val, 10000),
                                "存货": 0, "应收账款": 0,
                                "货币资金": 0, "短期理财": 0,
                                "合同负债": 0, "股东权益": 0,
                                "经营活动现金流净额": 0
                            }
                            print(f"[BS] {year}Q{q} 转亿后: 营收={row['营业收入']} 净利={row['归母净利润']}", file=sys.stderr)
                            rows.append(row)
                except Exception as ex:
                    print(f"[BS] {year}Q{q} 异常: {ex}", file=sys.stderr)

        bs.logout()
        print(f"[BS] 共{len(rows)}条", file=sys.stderr)
        if not rows:
            return pd.DataFrame(), "无数据"
        return pd.DataFrame(rows), "ok"
    except Exception as e:
        print(f"[BS] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            bs.logout()
        except Exception:
            pass
        return pd.DataFrame(), str(e)[:100]


def df_to_records(df):
    if df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        r = {}
        dt = row.get("报告期")
        if dt is not None and not pd.isna(dt):
            if isinstance(dt, pd.Timestamp):
                r["year"] = int(dt.year)
                r["quarter"] = (int(dt.month) - 1) // 3 + 1
                r["statDate"] = dt.strftime("%Y-%m-%d")
            elif isinstance(dt, str):
                r["year"] = "year" in row and int(row["year"])
                r["quarter"] = "quarter" in row and int(row["quarter"])
                r["statDate"] = dt
        elif "year" in row:
            r["year"] = int(row["year"]) if not pd.isna(row["year"]) else 0
            r["quarter"] = int(row["quarter"]) if not pd.isna(row["quarter"]) else 0
            r["statDate"] = str(row.get("statDate", ""))

        for col in df.columns:
            if col == "报告期" or col == "year" or col == "quarter" or col == "statDate":
                continue
            r[col] = safe_val(row[col])
        records.append(r)
    return records


def make_records(df, source):
    if df.empty:
        return [], ""

    if source == "yfinance":
        for col in df.columns:
            if col in MONETARY:
                df[col] = df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)
    else:
        for col in df.columns:
            if col in MONETARY:
                df[col] = df[col].apply(lambda x: safe_val(x))

    return df_to_records(df)


def main():
    print("=" * 70, file=sys.stderr)
    print(f" 股票:{STOCK_CODE}  {START_YEAR}-{END_YEAR}  yf={HAS_YFINANCE} bs={HAS_BAOSTOCK}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    yf_records = []
    yf_msg = ""
    bs_records = []
    bs_msg = ""

    print("\n" + "#" * 70, file=sys.stderr)
    print("### 第1步: yfinance", file=sys.stderr)
    print("#" * 70, file=sys.stderr)

    yf_df, yf_msg = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    print(f"[STEP1] yfinance: {len(yf_df)}行 msg={yf_msg}", file=sys.stderr)

    if not yf_df.empty:
        yf_records = make_records(yf_df, "yfinance")
        print(f"[STEP1] 转记录: {len(yf_records)}条", file=sys.stderr)

    print("\n" + "#" * 70, file=sys.stderr)
    print("### 第2步: baostock", file=sys.stderr)
    print("#" * 70, file=sys.stderr)

    bs_df, bs_msg = get_baostock_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    print(f"[STEP2] baostock: {len(bs_df)}行 msg={bs_msg}", file=sys.stderr)

    if not bs_df.empty:
        bs_records = make_records(bs_df, "baostock")
        print(f"[STEP2] 转记录: {len(bs_records)}条", file=sys.stderr)

    print("\n" + "=" * 70, file=sys.stderr)
    print(f" 最终: yfinance={len(yf_records)}条  baostock={len(bs_records)}条", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    result = {
        "yfinance": {"records": yf_records, "msg": yf_msg},
        "baostock": {"records": bs_records, "msg": bs_msg}
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({
            "yfinance": {"records": [], "msg": ""},
            "baostock": {"records": [], "msg": ""},
            "error": str(e)
        }, ensure_ascii=False))