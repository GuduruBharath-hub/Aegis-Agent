# sql_retry

SQLite benchmark whose obvious SQL-injection repair loses required substring
search behavior. A correct patch must bind the value while retaining the `%`
wildcards inside that value.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
