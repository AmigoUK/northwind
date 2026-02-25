"""
db.py - Database connection, schema DDL, and seed data for Northwind Traders
"""
import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "northwind.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS Categories (
        CategoryID   INTEGER PRIMARY KEY AUTOINCREMENT,
        CategoryName TEXT NOT NULL,
        Description  TEXT
    );

    CREATE TABLE IF NOT EXISTS Suppliers (
        SupplierID   INTEGER PRIMARY KEY AUTOINCREMENT,
        CompanyName  TEXT NOT NULL,
        ContactName  TEXT,
        ContactTitle TEXT,
        Address      TEXT,
        City         TEXT,
        Region       TEXT,
        PostalCode   TEXT,
        Country      TEXT,
        Phone        TEXT,
        Fax          TEXT,
        HomePage     TEXT
    );

    CREATE TABLE IF NOT EXISTS Shippers (
        ShipperID   INTEGER PRIMARY KEY AUTOINCREMENT,
        CompanyName TEXT NOT NULL,
        Phone       TEXT
    );

    CREATE TABLE IF NOT EXISTS Region (
        RegionID          INTEGER PRIMARY KEY AUTOINCREMENT,
        RegionDescription TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Territories (
        TerritoryID          TEXT PRIMARY KEY,
        TerritoryDescription TEXT NOT NULL,
        RegionID             INTEGER NOT NULL,
        FOREIGN KEY (RegionID) REFERENCES Region(RegionID)
    );

    CREATE TABLE IF NOT EXISTS Employees (
        EmployeeID       INTEGER PRIMARY KEY AUTOINCREMENT,
        LastName         TEXT NOT NULL,
        FirstName        TEXT NOT NULL,
        Title            TEXT,
        TitleOfCourtesy  TEXT,
        BirthDate        TEXT,
        HireDate         TEXT,
        Address          TEXT,
        City             TEXT,
        Region           TEXT,
        PostalCode       TEXT,
        Country          TEXT,
        HomePhone        TEXT,
        Extension        TEXT,
        Notes            TEXT,
        ReportsTo        INTEGER,
        FOREIGN KEY (ReportsTo) REFERENCES Employees(EmployeeID)
    );

    CREATE TABLE IF NOT EXISTS Customers (
        CustomerID   TEXT PRIMARY KEY,
        CompanyName  TEXT NOT NULL,
        ContactName  TEXT,
        ContactTitle TEXT,
        Address      TEXT,
        City         TEXT,
        Region       TEXT,
        PostalCode   TEXT,
        Country      TEXT,
        Phone        TEXT,
        Fax          TEXT
    );

    CREATE TABLE IF NOT EXISTS Products (
        ProductID       INTEGER PRIMARY KEY AUTOINCREMENT,
        ProductName     TEXT NOT NULL,
        SupplierID      INTEGER,
        CategoryID      INTEGER,
        QuantityPerUnit TEXT,
        UnitPrice       REAL DEFAULT 0.0,
        UnitsInStock    INTEGER DEFAULT 0,
        UnitsOnOrder    INTEGER DEFAULT 0,
        ReorderLevel    INTEGER DEFAULT 0,
        Discontinued    INTEGER DEFAULT 0,
        FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID),
        FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
    );

    CREATE TABLE IF NOT EXISTS Orders (
        OrderID        INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerID     TEXT,
        EmployeeID     INTEGER,
        OrderDate      TEXT,
        RequiredDate   TEXT,
        ShippedDate    TEXT,
        ShipVia        INTEGER,
        Freight        REAL DEFAULT 0.0,
        ShipName       TEXT,
        ShipAddress    TEXT,
        ShipCity       TEXT,
        ShipRegion     TEXT,
        ShipPostalCode TEXT,
        ShipCountry    TEXT,
        FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
        FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
        FOREIGN KEY (ShipVia) REFERENCES Shippers(ShipperID)
    );

    CREATE TABLE IF NOT EXISTS OrderDetails (
        OrderID   INTEGER NOT NULL,
        ProductID INTEGER NOT NULL,
        UnitPrice REAL NOT NULL DEFAULT 0.0,
        Quantity  INTEGER NOT NULL DEFAULT 1,
        Discount  REAL NOT NULL DEFAULT 0.0,
        PRIMARY KEY (OrderID, ProductID),
        FOREIGN KEY (OrderID) REFERENCES Orders(OrderID) ON DELETE CASCADE,
        FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
    );
    """)

    conn.commit()
    conn.close()


def _is_empty():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Categories")
    count = c.fetchone()[0]
    conn.close()
    return count == 0


def seed_data():
    if not _is_empty():
        return

    conn = get_connection()
    c = conn.cursor()

    # Categories
    categories = [
        (1, "Beverages",    "Soft drinks, coffees, teas, beers, and ales"),
        (2, "Condiments",   "Sweet and savory sauces, relishes, spreads, and seasonings"),
        (3, "Confections",  "Desserts, candies, and sweet breads"),
        (4, "Dairy Products", "Cheeses"),
        (5, "Grains/Cereals", "Breads, crackers, pasta, and cereal"),
        (6, "Meat/Poultry", "Prepared meats"),
        (7, "Produce",      "Dried fruit and bean curd"),
        (8, "Seafood",      "Seaweed and fish"),
    ]
    c.executemany(
        "INSERT INTO Categories (CategoryID, CategoryName, Description) VALUES (?,?,?)",
        categories
    )

    # Suppliers
    suppliers = [
        (1,  "Exotic Liquids",              "Charlotte Cooper",  "Purchasing Manager",   "49 Gilbert St.",       "London",        None,          "EC1 4SD",  "UK",         "(171) 555-2222",  None,              None),
        (2,  "New Orleans Cajun Delights",   "Shelley Burke",     "Order Administrator",  "P.O. Box 78934",       "New Orleans",   "LA",          "70117",    "USA",        "(100) 555-4822",  None,              "#CAJUN.htm#"),
        (3,  "Grandma Kelly's Homestead",    "Regina Murphy",     "Sales Representative", "707 Oxford Rd.",       "Ann Arbor",     "MI",          "48104",    "USA",        "(313) 555-5735",  "(313) 555-3349",  None),
        (4,  "Tokyo Traders",               "Yoshi Nagase",      "Marketing Manager",    "9-8 Sekimai Musashino-shi", "Tokyo",    None,          "100",      "Japan",      "(03) 3555-5011",  None,              None),
        (5,  "Cooperativa de Quesos 'Las Cabras'", "Antonio del Valle Saavedra", "Export Administrator", "Calle del Rosal 4", "Oviedo", "Asturias", "33007", "Spain", "(98) 598 76 54", None, None),
        (6,  "Mayumi's",                    "Mayumi Ohno",       "Marketing Representative", "92 Setsuko Chuo-ku", "Osaka",       None,          "545",      "Japan",      "(06) 431-7877",   None,              "Mayumi's (on the World Wide Web)#http://www.lainterred.com/~mayumi#"),
        (7,  "Pavlova, Ltd.",               "Ian Devling",       "Marketing Manager",    "74 Rose St. Moonie Ponds", "Melbourne",  "Victoria",    "3058",     "Australia",  "(03) 444-2343",   "(03) 444-6588",   None),
        (8,  "Specialty Biscuits, Ltd.",    "Peter Wilson",      "Sales Representative", "29 King's Way",        "Manchester",    None,          "M14 GSD",  "UK",         "(161) 555-4448",  None,              None),
        (9,  "PB Knäckebröd AB",            "Lars Peterson",     "Sales Agent",          "Kaloadagatan 13",      "Göteborg",      None,          "S-345 67", "Sweden",     "031-987 65 43",   "031-987 65 91",   None),
        (10, "Refrescos Americanas LTDA",   "Carlos Diaz",       "Marketing Manager",    "Av. das Americanas 12.890", "São Paulo", None,          "5442",     "Brazil",     "(11) 555 4640",   None,              None),
    ]
    c.executemany(
        "INSERT INTO Suppliers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        suppliers
    )

    # Shippers
    shippers = [
        (1, "Speedy Express", "(503) 555-9831"),
        (2, "United Package",  "(503) 555-3199"),
        (3, "Federal Shipping","(503) 555-9931"),
    ]
    c.executemany("INSERT INTO Shippers VALUES (?,?,?)", shippers)

    # Regions
    regions = [
        (1, "Eastern"),
        (2, "Western"),
        (3, "Northern"),
        (4, "Southern"),
    ]
    c.executemany("INSERT INTO Region VALUES (?,?)", regions)

    # Territories
    territories = [
        ("01581", "Westboro",       1),
        ("01730", "Bedford",        1),
        ("02116", "Boston",         1),
        ("02139", "Cambridge",      1),
        ("10019", "New York",       1),
        ("20852", "Rockville",      2),
        ("30346", "Atlanta",        4),
        ("60601", "Chicago",        3),
        ("98004", "Bellevue",       2),
        ("98052", "Redmond",        2),
    ]
    c.executemany("INSERT INTO Territories VALUES (?,?,?)", territories)

    # Employees  (LastName, FirstName, Title, ToC, BirthDate, HireDate, Address, City, Region, PostalCode, Country, HomePhone, Extension, Notes, ReportsTo)
    employees = [
        (1, "Davolio",   "Nancy",   "Sales Representative",    "Ms.", "1968-12-08", "1992-05-01", "507 - 20th Ave. E. Apt. 2A", "Seattle",  "WA", "98122", "USA", "(206) 555-9857", "5467", "Education includes a BA in psychology from Colorado State University.", None),
        (2, "Fuller",    "Andrew",  "Vice President, Sales",   "Dr.", "1952-02-19", "1992-08-14", "908 W. Capital Way",          "Tacoma",   "WA", "98401", "USA", "(206) 555-9482", "3457", "Andrew received his BTS commercial in 1974.",                          None),
        (3, "Leverling", "Janet",   "Sales Representative",    "Ms.", "1963-08-30", "1992-04-01", "722 Moss Bay Blvd.",           "Kirkland", "WA", "98033", "USA", "(206) 555-3412", "3355", "Janet has a BS degree in chemistry from Boston College.",             2),
        (4, "Peacock",   "Margaret","Sales Representative",    "Mrs.","1958-09-19", "1993-05-03", "4110 Old Redmond Rd.",         "Redmond",  "WA", "98052", "USA", "(206) 555-8122", "5176", "Margaret holds a BA in English literature from Concordia College.",   2),
        (5, "Buchanan",  "Steven",  "Sales Manager",           "Mr.", "1955-03-04", "1993-10-17", "14 Garrett Hill",             "London",   None, "SW1 8JR","UK",  "(71) 555-4848",  "3453", "Steven Buchanan graduated from St. Andrews University.",             2),
        (6, "Suyama",    "Michael", "Sales Representative",    "Mr.", "1963-07-02", "1993-10-17", "Coventry House Miner Rd.",    "London",   None, "EC2 7JR","UK",  "(71) 555-7773",  "428",  "Michael is a graduate of Sussex University.",                        5),
        (7, "King",      "Robert",  "Sales Representative",    "Mr.", "1960-05-29", "1994-01-02", "Edgeham Hollow Winchester Way","London",  None, "RG1 9SP","UK",  "(71) 555-5598",  "465",  "Robert King served in the Peace Corps.",                             5),
        (8, "Callahan",  "Laura",   "Inside Sales Coordinator","Ms.", "1958-01-09", "1994-03-05", "4726 - 11th Ave. N.E.",       "Seattle",  "WA", "98105", "USA", "(206) 555-1189", "2344", "Laura received a BA in psychology from the University of Washington.", 2),
        (9, "Dodsworth", "Anne",    "Sales Representative",    "Ms.", "1966-01-27", "1994-11-15", "7 Houndstooth Rd.",           "London",   None, "WG2 7LT","UK",  "(71) 555-4444",  "452",  "Anne has a BA degree in English from St. Lawrence College.",         5),
    ]
    c.executemany(
        "INSERT INTO Employees (EmployeeID,LastName,FirstName,Title,TitleOfCourtesy,BirthDate,HireDate,Address,City,Region,PostalCode,Country,HomePhone,Extension,Notes,ReportsTo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        employees
    )

    # Customers
    customers = [
        ("ALFKI", "Alfreds Futterkiste",        "Maria Anders",    "Sales Representative",  "Obere Str. 57",       "Berlin",        None,    "12209", "Germany",  "030-0074321",  "030-0076545"),
        ("ANATR", "Ana Trujillo Emparedados y helados", "Ana Trujillo", "Owner",           "Avda. de la Constitución 2222", "México D.F.", None, "05021", "Mexico", "(5) 555-4729", "(5) 555-3745"),
        ("AROUT", "Around the Horn",             "Thomas Hardy",    "Sales Representative",  "120 Hanover Sq.",     "London",        None,    "WA1 1DP","UK",      "(171) 555-7788","(171) 555-6750"),
        ("BERGS", "Berglunds snabbköp",           "Christina Berglund","Order Administrator","Berguvsvägen 8",      "Luleå",         None,    "S-958 22","Sweden",  "0921-12 34 65","0921-12 34 67"),
        ("BLAUS", "Blauer See Delikatessen",      "Hanna Moos",      "Sales Representative",  "Forsterstr. 57",      "Mannheim",      None,    "68306", "Germany",  "0621-08460",   "0621-08924"),
        ("BLONP", "Blondesddsl père et fils",     "Frédérique Citeaux","Marketing Manager",  "24, place Kléber",    "Strasbourg",    None,    "67000", "France",   "88.60.15.31",  "88.60.15.32"),
        ("BOLID", "Bólido Comidas preparadas",    "Martín Sommer",   "Owner",                 "C/ Araquil, 67",      "Madrid",        None,    "28023", "Spain",    "(91) 555 22 82","(91) 555 91 99"),
        ("BONAP", "Bon app'",                     "Laurence Lebihan","Owner",                 "12, rue des Bouchers","Marseille",     None,    "13008", "France",   "91.24.45.40",  "91.24.45.41"),
        ("BOTTM", "Bottom-Dollar Markets",        "Elizabeth Lincoln","Accounting Manager",   "23 Tsawassen Blvd.", "Tsawassen",     "BC",    "T2F 8M4","Canada",   "(604) 555-4729","(604) 555-3745"),
        ("BSBEV", "B's Beverages",                "Victoria Ashworth","Sales Representative", "Fauntleroy Circus",  "London",        None,    "EC2 5NT","UK",       "(171) 555-1212", None),
    ]
    c.executemany(
        "INSERT INTO Customers VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        customers
    )

    # Products
    products = [
        (1,  "Chai",                   1, 1, "10 boxes x 20 bags", 18.00,  39, 0,  10, 0),
        (2,  "Chang",                  1, 1, "24 - 12 oz bottles", 19.00,  17, 40, 25, 0),
        (3,  "Aniseed Syrup",          1, 2, "12 - 550 ml bottles",10.00,  13, 70, 25, 0),
        (4,  "Chef Anton's Cajun Seasoning", 2, 2, "48 - 6 oz jars", 22.00, 53, 0,  0,  0),
        (5,  "Chef Anton's Gumbo Mix", 2, 2, "36 boxes",           21.35,  0,  0,  0,  1),
        (6,  "Grandma's Boysenberry Spread", 3, 2, "12 - 8 oz jars", 25.00, 120,0, 25, 0),
        (7,  "Uncle Bob's Organic Dried Pears", 3, 7, "12 - 1 lb pkgs.", 30.00, 15, 0, 10, 0),
        (8,  "Northwoods Cranberry Sauce", 3, 2, "12 - 12 oz jars", 40.00, 6, 0,  0,  0),
        (9,  "Mishi Kobe Niku",        4, 6, "18 - 500 g pkgs.",   97.00,  29, 0,  0,  1),
        (10, "Ikura",                  4, 8, "12 - 200 ml jars",   31.00,  31, 0,  0,  0),
        (11, "Queso Cabrales",         5, 4, "1 kg pkg.",           21.00,  22, 30, 30, 0),
        (12, "Queso Manchego La Pastora", 5, 4, "10 - 500 g pkgs.", 38.00, 86, 0,  0,  0),
        (13, "Konbu",                  6, 8, "2 kg box",            6.00,  24, 0,  5,  0),
        (14, "Tofu",                   6, 7, "40 - 100 g pkgs.",   23.25,  35, 0,  0,  0),
        (15, "Genen Shouyu",           6, 2, "24 - 250 ml bottles", 15.50,  39, 0,  5,  0),
        (16, "Pavlova",                7, 3, "32 - 500 g boxes",   17.45, 29, 0,  10, 0),
        (17, "Alice Mutton",           7, 6, "20 - 1 kg tins",     39.00,  0,  0,  0,  1),
        (18, "Carnarvon Tigers",       7, 8, "16 kg pkg.",          62.50,  42, 0,  0,  0),
        (19, "Teatime Chocolate Biscuits", 8, 3, "10 boxes x 12 pieces", 9.20, 25, 0, 5, 0),
        (20, "Sir Rodney's Marmalade", 8, 3, "30 gift boxes",      81.00,  40, 0,  0,  0),
    ]
    c.executemany(
        "INSERT INTO Products (ProductID,ProductName,SupplierID,CategoryID,QuantityPerUnit,UnitPrice,UnitsInStock,UnitsOnOrder,ReorderLevel,Discontinued) VALUES (?,?,?,?,?,?,?,?,?,?)",
        products
    )

    # Orders
    orders = [
        (10248, "VINET", 5, "1996-07-04", "1996-08-01", "1996-07-16", 3, 32.38, "Vins et alcools Chevalier", "59 rue de l'Abbaye", "Reims",     None,   "51100", "France"),
        (10249, "TOMSP", 6, "1996-07-05", "1996-08-16", "1996-07-10", 1, 11.61, "Toms Spezialitäten",        "Luisenstr. 48",       "Münster",   None,   "44087", "Germany"),
        (10250, "HANAR", 4, "1996-07-08", "1996-08-05", "1996-07-12", 2, 65.83, "Hanari Carnes",             "Rua do Paço, 67",     "Rio de Janeiro","RJ","05454-876","Brazil"),
        (10251, "VICTE", 3, "1996-07-08", "1996-08-05", "1996-07-15", 1, 41.34, "Victuailles en stock",      "2, rue du Commerce",  "Lyon",      None,   "69004", "France"),
        (10252, "SUPRD", 4, "1996-07-09", "1996-08-06", "1996-07-11", 2, 51.30, "Suprêmes délices",          "Boulevard Tirou, 255","Charleroi", None,   "B-6000","Belgium"),
        (10253, "HANAR", 3, "1996-07-10", "1996-07-24", "1996-07-16", 2, 58.17, "Hanari Carnes",             "Rua do Paço, 67",     "Rio de Janeiro","RJ","05454-876","Brazil"),
        (10254, "CHOPS", 5, "1996-07-11", "1996-08-08", "1996-07-23", 2, 22.98, "Chop-suey Chinese",         "Hauptstr. 31",        "Bern",      None,   "3012",  "Switzerland"),
        (10255, "RICSU", 9, "1996-07-12", "1996-08-09", "1996-07-15", 3, 148.33,"Richter Supermarkt",        "Starenweg 5",         "Genève",    None,   "1204",  "Switzerland"),
        (10256, "WELLI", 3, "1996-07-15", "1996-08-12", "1996-07-17", 2, 13.97, "Wellington Importadora",    "Rua do Mercado, 12",  "Resende",   "SP",   "08737-363","Brazil"),
        (10257, "HILAA", 4, "1996-07-16", "1996-08-13", "1996-07-22", 3, 81.91, "HILARION-Abastos",          "Carrera 22 con Ave. Carlos Soublette #8-35", "San Cristóbal", "Táchira", "5022", "Venezuela"),
    ]
    # Note: some CustomerIDs above (VINET, TOMSP etc.) are not in our 10-customer seed,
    # so we use customers that ARE in our seed for orders.
    orders_adjusted = [
        (10248, "ALFKI", 5, "1996-07-04", "1996-08-01", "1996-07-16", 3, 32.38, "Alfreds Futterkiste",       "Obere Str. 57",       "Berlin",    None,   "12209", "Germany"),
        (10249, "ANATR", 6, "1996-07-05", "1996-08-16", "1996-07-10", 1, 11.61, "Ana Trujillo",              "Avda. de la Constitución 2222","México D.F.",None,"05021","Mexico"),
        (10250, "AROUT", 4, "1996-07-08", "1996-08-05", "1996-07-12", 2, 65.83, "Around the Horn",           "120 Hanover Sq.",     "London",    None,   "WA1 1DP","UK"),
        (10251, "BERGS", 3, "1996-07-08", "1996-08-05", "1996-07-15", 1, 41.34, "Berglunds snabbköp",        "Berguvsvägen 8",      "Luleå",     None,   "S-958 22","Sweden"),
        (10252, "BLAUS", 4, "1996-07-09", "1996-08-06", "1996-07-11", 2, 51.30, "Blauer See Delikatessen",   "Forsterstr. 57",      "Mannheim",  None,   "68306", "Germany"),
        (10253, "BLONP", 3, "1996-07-10", "1996-07-24", "1996-07-16", 2, 58.17, "Blondesddsl père et fils",  "24, place Kléber",    "Strasbourg",None,   "67000", "France"),
        (10254, "BOLID", 5, "1996-07-11", "1996-08-08", "1996-07-23", 2, 22.98, "Bólido Comidas preparadas", "C/ Araquil, 67",      "Madrid",    None,   "28023", "Spain"),
        (10255, "BONAP", 9, "1996-07-12", "1996-08-09", "1996-07-15", 3, 148.33,"Bon app'",                  "12, rue des Bouchers","Marseille", None,   "13008", "France"),
        (10256, "BOTTM", 3, "1996-07-15", "1996-08-12", "1996-07-17", 2, 13.97, "Bottom-Dollar Markets",     "23 Tsawassen Blvd.", "Tsawassen", "BC",   "T2F 8M4","Canada"),
        (10257, "BSBEV", 4, "1996-07-16", "1996-08-13", "1996-07-22", 3, 81.91, "B's Beverages",             "Fauntleroy Circus",   "London",    None,   "EC2 5NT","UK"),
    ]
    c.executemany(
        "INSERT INTO Orders (OrderID,CustomerID,EmployeeID,OrderDate,RequiredDate,ShippedDate,ShipVia,Freight,ShipName,ShipAddress,ShipCity,ShipRegion,ShipPostalCode,ShipCountry) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        orders_adjusted
    )

    # OrderDetails  (OrderID, ProductID, UnitPrice, Quantity, Discount)
    order_details = [
        (10248, 11, 14.00, 12, 0.0),
        (10248, 42, 9.80,  10, 0.0),
        (10248, 72, 34.80,  5, 0.0),
        (10249,  14, 18.60,  9, 0.0),
        (10249,  51, 42.40, 40, 0.0),
        (10250,  41, 7.70,  10, 0.0),
        (10250,  51, 42.40, 35, 0.15),
        (10250,  65, 16.80, 15, 0.15),
        (10251,  22, 16.80,  6, 0.05),
        (10251,  57, 15.60, 15, 0.05),
        (10251,  65, 16.80, 20, 0.0),
        (10252,   5, 17.00,  2, 0.0),
        (10252,  50, 13.00,  5, 0.0),
        (10252,  77, 10.40, 12, 0.0),
        (10253,  31, 10.00, 20, 0.0),
        (10253,  39, 14.40, 42, 0.0),
        (10253,  49, 16.00, 40, 0.0),
        (10254,  24, 3.60,  15, 0.15),
        (10254,  55, 19.20, 21, 0.15),
        (10254,  74, 8.00,  21, 0.0),
        (10255,   2, 15.20, 20, 0.0),
        (10255,  16, 13.90, 35, 0.0),
        (10255,  36, 15.20, 25, 0.0),
        (10256,  53, 26.20, 15, 0.0),
        (10257,  27, 35.10, 25, 0.0),
        (10257,  39, 14.40,  6, 0.0),
        (10257,  77, 10.40, 15, 0.0),
    ]
    # Remap ProductIDs to ones that exist in our 20-product seed
    order_details_adjusted = [
        (10248,  1, 18.00, 12, 0.0),
        (10248,  2, 19.00, 10, 0.0),
        (10248,  3, 10.00,  5, 0.0),
        (10249,  4, 22.00,  9, 0.0),
        (10249,  6, 25.00, 10, 0.0),
        (10250,  7, 30.00, 10, 0.0),
        (10250,  8, 40.00,  5, 0.15),
        (10250, 10, 31.00, 15, 0.15),
        (10251, 11, 21.00,  6, 0.05),
        (10251, 13,  6.00, 15, 0.05),
        (10251, 14, 23.25, 20, 0.0),
        (10252,  5, 21.35,  2, 0.0),
        (10252, 15, 15.50,  5, 0.0),
        (10252, 16, 17.45, 12, 0.0),
        (10253, 12, 38.00, 20, 0.0),
        (10253, 18, 62.50,  4, 0.0),
        (10253, 19,  9.20, 10, 0.0),
        (10254,  1, 18.00, 15, 0.15),
        (10254,  2, 19.00, 21, 0.15),
        (10254,  3, 10.00, 21, 0.0),
        (10255,  4, 22.00, 20, 0.0),
        (10255,  6, 25.00, 35, 0.0),
        (10255,  7, 30.00, 25, 0.0),
        (10256,  8, 40.00, 15, 0.0),
        (10257,  9, 97.00,  5, 0.0),
        (10257, 10, 31.00,  6, 0.0),
        (10257, 11, 21.00, 15, 0.0),
    ]
    c.executemany(
        "INSERT INTO OrderDetails (OrderID,ProductID,UnitPrice,Quantity,Discount) VALUES (?,?,?,?,?)",
        order_details_adjusted
    )

    conn.commit()
    conn.close()


def init_db():
    create_tables()
    seed_data()
