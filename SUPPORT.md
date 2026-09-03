# Support

Nakeuri Foundry is currently beta software.

For a reproducible defect, use the GitHub **Bug report** template and include the smallest reproduction, operating system, Python/toolchain versions, the command that failed and deterministic evidence where available.

For setup problems, run:

```bash
nakeuri doctor
nakeuri doctor-deep . --probe-docker
nakeuri compatibility .
```

For security vulnerabilities, do **not** open a public issue with exploit details. Follow `SECURITY.md` and use GitHub private vulnerability reporting / Security Advisories when the repository has them enabled.

Feature proposals should explain the concrete present use case and the smallest acceptable solution. Generic framework expansion without current evidence is intentionally discouraged.
