# Verificación de análisis y políticas

Fecha: 2026-11-13.

## Evidencia remota

[Security, ejecución 43452105398](https://github.com/mariaig01/application-security-pipeline/actions/runs/43452105398):
Semgrep y ZAP correctos; Trivy bloqueó el primer conjunto de hallazgos de Debian 13.
Los tres informes se publicaron como artefactos. El parche posterior de zlib
reduce otros dos hallazgos y se verifica en la ejecución del commit siguiente.

[Tests, ejecución 43452105303](https://github.com/mariaig01/application-security-pipeline/actions/runs/43452105303):
correcta con PostgreSQL temporal. La versión Alpine posterior también pasa
localmente los 86 tests, las cuatro pruebas de política y Ruff.

## Resultados locales

- Ruff: checks y formato correctos.
- Tests funcionales: 86 pasados tanto en Debian como en la imagen Alpine final.
- Políticas: cuatro tests que cubren umbrales por escáner, informes inválidos,
  autenticación incompleta, alcance de excepciones, metadatos y caducidad.
- Demo BOLA: la misma comprobación detecta el fallo en la consulta vulnerable y
  pasa tras el control de propietario. No se modifica la API real.
- Semgrep: cero hallazgos en el código normal con seis reglas locales; detecta
  un hallazgo ERROR en `demos/unsafe.py` y comprueba que la política lo bloquea.
- Trivy: el primer análisis de Debian 12 bloqueó 110 hallazgos High/Critical;
  tras actualizar la base a Debian 13, bloqueó 49. La actualización fijada de
  zlib corrigió otros dos y quedaron 47. Esta es la evidencia histórica que motivó
  la remediación descrita a continuación, no el resultado de la imagen actual.
- ZAP: 401 anónimo y 200 autenticado en identidad y documento; análisis activo
  completo, cola pasiva vacía y 34 respuestas 200 de documentos asociadas a IDs
  de mensajes del análisis activo. Cero High, un Medium (HTTP Only Site) y 39
  Informational en esa ejecución local. Los recuentos pueden variar por ejecución.

## Remediación de los bloqueos de la imagen

Los 47 hallazgos de Debian correspondían a 11 CVE únicos, repetidos en varios
paquetes. La base Alpine fijada por digest evita componentes innecesarios como
Perl, systemd y las herramientas util-linux. Su ncurses es 6.6 y libuuid 2.42.3.
El primer escaneo de Alpine aún detectó Kerberos sin actualizar: se instaló
`krb5-libs=1.22.3-r0`, versión corregida indicada por Trivy.

SQLite 3.53.4 seguía instalado aunque el informe de Alpine no mostrase los avisos
de SQLite vistos en Debian. Por ello se retiraron tanto `sqlite-libs` como
`_sqlite3`, en lugar de interpretar la diferencia de avisos entre distribuciones
como una corrección. La API solo admite PostgreSQL. Se conserva el inventario APK
y el resto de dependencias nativas del intérprete mediante `.app-rundeps`.

Resultado local final: 37 paquetes del SO analizados, cero High/Critical,
ocho Medium y un Low; se analizan también las dependencias Python. No hay
excepciones, exclusiones de CVE ni cambios en el umbral de bloqueo.
`_sqlite3` no está disponible; Psycopg 3.3.6 y scrypt funcionan y los 86 tests
contra PostgreSQL pasan. Los resultados son del 2026-11-13 y pueden cambiar con
la base de avisos de Trivy. No se ha probado la imagen en ARM64.

## Riesgos residuales

Revisar los avisos Medium/Low y mantener seguimiento de actualizaciones de Alpine.
No interpretar el cumplimiento de los umbrales como ausencia de vulnerabilidades.

ZAP observa HTTP local y señala la falta de HTTPS: la terminación TLS permanece
fuera del entorno temporal. La prueba no sustituye la revisión manual ni amplía
su cobertura al rol administrador. Ver alcance en SECURITY_PIPELINE.md.
