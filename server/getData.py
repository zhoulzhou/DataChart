import sys
import json
import warnings
import traceback
warnings.filterwarnings("ignore")

try:
    import pandas as pd
except Exception as e:
    print(json.dumps({
        "yfinance": {"records": [], "msg": ""},
        "baostock": {"records": [], "msg": ""},
        "error": f"pandas 未安装: {e}"
    }, ensure_ascii=False))
    sys.exit(0)

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

HAS_YFINANCE = False
HAS_BAOSTOCK = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except Exception:
    pass

try:
    import baostock as bs
    HAS_BAOSTOCK = True
except Exception:
    pass


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


def get_yfinance_quarterly(stock_code, start_year, end_year):
    if not HAS_YFINANCE:
        print("[yfinance] yfinance 未安装，跳过", file=sys.stderr)
        return pd.DataFrame(), "yfinance 未安装"

    try:
        code = fix_code(stock_code)
        ticker = yf.Ticker(code)
        q_is = ticker.quarterly_financials
        q_bs = ticker.quarterly_balance_sheet
        q_cf = ticker.quarterly_cashflow

        if q_is.empty:
            print("[yfinance] 无利润表数据", file=sys.stderr)
            return pd.DataFrame(), "无利润表数据"

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

        return df, "ok"
    except Exception as e:
        print(f"[yfinance] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return pd.DataFrame(), str(e)


def get_baostock_quarterly(stock_code, start_year, end_year):
    if not HAS_BAOSTOCK:
        print("[baostock] baostock 未安装，跳过", file=sys.stderr)
        return pd.DataFrame(), "baostock 未安装"

    try:
        lg = bs.login()
        if lg.error_code != "0":
            print(f"[baostock] 登录失败: {lg.error_msg}", file=sys.stderr)
            bs.logout()
            return pd.DataFrame(), f"登录失败: {lg.error_msg}"

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
                            row = {
                                "year": year, "quarter": q,
                                "statDate": str(r.get("statDate", "")),
                                "营业收入": to_yi(r.get("MBRevenue", 0), 100),
                                "营业成本": 0,
                                "归母净利润": to_yi(r.get("netProfit", 0), 10000),
                                "存货": 0, "应收账款": 0,
                                "货币资金": 0, "短期理财": 0,
                                "合同负债": 0, "股东权益": 0,
                                "经营活动现金流净额": 0
                            }
                            rows.append(row)
                except Exception:
                    continue

        bs.logout()
        if not rows:
            print("[baostock] 无数据", file=sys.stderr)
            return pd.DataFrame(), "无数据"

        return pd.DataFrame(rows), "ok"
    except Exception as e:
        print(f"[baostock] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            bs.logout()
        except Exception:
            pass
        return pd.DataFrame(), str(e)


def df_to_records(df):
    if df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        r = {}
        for col in df.columns:
            v = row[col]
            r[col] = 0 if pd.isna(v) else v
        records.append(r)
    return records


def make_result(yf_df, bs_df, yf_msg, bs_msg):
    if not yf_df.empty:
        for col in yf_df.columns:
            if col in MONETARY:
                yf_df[col] = yf_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)
    if not bs_df.empty:
        for col in bs_df.columns:
            if col in MONETARY:
                bs_df[col] = bs_df[col].apply(lambda x: float(x) if pd.notna(x) else 0)

    yf_records = df_to_records(yf_df)
    bs_records = df_to_records(bs_df)

    return {
        "yfinance": {"records": yf_records, "msg": yf_msg},
        "baostock": {"records": bs_records, "msg": bs_msg}
    }


def main():
    print("=" * 60, file=sys.stderr)
    print(f" 股票代码: {STOCK_CODE}  (Yahoo: {HAS_YFINANCE}  Baostock: {HAS_BAOSTOCK})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    yf_df, yf_msg = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    bs_df, bs_msg = get_baostock_quarterly(STOCK_CODE, START_YEAR, END_YEAR)

    result = make_result(yf_df, bs_df, yf_msg, bs_msg)

    yf_records = result["yfinance"]["records"]
    bs_records = result["baostock"]["records"]

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "yfinance": {"records": [], "msg": ""},
            "baostock": {"records": [], "msg": ""},
            "error": str(e)
        }, ensure_ascii=False))