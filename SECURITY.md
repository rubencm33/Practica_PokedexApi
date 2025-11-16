# Consideraciones de Seguridad

## Autenticación
La API utiliza autenticación basada en **JSON Web Tokens (JWT)** para asegurar los endpoints privados.  
Los usuarios deben autenticarse mediante `/api/v1/auth/login` para obtener un token válido que se incluye en cada petición como:

``Authorization: Bearer <token>``

### Implementación JWT
- Algoritmo usado: **HS256**
- El token incluye:
  - `sub` (ID del usuario)
  - `exp` (fecha de expiración)
  - `iat` (fecha de emisión)
- La clave secreta (`SECRET_KEY`) se almacena en `.env`.

### Expiración del token
- Los tokens expiran en **60 minutos**
- Esta política reduce el tiempo en el que un token robado puede ser usado por un atacante
- Se puede renovar obteniendo un nuevo token mediante login

---

## Contraseñas
### Hashing de contraseñas
Las contraseñas **no se almacenan en texto plano**.  
Se utiliza un algoritmo de hashing seguro mediante `passlib`.

- Algoritmo usado: **bcrypt**
- Resistente a ataques por fuerza bruta y rainbow tables
- Las contraseñas se verifican mediante el hash, nunca desencriptándolas

### Política de contraseñas
- Deben tener una longitud mínima de 6 caracteres
- No se permiten contraseñas vacías
- Se recomienda incluir letras, números y caracteres especiales

---

## Rate Limiting
Se utiliza un sistema de rate limiting personalizado para evitar abusos de la API.

### Límites por endpoint
| Endpoint | Límite | Intervalo |
|---------|--------|-----------|
| `/pokemon/search` | 100 req | 60 s |
| `/pokemon/{id}` | 100 req | 60 s |
| `/pokemon/{id}/card` | 100 req | 60 s |
| `/pokedex/export` | 100 req | 60 s |

### Justificación
- Evita ataques DoS
- Limita scrapers automáticos
- Protege la PokeAPI de peticiones excesivas
- Garantiza un uso justo entre usuarios

---

## CORS
### Orígenes permitidos
Actualmente solo se permite:
- `http://localhost:8000`

### Justificación
CORS se activa para evitar que páginas externas puedan hacer peticiones a la API sin autorización.  
Restringir los orígenes ayuda a bloquear ataques como:
- Cross-Site Request Forgery (CSRF)
- Cross-Site Script Inclusion (XSSI)

---

## Variables de Entorno
La configuración sensible se almacena en `.env`:

- `SECRET_KEY`
- `DATABASE_URL`
- `POKEAPI_URL`
- `LOG_LEVEL`

### Cómo protegerlas
- No subir `.env` al repositorio
- Generar un `SECRET_KEY` complejo
- Usar valores distintos en desarrollo y producción
- Restringir permisos del archivo en el servidor

---

## Vulnerabilidades Conocidas

### OWASP Top 10 Consideradas

#### 1. **Broken Authentication**
- Uso de JWT correctamente implementado
- Expiración corta
- Hashing seguro con bcrypt

#### 2. **Sensitive Data Exposure**
- No se almacenan contraseñas en texto plano
- Variables sensibles aisladas en `.env`

#### 3. **Rate Limiting**
- Previene DoS y ataques de fuerza bruta

#### 4. **Injection Attacks**
- Uso de ORM SQLModel evita SQL injection
- Validación por pydantic en los endpoints

#### 5. **Broken Access Control**
- Endpoints protegidos con `get_current_user()`
- Recursos aislados por `owner_id`

#### 6. **Security Misconfiguration**
- CORS restringido
- Manejo de errores centralizado

### Mitigaciones implementadas
- Autenticación segura
- Control de acceso basado en usuario
- Hashing robusto
- Rate limit por usuario
- CORS seguro
- Logging estructurado para auditoría

---

  