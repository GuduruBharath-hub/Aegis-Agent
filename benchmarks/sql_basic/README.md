# sql_basic

Minimal SQLite benchmark for AegisAgent's direct SQL-injection path. The
application is intentionally vulnerable; its public tests describe required
behavior but are not the security oracle.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
