# Plan de desarrollo — Coordinador de juntas de juegos de mesa

Caso práctico Product Engineer — Wherex
Tiempo disponible: 36 horas (prototipo + presentación)

---

## 1. Decisión de interfaz

En vez de un bot de Telegram real, la interfaz del prototipo será **la API con su documentación interactiva (Swagger UI / FastAPI `/docs`)**. Motivos:

- Cero esfuerzo de frontend o de manejo de estados conversacionales de un bot.
- Los entrevistadores pueden interactuar en vivo: crear un evento, votar, ver resultados — clic a clic, sin necesidad de credenciales de Telegram.
- El bot de Telegram queda documentado como **el siguiente paso natural** en la sección de evolución del producto — refuerza tu argumento de "elegí el canal más simple de validar, no el canal final".
- Si al final sobra tiempo, se puede envolver el flujo de "crear evento → proponer fechas" en 2-3 endpoints con nombres conversacionales, para que la demo se sienta más cercana a un bot aunque técnicamente sea REST.

**Resolución de identidad (importante, simplificación intencional):** el prototipo no incluye autenticación. Cada endpoint recibe `persona_id` como parámetro explícito — quien prueba la API "actúa como" esa persona. Con Telegram, esto se vuelve implícito: el webhook trae `telegram_user_id` y el sistema resuelve la persona por `lookup` contra `personas.telegram_user_id`, sin que nadie tenga que elegir quién es. Vale la pena decir esto explícito en la presentación en vez de ocultarlo — es una simplificación consciente, no un descuido.

---

## 2. Estructura del repositorio (monorepo)

```
juntas-juegos/
├── docker-compose.yml
├── .env.example
├── README.md
├── migrations/
│   ├── README.md
│   ├── 001_create_personas.sql
│   ├── 002_create_grupos.sql
│   ├── 003_create_miembros_grupo.sql
│   ├── 004_create_juegos.sql
│   ├── 005_create_biblioteca_juegos.sql
│   ├── 006_create_eventos.sql
│   ├── 007_create_fechas_propuestas.sql
│   ├── 008_create_votos_disponibilidad.sql
│   ├── 009_create_asistencias.sql
│   ├── 010_create_juegos_jugados.sql
│   ├── 011_create_valoraciones.sql
│   └── 012_indexes_and_constraints.sql
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   ├── config.py          # env vars, Supabase connection string
    │   │   └── database.py        # SQLAlchemy engine/session
    │   ├── domain/
    │   │   └── models.py          # Pydantic schemas (request/response)
    │   ├── repositories/
    │   │   ├── person_repository.py
    │   │   ├── group_repository.py
    │   │   ├── event_repository.py
    │   │   ├── vote_repository.py
    │   │   ├── attendance_repository.py
    │   │   └── rating_repository.py
    │   ├── services/
    │   │   ├── host_rotation_service.py
    │   │   ├── event_service.py
    │   │   ├── voting_service.py
    │   │   ├── attendance_service.py
    │   │   └── recommender_service.py   # fase final, opcional
    │   ├── api/
    │   │   ├── events.py
    │   │   ├── votes.py
    │   │   ├── attendance.py
    │   │   └── ratings.py
    │   └── scheduler/
    │       └── jobs.py            # stub de recordatorios (log, no envío real)
    ├── seed/
    │   └── seed_data.py
    └── tests/
        ├── unit/
        │   ├── test_host_rotation_service.py
        │   └── test_voting_service.py
        └── integration/
            └── test_events_api.py
```

**Justificación de las capas** (conecta directo con la sección "Arquitectura simple" del caso):

- `repositories/` — único punto de contacto con la base de datos. Si más adelante cambia el motor o se agrega cache, no se toca `services/`.
- `services/` — toda la lógica de decisión (rotación, tally de votos, futura recomendación). Es la capa que más "producto" demuestra.
- `api/` — adaptador delgado; solo traduce HTTP a llamadas de servicio. Si mañana se reemplaza por un bot de Telegram, esta es la única capa que cambia.
- `scheduler/` — aislado a propósito para que un cron real (Cloud Scheduler) pueda reemplazar el stub sin tocar nada más.

---

## 3. Grupos y multi-tenancy

El diseño inicial no tenía el concepto de "grupo" — `personas` y `eventos` se conectaban directo, asumiendo un único grupo global. Se corrige antes de escribir código:

- **`grupos`** — cada grupo de coordinación es su propia entidad (nombre, fecha de creación).
- **`miembros_grupo`** — relación persona ↔ grupo. Aquí vive todo lo que es *específico de esa membresía*: si la persona está `activo` en ese grupo, y **`ultima_vez_host`** (se mueve desde `personas`, porque el turno de host de alguien en un grupo no debe afectar su rol en otro).
- **`eventos.grupo_id`** — todo evento pertenece a un grupo; la rotación de host y el padrón de votantes quedan acotados por ese `grupo_id`.

Esto permite el escenario de demo en vivo: un grupo semilla con historial (rotación ya avanzada) y un grupo nuevo creado en el momento con los entrevistadores como miembros, corriendo el flujo completo desde cero.

---

## 4. Migraciones (Supabase cloud)

Carpeta `migrations/` con SQL plano, numerado y ejecutado una sola vez a mano (pegado en el SQL Editor de Supabase o vía `psql` contra la connection string). No se usa una herramienta de migraciones versionada (Alembic, etc.) — no aporta para un prototipo de esta escala.

Cada archivo declara una tabla con sus claves foráneas, restricciones (`NOT NULL`, `CHECK` de rangos, `UNIQUE` donde corresponda) e índices sobre las columnas que se consultan seguido (`persona_id`, `grupo_id`, `evento_id`, `estado`). El archivo `012_indexes_and_constraints.sql` agrupa los índices que cruzan varias tablas (por ejemplo, el índice compuesto para el tally de votos por fecha).

`migrations/README.md` incluye el orden de ejecución y el comando `psql` de referencia.

---

## 4. Plan incremental por fases

Cada fase es un punto de parada válido — si el tiempo se acaba, lo construido hasta ahí ya es demostrable. Las horas son estimadas y acumulativas.

| Fase | Contenido | Horas | Acumulado | Qué puedes mostrar si paras aquí |
| --- | --- | --- | --- | --- |
| **0. Setup** | Repo, `docker-compose.yml`, `.env`, migraciones aplicadas en Supabase, esqueleto FastAPI respondiendo `/health` | 3h | 3h | El proyecto levanta con un comando y conecta a la base de datos real |
| **1. Dominio + seed** | Modelos Pydantic, repositorios base (incluye `grupos`/`miembros_grupo`), script de datos de prueba con un grupo semilla ya con historial | 3.5h | 6.5h | Puedes consultar personas, grupos y juegos vía API; puedes crear un grupo nuevo y agregar miembros en vivo |
| **2. Rotación de host** | `host_rotation_service`: elige próximo host por `ultima_vez_host` acotado a `grupo_id`; endpoint que crea evento y lo asigna | 3h | 9.5h | Demuestra la primera decisión real del sistema, ya funcionando de forma independiente por grupo — con test unitario |
| **3. Propuesta y votación de fechas** | Host propone fechas (`fechas_propuestas`), invitados votan (`votos_disponibilidad`), endpoint de tally | 4h | 13h | Flujo completo de coordinación de fecha, el corazón del problema original |
| **4. Confirmación de fecha + asistencia** | Host confirma fecha, se crea registro de `asistencias`; endpoint de resumen del evento | 3h | 16h | El ciclo completo de organización (pasos 1 a 4 del flujo original) queda demostrable |
| **5. Subtasks: recordatorio + valoración** | Job stub de recordatorio (log un día antes), endpoint para registrar juegos jugados y valoraciones post-sesión | 4h | 20h | Cierra el ciclo completo, incluyendo el paso que mencionaste como el de mayor fricción de adopción |
| **6. Tests de integración + limpieza** | Tests de endpoints principales, revisión de nombres/estructura, README de uso | 3h | 23h | Proyecto con cobertura básica y presentable como "código serio", no solo script |
| **7. Recomendador de juegos (opcional)** | Heurística simple de scoring (gustos + valoraciones + disponibilidad de biblioteca) | 5h | 28h | **Se descarta primero si el tiempo aprieta** — es la única fase no crítica |
| **8. Presentación** | Slides, diagrama de arquitectura, guion de demo, ensayo | 8h | 36h | — |

Si el tiempo se ajusta más de lo esperado, el orden de recorte es: primero fase 7 (recomendador), luego reducir fase 6 (menos tests), nunca las fases 0-5 — son las que sostienen el argumento de "sistema que toma decisiones", que es lo que evalúan.

---

## 5. Testing

Enfoque pragmático, no cobertura exhaustiva:

- **Unitarios** sobre la lógica de servicio pura (sin base de datos): rotación de host dado un set de personas con distintos `ultima_vez_host`; tally de votos dado un set de respuestas. Estos son rápidos de escribir y son justamente la lógica que quieres mostrar que funciona.
- **Integración** sobre 2-3 endpoints críticos (crear evento, votar, confirmar fecha) contra una base de datos real de prueba — puede ser el mismo proyecto Supabase con datos de seed, o un schema aparte si prefieres aislar.
- No se testea `scheduler/` (es un stub) ni `api/` línea por línea — el valor está en los `services/`.

---

## 6. Datos de prueba

`seed/seed_data.py` inserta:

- 5-6 personas ficticias con distintos `ultima_vez_host` (para que la rotación se note)
- 8-10 juegos con rangos de jugadores variados
- 1-2 registros de `biblioteca_juegos` por persona
- 1 evento de ejemplo ya en estado "votando" con algunas fechas propuestas y votos, para que la demo no arranque en blanco

Tú luego reemplazas nombres y juegos por los reales de tu grupo antes de la presentación.

---

## 7. Docker

Como Supabase es cloud, `docker-compose.yml` solo necesita levantar el backend (no hay contenedor de base de datos). Un único servicio, variables de entorno con la connection string de Supabase vía `.env`, y `docker compose up` deja todo arriba y corriendo contra la base real.

---

## 8. Escenario sugerido para la demo en vivo

1. **Grupo A (seed, con historial):** "Junta de juegos" con 5-6 personas ficticias, con `ultima_vez_host` ya distribuido en `miembros_grupo` — la rotación se ve funcionando desde el primer clic, no parte en blanco.
2. **Grupo B (creado en vivo):** durante la reunión, se crea un grupo nuevo, se agregan los entrevistadores como `personas` + `miembros_grupo`, y se corre el flujo completo desde cero (crear evento → proponer fechas → votar → confirmar) delante de ellos.

Esto demuestra en vivo que el sistema no está hardcodeado a un solo grupo — es la prueba de robustez más simple y más convincente que se puede mostrar en 45 minutos.

---

## Roadmap futuro: grupos de actividad puntual

Fuera del alcance de este prototipo, documentado como evolución post-validación.

De un grupo más grande (ej. amigos en general), alguien puede querer coordinar una actividad puntual — un partido de tenis, fútbol, subir un cerro — sin la recurrencia ni la rotación de host del modelo actual. La mecánica es distinta:

- **Sin rotación de host** — cualquier miembro puede abrir una invitación con un rango de fechas.
- **Votación de disponibilidad/interés** del resto del grupo (o un subgrupo), igual que en el modelo recurrente.
- **Cierre por decisión de quien invita**, no por tally automático — el creador elige con quién se queda y cierra la invitación manualmente, a diferencia del evento recurrente que se cierra cuando el host elige la fecha con más votos.

Esto probablemente implica generalizar `eventos` en dos modos, o introducir una entidad `invitaciones` separada que reutilice `grupos`/`miembros_grupo` pero con su propia máquina de estados. Se deja señalado como tensión de diseño a resolver en la iteración siguiente — no se fuerza en el modelo actual.

Con esto, el sistema queda pensado para dos tipos de grupo: **grupos de coordinación recurrente organizada** (el prototipo actual) y **grupos de actividad puntual no periódica** (roadmap futuro).

---

## Siguiente paso

Con este plan puedo armar el prompt inicial para Claude Code (fase 0 y 1 primero), o si prefieres, lo revisamos juntos fase por fase a medida que avanzas. ¿Cómo prefieres proceder?
