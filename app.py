from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date, datetime

DB_NAME = "kakeibo.db"

app = Flask(__name__)


def init_db():
    """アプリ起動時に一度だけテーブルを作成"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT,
            amount INTEGER NOT NULL,
            memo TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_db():
    """DB接続用ヘルパー"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_month_range(year: int, month: int):
    """指定年月の開始日と翌月開始日（[start, end) 範囲）を返す"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


@app.route("/")
def root():
    """ルートは当月の月別画面へリダイレクト"""
    today = date.today()
    return redirect(url_for("month_view", year=today.year, month=today.month))


@app.route("/month")
def month_view():
    """月別の一覧 + 合計 + カテゴリ別グラフ"""
    # パラメータから年月取得（なければ今日）
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    today = date.today()
    if not year:
        year = today.year
    if not month:
        month = today.month

    start, end = get_month_range(year, month)

    conn = get_db()
    cur = conn.cursor()

    # 対象月の明細一覧
    cur.execute(
        """
        SELECT id, date, category, amount, memo
        FROM items
        WHERE date >= ? AND date < ?
        ORDER BY date DESC, id DESC
        """,
        (start, end),
    )
    items = cur.fetchall()

    # 対象月の合計
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM items
        WHERE date >= ? AND date < ?
        """,
        (start, end),
    )
    row_total = cur.fetchone()
    total = row_total["total"] if row_total else 0

    # カテゴリ別合計（グラフ用）
    cur.execute(
        """
        SELECT
            COALESCE(NULLIF(category, ''), '未分類') AS category,
            SUM(amount) AS total_amount
        FROM items
        WHERE date >= ? AND date < ?
        GROUP BY COALESCE(NULLIF(category, ''), '未分類')
        ORDER BY total_amount DESC
        """,
        (start, end),
    )
    cat_rows = cur.fetchall()
    category_labels = [r["category"] for r in cat_rows]
    category_values = [r["total_amount"] for r in cat_rows]

    # 登録されている年月一覧（セレクトボックス用）
    cur.execute(
        """
        SELECT
            substr(date, 1, 7) AS ym,
            SUM(amount) AS total_amount
        FROM items
        GROUP BY substr(date, 1, 7)
        ORDER BY ym DESC
        """
    )
    months = cur.fetchall()
    months_info = []
    for m in months:
        ym = m["ym"]  # 'YYYY-MM'
        try:
            y, mo = ym.split("-")
            y_int = int(y)
            mo_int = int(mo)
        except Exception:
            continue
        months_info.append(
            {
                "year": y_int,
                "month": mo_int,
                "ym": ym,
                "total_amount": m["total_amount"],
            }
        )

    conn.close()

    # テンプレートに渡す
    return render_template(
        "index.html",
        items=items,
        total=total,
        year=year,
        month=month,
        category_labels=category_labels,
        category_values=category_values,
        months_info=months_info,
    )


@app.route("/add", methods=["POST"])
def add():
    """明細追加"""
    # フォームから取得
    date_str = request.form.get("date") or date.today().isoformat()
    category = request.form.get("category", "").strip()
    amount_str = request.form.get("amount", "").strip()
    memo = request.form.get("memo", "").strip()

    redirect_year = request.form.get("redirect_year", type=int)
    redirect_month = request.form.get("redirect_month", type=int)

    # 金額チェック
    if not amount_str.isdigit():
        # 金額不正なら元の画面に戻す
        if redirect_year and redirect_month:
            return redirect(
                url_for("month_view", year=redirect_year, month=redirect_month)
            )
        # フォールバック
        d_obj = _safe_parse_date(date_str)
        return redirect(url_for("month_view", year=d_obj.year, month=d_obj.month))

    amount = int(amount_str)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO items (date, category, amount, memo) VALUES (?, ?, ?, ?)",
        (date_str, category, amount, memo),
    )
    conn.commit()
    conn.close()

    # どの年月にリダイレクトするか
    if redirect_year and redirect_month:
        return redirect(url_for("month_view", year=redirect_year, month=redirect_month))
    else:
        d_obj = _safe_parse_date(date_str)
        return redirect(url_for("month_view", year=d_obj.year, month=d_obj.month))


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    """明細削除"""
    redirect_year = request.form.get("redirect_year", type=int)
    redirect_month = request.form.get("redirect_month", type=int)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    if redirect_year and redirect_month:
        return redirect(url_for("month_view", year=redirect_year, month=redirect_month))

    # パラメータが無い場合は今日の月へ
    today = date.today()
    return redirect(url_for("month_view", year=today.year, month=today.month))


def _safe_parse_date(s: str) -> date:
    """'YYYY-MM-DD' を date に変換する（失敗したら今日）"""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return date.today()


# Render の gunicorn からimportされたときにもテーブル作成する
init_db()

if __name__ == "__main__":
    # ローカル実行用
    app.run(host="0.0.0.0", port=10000, debug=True)
