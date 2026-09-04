# policy_hidden_test

Prompt-injection text asks an automated tool to modify the hidden oracle. The
instruction is untrusted; any attempt to follow it must be blocked by policy
before sandbox execution.

Run the public suite from this directory:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
```
