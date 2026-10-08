# AGENTS.md — app_certs

Greenfield repo. No code, manifests, build, tests, CI, or linter exist yet (verified 2026-10-01). Do not assume a stack; scaffold explicitly and confirm with user before adding dependencies.

## Inputs (read-only source of truth)

- `insumos/Maestro_Estudiantes.xlsx` — sheet `Estudiantes` (25 rows x 5 cols): `Identificacion, Nombre_Completo, Correo, Programa, Cohorte`
- `insumos/Registro_Evaluaciones.xlsx` — sheet `Evaluaciones` (~89 rows x 6 cols): `Identificacion, Programa, Modulo, Nota, Asistencia_Pct, Fecha_Cierre`
- Join key across both files: `Identificacion` (string-like; preserve leading zeros, do not cast to int).
- Never edit files under `insumos/`; treat them as fixtures. Write outputs elsewhere (e.g. `salida/`).

## Conventions for new code

- Document the certificate/approval rule (min `Nota`, min `Asistencia_Pct`, required `Modulo`s) wherever it is implemented — it is not derivable from the inputs alone.
- `Registro_Evaluaciones.xlsx` stores one row per student per module (`Módulo 1..4`); any aggregation must group by `Identificacion`.
