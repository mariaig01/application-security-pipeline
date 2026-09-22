# Checklist de revisión de código

Aplicar a cada PR. Marcar N/A con explicación cuando no corresponda; los checks
automáticos complementan esta revisión. No es una declaración de certificación.

## Autenticación y autorización

- [ ] Las rutas privadas exigen sesión; respuestas API usan 401, sin redirección HTML.
- [ ] Lectura, listado, modificación y borrado filtran por propietario desde servidor.
- [ ] Un test con otra identidad intenta cada operación y comprueba ausencia de efectos.
- [ ] El administrador solo tiene lectura/borrado globales por rutas explícitas.
- [ ] No se aceptan `role`, `owner_id`, hashes ni atributos arbitrarios del cliente.
- [ ] Las decisiones de rol consultan DB y no valores confiados a la cookie.
- [ ] Se utiliza la biblioteca de hashing; no aparecen contraseñas constantes fuera de tests.

## Sesión, CSRF y entradas

- [ ] Mutaciones, login y logout requieren CSRF, también en tests.
- [ ] Después del login se borra la sesión anterior y se obtiene un token nuevo.
- [ ] Cookies conservan HttpOnly, SameSite y Secure fuera del HTTP local documentado.
- [ ] Cambios de sesión documentan caducidad y limitaciones de revocación/replay.
- [ ] JSON, campos permitidos, tipos, longitudes y tamaño HTTP se validan explícitamente.
- [ ] Consultas usan parámetros; identificadores SQL dinámicos tienen origen controlado.
- [ ] Texto privado se devuelve como JSON; un futuro frontend no lo interpreta como HTML.
- [ ] Los errores y logs no contienen cuerpos, hashes, tokens, credenciales ni SQL sensible.

## Datos, infraestructura y dependencias

- [ ] La migración desde una base vacía funciona y coincide con los modelos.
- [ ] Los tests usan PostgreSQL aislado y no alteran datos de desarrollo.
- [ ] El seed sigue limitado a desarrollo y no cambia permisos/contraseñas existentes.
- [ ] Secrets, cookies y salida del seed quedan fuera de Git y del contexto Docker.
- [ ] La imagen conserva usuario sin privilegios y carece de dependencias de tests.
- [ ] La conexión DB no es superusuario y los puertos publicados están justificados.
- [ ] Cambios de lock/digests se revisan y se ejecutan checks congelados.
- [ ] Cada nueva dependencia tiene un motivo que no cubre ya la biblioteca estándar.

## Pipeline y evidencia

- [ ] El job falla si falla lint, pytest o la infraestructura de tests.
- [ ] El workflow no expone secretos a código de PR no confiable ni usa `pull_request_target`.
- [ ] Resultados documentados corresponden a comandos ejecutados; no se inventan métricas.
- [ ] Se actualizan amenazas, decisiones y riesgos pendientes cuando cambia el comportamiento.
- [ ] Hitos 2/3: ZAP demuestra autenticación y cobertura; excepciones tienen motivo y fecha.
- [ ] Hito 3: los checks requeridos se configuran en GitHub y las demos quedan aisladas.
