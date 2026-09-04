import subprocess


def ping_host(host: str, count: int = 2) -> str:
    completed = subprocess.run(
        "ping -c " + str(count) + " " + host,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout
