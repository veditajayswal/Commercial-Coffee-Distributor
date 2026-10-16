from decimal import Decimal

ORDER_STATUSES = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "UPI", "Bank Transfer"]
PAYMENT_STATUSES = ["Completed", "Pending", "Failed", "Refunded"]

MAX_INT = 2147483647
MAX_MONEY_10_2 = Decimal("99999999.99")
MAX_MONEY_8_2 = Decimal("999999.99")


def field(name, label, ftype, required=False, **extra):
    spec = {"name": name, "label": label, "type": ftype, "required": required}
    spec.update(extra)
    return spec


# Column kinds used by templates/list.html:
# text, int, money, date, percent, badge, order_link (links id to order detail),
# order_ref (links OrderID column to order detail)
ENTITIES = {
    "companies": {
        "key": "companies",
        "table": "Companies",
        "pk": "CompanyID",
        "title": "Companies",
        "singular": "Company",
        "icon": "building",
        "select": "c.CompanyID AS id, c.CompanyName, c.Phone, c.Email, c.Address, c.Website",
        "from_": "Companies c",
        "search": ["c.CompanyName", "c.Email", "c.Phone", "c.Address", "c.Website"],
        "order": "c.CompanyName",
        "columns": [
            ("CompanyName", "Company", "text"),
            ("Phone", "Phone", "text"),
            ("Email", "Email", "text"),
            ("Address", "Address", "text"),
            ("Website", "Website", "text"),
        ],
        "fields": [
            field("CompanyName", "Company name", "text", True, max_len=100),
            field("Phone", "Phone", "phone", max_len=15),
            field("Email", "Email", "email", max_len=100),
            field("Address", "Address", "text", max_len=255),
            field("Website", "Website", "text", max_len=150),
        ],
        "unique": {"Email": "This email is already used by another company."},
    },
    "customers": {
        "key": "customers",
        "table": "Customers",
        "pk": "CustomerID",
        "title": "Customers",
        "singular": "Customer",
        "icon": "users",
        "select": (
            "cu.CustomerID AS id, cu.Name, co.CompanyName, cu.Email, cu.Phone, "
            "cu.City, cu.Country, cu.CreditLimit"
        ),
        "from_": "Customers cu INNER JOIN Companies co ON co.CompanyID = cu.CompanyID",
        "search": ["cu.Name", "co.CompanyName", "cu.Email", "cu.Phone", "cu.City", "cu.Country"],
        "order": "cu.Name",
        "columns": [
            ("Name", "Name", "text"),
            ("CompanyName", "Company", "text"),
            ("Email", "Email", "text"),
            ("Phone", "Phone", "text"),
            ("City", "City", "text"),
            ("Country", "Country", "text"),
            ("CreditLimit", "Credit limit", "money"),
        ],
        "fields": [
            field("CompanyID", "Company", "fk", True, fk="companies"),
            field("Name", "Name", "text", True, max_len=100),
            field("Email", "Email", "email", max_len=100),
            field("Phone", "Phone", "phone", max_len=15),
            field("Address", "Address", "text", max_len=255),
            field("City", "City", "text", max_len=50),
            field("Country", "Country", "text", max_len=50),
            field(
                "CreditLimit", "Credit limit", "decimal",
                min=Decimal("0"), max=MAX_MONEY_10_2, default=Decimal("10000.00"),
                step="0.01",
            ),
        ],
        "unique": {"Email": "This email is already used by another customer."},
    },
    "products": {
        "key": "products",
        "table": "Products",
        "pk": "ProductID",
        "title": "Products",
        "singular": "Product",
        "icon": "coffee",
        "select": "p.ProductID AS id, p.ProductName, p.Category, p.Origin, p.Price",
        "from_": "Products p",
        "search": ["p.ProductName", "p.Category", "p.Origin", "p.Description"],
        "order": "p.ProductName",
        "columns": [
            ("ProductName", "Product", "text"),
            ("Category", "Category", "text"),
            ("Origin", "Origin", "text"),
            ("Price", "Price", "money"),
        ],
        "fields": [
            field("ProductName", "Product name", "text", True, max_len=100),
            field("Category", "Category", "text", max_len=50),
            field("Origin", "Origin", "text", max_len=50),
            field(
                "Price", "Price", "decimal", True,
                gt=Decimal("0"), max=MAX_MONEY_8_2, step="0.01",
            ),
            field("Description", "Description", "textarea", max_len=5000),
        ],
        "unique": {},
    },
    "suppliers": {
        "key": "suppliers",
        "table": "Suppliers",
        "pk": "SupplierID",
        "title": "Suppliers",
        "singular": "Supplier",
        "icon": "truck",
        "select": (
            "s.SupplierID AS id, s.SupplierName, s.ContactPerson, s.Email, "
            "s.Phone, s.City, s.Country"
        ),
        "from_": "Suppliers s",
        "search": ["s.SupplierName", "s.ContactPerson", "s.Email", "s.Phone", "s.City", "s.Country"],
        "order": "s.SupplierName",
        "columns": [
            ("SupplierName", "Supplier", "text"),
            ("ContactPerson", "Contact", "text"),
            ("Email", "Email", "text"),
            ("Phone", "Phone", "text"),
            ("City", "City", "text"),
            ("Country", "Country", "text"),
        ],
        "fields": [
            field("SupplierName", "Supplier name", "text", True, max_len=100),
            field("ContactPerson", "Contact person", "text", max_len=100),
            field("Email", "Email", "email", max_len=100),
            field("Phone", "Phone", "phone", max_len=15),
            field("City", "City", "text", max_len=50),
            field("Country", "Country", "text", max_len=50),
        ],
        "unique": {},
    },
    "inventory": {
        "key": "inventory",
        "table": "Inventory",
        "pk": "InventoryID",
        "title": "Inventory",
        "singular": "Inventory record",
        "icon": "box",
        "select": (
            "i.InventoryID AS id, co.CompanyName, p.ProductName, s.SupplierName, "
            "i.Quantity, i.ReorderLevel, i.WarehouseLocation, "
            "(i.Quantity <= i.ReorderLevel) AS LowStock"
        ),
        "from_": (
            "Inventory i "
            "INNER JOIN Companies co ON co.CompanyID = i.CompanyID "
            "INNER JOIN Products p ON p.ProductID = i.ProductID "
            "INNER JOIN Suppliers s ON s.SupplierID = i.SupplierID"
        ),
        "search": ["co.CompanyName", "p.ProductName", "s.SupplierName", "i.WarehouseLocation"],
        "order": "co.CompanyName",
        "columns": [
            ("CompanyName", "Company", "text"),
            ("ProductName", "Product", "text"),
            ("SupplierName", "Supplier", "text"),
            ("Quantity", "Quantity", "int"),
            ("ReorderLevel", "Reorder level", "int"),
            ("WarehouseLocation", "Warehouse", "text"),
        ],
        "row_flag": "LowStock",
        "fields": [
            field("CompanyID", "Company", "fk", True, fk="companies"),
            field("ProductID", "Product", "fk", True, fk="products"),
            field("SupplierID", "Supplier", "fk", True, fk="suppliers"),
            field("Quantity", "Quantity", "int", min=0, max=MAX_INT),
            field("ReorderLevel", "Reorder level", "int", min=0, max=MAX_INT),
            field("WarehouseLocation", "Warehouse location", "text", max_len=100),
        ],
        "unique": {"CompanyID": "This company already has an inventory record."},
    },
    "orders": {
        "key": "orders",
        "table": "Orders",
        "pk": "OrderID",
        "title": "Orders",
        "singular": "Order",
        "icon": "receipt",
        "select": (
            "o.OrderID AS id, co.CompanyName, cu.Name AS CustomerName, "
            "o.OrderDate, o.DeliveryDate, o.TotalAmount, o.Status"
        ),
        "from_": (
            "Orders o "
            "INNER JOIN Companies co ON co.CompanyID = o.CompanyID "
            "INNER JOIN Customers cu ON cu.CustomerID = o.CustomerID"
        ),
        "search": ["CAST(o.OrderID AS CHAR)", "co.CompanyName", "cu.Name", "o.Status"],
        "order": "o.OrderDate DESC, o.OrderID DESC",
        "columns": [
            ("id", "Order", "order_link"),
            ("CompanyName", "Company", "text"),
            ("CustomerName", "Customer", "text"),
            ("OrderDate", "Order date", "date"),
            ("DeliveryDate", "Delivery", "date"),
            ("TotalAmount", "Total", "money"),
            ("Status", "Status", "badge"),
        ],
        "fields": [
            field("CompanyID", "Company", "fk", True, fk="companies"),
            field("CustomerID", "Customer", "fk", True, fk="customers"),
            field("OrderDate", "Order date", "date", True),
            field("Status", "Status", "choice", True, choices=ORDER_STATUSES, default="Pending"),
            field("DeliveryDate", "Delivery date", "date"),
        ],
        "insert_defaults": {"TotalAmount": Decimal("0.00")},
        "unique": {},
    },
    "order-items": {
        "key": "order-items",
        "table": "OrderItems",
        "pk": "OrderItemID",
        "title": "Order Items",
        "singular": "Order item",
        "icon": "list",
        "select": (
            "oi.OrderItemID AS id, oi.OrderID, p.ProductName, oi.Quantity, "
            "oi.UnitPrice, oi.Discount, oi.LineTotal"
        ),
        "from_": (
            "OrderItems oi "
            "INNER JOIN Orders o ON o.OrderID = oi.OrderID "
            "INNER JOIN Products p ON p.ProductID = oi.ProductID"
        ),
        "search": ["CAST(oi.OrderID AS CHAR)", "p.ProductName"],
        "order": "oi.OrderID DESC, oi.OrderItemID",
        "columns": [
            ("OrderID", "Order", "order_ref"),
            ("ProductName", "Product", "text"),
            ("Quantity", "Qty", "int"),
            ("UnitPrice", "Unit price", "money"),
            ("Discount", "Discount", "percent"),
            ("LineTotal", "Line total", "money"),
        ],
        "fields": [
            field("OrderID", "Order", "fk", True, fk="orders"),
            field("ProductID", "Product", "fk", True, fk="products"),
            field("Quantity", "Quantity", "int", True, min=1, max=1000000),
            field(
                "UnitPrice", "Unit price", "decimal", True,
                gt=Decimal("0"), max=MAX_MONEY_8_2, step="0.01",
            ),
            field(
                "Discount", "Discount (%)", "decimal",
                min=Decimal("0"), max=Decimal("100"), default=Decimal("0.00"),
                step="0.01",
            ),
        ],
        "unique": {},
    },
    "employees": {
        "key": "employees",
        "table": "Employees",
        "pk": "EmployeeID",
        "title": "Employees",
        "singular": "Employee",
        "icon": "badge",
        "select": (
            "e.EmployeeID AS id, e.Name, co.CompanyName, e.Position, e.Department, "
            "e.Salary, e.Email, e.Phone, e.HireDate"
        ),
        "from_": "Employees e INNER JOIN Companies co ON co.CompanyID = e.CompanyID",
        "search": [
            "e.Name", "co.CompanyName", "e.Position", "e.Department", "e.Email", "e.Phone",
        ],
        "order": "e.Name",
        "columns": [
            ("Name", "Name", "text"),
            ("CompanyName", "Company", "text"),
            ("Position", "Position", "text"),
            ("Department", "Department", "text"),
            ("Salary", "Salary", "money"),
            ("Email", "Email", "text"),
            ("HireDate", "Hired", "date"),
        ],
        "fields": [
            field("CompanyID", "Company", "fk", True, fk="companies"),
            field("Name", "Name", "text", True, max_len=100),
            field("Position", "Position", "text", max_len=50),
            field(
                "Salary", "Salary", "decimal",
                min=Decimal("0"), max=MAX_MONEY_10_2, step="0.01",
            ),
            field("Department", "Department", "text", max_len=50),
            field("Email", "Email", "email", max_len=100),
            field("Phone", "Phone", "phone", max_len=15),
            field("HireDate", "Hire date", "date"),
        ],
        "unique": {"Email": "This email is already used by another employee."},
    },
    "payments": {
        "key": "payments",
        "table": "Payments",
        "pk": "PaymentID",
        "title": "Payments",
        "singular": "Payment",
        "icon": "card",
        "select": (
            "pa.PaymentID AS id, pa.OrderID, cu.Name AS CustomerName, pa.PaymentDate, "
            "pa.Amount, pa.PaymentMethod, pa.Status, pa.ReferenceNo"
        ),
        "from_": (
            "Payments pa "
            "INNER JOIN Orders o ON o.OrderID = pa.OrderID "
            "INNER JOIN Customers cu ON cu.CustomerID = o.CustomerID"
        ),
        "search": [
            "CAST(pa.OrderID AS CHAR)", "cu.Name", "pa.PaymentMethod",
            "pa.Status", "pa.ReferenceNo",
        ],
        "order": "pa.PaymentDate DESC, pa.PaymentID DESC",
        "columns": [
            ("OrderID", "Order", "order_ref"),
            ("CustomerName", "Customer", "text"),
            ("PaymentDate", "Date", "date"),
            ("Amount", "Amount", "money"),
            ("PaymentMethod", "Method", "text"),
            ("Status", "Status", "badge"),
            ("ReferenceNo", "Reference", "text"),
        ],
        "fields": [
            field("OrderID", "Order", "fk", True, fk="orders"),
            field("PaymentDate", "Payment date", "date", True),
            field(
                "Amount", "Amount", "decimal", True,
                gt=Decimal("0"), max=MAX_MONEY_10_2, step="0.01",
            ),
            field("PaymentMethod", "Payment method", "choice", False, choices=PAYMENT_METHODS),
            field("Status", "Status", "choice", True, choices=PAYMENT_STATUSES, default="Completed"),
            field("ReferenceNo", "Reference no.", "text", max_len=100),
        ],
        "unique": {},
    },
}

NAV_ORDER = [
    "companies", "customers", "products", "suppliers", "inventory",
    "orders", "order-items", "employees", "payments",
]

# Foreign-key drop-down sources. Each query returns id and label (products also return price).
FK_OPTIONS = {
    "companies": (
        "SELECT CompanyID AS id, CompanyName AS label "
        "FROM Companies ORDER BY CompanyName"
    ),
    "customers": (
        "SELECT cu.CustomerID AS id, CONCAT(cu.Name, ' - ', co.CompanyName) AS label "
        "FROM Customers cu INNER JOIN Companies co ON co.CompanyID = cu.CompanyID "
        "ORDER BY cu.Name"
    ),
    "products": (
        "SELECT ProductID AS id, ProductName AS label, Price AS price "
        "FROM Products ORDER BY ProductName"
    ),
    "suppliers": (
        "SELECT SupplierID AS id, SupplierName AS label "
        "FROM Suppliers ORDER BY SupplierName"
    ),
    "orders": (
        "SELECT o.OrderID AS id, CONCAT('Order #', o.OrderID, ' - ', cu.Name) AS label "
        "FROM Orders o INNER JOIN Customers cu ON cu.CustomerID = o.CustomerID "
        "ORDER BY o.OrderID DESC"
    ),
}


def get_entity(key):
    return ENTITIES.get(key)