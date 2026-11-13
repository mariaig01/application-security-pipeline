# Pipeline de seguridad

Los jobs `Security (semgrep)`, `Security (trivy)` y `Security (zap)` corren ante
push, pull request y ejecución manual. Sus imágenes están fijadas por versión y
digest en `security/images.json`. Las acciones también están fijadas por SHA.

## Reproducir los análisis

Desde la raíz, con Docker, Compose y Python 3.12:

```bash
python3 -m unittest discover -s security/tests -v
python3 demos/idor.py
python3 security/scan.py semgrep
python3 security/scan.py trivy
python3 security/scan.py zap
```

Cada comando devuelve salida distinta de cero si falla el escáner, falta el
informe, hay problemas de autenticación/cobertura o se incumple la política.
No se usan `continue-on-error`, `--ignore-unfixed` ni listas de exclusiones CVE
globales. Se conservan también los hallazgos Medium y Low para su revisión.

Los informes JSON se guardan en `reports/` (ignorado por Git). En Actions se
publican durante 14 días como artefactos, incluso cuando bloquean. La base de
vulnerabilidades de Trivy cambia: fijar la herramienta no congela los avisos CVE.
La imagen tar temporal se elimina y no se publica como artefacto.

## Cobertura y límites

Semgrep aplica seis reglas locales revisables sobre la aplicación, migraciones,
scripts y herramientas de seguridad: evaluación dinámica, pickle, shell,
debug, desactivación de CSRF y SQL formateado. Es una selección educativa acotada,
no el catálogo completo de reglas de Semgrep. La fixture `demos/unsafe.py` se
analiza aparte: el pipeline exige que el escáner detecte y bloquee su `eval`.

Trivy examina paquetes del sistema operativo y Python en la imagen runtime que
se construye desde el Dockerfile. Un High/Critical sin parche también bloquea.
Se actualizó la base de Debian 12 a Debian 13 tras observar vulnerabilidades;
los hallazgos residuales se mantienen visibles para priorizar remediación.

ZAP arranca un entorno exclusivo `appsec-security`, con DB en tmpfs y una clave
de sesión aleatoria. Genera un usuario, obtiene CSRF, inicia sesión y crea un
documento ficticio a través del proxy. Registra 401 anónimo y 200 autenticado en
identidad y documento. Reutiliza cookie y CSRF mediante reglas del proxy limitadas
a `http://app:8000/`; excluye login/logout del ataque para conservar la sesión.
Realiza análisis activo de los mensajes descubiertos y espera al análisis pasivo.
Comprueba de nuevo la identidad antes de exportar. La evidencia exportada cuenta
respuestas 200 de documentos; no publica cookies, contraseña ni historial HTTP.

El informe no acredita todos los roles y operaciones de la API: autorización y
CRUD completos se verifican con pytest. El usuario ZAP es normal, no administrador.
El ataque tiene un presupuesto de cinco minutos y el controlador un deadline de
ocho; el análisis no pretende ser una evaluación manual exhaustiva. Solo se
publica el puerto del proxy en loopback (18082), nunca la aplicación ni la DB.
La API de ZAP sin clave se limita a este entorno local temporal. El bloque finally
retira contenedores/red incluso ante errores; si el proceso se termina con SIGKILL,
usar `SCAN_SECRET_KEY=cleanup docker compose -f compose.security.yaml down --volumes`.

## Políticas y excepciones

| Control | Condición de bloqueo |
|---|---|
| Tests | Fallo de Ruff, pytest o infraestructura PostgreSQL |
| Semgrep | ERROR/HIGH/CRITICAL, error de análisis o ningún archivo analizado |
| Trivy | HIGH/CRITICAL del SO o dependencias Python, tenga o no parche |
| ZAP | Riesgo High, o evidencia de autenticación/cobertura incompleta |
| Informes | Archivo ausente, JSON inválido o estructura incompleta |
| Excepciones | Metadatos inválidos o fecha de revisión vencida |

`security/exceptions.json` empieza vacío. Una excepción debe incluir exactamente
`scanner`, `finding`, `target`, `reason`, `owner` y `review_date` (YYYY-MM-DD).
Se limita al identificador y destino exactos del informe. No admite comodines.
La fecha se evalúa con la fecha del runner; una excepción vencida falla incluso
si el hallazgo desapareció: eliminarla o revisarla expresamente en un PR.

Para Trivy, `target` es `Target:PkgName`; para Semgrep es la ruta y para ZAP la URL.
No aprobar excepciones solo para obtener un check verde. Registrar alcance,
explotabilidad y controles compensatorios en el motivo y enlazar el seguimiento.
Los tests de política usan informes sintéticos etiquetados como tales para
demostrar cada bloqueo; no se presentan como hallazgos reales de los escáneres.

## Protección de main

Checks requeridos: `PostgreSQL tests`, `Security (semgrep)`, `Security (trivy)` y
`Security (zap)`. Configurar en Settings → Branches → protección de `main`:
PR obligatorio, rama actualizada, aplicar también a administradores, impedir
force push y borrado. Un portfolio con un único mantenedor puede usar cero
aprobaciones externas manteniendo el PR y los checks obligatorios.

Las políticas viven en Git y la protección vive en GitHub: un YAML no hace
obligatorio su propio check. Verificar la configuración con:

```bash
gh api repos/mariaig01/application-security-pipeline/branches/main/protection
```

## Demostración para entrevista

`python3 demos/idor.py` muestra que conocer el ID permite a Bob leer texto de Alice
cuando falta el control de propietario; la misma comprobación rechaza el acceso
tras añadirlo. La demo no importa la aplicación ni abre puertos o bases de datos.
La regresión real de la API está en el test de aislamiento entre usuarios.

El ejemplo estático `demos/unsafe.py` no se ejecuta ni entra en la imagen Docker.
Semgrep lo analiza separadamente y la política debe bloquearlo. Los tests de
política muestran High/Critical, informes defectuosos y excepciones caducadas.
No existe un interruptor para debilitar la API normal.

Fuentes de integración: [ZAP API](https://www.zaproxy.org/docs/api/),
[Semgrep CLI](https://semgrep.dev/docs/cli-reference),
[Trivy vulnerability scanning](https://trivy.dev/docs/dev/guide/scanner/vulnerability/).
