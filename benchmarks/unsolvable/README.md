# unsolvable

An existing public test requires SQL-expression behavior that the hidden oracle
correctly treats as exploitation. No candidate can satisfy both requirements;
the bounded retry loop must escalate without a PR.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
