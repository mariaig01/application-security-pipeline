# Application Security Pipeline — plan

## Hito 1 — API, Docker, amenazas y tests

Estado: **completado y verificado localmente** (2026-09-22).

- [x] API Flask con sesiones, CSRF, documentos privados y administración explícita.
- [x] PostgreSQL, migración Alembic y datos ficticios reproducibles.
- [x] Dependencias bloqueadas, Docker y Compose.
- [x] Tests funcionales y de autorización contra PostgreSQL aislado: 86 tests pasados.
- [x] Workflow básico de tests en GitHub Actions creado; publicación remota realizada.
- [x] README, STRIDE (11 amenazas) y checklist de revisión.
- [x] Arranque, recorrido HTTP y seed repetido verificados; resultados en
      [docs/VERIFICATION.md](docs/VERIFICATION.md).

Aceptación: seguir el README permite arrancar; un usuario crea y consulta sus
documentos; otro no puede leerlos, modificarlos ni borrarlos; las rutas protegidas
rechazan anónimos; usuarios normales no administran; los tests son repetibles.

Resultado: dos suites consecutivas con 86/86 tests correctos, Ruff correcto,
imagen construida, migración `0001` aplicada y API/DB saludables. Recorrido HTTP
con tres sesiones correcto. Se usó el puerto local 18000 porque el 8000 estaba
ocupado; las credenciales generadas se guardaron con permisos 0600 fuera de Git.
El repositorio público está en https://github.com/mariaig01/application-security-pipeline.
Se intentaron dos ejecuciones remotas de Actions; ambas terminaron en
`failure/startup_failure` antes de crear pasos del job. La causa debe revisarse
en la configuración/runner de GitHub; no se presentan como tests remotos pasados.

## Hito 2 — Semgrep, Trivy y OWASP ZAP

Estado: **pendiente**.

- [ ] Integrar escáneres con versiones fijadas e informes como artefactos de CI.
- [ ] Semgrep sobre código, Trivy sobre la imagen construida y ZAP sobre un
      entorno temporal con PostgreSQL y datos ficticios.
- [ ] Configurar login, cookies y CSRF de ZAP; demostrar que visita rutas
      autenticadas. Fallar si el entorno o la autenticación no están disponibles.

Aceptación: informes reales de los tres escáneres y evidencia de cobertura
autenticada de ZAP. Un fallo del escáner nunca equivale a un análisis limpio.

## Hito 3 — Bloqueos, demostraciones y documentación final

Estado: **pendiente**.

- [ ] Bloquear tests fallidos, errores de escáner, Semgrep ERROR, Trivy
      High/Critical y ZAP High. Revisar Medium/Low sin convertirlos en silencio.
- [ ] Excepciones con identificador, alcance, motivo, responsable y fecha de
      revisión; rechazar excepciones vencidas.
- [ ] Documentar rulesets/checks requeridos de GitHub antes de integrar cambios.
- [ ] Demostraciones vulnerables aisladas del código y despliegue normales.
- [ ] Mostrar riesgo → fallo reproducible → control → test posterior.

Aceptación: cada bloqueo tiene una demostración, las excepciones son auditables
y ninguna opción de configuración vuelve vulnerable la aplicación normal.

## Decisiones

- Administrador: lectura y borrado globales por rutas `/admin`; solo el dueño edita.
- Sin registro público: usuarios y roles se crean mediante CLI de confianza.
- Sin frontend, archivos adjuntos, Redis, JWT ni servicio de sesiones adicional.
- Documentación en español; nombres de código y contrato de API en inglés.
- Las ejecuciones remotas y los escáneres se registrarán solo cuando ocurran.
