import hmac
import logging
import os
import secrets
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import mysql.connector
from flask import (
    Flask, abort, current_app, flash, redirect, render_template,
    request, session, url_for,
)
from config import Config, validate_config
from db import (
    close_db, commit, delete_row, execute, insert_row, query_all, query_one,
    rollback, scalar, update_row,
)
from entities import ENTITIES, FK_OPTIONS, NAV_ORDER, get_entity
from validators import compute_line_total, cross_validate, validate_form
PAGE_SIZE = 25
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "Coffee@123"
REPORTS = [
    {
        "title": "Customers with company name",
        "feature": "INNER JOIN, UPPER, LOWER",
        "columns": [
            ("CustomerName", "Customer (upper)", "text"),
            ("Email", "Email (lower)", "text"),
            ("CompanyName", "Company", "text"),
        ],
        "sql": (
            "SELECT UPPER(cu.Name) AS CustomerName, LOWER(cu.Email) AS Email, "
            "co.CompanyName AS CompanyName "
            "FROM Customers cu INNER JOIN Companies co ON co.CompanyID = cu.CompanyID "
            "ORDER BY cu.Name LIMIT 100"
        ),
    },
    {
        "title": "Companies with order counts (including companies with no orders)",
        "feature": "LEFT JOIN, COUNT",
        "columns": [
            ("CompanyName", "Company", "text"),
            ("OrderCount", "Orders", "int"),
        ],
        "sql": (
            "SELECT co.CompanyName AS CompanyName, COUNT(o.OrderID) AS OrderCount "
            "FROM Companies co LEFT JOIN Orders o ON o.CompanyID = co.CompanyID "
            "GROUP BY co.CompanyID, co.CompanyName "
            "ORDER BY OrderCount DESC, co.CompanyName"
        ),
    },
    {
        "title": "Orders per status",
        "feature": "GROUP BY, COUNT, SUM, AVG, MAX, MIN, ROUND",
        "columns": [
            ("Status", "Status", "badge"),
            ("OrderCount", "Orders", "int"),
            ("TotalAmt", "Total", "money"),
            ("AvgAmt", "Average", "money"),
            ("MaxAmt", "Maximum", "money"),
            ("MinAmt", "Minimum", "money"),
        ],
        "sql": (
            "SELECT Status, COUNT(*) AS OrderCount, ROUND(SUM(TotalAmount), 2) AS TotalAmt, "
            "ROUND(AVG(TotalAmount), 2) AS AvgAmt, MAX(TotalAmount) AS MaxAmt, "
            "MIN(TotalAmount) AS MinAmt "
            "FROM Orders GROUP BY Status ORDER BY OrderCount DESC"
        ),
    },
    {
        "title": "Customers with more than one order",
        "feature": "GROUP BY, HAVING",
        "columns": [
            ("Name", "Customer", "text"),
            ("OrderCount", "Orders", "int"),
            ("TotalAmt", "Total", "money"),
        ],
        "sql": (
            "SELECT cu.Name AS Name, COUNT(o.OrderID) AS OrderCount, "
            "ROUND(SUM(o.TotalAmount), 2) AS TotalAmt "
            "FROM Customers cu INNER JOIN Orders o ON o.CustomerID = cu.CustomerID "
            "GROUP BY cu.CustomerID, cu.Name HAVING COUNT(o.OrderID) > 1 "
            "ORDER BY OrderCount DESC, cu.Name"
        ),
    },
    {
        "title": "Products priced above the average price",
        "feature": "Subquery, AVG",
        "columns": [
            ("ProductName", "Product", "text"),
            ("Category", "Category", "text"),
            ("Price", "Price", "money"),
        ],
        "sql": (
            "SELECT ProductName, Category, Price FROM Products "
            "WHERE Price > (SELECT AVG(Price) FROM Products) ORDER BY Price DESC"
        ),
    },
    {
        "title": "Inventory at or below reorder level",
        "feature": "WHERE comparison, INNER JOIN",
        "columns": [
            ("CompanyName", "Company", "text"),
            ("ProductName", "Product", "text"),
            ("Quantity", "Quantity", "int"),
            ("ReorderLevel", "Reorder level", "int"),
        ],
        "sql": (
            "SELECT co.CompanyName AS CompanyName, p.ProductName AS ProductName, "
            "i.Quantity AS Quantity, i.ReorderLevel AS ReorderLevel "
            "FROM Inventory i "
            "INNER JOIN Companies co ON co.CompanyID = i.CompanyID "
            "INNER JOIN Products p ON p.ProductID = i.ProductID "
            "WHERE i.Quantity <= i.ReorderLevel ORDER BY co.CompanyName"
        ),
    },
    {
        "title": "Revenue per product from order items",
        "feature": "SUM, GROUP BY, INNER JOIN",
        "columns": [
            ("ProductName", "Product", "text"),
            ("UnitsSold", "Units sold", "int"),
            ("Revenue", "Revenue", "money"),
        ],
        "sql": (
            "SELECT p.ProductName AS ProductName, SUM(oi.Quantity) AS UnitsSold, "
            "SUM(oi.LineTotal) AS Revenue "
            "FROM OrderItems oi INNER JOIN Products p ON p.ProductID = oi.ProductID "
            "GROUP BY p.ProductID, p.ProductName ORDER BY Revenue DESC"
        ),
    },
    {
        "title": "Customer name length and country code",
        "feature": "LENGTH, SUBSTRING",
        "columns": [
            ("Name", "Customer", "text"),
            ("NameLength", "Name length", "int"),
            ("Country", "Country", "text"),
            ("CountryCode", "First 3 letters", "text"),
        ],
        "sql": (
            "SELECT Name, LENGTH(Name) AS NameLength, Country, "
            "UPPER(SUBSTRING(Country, 1, 3)) AS CountryCode "
            "FROM Customers ORDER BY Name LIMIT 100"
        ),
    },
    {
        "title": "Payments per method",
        "feature": "GROUP BY, COUNT, SUM",
        "columns": [
            ("PaymentMethod", "Method", "text"),
            ("PaymentCount", "Payments", "int"),
            ("TotalAmount", "Total", "money"),
        ],
        "sql": (
            "SELECT PaymentMethod, COUNT(*) AS PaymentCount, SUM(Amount) AS TotalAmount "
            "FROM Payments GROUP BY PaymentMethod ORDER BY TotalAmount DESC"
        ),
    },
    {
        "title": "Employees per department",
        "feature": "GROUP BY, COUNT, AVG, ROUND",
        "columns": [
            ("Department", "Department", "text"),
            ("EmployeeCount", "Employees", "int"),
            ("AvgSalary", "Average salary", "money"),
        ],
        "sql": (
            "SELECT Department, COUNT(*) AS EmployeeCount, ROUND(AVG(Salary), 2) AS AvgSalary "
            "FROM Employees GROUP BY Department ORDER BY EmployeeCount DESC"
        ),
    },
]
# ---------------------------------------------------------------- helpers
def entity_or_404(entity_key):
    entity = get_entity(entity_key)
    if entity is None:
        abort(404)
    return entity
def like_pattern(text):
    escaped = text.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")
    return "%" + escaped + "%"
def load_options(entity):
    options = {}
    for spec in entity["fields"]:
        if spec["type"] == "fk":
            options[spec["name"]] = query_all(FK_OPTIONS[spec["fk"]])
    return options
def to_form_value(value):
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)
def initial_values(entity, existing):
    values = {}
    for spec in entity["fields"]:
        name = spec["name"]
        if existing is not None:
            values[name] = to_form_value(existing.get(name))
            continue
        passed = request.args.get(name)
        if passed:
            values[name] = passed
        elif spec["type"] == "date" and name in ("OrderDate", "PaymentDate"):
            values[name] = date.today().strftime("%Y-%m-%d")
        else:
            values[name] = to_form_value(spec.get("default"))
    return values
def recalc_order_total(order_id):
    execute(
        "UPDATE Orders SET TotalAmount = ("
        "SELECT COALESCE(SUM(LineTotal), 0) FROM OrderItems WHERE OrderID = %s"
        ") WHERE OrderID = %s",
        [order_id, order_id],
    )
def map_db_error(entity, exc):
    errno = getattr(exc, "errno", None)
    if errno == 1062:
        key_part = str(exc.msg).split("for key")[-1].lower()
        errors = {}
        for field_name, message in entity.get("unique", {}).items():
            if field_name.lower() in key_part:
                errors[field_name] = message
        if errors:
            return errors
        return {"_form": "A record with the same unique value already exists."}
    if errno == 1452:
        return {"_form": "A selected related record does not exist."}
    if errno in (3819, 4025):
        return {"_form": "A value violates a database check constraint."}
    current_app.logger.error("Database error %s: %s", errno, exc)
    return {"_form": "The database rejected this change. Review the values and try again."}
def after_save_url(entity, data, new_id):
    key = entity["key"]
    if key in ("order-items", "payments"):
        return url_for("order_detail", order_id=data["OrderID"])
    if key == "orders" and new_id:
        return url_for("order_detail", order_id=new_id)
    return url_for("list_view", entity_key=key)
# ---------------------------------------------------------------- app factory
def create_app():
    validate_config()
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["CURRENCY_SYMBOL"] = os.environ.get("CURRENCY_SYMBOL", "$")
    app.teardown_appcontext(close_db)
    logging.basicConfig(level=logging.INFO)
        # ---- authentication gate
    @app.before_request
    def require_login():
        if request.endpoint in (None, "static", "login"):
            return None
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return None
    # ---- CSRF
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]
    app.jinja_env.globals["csrf_token"] = csrf_token
    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400)
    # ---- template helpers
    @app.template_filter("money")
    def money_filter(value):
        if value is None or value == "":
            return "\u2014"
        try:
            return "{}{:,.2f}".format(app.config["CURRENCY_SYMBOL"], Decimal(value))
        except (InvalidOperation, ValueError, TypeError):
            return str(value)
    @app.template_filter("datefmt")
    def date_filter(value):
        if value is None or value == "":
            return "\u2014"
        if isinstance(value, (date, datetime)):
            return value.strftime("%d %b %Y")
        return str(value)
    @app.template_filter("pct")
    def percent_filter(value):
        if value is None or value == "":
            return "\u2014"
        try:
            return "{:.2f}%".format(Decimal(value))
        except (InvalidOperation, ValueError, TypeError):
            return str(value)
    @app.template_filter("slug")
    def slug_filter(value):
        return str(value or "").strip().lower().replace(" ", "-")
    @app.context_processor
    def inject_globals():
        endpoint = request.endpoint or ""
        active_key = ""
        if endpoint == "dashboard":
            active_key = "dashboard"
        elif endpoint == "reports":
            active_key = "reports"
        elif endpoint == "order_detail":
            active_key = "orders"
        elif request.view_args and "entity_key" in request.view_args:
            active_key = request.view_args["entity_key"]
        return {
            "nav_items": [ENTITIES[k] for k in NAV_ORDER],
            "active_key": active_key,
            "current_year": date.today().year,
        }
    # ---------------------------------------------------------------- dashboard
    @app.route("/")
    def dashboard():
        counts = []
        for key in NAV_ORDER:
            ent = ENTITIES[key]
            counts.append({
                "key": key,
                "title": ent["title"],
                "icon": ent["icon"],
                "count": scalar("SELECT COUNT(*) FROM `{}`".format(ent["table"])),
            })
        stats = {
            "total_sales": scalar(
                "SELECT COALESCE(SUM(TotalAmount), 0) FROM Orders WHERE Status <> 'Cancelled'"
            ),
            "payments_received": scalar(
                "SELECT COALESCE(SUM(Amount), 0) FROM Payments WHERE Status = 'Completed'"
            ),
            "pending_orders": scalar("SELECT COUNT(*) FROM Orders WHERE Status = 'Pending'"),
            "low_stock_count": scalar(
                "SELECT COUNT(*) FROM Inventory WHERE Quantity <= ReorderLevel"
            ),
        }
        recent_orders = query_all(
            "SELECT o.OrderID AS id, cu.Name AS CustomerName, co.CompanyName AS CompanyName, "
            "o.OrderDate AS OrderDate, o.TotalAmount AS TotalAmount, o.Status AS Status "
            "FROM Orders o "
            "INNER JOIN Customers cu ON cu.CustomerID = o.CustomerID "
            "INNER JOIN Companies co ON co.CompanyID = o.CompanyID "
            "ORDER BY o.OrderDate DESC, o.OrderID DESC LIMIT 8"
        )
        low_stock = query_all(
            "SELECT i.InventoryID AS id, p.ProductName AS ProductName, "
            "co.CompanyName AS CompanyName, i.Quantity AS Quantity, "
            "i.ReorderLevel AS ReorderLevel, i.WarehouseLocation AS WarehouseLocation "
            "FROM Inventory i "
            "INNER JOIN Products p ON p.ProductID = i.ProductID "
            "INNER JOIN Companies co ON co.CompanyID = i.CompanyID "
            "WHERE i.Quantity <= i.ReorderLevel "
            "ORDER BY (i.ReorderLevel - i.Quantity) DESC, co.CompanyName LIMIT 8"
        )
        status_rows = query_all(
            "SELECT Status, COUNT(*) AS cnt FROM Orders GROUP BY Status ORDER BY cnt DESC"
        )
        status_total = sum(r["cnt"] for r in status_rows)
        status_breakdown = []
        for r in status_rows:
            pct = round(r["cnt"] * 100.0 / status_total, 1) if status_total else 0
            status_breakdown.append({"status": r["Status"], "count": r["cnt"], "pct": pct})
        month_rows = query_all(
            "SELECT DATE_FORMAT(OrderDate, '%Y-%m') AS ym, "
            "COALESCE(SUM(TotalAmount), 0) AS total "
            "FROM Orders WHERE Status <> 'Cancelled' "
            "GROUP BY DATE_FORMAT(OrderDate, '%Y-%m') ORDER BY ym DESC LIMIT 6"
        )
        month_rows.reverse()
        max_total = max([r["total"] for r in month_rows], default=0)
        monthly_sales = []
        for r in month_rows:
            label = datetime.strptime(r["ym"], "%Y-%m").strftime("%b %Y")
            pct = float(r["total"] * 100 / max_total) if max_total else 0
            monthly_sales.append({"label": label, "total": r["total"], "pct": round(pct, 1)})
        return render_template(
            "dashboard.html",
            counts=counts,
            stats=stats,
            recent_orders=recent_orders,
            low_stock=low_stock,
            status_breakdown=status_breakdown,
            monthly_sales=monthly_sales,
        )
    # ---------------------------------------------------------------- reports
    @app.route("/reports")
    def reports():
        results = []
        for rep in REPORTS:
            results.append({
                "title": rep["title"],
                "feature": rep["feature"],
                "columns": rep["columns"],
                "rows": query_all(rep["sql"]),
            })
        return render_template("reports.html", reports=results)
    # ---------------------------------------------------------------- order detail
    @app.route("/orders/<int:order_id>")
    def order_detail(order_id):
        order = query_one(
            "SELECT o.OrderID, o.OrderDate, o.DeliveryDate, o.TotalAmount, o.Status, "
            "co.CompanyName, cu.Name AS CustomerName "
            "FROM Orders o "
            "INNER JOIN Companies co ON co.CompanyID = o.CompanyID "
            "INNER JOIN Customers cu ON cu.CustomerID = o.CustomerID "
            "WHERE o.OrderID = %s",
            [order_id],
        )
        if order is None:
            abort(404)
        items = query_all(
            "SELECT oi.OrderItemID AS id, p.ProductName, oi.Quantity, oi.UnitPrice, "
            "oi.Discount, oi.LineTotal "
            "FROM OrderItems oi INNER JOIN Products p ON p.ProductID = oi.ProductID "
            "WHERE oi.OrderID = %s ORDER BY oi.OrderItemID",
            [order_id],
        )
        payments = query_all(
            "SELECT PaymentID AS id, PaymentDate, Amount, PaymentMethod, Status, ReferenceNo "
            "FROM Payments WHERE OrderID = %s ORDER BY PaymentDate, PaymentID",
            [order_id],
        )
        total_paid = scalar(
            "SELECT COALESCE(SUM(Amount), 0) FROM Payments "
            "WHERE OrderID = %s AND Status = 'Completed'",
            [order_id],
        )
        order_total = order["TotalAmount"] if order["TotalAmount"] is not None else Decimal("0")
        balance = order_total - total_paid
        return render_template(
            "order_detail.html",
            order=order,
            items=items,
            payments=payments,
            total_paid=total_paid,
            balance=balance,
            item_entity=ENTITIES["order-items"],
            payment_entity=ENTITIES["payments"],
        )
    # ---------------------------------------------------------------- list
    @app.route("/<entity_key>")
    def list_view(entity_key):
        entity = entity_or_404(entity_key)
        q = (request.args.get("q") or "").strip()[:100]
        try:
            page = max(int(request.args.get("page", "1")), 1)
        except ValueError:
            page = 1
        where = ""
        params = []
        if q:
            pattern = like_pattern(q)
            where = " WHERE " + " OR ".join("{} LIKE %s".format(c) for c in entity["search"])
            params = [pattern] * len(entity["search"])
        total = scalar(
            "SELECT COUNT(*) FROM {}{}".format(entity["from_"], where), params
        ) or 0
        pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
        if page > pages:
            page = pages
        rows = query_all(
            "SELECT {} FROM {}{} ORDER BY {} LIMIT %s OFFSET %s".format(
                entity["select"], entity["from_"], where, entity["order"]
            ),
            params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
        )
        return render_template(
            "list.html",
            entity=entity,
            rows=rows,
            q=q,
            page=page,
            pages=pages,
            total=total,
            page_size=PAGE_SIZE,
        )
    # ---------------------------------------------------------------- add / edit
    def handle_form(entity, rid=None):
        mode = "edit" if rid is not None else "add"
        existing = None
        if mode == "edit":
            existing = query_one(
                "SELECT * FROM `{}` WHERE `{}` = %s".format(entity["table"], entity["pk"]),
                [rid],
            )
            if existing is None:
                abort(404)
        options = load_options(entity)
        errors = {}
        if request.method == "POST":
            cleaned, errors = validate_form(entity["fields"], request.form, options, existing)
            cross_validate(entity["key"], cleaned, errors)
            if not errors:
                data = dict(cleaned)
                if entity["key"] == "order-items":
                    data["LineTotal"] = compute_line_total(
                        data["Quantity"], data["UnitPrice"], data["Discount"]
                    )
                if mode == "add":
                    data.update(entity.get("insert_defaults", {}))
                new_id = None
                try:
                    if mode == "add":
                        new_id = insert_row(entity["table"], data)
                    else:
                        update_row(entity["table"], entity["pk"], rid, data)
                    if entity["key"] == "order-items":
                        recalc_order_total(data["OrderID"])
                        if existing is not None and existing["OrderID"] != data["OrderID"]:
                            recalc_order_total(existing["OrderID"])
                    commit()
                except mysql.connector.Error as exc:
                    rollback()
                    errors = map_db_error(entity, exc)
                else:
                    flash(
                        "{} {}.".format(
                            entity["singular"], "added" if mode == "add" else "updated"
                        ),
                        "success",
                    )
                    return redirect(after_save_url(entity, data, new_id))
            values = {
                spec["name"]: request.form.get(spec["name"], "")
                for spec in entity["fields"]
            }
        else:
            values = initial_values(entity, existing)
        return render_template(
            "form.html",
            entity=entity,
            mode=mode,
            record_id=rid,
            values=values,
            errors=errors,
            options=options,
        )
    @app.route("/<entity_key>/add", methods=["GET", "POST"])
    def add_view(entity_key):
        return handle_form(entity_or_404(entity_key))
    @app.route("/<entity_key>/edit/<int:rid>", methods=["GET", "POST"])
    def edit_view(entity_key, rid):
        return handle_form(entity_or_404(entity_key), rid)
    # ---------------------------------------------------------------- delete
    @app.route("/<entity_key>/delete/<int:rid>", methods=["POST"])
    def delete_view(entity_key, rid):
        entity = entity_or_404(entity_key)
        existing = query_one(
            "SELECT * FROM `{}` WHERE `{}` = %s".format(entity["table"], entity["pk"]),
            [rid],
        )
        if existing is None:
            abort(404)
        order_id = existing.get("OrderID") if entity["key"] in ("order-items", "payments") else None
        try:
            delete_row(entity["table"], entity["pk"], rid)
            if entity["key"] == "order-items":
                recalc_order_total(order_id)
            commit()
        except mysql.connector.Error as exc:
            rollback()
            if getattr(exc, "errno", None) == 1451:
                flash("Record is referenced by other records and cannot be deleted.", "error")
            else:
                current_app.logger.error("Delete failed: %s", exc)
                flash("The record could not be deleted.", "error")
        else:
            flash("{} deleted.".format(entity["singular"]), "success")
        if order_id is not None and request.form.get("next") == "order":
            return redirect(url_for("order_detail", order_id=order_id))
        return redirect(url_for("list_view", entity_key=entity["key"]))
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("logged_in"):
            return redirect(url_for("dashboard"))
        error = None
        username = ""
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()[:100]
            password = request.form.get("password") or ""
            if not username or not password:
                error = "Enter both your username and password."
            else:
                user_ok = hmac.compare_digest(
                    username.encode("utf-8"), LOGIN_USERNAME.encode("utf-8")
                )
                pass_ok = hmac.compare_digest(
                    password.encode("utf-8"), LOGIN_PASSWORD.encode("utf-8")
                )
                if user_ok and pass_ok:
                    session.clear()
                    session["logged_in"] = True
                    session["user"] = LOGIN_USERNAME
                    return redirect(url_for("dashboard"))
                error = "Invalid username or password."
        return render_template("login.html", error=error, username=username)
    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))
    # ---------------------------------------------------------------- errors
    def render_error(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code
    @app.errorhandler(400)
    def bad_request(error):
        return render_error(
            400, "Request rejected",
            "The form session is invalid or has expired. Go back, reload the page, and try again.",
        )
    @app.errorhandler(404)
    def not_found(error):
        return render_error(404, "Page not found", "The page or record you requested does not exist.")
    @app.errorhandler(mysql.connector.Error)
    def database_error(error):
        current_app.logger.error("Database error: %s", error)
        return render_error(
            503, "Database unavailable",
            "The application could not complete the database request. "
            "Check that MySQL is running and that the values in .env are correct.",
        )
    @app.errorhandler(500)
    def server_error(error):
        return render_error(500, "Something went wrong", "An unexpected error occurred.")
    return app
app = create_app()
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
