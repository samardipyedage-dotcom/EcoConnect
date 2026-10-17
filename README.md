# EcoConnect - Reuse Before You Recycle
Run: `pip install -r requirements.txt && python app.py` then open http://127.0.0.1:5000
Demo logins (password `demo1234`): demo@ecoconnect.test, priya@ecoconnect.test, admin@ecoconnect.test
Google login and mobile OTP are DEMO flows. For production, use Authlib (Google OAuth) and an SMS provider.
Set SECRET_KEY in the environment. To move to MySQL, keep the SQL and swap the connection layer in `db()`.
