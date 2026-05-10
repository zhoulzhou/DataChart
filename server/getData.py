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

print("[INIT] 开始导入 yfinance...", file=sys.stderr)
try:
    import yfinance as yf
    HAS_YFINANCE = True
    print("[INIT] yfinance 导入成功", file=sys.stderr)
except Exception as e:
    print(f"[INIT] yfinance 导入失败: {e}", file=sys.stderr)

print("[INIT] 开始导入 baostock...", file=sys.stderr)
try:
    import baostock as bs
    HAS_BAOSTOCK = True
    print("[INIT] baostock 导入成功", file=sys.stderr)
except Exception as e:
    print(f"[INIT] baostock 导入失败: {e}", file=sys.stderr)

print(f"[INIT] 环境: yfinance={HAS_YFINANCE} baostock={HAS_BAOSTOCK} pandas=OK", file=sys.stderr)


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
        print("[YF] yfinance 未安装，跳过", file=sys.stderr)
        return pd.DataFrame(), "yfinance未安装"

    try:
        code = fix_code(stock_code)
        print(f"[YF] 股票代码: {stock_code} -> {code}", file=sys.stderr)

        ticker = yf.Ticker(code)
        print(f"[YF] Ticker 创建成功, info keys: {list(ticker.info.keys())[:10] if ticker.info else 'None'}", file=sys.stderr)

        print("[YF] 获取 quarterly_financials...", file=sys.stderr)
        q_is = ticker.quarterly_financials
        print(f"[YF] quarterly_financials shape: {q_is.shape}, empty={q_is.empty}", file=sys.stderr)
        if not q_is.empty:
            print(f"[YF]   columns: {list(q_is.columns)[:5]}...", file=sys.stderr)
            print(f"[YF]   index: {list(q_is.index)[:5]}...", file=sys.stderr)
            for idx in list(q_is.index)[:3]:
                row_vals = {k: q_is.loc[idx, k] for k in list(q_is.columns)[:5]}
                print(f"[YF]   {idx}: {row_vals}", file=sys.stderr)

        print("[YF] 获取 quarterly_balance_sheet...", file=sys.stderr)
        q_bs = ticker.quarterly_balance_sheet
        print(f"[YF] quarterly_balance_sheet shape: {q_bs.shape}, empty={q_bs.empty}", file=sys.stderr)
        if not q_bs.empty:
            print(f"[YF]   columns: {list(q_bs.columns)[:5]}...", file=sys.stderr)

        print("[YF] 获取 quarterly_cashflow...", file=sys.stderr)
        q_cf = ticker.quarterly_cashflow
        print(f"[YF] quarterly_cashflow shape: {q_cf.shape}, empty={q_cf.empty}", file=sys.stderr)
        if not q_cf.empty:
            print(f"[YF]   columns: {list(q_cf.columns)[:5]}...", file=sys.stderr)

        if q_is.empty:
            print("[YF] 无利润表数据，跳过", file=sys.stderr)
            return pd.DataFrame(), "无利润表数据"

        q_is = q_is.T
        print(f"[YF] 转置后 profit shape: {q_is.shape}", file=sys.stderr)
        q_bs = q_bs.T if not q_bs.empty else pd.DataFrame()
        q_cf = q_cf.T if not q_cf.empty else pd.DataFrame()

        dfs = [q_is]
        if not q_bs.empty:
            dfs.append(q_bs)
        if not q_cf.empty:
            dfs.append(q_cf)

        df = pd.concat(dfs, axis=1)
        print(f"[YF] 合并后 shape: {df.shape}, columns: {list(df.columns)[:10]}...", file=sys.stderr)
        df = df.reset_index()
        df.rename(columns={"index": "报告期"}, inplace=True)

        df["报告期"] = pd.to_datetime(df["报告期"])
        df = df[(df["报告期"].dt.year >= start_year) & (df["报告期"].dt.year <= end_year)]
        print(f"[YF] 筛选 {start_year}-{end_year} 后: {len(df)} 行", file=sys.stderr)
        print(f"[YF] 报告期: {list(df['报告期'].astype(str).values)}", file=sys.stderr)

        for eng, cn in FIELD_MAP.items():
            if eng in df.columns:
                df.rename(columns={eng: cn}, inplace=True)
                print(f"[YF] 字段映射: {eng} -> {cn}", file=sys.stderr)
            else:
                print(f"[YF] 字段缺失: {eng} (不在{list(df.columns)[:15]}...)", file=sys.stderr)

        for _, row in df.iterrows():
            dt = row["报告期"]
            vals = {}
            for cn in FIELD_MAP.values():
                if cn in df.columns:
                    vals[cn] = row[cn]
            print(f"[YF] {dt.date()} 原始值: {vals}", file=sys.stderr)

        print("[YF] 完成", file=sys.stderr)
        return df, "ok"
    except Exception as e:
        print(f"[YF] 异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return pd.DataFrame(), str(e)[:100]


def get_baostock_quarterly(stock_code, start_year, end_year):
    if not HAS_BAOSTOCK:
        print("[BS] baostock 未安装，跳过", file=sys.stderr)
        return pd.DataFrame(), "baostock未安装"

    try:
        print("[BS] 登录 baostock...", file=sys.stderr)
        lg = bs.login()
        print(f"[BS] 登录结果: error_code={lg.error_code} error_msg={lg.error_msg}", file=sys.stderr)
        if lg.error_code != "0":
            bs.logout()
            return pd.DataFrame(), f"登录失败:{lg.error_msg}"

        if stock_code.startswith(("3", "0")):
            code = f"sz.{stock_code}"
        else:
            code = f"sh.{stock_code}"
        print(f"[BS] 股票代码: {stock_code} -> {code}", file=sys.stderr)

        rows = []
        for year in range(start_year, end_year + 1):
            for q in [1, 2, 3, 4]:
                try:
                    print(f"[BS] 查询 {year}Q{q}...", file=sys.stderr)
                    rs = bs.query_profit_data(code=code, year=year, quarter=q)
                    print(f"[BS]   query_profit_data: error_code={rs.error_code}", file=sys.stderr)
                    if rs.error_code == "0":
                        pdf = rs.get_data()
                        print(f"[BS]   get_data shape: {pdf.shape}, empty={pdf.empty}", file=sys.stderr)
                        if not pdf.empty:
                            r = pdf.iloc[0].to_dict()
                            print(f"[BS]   原始数据: {r}", file=sys.stderr)
                            mr = r.get("MBRevenue", 0)
                            np_val = r.get("netProfit", 0)
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
                            print(f"[BS]   转换后: MBRevenue({mr}) -> 营业收入亿({row['营业收入']}), netProfit({np_val}) -> 归母净利润亿({row['归母净利润']})", file=sys.stderr)
                            rows.append(row)
                except Exception as ex:
                    print(f"[BS] {year}Q{q} 异常: {ex}", file=sys.stderr)

        bs.logout()
        print(f"[BS] 共获取 {len(rows)} 条", file=sys.stderr)
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
        for col in df.columns:
            v = row[col]
            r[col] = 0 if pd.isna(v) else v
        records.append(r)
    return records


def make_result(yf_df, bs_df, yf_msg, bs_msg):
    print(f"[RESULT] yfinance: {len(yf_df)}行 msg={yf_msg}, baostock: {len(bs_df)}行 msg={bs_msg}", file=sys.stderr)

    if not yf_df.empty:
        print("[RESULT] yfinance 元->亿转换...", file=sys.stderr)
        for col in yf_df.columns:
            if col in MONETARY:
                yf_df[col] = yf_df[col].apply(lambda x: to_yi(x) if pd.notna(x) else 0)
    if not bs_df.empty:
        print("[RESULT] baostock 值规范化...", file=sys.stderr)
        for col in bs_df.columns:
            if col in MONETARY:
                bs_df[col] = bs_df[col].apply(lambda x: float(x) if pd.notna(x) else 0)

    yf_records = df_to_records(yf_df)
    bs_records = df_to_records(bs_df)

    print(f"[RESULT] 最终: yfinance {len(yf_records)}条, baostock {len(bs_records)}条", file=sys.stderr)

    return {
        "yfinance": {"records": yf_records, "msg": yf_msg},
        "baostock": {"records": bs_records, "msg": bs_msg}
    }


def main():
    print("=" * 60, file=sys.stderr)
    print(f"[MAIN] 股票: {STOCK_CODE} 年份: {START_YEAR}-{END_YEAR}", file=sys.stderr)
    print(f"[MAIN] yfinance={HAS_YFINANCE} baostock={HAS_BAOSTOCK}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    print("[MAIN] 开始获取 yfinance 数据...", file=sys.stderr)
    yf_df, yf_msg = get_yfinance_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    print(f"[MAIN] yfinance 完成: {len(yf_df)}行, msg={yf_msg}", file=sys.stderr)

    print("[MAIN] 开始获取 baostock 数据...", file=sys.stderr)
    bs_df, bs_msg = get_baostock_quarterly(STOCK_CODE, START_YEAR, END_YEAR)
    print(f"[MAIN] baostock 完成: {len(bs_df)}行, msg={bs_msg}", file=sys.stderr)

    result = make_result(yf_df, bs_df, yf_msg, bs_msg)
    print("[MAIN] 输出 JSON...", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] 未捕获异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({
            "yfinance": {"records": [], "msg": ""},
            "baostock": {"records": [], "msg": ""},
            "error": str(e)
        }, ensure_ascii=False))