# cmd_retry

Command-injection benchmark whose obvious `shell=True` repair leaves the integer
`count` inside an argv list. Python subprocess argv entries must be strings, so a
correct patch must remove the shell and retain `str(count)`.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
