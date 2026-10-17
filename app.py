"""EcoConnect - Reuse Before You Recycle. Flask + SQLite (plain SQL, portable to MySQL)."""
import os, sqlite3, random, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "ecoconnect.db")
UPLOADS = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOADS, exist_ok=True)

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
                  MAX_CONTENT_LENGTH=4 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax")

CATS = [("Mobile Phones", "📱"), ("Laptops", "💻"), ("Monitors", "🖥️"), ("Printers", "🖨️"),
        ("Audio Devices", "🎧"), ("Computer Accessories", "⌨️"), ("Televisions", "📺"),
        ("Gaming Devices", "🎮"), ("Chargers & Cables", "🔌"), ("Batteries", "🔋"), ("Other Electronics", "🔧")]
ICONS = dict(CATS)
CONDITIONS = ["Like New", "Good", "Fair", "Needs Repair"]
TYPES = ["sell", "donate", "exchange"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE,
 phone TEXT UNIQUE, password_hash TEXT, location TEXT, profile_image TEXT, is_admin INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL REFERENCES users(id),
 title TEXT NOT NULL, category TEXT, brand TEXT, model TEXT, condition TEXT, age TEXT, description TEXT, price INTEGER DEFAULT 0,
 listing_type TEXT, exchange_for TEXT, location TEXT, status TEXT DEFAULT 'active', created_at TEXT);
CREATE TABLE IF NOT EXISTS product_images(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER REFERENCES products(id), image_url TEXT);
CREATE TABLE IF NOT EXISTS interests(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER REFERENCES products(id),
 user_id INTEGER REFERENCES users(id), purpose TEXT, message TEXT, contact_pref TEXT, status TEXT DEFAULT 'pending', created_at TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, message TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS favorites(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, UNIQUE(user_id, product_id));
CREATE TABLE IF NOT EXISTS pickup_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT, quantity TEXT,
 address TEXT, city TEXT, pin TEXT, phone TEXT, date TEXT, time TEXT, notes TEXT, status TEXT DEFAULT 'Pending', created_at TEXT);
CREATE TABLE IF NOT EXISTS collection_centers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, address TEXT, city TEXT, pin TEXT,
 phone TEXT, opening_hours TEXT, accepts TEXT, latitude REAL, longitude REAL);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER, product_id INTEGER, reason TEXT,
 description TEXT, status TEXT DEFAULT 'open', created_at TEXT);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TEXT);
"""

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def q(sql, args=(), one=False):
    rows = db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows

def run(sql, args=()):
    c = db().execute(sql, args); db().commit(); return c.lastrowid

def notify(uid, msg): run("INSERT INTO notifications(user_id,message,created_at) VALUES(?,?,?)", (uid, msg, now()))

def init_db():
    con = sqlite3.connect(DB); con.executescript(SCHEMA)
    if not con.execute("SELECT 1 FROM users").fetchone():
        pw = generate_password_hash("demo1234")
        for n, e, ph, c in [("Samardeep", "demo@ecoconnect.test", "9000000001", "Pune"),
                            ("Priya Nair", "priya@ecoconnect.test", "9000000002", "Pimpri"),
                            ("Rahul Patil", "rahul@ecoconnect.test", "9000000003", "Mumbai")]:
            con.execute("INSERT INTO users(name,email,phone,password_hash,location,created_at) VALUES(?,?,?,?,?,?)", (n, e, ph, pw, c, now()))
        con.execute("INSERT INTO users(name,email,password_hash,location,is_admin,created_at) VALUES('Admin','admin@ecoconnect.test',?,'Pune',1,?)", (pw, now()))
        demo = [("Dell Inspiron Laptop", "Laptops", "Dell", "Inspiron 15", "Good", "3 years", "i5, 8GB RAM, 256GB SSD. Battery holds ~3 hours.", 18000, "sell", "Pune", 2),
                ("Samsung 22-inch Monitor", "Monitors", "Samsung", "S22", "Like New", "1 year", "Full HD, HDMI and VGA. No dead pixels.", 3500, "sell", "Pimpri", 2),
                ("Redmi Note 8", "Mobile Phones", "Xiaomi", "Note 8", "Fair", "5 years", "Works well, small crack on the back. Charger included.", 0, "donate", "Pune", 3),
                ("HP LaserJet Printer", "Printers", "HP", "1020", "Good", "4 years", "Prints cleanly. Toner half full.", 0, "exchange", "Mumbai", 3),
                ("Boat Bluetooth Headphones", "Audio Devices", "boAt", "Rockerz 450", "Good", "2 years", "Battery lasts a full day.", 900, "sell", "Pune", 2),
                ("Logitech Keyboard and Mouse", "Computer Accessories", "Logitech", "MK215", "Good", "2 years", "Wireless combo with USB receiver.", 0, "donate", "Pimpri", 3),
                ("Sony 32-inch LED TV", "Televisions", "Sony", "Bravia 32", "Needs Repair", "6 years", "Powers on but backlight is faulty. Good for parts or repair.", 0, "donate", "Pune", 2),
                ("Old Laptop Batteries (x3)", "Batteries", "Assorted", "", "Fair", "5+ years", "Weak batteries. Best for a repair workshop.", 0, "exchange", "Mumbai", 3)]
        for d in demo:
            con.execute("INSERT INTO products(title,category,brand,model,condition,age,description,price,listing_type,location,seller_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", d + (now(),))
        con.execute("UPDATE products SET exchange_for='A working USB hub or a webcam' WHERE listing_type='exchange'")
        for c in [("GreenLoop Recyclers", "Plot 14, MIDC Bhosari", "Pimpri", "411026", "020-5550101", "Mon-Sat 10:00-18:00", "Phones, laptops, batteries", 18.6279, 73.8009),
                  ("Pune Municipal E-Waste Depot", "Shivajinagar", "Pune", "411005", "020-5550102", "Mon-Fri 9:00-17:00", "All electronics", 18.5308, 73.8475),
                  ("CleanTech Collection Point", "Andheri East", "Mumbai", "400069", "022-5550103", "Daily 10:00-19:00", "TVs, monitors, printers", 19.1136, 72.8697),
                  ("Campus Drop Box (CEP)", "College Main Gate", "Pune", "411001", "020-5550104", "Mon-Sat 9:00-16:00", "Phones, chargers, cables", 18.5204, 73.8567)]:
            con.execute("INSERT INTO collection_centers(name,address,city,pin,phone,opening_hours,accepts,latitude,longitude) VALUES(?,?,?,?,?,?,?,?,?)", c)
        con.commit()
    con.close()

# ---------- helpers ----------
@app.before_request
def csrf_check():
    session.setdefault("_csrf", secrets.token_hex(16))
    if request.method == "POST" and not secrets.compare_digest(request.form.get("_csrf", ""), session["_csrf"]):
        abort(400, "Invalid form token. Reload the page and try again.")

def me():
    return q("SELECT * FROM users WHERE id=?", (session["uid"],), one=True) if "uid" in session else None

@app.context_processor
def inject():
    u = me()
    unread = q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (u["id"],), one=True)["c"] if u else 0
    return dict(user=u, unread=unread, CATS=CATS, ICONS=ICONS, csrf=session.get("_csrf", ""))

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            flash("Log in to continue.", "info"); return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return w

def save_photo(f):
    if not f or not f.filename: return None
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        flash("Photos must be PNG, JPG or WebP.", "error"); return None
    name = secrets.token_hex(8) + "." + ext
    f.save(os.path.join(UPLOADS, name)); return name

PRODUCT_SQL = """SELECT p.*, u.name seller_name, u.location seller_city, u.created_at seller_since,
 (SELECT image_url FROM product_images WHERE product_id=p.id LIMIT 1) image FROM products p JOIN users u ON u.id=p.seller_id """

def start_session(uid):
    session.clear(); session["uid"] = uid; session["_csrf"] = secrets.token_hex(16)

# ---------- public pages ----------
@app.route("/")
def home():
    stats = dict(
        members=q("SELECT COUNT(*) c FROM users", one=True)["c"],
        listings=q("SELECT COUNT(*) c FROM products", one=True)["c"],
        reused=q("SELECT COUNT(*) c FROM products WHERE status IN ('sold','donated','exchanged')", one=True)["c"],
        pickups=q("SELECT COUNT(*) c FROM pickup_requests", one=True)["c"],
        centers=q("SELECT COUNT(*) c FROM collection_centers", one=True)["c"])
    featured = q(PRODUCT_SQL + "WHERE p.status='active' ORDER BY p.id DESC LIMIT 6")
    return render_template("home.html", stats=stats, featured=featured)

@app.route("/market")
def market():
    where, args = ["p.status='active'"], []
    s = request.args.get("q", "").strip()
    if s: where.append("(p.title LIKE ? OR p.brand LIKE ? OR p.model LIKE ?)"); args += [f"%{s}%"] * 3
    for key, col in [("category", "p.category"), ("type", "p.listing_type"), ("condition", "p.condition")]:
        if request.args.get(key): where.append(f"{col}=?"); args.append(request.args[key])
    if request.args.get("city"): where.append("p.location LIKE ?"); args.append(f"%{request.args['city']}%")
    if request.args.get("max_price", "").isdigit(): where.append("p.price<=?"); args.append(int(request.args["max_price"]))
    items = q(PRODUCT_SQL + "WHERE " + " AND ".join(where) + " ORDER BY p.id DESC", args)
    return render_template("market.html", items=items, CONDITIONS=CONDITIONS, TYPES=TYPES)

@app.route("/product/<int:pid>")
def product(pid):
    p = q(PRODUCT_SQL + "WHERE p.id=?", (pid,), one=True) or abort(404)
    saved = bool(user_id() and q("SELECT 1 FROM favorites WHERE user_id=? AND product_id=?", (user_id(), pid), one=True))
    n = q("SELECT COUNT(*) c FROM products WHERE seller_id=?", (p["seller_id"],), one=True)["c"]
    return render_template("product.html", p=p, saved=saved, listings=n)

def user_id(): return session.get("uid")

@app.route("/centers")
def centers():
    s = request.args.get("q", "").strip()
    rows = q("SELECT * FROM collection_centers WHERE city LIKE ? OR address LIKE ? OR pin LIKE ?", (f"%{s}%",) * 3)
    return render_template("centers.html", rows=rows)

@app.route("/recycle")
def recycle(): return render_template("recycle.html")

# ---------- auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=?", (request.form.get("email", "").strip().lower(),), one=True)
        if u and u["password_hash"] and check_password_hash(u["password_hash"], request.form.get("password", "")):
            start_session(u["id"]); return redirect(request.args.get("next") if (request.args.get("next") or "").startswith("/") else url_for("home"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        f = request.form
        name, email, phone, city, pw = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("phone", "").strip(), f.get("city", "").strip(), f.get("password", "")
        err = None
        if not name or "@" not in email: err = "Enter your name and a valid email."
        elif not phone.isdigit() or len(phone) != 10: err = "Mobile number must be 10 digits."
        elif len(pw) < 8: err = "Password needs at least 8 characters."
        elif pw != f.get("confirm"): err = "Passwords do not match."
        elif not f.get("terms"): err = "Accept the Terms & Conditions to continue."
        elif q("SELECT 1 FROM users WHERE email=? OR phone=?", (email, phone), one=True): err = "An account with this email or mobile already exists."
        if err: flash(err, "error")
        else:
            uid = run("INSERT INTO users(name,email,phone,password_hash,location,profile_image,created_at) VALUES(?,?,?,?,?,?,?)",
                      (name, email, phone, generate_password_hash(pw), city, save_photo(request.files.get("photo")), now()))
            start_session(uid); flash("Welcome to EcoConnect!", "ok"); return redirect(url_for("home"))
    return render_template("signup.html")

@app.route("/auth/google/demo", methods=["POST"])
def google_demo():
    # DEMO ONLY. Production: use Authlib with Google OAuth (client id/secret) and verify the ID token.
    u = q("SELECT * FROM users WHERE email='google.demo@ecoconnect.test'", one=True)
    uid = u["id"] if u else run("INSERT INTO users(name,email,location,created_at) VALUES('Google Demo User','google.demo@ecoconnect.test','Pune',?)", (now(),))
    start_session(uid); return redirect(url_for("home"))

@app.route("/auth/otp", methods=["POST"])
def otp():
    # DEMO ONLY. Production: send the OTP through an SMS provider and rate-limit attempts.
    phone, action = request.form.get("phone", "").strip(), request.form.get("action")
    if not (phone.isdigit() and len(phone) == 10): flash("Enter a 10-digit mobile number.", "error")
    elif action == "send":
        session["otp"], session["otp_phone"] = str(random.randint(100000, 999999)), phone
        flash(f"Demo mode: your OTP is {session['otp']} (no SMS is sent).", "info")
    elif session.get("otp") and phone == session.get("otp_phone") and request.form.get("code") == session["otp"]:
        u = q("SELECT * FROM users WHERE phone=?", (phone,), one=True)
        uid = u["id"] if u else run("INSERT INTO users(name,phone,location,created_at) VALUES(?,?,'',?)", ("Member " + phone[-4:], phone, now()))
        start_session(uid); return redirect(url_for("home"))
    else: flash("That OTP is not correct. Send a new one.", "error")
    return redirect(url_for("login"))

@app.route("/logout", methods=["POST"])
def logout(): session.clear(); return redirect(url_for("home"))

# ---------- listings & requests ----------
@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    if request.method == "POST":
        f = request.form; t = f.get("listing_type")
        if t == "recycle": return redirect(url_for("recycle"))
        if t not in TYPES or not f.get("title", "").strip() or f.get("category") not in ICONS:
            flash("Add a title, category and what you want to do with the item.", "error"); return render_template("post.html", CONDITIONS=CONDITIONS)
        price = int(f["price"]) if t == "sell" and f.get("price", "").isdigit() else 0
        pid = run("INSERT INTO products(seller_id,title,category,brand,model,condition,age,description,price,listing_type,exchange_for,location,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (user_id(), f["title"].strip(), f["category"], f.get("brand", ""), f.get("model", ""), f.get("condition"), f.get("age", ""),
                   f.get("description", ""), price, t, f.get("exchange_for", ""), f.get("location", ""), now()))
        img = save_photo(request.files.get("photo"))
        if img: run("INSERT INTO product_images(product_id,image_url) VALUES(?,?)", (pid, img))
        flash("Your item is live.", "ok"); return redirect(url_for("product", pid=pid))
    return render_template("post.html", CONDITIONS=CONDITIONS)

@app.route("/product/<int:pid>/interest", methods=["POST"])
@login_required
def interest(pid):
    p = q("SELECT * FROM products WHERE id=?", (pid,), one=True) or abort(404)
    if p["seller_id"] == user_id(): flash("This is your own listing.", "error"); return redirect(url_for("product", pid=pid))
    f = request.form
    rid = run("INSERT INTO interests(product_id,user_id,purpose,message,contact_pref,created_at) VALUES(?,?,?,?,?,?)",
              (pid, user_id(), f.get("purpose", "Other"), f.get("message", "")[:500], f.get("contact_pref", "Platform"), now()))
    notify(p["seller_id"], f"Someone is interested in your {p['title']}.")
    flash(f"Application sent successfully! Request ID: REQ-{10000 + rid}", "ok")
    return redirect(url_for("product", pid=pid))

@app.route("/interest/<int:iid>/<action>", methods=["POST"])
@login_required
def decide(iid, action):
    r = q("SELECT i.*, p.seller_id, p.title FROM interests i JOIN products p ON p.id=i.product_id WHERE i.id=?", (iid,), one=True) or abort(404)
    if r["seller_id"] != user_id() or action not in ("accept", "reject"): abort(403)
    status = "accepted" if action == "accept" else "rejected"
    run("UPDATE interests SET status=? WHERE id=?", (status, iid))
    notify(r["user_id"], f"Your request for {r['title']} was {status}.")
    flash("Request Accepted 🎉" if status == "accepted" else "Request rejected.", "ok"); return redirect(url_for("dashboard"))

@app.route("/product/<int:pid>/status", methods=["POST"])
@login_required
def set_status(pid):
    p = q("SELECT * FROM products WHERE id=?", (pid,), one=True) or abort(404)
    st = request.form.get("status")
    if p["seller_id"] != user_id() or st not in ("active", "sold", "donated", "exchanged", "recycled", "deleted"): abort(403)
    if st == "deleted": run("DELETE FROM products WHERE id=?", (pid,))
    else: run("UPDATE products SET status=? WHERE id=?", (st, pid))
    return redirect(url_for("dashboard"))

@app.route("/product/<int:pid>/favorite", methods=["POST"])
@login_required
def favorite(pid):
    if q("SELECT 1 FROM favorites WHERE user_id=? AND product_id=?", (user_id(), pid), one=True):
        run("DELETE FROM favorites WHERE user_id=? AND product_id=?", (user_id(), pid))
    else: run("INSERT INTO favorites(user_id,product_id) VALUES(?,?)", (user_id(), pid))
    return redirect(request.referrer or url_for("product", pid=pid))

@app.route("/product/<int:pid>/report", methods=["POST"])
@login_required
def report(pid):
    run("INSERT INTO reports(reporter_id,product_id,reason,description,created_at) VALUES(?,?,?,?,?)",
        (user_id(), pid, request.form.get("reason", "Other"), request.form.get("description", "")[:500], now()))
    flash("Thanks. Our team will review this listing.", "ok"); return redirect(url_for("product", pid=pid))

@app.route("/dashboard")
@login_required
def dashboard():
    uid = user_id()
    mine = q(PRODUCT_SQL + "WHERE p.seller_id=? ORDER BY p.id DESC", (uid,))
    incoming = q("""SELECT i.*, p.title, u.name applicant, u.location applicant_city FROM interests i JOIN products p ON p.id=i.product_id
                    JOIN users u ON u.id=i.user_id WHERE p.seller_id=? ORDER BY i.id DESC""", (uid,))
    sent = q("SELECT i.*, p.title FROM interests i JOIN products p ON p.id=i.product_id WHERE i.user_id=? ORDER BY i.id DESC", (uid,))
    favs = q(PRODUCT_SQL + "WHERE p.id IN (SELECT product_id FROM favorites WHERE user_id=?)", (uid,))
    pickups = q("SELECT * FROM pickup_requests WHERE user_id=? ORDER BY id DESC", (uid,))
    return render_template("dashboard.html", mine=mine, incoming=incoming, sent=sent, favs=favs, pickups=pickups)

@app.route("/pickup", methods=["POST"])
@login_required
def pickup():
    f = request.form
    if not (f.get("address") and f.get("category") and f.get("phone", "").isdigit()):
        flash("Fill in address, category and a valid mobile number.", "error"); return redirect(url_for("recycle") + "#pickup")
    rid = run("INSERT INTO pickup_requests(user_id,category,quantity,address,city,pin,phone,date,time,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
              (user_id(), f["category"], f.get("quantity", ""), f["address"], f.get("city", ""), f.get("pin", ""), f["phone"], f.get("date", ""), f.get("time", ""), f.get("notes", "")[:500], now()))
    flash(f"Pickup Request Submitted Successfully. Pickup ID: EW-{10240 + rid}. Status: Pending → Assigned → Picked Up → Recycled", "ok")
    return redirect(url_for("dashboard") + "#pickups")

@app.route("/notifications")
@login_required
def notifications():
    rows = q("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (user_id(),))
    run("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id(),))
    return render_template("notifications.html", rows=rows)

# ---------- admin ----------
def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        u = me()
        if not u or not u["is_admin"]:
            return redirect(url_for("admin_login"))
        return f(*a, **k)
    return w

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=? AND is_admin=1",
              (request.form.get("email", "").strip().lower(),), one=True)
        if u and u["password_hash"] and check_password_hash(u["password_hash"], request.form.get("password", "")):
            start_session(u["id"]); return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin_login.html")

@app.route("/admin")
@admin_required
def admin_dashboard():
    pickups = q("""SELECT r.*, u.name user_name FROM pickup_requests r
                   LEFT JOIN users u ON u.id=r.user_id ORDER BY r.id DESC""")
    exchanges = q("""SELECT i.*, p.title, p.listing_type, a.name applicant, s.name seller
                     FROM interests i JOIN products p ON p.id=i.product_id
                     JOIN users a ON a.id=i.user_id JOIN users s ON s.id=p.seller_id
                     ORDER BY i.id DESC""")
    return render_template("admin.html", pickups=pickups, exchanges=exchanges)

@app.route("/admin/pickup/<int:rid>/<action>", methods=["POST"])
@admin_required
def admin_pickup(rid, action):
    states = {"approve": "Assigned", "reject": "Rejected", "picked": "Picked Up", "recycled": "Recycled"}
    r = q("SELECT * FROM pickup_requests WHERE id=?", (rid,), one=True) or abort(404)
    if action not in states: abort(400)
    run("UPDATE pickup_requests SET status=? WHERE id=?", (states[action], rid))
    notify(r["user_id"], f"Your pickup EW-{10240 + rid} is now: {states[action]}.")
    flash(f"Pickup EW-{10240 + rid} marked {states[action]}.", "ok")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/interest/<int:iid>/<action>", methods=["POST"])
@admin_required
def admin_interest(iid, action):
    r = q("SELECT i.*, p.title FROM interests i JOIN products p ON p.id=i.product_id WHERE i.id=?", (iid,), one=True) or abort(404)
    if action not in ("accept", "reject"): abort(400)
    status = "accepted" if action == "accept" else "rejected"
    run("UPDATE interests SET status=? WHERE id=?", (status, iid))
    notify(r["user_id"], f"Your request for {r['title']} was {status}.")
    flash(f"Request REQ-{10000 + iid} {status}.", "ok")
    return redirect(url_for("admin_dashboard"))

init_db()
if __name__ == "__main__": app.run(debug=True)
