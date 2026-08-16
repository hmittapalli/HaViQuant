import ast, os, re, subprocess, sys, json

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend=os.path.join(ROOT,"backend","main.py")
appjs=os.path.join(ROOT,"frontend","web","app.js")
css=os.path.join(ROOT,"frontend","web","styles.css")

ast.parse(open(backend,encoding="utf-8").read())
print("PASS: backend Python syntax")

# Node is optional; if present, validate JavaScript syntax.
if shutil_which := __import__("shutil").which("node"):
    p=subprocess.run([shutil_which,"--check",appjs],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    print("PASS: frontend JavaScript syntax")
else:
    print("SKIP: node not installed")

js=open(appjs,encoding="utf-8").read()
for token in ["Stock Analysis","Company Intelligence","Fundamentals","Technical","Decision","Evidence Research","Portfolio","Risk","Backtesting","News","Watchlist","Alerts","Calendar","Settings"]:
    assert token in js, token
print("PASS: all navigation labels present")

for token in ['"1m":["7d","1m"]','"5m":["60d","5m"]','"15m":["60d","15m"]','"1h":["60d","1h"]','"4h":["60d","4h"]']:
    assert token in js, token
print("PASS: 1m/5m/15m/1h/4h controls present")

for token in ["Risk budget (%)","Stop distance (%)","Target 3","Suggested daily stop","R/R T3"]:
    assert token in js, token
print("PASS: trade-plan controls present")

for token in ['positive','neutral','negative','sentimentBadge']:
    assert token in js, token
print("PASS: news/calendar sentiment UI present")

for path in [backend,appjs,css]:
    assert os.path.getsize(path)>0
print("PASS: required UI/backend assets present")
print("PASS: source validation complete")
