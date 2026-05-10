import pandas as pd

HAS_YFINANCE = False
try:
    import yfinance as yf
    HAS_YFINANCE = True
except Exception:
    pass


def get_yfinance_data(stock_code, start_year, end_year):
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