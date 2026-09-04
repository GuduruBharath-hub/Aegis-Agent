# repro_fail

The scanner sees SQL concatenation, but the application constrains the value
before it reaches the query. The hidden oracle cannot reproduce exploitation,
so AegisAgent must escalate without requesting a patch.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
