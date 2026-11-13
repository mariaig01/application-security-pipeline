# Application Security Pipeline

API de documentos privados para aprender Application Security y DevSecOps y
explicar decisiones en una entrevista. Python/Flask, SQLAlchemy, PostgreSQL,
pytest y Docker Compose. Sin frontend ni subida de archivos.

Incluye la aplicación, tests, Docker y un pipeline con Semgrep, Trivy y ZAP
autenticado. Las políticas de bloqueo, excepciones y demostraciones se explican
en [SECURITY_PIPELINE.md](docs/SECURITY_PIPELINE.md). Estado y aceptación en
[PLAN.md](PLAN.md); ejecuciones reales en [VERIFICATION.md](docs/VERIFICATION.md).

## Arranque con Docker

Requisitos: Docker Engine con Compose v2 o posterior, Python 3.12 para las
utilidades locales, acceso a Docker Hub y PyPI en la primera construcción.
Ejecutar desde la raíz del proyecto:

```bash
python3 scripts/init_env.py
docker compose config --quiet
docker compose up --build --wait
curl --fail http://127.0.0.1:8000/health
```

El primer comando crea `.env` con secretos aleatorios y permisos `0600`; se niega
a sobrescribirlo. Si ya existe, conservarlo y empezar por `docker compose`.
`.env.example` documenta las variables y no contiene contraseñas utilizables.
La respuesta de salud esperada es `{"status":"ok"}`.

Compose espera a PostgreSQL, ejecuta `alembic upgrade head` y arranca Gunicorn.
La API se publica en `127.0.0.1:8000`; la base de datos no publica puertos.
Puede cambiarse `APP_PORT` en `.env` si el puerto está ocupado. La imagen usa un
usuario sin privilegios y la API tiene filesystem de solo lectura con `/tmp`
temporal. La conexión de aplicación usa el rol PostgreSQL `appsec`, sin
superusuario, creación de bases ni creación de roles.

Crear datos de desarrollo:

```bash
docker compose exec app flask --app appsec_pipeline seed-dev
```

Crea `alice`, `bob`, `admin` y un documento ficticio para cada uno. Muestra
contraseñas aleatorias **solo al crear los usuarios**: guárdalas fuera del
repositorio. Repetir el comando conserva usuarios, contraseñas y documentos
existentes; no convierte un usuario normal en administrador. Solo funciona con
`APP_ENV=development`. Un documento de seed borrado se repone al repetirlo.

Para guardar la primera salida de forma privada y ejecutar el recorrido HTTP:

```bash
umask 077
docker compose exec -T app flask --app appsec_pipeline seed-dev > .env.dev-users
python3 scripts/smoke.py --credentials .env.dev-users
```

Esta alternativa debe usarse en la **primera** ejecución del seed; una ejecución
posterior no recupera las contraseñas originales. Si ya las guardaste, ejecuta
`python3 scripts/smoke.py` y escríbelas cuando las pida. El script crea un
documento temporal, prueba tres sesiones independientes y lo elimina. No muestra
contraseñas ni elimina documentos anteriores. `.env.dev-users` está ignorado por
Git y excluido de la imagen.

Usuarios adicionales se crean por una CLI de confianza, no por la API:

```bash
docker compose exec app flask --app appsec_pipeline create-user --username carol
docker compose exec app flask --app appsec_pipeline create-user --username reviewer --admin
```

La CLI pide la contraseña sin mostrarla (15–128 caracteres), o admite
`--generate-password` para generar una aleatoria. No existe un argumento de
contraseña que deba quedar en el historial del shell. Los nombres tienen 3–64
caracteres ASCII alfanuméricos, `_`, `.` o `-`, empiezan por alfanumérico y se
normalizan a minúsculas.

```bash
docker compose ps
docker compose logs --tail=50 app
docker compose down
```

`down` conserva el volumen de datos. Para **borrar los datos locales** y empezar
de cero, usar conscientemente `docker compose down --volumes`; después arrancar y
volver a ejecutar el seed. Cambiar contraseñas en `.env` no cambia las de un
volumen ya inicializado: PostgreSQL ejecuta el script de roles solo la primera vez.

## Tests y desarrollo

La vía reproducible, idéntica al job de CI, no necesita `.env` ni PostgreSQL local:

```bash
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down --volumes --remove-orphans
```

El primer comando devuelve el código de salida de los tests; no confundirlo con
el código del comando de limpieza. Ejecuta Ruff y pytest. PostgreSQL de tests
usa almacenamiento temporal y red independiente; sus únicas credenciales fijas
son de tests. Cada ejecución migra un esquema nuevo y cada test revierte su
transacción, incluso cuando el código de aplicación hace `commit`. CSRF permanece
activo. La suite falla si PostgreSQL no está disponible; no sustituye PostgreSQL
por SQLite ni omite silenciosamente pruebas.

Para trabajar directamente con Python, instalar `uv` 0.12.16 y PostgreSQL 17,
crear una base exclusiva cuyo nombre termine en `_test`, y proporcionar su URL:

```bash
uv sync --frozen
read -r -s -p 'TEST_DATABASE_URL: ' TEST_DATABASE_URL; echo
export TEST_DATABASE_URL
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

Formato de URL: `postgresql+psycopg://USUARIO:CONTRASEÑA@HOST:5432/appsec_test`.
El usuario de tests necesita crear esquemas en esa base. La suite solo elimina su
esquema aleatorio; nunca trunca una base proporcionada por el usuario.

Para arrancar sin Docker: configurar `APP_ENV=development`, `SECRET_KEY` aleatoria
y `DATABASE_URL` para una base PostgreSQL propia; ejecutar `uv run --frozen alembic
upgrade head` y `uv run --frozen gunicorn --bind 127.0.0.1:8000
'appsec_pipeline:create_app()'`. La URL de `.env` generada apunta al hostname
interno `db`; no sirve directamente desde el host.

Tras cambiar modelos, generar y revisar una migración con `alembic revision
--autogenerate -m "description"`; probarla desde cero. `alembic check`, también
cubierto por pytest, detecta divergencias de modelos y esquema. Nunca se llama a
`create_all()` al arrancar.

## Contrato y ejemplos de uso

| Método y ruta | Acceso y resultado |
|---|---|
| `GET /health` | Público; 200 si PostgreSQL responde, 503 si no. No enumera tablas ni versiones. |
| `GET /auth/csrf` | Público; token CSRF ligado a la cookie de sesión. |
| `POST /auth/login` | `username`, `password`; requiere CSRF, devuelve identidad. |
| `POST /auth/logout` | Sesión y CSRF; 204. |
| `GET /auth/me` | Identidad y rol actuales; requiere sesión. |
| `GET /documents` | Solo documentos propios, paginados. |
| `POST /documents` | `title`, `content`; 201 y cabecera `Location`. |
| `GET /documents/<uuid>` | Solo propietario. |
| `PATCH /documents/<uuid>` | Solo propietario; actualiza título y/o contenido. |
| `DELETE /documents/<uuid>` | Solo propietario; 204. |
| `GET /admin/documents` | Administrador; lista global paginada. |
| `GET /admin/documents/<uuid>` | Administrador; lectura de cualquier documento. |
| `DELETE /admin/documents/<uuid>` | Administrador; borrado global y registro del evento. |

El administrador también puede gestionar sus propios documentos por las rutas
normales. **No puede editar documentos ajenos**, ni siquiera por `/admin`.
No hay registro público ni endpoint para asignar roles. La autorización consulta
el rol actual en PostgreSQL; no confía en un rol enviado o guardado en la cookie.

Un documento contiene `id`, `owner_id`, `title`, `content`. Listas:
`{"items": [...], "page": 1, "per_page": 20, "has_next": false}`.
Admiten `?page=1&per_page=20`, con máximo 100 resultados por página. Se ordenan por
UUID; la paginación no garantiza una instantánea frente a escrituras concurrentes.

Título: texto no vacío tras recortar espacios, máximo 200 caracteres. Contenido:
texto de 0–50.000 caracteres. Cuerpo HTTP máximo 256 KiB. Se rechazan tipos
incorrectos, caracteres nulos y campos desconocidos; `id`, `owner_id` y `role`
no son campos editables. PATCH requiere al menos un campo.

Ejemplo en Bash, con Python para extraer JSON y una contraseña del seed:

```bash
BASE=http://127.0.0.1:8000
umask 077
COOKIE_JAR=$(mktemp)
CSRF=$(curl --fail -sS -c "$COOKIE_JAR" "$BASE/auth/csrf" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["csrf_token"])')
read -r -s -p 'Contraseña de alice: ' APP_PASSWORD; echo
export APP_PASSWORD
python3 -c 'import json,os; print(json.dumps({"username":"alice","password":os.environ["APP_PASSWORD"]}))' |
  curl --fail-with-body -sS -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H 'Content-Type: application/json' -H "X-CSRFToken: $CSRF" \
    --data-binary @- "$BASE/auth/login"
unset APP_PASSWORD

# El login renueva la sesión: obtener un token nuevo.
CSRF=$(curl --fail -sS -b "$COOKIE_JAR" -c "$COOKIE_JAR" "$BASE/auth/csrf" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["csrf_token"])')
DOCUMENT_ID=$(curl --fail -sS -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' -H "X-CSRFToken: $CSRF" \
  -d '{"title":"Notas privadas","content":"Datos ficticios de portfolio"}' "$BASE/documents" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["document"]["id"])')
curl --fail -sS -b "$COOKIE_JAR" "$BASE/documents/$DOCUMENT_ID"
curl --fail -sS -b "$COOKIE_JAR" "$BASE/documents"
curl --fail -sS -b "$COOKIE_JAR" -X PATCH \
  -H 'Content-Type: application/json' -H "X-CSRFToken: $CSRF" \
  -d '{"content":"Contenido revisado"}' "$BASE/documents/$DOCUMENT_ID"
curl --fail -sS -b "$COOKIE_JAR" -X DELETE -H "X-CSRFToken: $CSRF" \
  "$BASE/documents/$DOCUMENT_ID"
curl --fail -sS -b "$COOKIE_JAR" -X POST -H "X-CSRFToken: $CSRF" "$BASE/auth/logout"
rm -f "$COOKIE_JAR"
```

Errores: `{"error":{"code":"...","message":"..."}}`. 401 sin sesión o con
credenciales incorrectas; 403 sin rol administrador; 404 para documentos ajenos
e inexistentes en rutas normales; 400 para validación/CSRF; 413 para tamaño; 415
para Content-Type incorrecto. CSRF se comprueba antes de autorización: una mutación
anónima sin token devuelve 400, y con token válido devuelve 401. Ninguna devuelve
el documento o modifica datos. `/health` tiene su respuesta mínima independiente.

## Decisiones de seguridad y dependencias

| Componente | Motivo |
|---|---|
| Flask / Werkzeug / Click | API pequeña, hash scrypt y CLI con entrada oculta de contraseña. |
| SQLAlchemy / Psycopg 3 | Consultas parametrizadas y PostgreSQL real en desarrollo y tests. |
| Alembic | Esquema versionado y reproducible, separado del arranque del servidor. |
| Flask-Login | Identidad de sesión, carga del usuario y protección de rutas mantenidas por una biblioteca. |
| Flask-WTF | CSRF con token firmado ligado a la sesión, también en login/logout. |
| Gunicorn | Servidor WSGI, dos workers; sin debug ni servidor de desarrollo público. |
| pytest / Ruff | Pruebas de comportamiento y revisión mecánica; solo en desarrollo/tests. |
| uv | Resolver e instalar versiones y hashes desde `uv.lock`; no forma parte del runtime. |

`pyproject.toml` expresa familias compatibles y `uv.lock` fija versiones
directas/transitivas y hashes. Docker y CI instalan con `--frozen`. Python
3.12 sobre Debian 13 y PostgreSQL 17.11 están fijados por digest multi-arquitectura. Actualizar
el lock/digests será una decisión revisada; fijarlos no implica ausencia de CVE.

Las contraseñas usan scrypt `N=32768, r=8, p=3`, una configuración recogida por
[OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Cada hash lleva sal aleatoria. El login da el mismo error para usuario inexistente
y contraseña incorrecta y realiza una comprobación de hash también para usuarios
inexistentes; esto reduce diferencias, sin prometer tiempo constante extremo a extremo.

La [sesión de Flask](https://flask.palletsprojects.com/en/stable/web-security/)
está firmada, **no cifrada**. No contiene contraseñas, roles ni documentos.
Cookie `HttpOnly`, `SameSite=Lax`, sin `Domain`, `Path=/` y duración de 30 minutos;
no se renueva con cada petición ordinaria. `Secure` es obligatorio en producción
y está desactivado únicamente para desarrollo HTTP local. No se usa remember-me.
El login borra el estado anterior y requiere obtener un token CSRF nuevo.

[Flask-WTF](https://flask-wtf.readthedocs.io/en/latest/csrf/) valida
`X-CSRFToken` en POST/PATCH/DELETE (también PUT si se añadiera). En HTTPS mantiene
además su comprobación de `Referer`: clientes como curl deben enviar
`-H "Referer: https://HOST/"`. No se habilita CORS. El modo production requiere
TLS terminado por infraestructura externa y hosts explícitos; este Compose es
para desarrollo, no proporciona certificados ni un despliegue productivo.

La cookie robada puede reutilizarse hasta caducar aunque su propietario haga
logout: no hay almacén servidor de revocación. Tampoco hay rate limiting,
MFA, auditoría duradera, límites de almacenamiento por usuario ni cifrado en
reposo. El rol de conexión no es superusuario pero es dueño de las tablas y se
comparte con migraciones; separar permisos DDL/DML es trabajo futuro. Estas
limitaciones están reflejadas en [STRIDE](docs/THREAT_MODEL.md), no se presentan
como controles implementados.

## Pipeline y explicación en entrevista

[Tests](.github/workflows/tests.yml) se ejecuta ante push, pull request o ejecución
manual. Usa una acción fijada por SHA, permisos `contents: read`, sin credenciales
persistidas de checkout, PostgreSQL temporal y el mismo comando Compose local.
El job falla si fallan lint, tests o infraestructura. Crear el archivo no acredita
una ejecución remota: consultar la pestaña Actions tras publicar en GitHub.

El workflow Security aplica los umbrales de bloqueo y publica informes como
artefactos. ZAP verifica acceso autenticado a rutas privadas. Las demostraciones
vulnerables se ejecutan aparte mediante `python3 demos/idor.py` y el análisis
estático de `demos/unsafe.py`; están excluidas de la imagen de aplicación.

Para explicar el caso IDOR/BOLA: un UUID conocido no otorga permiso; la consulta
combina identificador y propietario. El test
`test_cross_user_isolation_read_write_delete_and_list` intenta leer, modificar,
borrar y listar documentos de otra persona y comprueba que permanecen intactos.
El modelo enlaza amenazas con controles y pruebas; las demostraciones vulnerables
aisladas permiten enseñar el antes/después sin debilitar la aplicación.

Antes de revisar cambios, usar la [checklist](docs/CODE_REVIEW_CHECKLIST.md).
