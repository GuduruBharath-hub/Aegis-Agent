# cmd_basic

Direct command-injection case without the custom-count regression trap. A
minimal fix replaces shell parsing with an argument vector.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
