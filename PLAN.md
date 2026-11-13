# Application Security Pipeline — plan

## Hito 1 — API, Docker, amenazas y tests

Estado: **completado y verificado localmente** (2026-09-22).

- [x] API Flask con sesiones, CSRF, documentos privados y administración explícita.
- [x] PostgreSQL, migración Alembic y datos ficticios reproducibles.
- [x] Dependencias bloqueadas, Docker y Compose.
- [x] Tests funcionales y de autorización contra PostgreSQL aislado: 86 tests pasados.
- [x] Workflow básico de tests en GitHub Actions creado, publicado y ejecutado correctamente.
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
La ejecución remota `43377302994` terminó correctamente: 86 tests pasados,
Ruff correcto y limpieza de PostgreSQL completada. Las ejecuciones anteriores
fallaron por el bloqueo de facturación ya resuelto.

## Hito 2 — Semgrep, Trivy y OWASP ZAP

Estado: **completado y verificado localmente y en GitHub** (2026-11-13).

- [x] Integrar escáneres con versiones fijadas e informes como artefactos de CI.
- [x] Semgrep sobre código, Trivy sobre la imagen construida y ZAP sobre un
      entorno temporal con PostgreSQL y datos ficticios.
- [x] Configurar login, cookies y CSRF de ZAP; demostrar que visita rutas
      autenticadas. Fallar si el entorno o la autenticación no están disponibles.

Aceptación: informes reales de los tres escáneres y evidencia de cobertura
autenticada de ZAP. Un fallo del escáner nunca equivale a un análisis limpio.

Evidencia: ejecución Security `43452105398`, con Semgrep y ZAP correctos y Trivy
bloqueando hallazgos reales, con artefactos publicados para los tres escáneres.
La base actualizada y el parche de zlib reducen los bloqueos locales de 110 a 47.
Queda trabajo de remediación de esos hallazgos, independiente de la integración.

## Hito 3 — Bloqueos, demostraciones y documentación final

Estado: **completado**. Políticas y configuración de protección versionadas.

- [x] Bloquear tests fallidos, errores de escáner, Semgrep ERROR, Trivy
      High/Critical y ZAP High. Revisar Medium/Low sin convertirlos en silencio.
- [x] Excepciones con identificador, alcance, motivo, responsable y fecha de
      revisión; rechazar excepciones vencidas.
- [x] Documentar rulesets/checks requeridos de GitHub antes de integrar cambios.
- [x] Demostraciones vulnerables aisladas del código y despliegue normales.
- [x] Mostrar riesgo → fallo reproducible → control → test posterior.

Aceptación: cada bloqueo tiene una demostración, las excepciones son auditables
y ninguna opción de configuración vuelve vulnerable la aplicación normal.

Cuatro pruebas de política verifican bloqueos y excepciones; la demo BOLA
comprueba el fallo y su corrección y Semgrep debe detectar la fixture aislada.
La protección exige PR, rama actualizada y los cuatro checks, también al administrador.
Configuración: `security/branch-protection.json`. Los hallazgos de Trivy impiden
integrar cambios hasta remediarlos o aprobar una excepción concreta justificada.

## Decisiones

- Los umbrales también bloquean vulnerabilidades sin parche; no se han aprobado
  excepciones para ocultar los hallazgos actuales de Trivy.
- Instrucciones de análisis y revisión en [SECURITY_PIPELINE.md](docs/SECURITY_PIPELINE.md).

- Administrador: lectura y borrado globales por rutas `/admin`; solo el dueño edita.
- Sin registro público: usuarios y roles se crean mediante CLI de confianza.
- Sin frontend, archivos adjuntos, Redis, JWT ni servicio de sesiones adicional.
- Documentación en español; nombres de código y contrato de API en inglés.
- Las ejecuciones remotas y los escáneres se registrarán solo cuando ocurran.
