# Verificación de análisis y políticas

Fecha: 2026-11-13.

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
  tras actualizar la base a Debian 13, bloquea 49. Estos son avisos reales del
  escáner; no se ha hecho una validación manual de explotabilidad de cada uno.
  No hay excepciones aprobadas. El check debe continuar rojo mientras persistan.
- ZAP: el primer recorrido obtuvo 401 anónimo y 200 autenticado en identidad y
  documento; completó análisis activo y pasivo. La verificación final y sus
  artefactos se consultan en GitHub Actions.

## Riesgos pendientes

Revisar y remediar los hallazgos de la imagen; dos avisos de zlib tienen versión
corregida y otros paquetes no la indicaban en ese análisis. No interpretar la
integración completa como un informe sin vulnerabilidades.

ZAP observa HTTP local y señala la falta de HTTPS: la terminación TLS permanece
fuera del entorno temporal. La prueba no sustituye la revisión manual ni amplía
su cobertura al rol administrador. Ver alcance en SECURITY_PIPELINE.md.

## Revisión editorial

Se revisaron los archivos versionados, comentarios y mensajes de commit para
eliminar referencias ajenas al proyecto y atribuciones de generación automática.
No se alteran hallazgos, métricas ni resultados reales de las comprobaciones.
