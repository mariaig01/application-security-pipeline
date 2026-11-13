# Verificación de análisis y políticas

Fecha: 2026-11-13.

## Evidencia remota

[Security, ejecución 43452105398](https://github.com/mariaig01/application-security-pipeline/actions/runs/43452105398):
Semgrep y ZAP correctos; Trivy bloqueó el primer conjunto de hallazgos de Debian 13.
Los tres informes se publicaron como artefactos. El parche posterior de zlib
reduce otros dos hallazgos y se verifica en la ejecución del commit siguiente.

[Tests, ejecución 43452105303](https://github.com/mariaig01/application-security-pipeline/actions/runs/43452105303):
correcta con PostgreSQL temporal. En local, la versión final con zlib actualizado
también pasa los 86 tests, las cuatro pruebas de política y Ruff.

## Resultados locales

- Ruff: checks y formato correctos.
- Tests funcionales: 86 pasados tras actualizar la imagen base a Debian 13.
- Políticas: cuatro tests que cubren umbrales por escáner, informes inválidos,
  autenticación incompleta, alcance de excepciones, metadatos y caducidad.
- Demo BOLA: la misma comprobación detecta el fallo en la consulta vulnerable y
  pasa tras el control de propietario. No se modifica la API real.
- Semgrep: cero hallazgos en el código normal con seis reglas locales; detecta
  un hallazgo ERROR en `demos/unsafe.py` y comprueba que la política lo bloquea.
- Trivy: el primer análisis de Debian 12 bloqueó 110 hallazgos High/Critical;
  tras actualizar la base a Debian 13, bloqueó 49. La actualización fijada de
  zlib corrige otros dos: el informe final bloquea 47, sin versión corregida
  indicada por Trivy en ese momento. Estos son avisos reales del
  escáner; no se ha hecho una validación manual de explotabilidad de cada uno.
  No hay excepciones aprobadas. El check debe continuar rojo mientras persistan.
- ZAP: 401 anónimo y 200 autenticado en identidad y documento; análisis activo
  completo, cola pasiva vacía y 34 respuestas 200 de documentos asociadas a IDs
  de mensajes del análisis activo. Cero High, un Medium (HTTP Only Site) y 39
  Informational en esa ejecución local. Los recuentos pueden variar por ejecución.

## Riesgos pendientes

Revisar y remediar los hallazgos residuales de la imagen; mantener seguimiento
de actualizaciones de Debian. No interpretar la
integración completa como un informe sin vulnerabilidades.

ZAP observa HTTP local y señala la falta de HTTPS: la terminación TLS permanece
fuera del entorno temporal. La prueba no sustituye la revisión manual ni amplía
su cobertura al rol administrador. Ver alcance en SECURITY_PIPELINE.md.
