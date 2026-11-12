# Verificación del hito 1

Fecha: 2026-09-22. Comprobaciones locales; no representa una ejecución de GitHub
Actions ni resultados de Semgrep, Trivy o ZAP.

Estado: **hito 1 verificado localmente**. Los comandos se ejecutaron mediante el
proxy `rtk`; se muestran sin ese prefijo para que puedan reproducirse sin instalarlo.

## Comandos y resultados

| Comando / comprobación | Resultado real |
|---|---|
| `uv lock`, `uv sync --frozen` | Lock generado e instalación correcta de dependencias. Se necesitó acceso externo a PyPI. |
| `uv lock --check --offline` | Correcto: manifest y lock coinciden. |
| `.venv/bin/ruff check .` | Todos los checks correctos. |
| `.venv/bin/ruff format --check .` | Correcto. |
| `python3 scripts/init_env.py` | `.env` con secretos aleatorios; permisos 0600 verificados. |
| `docker compose config --quiet` y configuración de `compose.test.yaml` | Ambas válidas. No se imprimió la configuración expandida con secretos. |
| `docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests` | Tras la corrección CSRF, 86 tests pasados en 11,90 s. Segunda ejecución independiente: 86 pasados en 11,69 s. Salida 0 en ambas, con Ruff correcto. |
| `docker compose up --build --wait` | Imagen construida, migración aplicada y servicios saludables. El primer intento encontró el puerto 8000 ocupado; se cambió únicamente `APP_PORT` local a 18000 y el segundo terminó con salida 0. |
| `docker compose exec -T app flask --app appsec_pipeline seed-dev` | Tres identidades y datos ficticios creados; contraseñas guardadas en `.env.dev-users` (0600). Repetición correcta, sin mostrar de nuevo contraseñas ni alterar datos existentes. |
| `python3 scripts/smoke.py --base-url http://127.0.0.1:18000 --credentials .env.dev-users` | PASS: salud, login, CSRF, CRUD propio, aislamiento, permisos administrativos y logout. Eliminó su documento temporal. |
| `docker compose ps` | API y PostgreSQL saludables; únicamente API publicada en `127.0.0.1:18000`. |
| Consulta de UID/rol/esquema desde el contenedor API | UID 10001; usuario DB `appsec`; `rolsuper`, `rolcreatedb`, `rolcreaterole` falsos; migración `0001`. |
| Suite final tras incluir utilidades en Ruff del contenedor de tests | Ruff correcto y 86 tests pasados en 11,63 s; salida 0. |
| Inspección del filesystem y módulos de la imagen runtime | No incluye `.env`, `.env.dev-users`, tests, scripts operativos, pytest ni Ruff. |
| Enlaces locales de README, PLAN y documentos | Todos resuelven a archivos existentes. |
| Publicación GitHub | Repositorio público `mariaig01/application-security-pipeline`; `main` contiene los commits `d8d1786` y `225cf55`. |
| Actions run `43188185846` | `startup_failure`, sin jobs/pasos ejecutados; no se cuenta como validación. |
| Actions run `43188295388` | Job creado pero `failure` inmediato con `steps: []`; no se cuenta como validación. |
| Actions run `43188416793` | Repetición con `ubuntu-latest`; `failure` inmediato con `steps: []`; no se cuenta como validación. |

Los tests migran un esquema aleatorio por ejecución, revierten cada test y
comprueban también que la migración coincide con los modelos (`alembic check`).
No se ha medido cobertura porcentual ni se presenta una métrica inventada.

## Reproducir en esta carpeta

La configuración local conserva `APP_PORT=18000` y los datos ficticios. Las
contraseñas están en `.env.dev-users`, no en esta documentación ni en la imagen.

```bash
docker compose up --build --wait
python3 scripts/smoke.py --base-url http://127.0.0.1:18000 --credentials .env.dev-users
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down --volumes --remove-orphans
```

## Incidencias corregidas durante la implementación

La primera suite ejecutó 86 casos: 21 pasaron y 65 fallaron. El fallo común era
un TypeError al validar CSRF: `WTF_CSRF_TIME_LIMIT` requiere segundos enteros,
pero se había proporcionado un `timedelta`, válido para la duración de sesión de
Flask. Se corrigió a `1800`. Las pruebas mantienen CSRF activo; no se desactivó
el control para hacerlas pasar.

## Límites

- El acceso a Docker y los registros de paquetes requirió ejecución fuera del sandbox.
- GitHub Actions está publicado, pero GitHub no ha ejecutado ningún paso del job;
  hay que revisar la configuración de Actions/runner o las restricciones de la
  cuenta antes de considerar CI validada.
- El repositorio público es `https://github.com/mariaig01/application-security-pipeline`.
- La cuenta personal confirmada por el usuario y activada en GitHub CLI es `mariaig01`.
- No se han ejecutado los escáneres de los hitos 2/3.
- No se ha desplegado TLS real ni se han realizado pruebas de carga.
