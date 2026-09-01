# Bloque C — Bot de Telegram (implementación)

Brief listo para pasar a Claude Code contra el repo ya existente. Reutiliza `services/` y `repositories/` tal cual están — el bot es solo un adaptador nuevo, ninguna lógica de negocio se duplica ni se mueve.

---

## Decisiones de diseño antes de codear

**Long polling, no webhook.** El bot corre como proceso propio (`bot/main.py`), sin URL pública ni túnel. Se agrega como segundo servicio en `docker-compose.yml`, mismo Dockerfile/imagen del backend, comando distinto, sin puerto expuesto.

**Identidad vía deep-link con token, no preguntando el nombre.** Cada persona recibe un enlace único `t.me/<bot_username>?start=<token>`. El bot resuelve la persona por el token y guarda su `telegram_user_id` — sin ambigüedad, sin tipeo, y reutiliza directamente el patrón de QR que ya habíamos pensado para la demo (cada invitado escanea su propio QR para vincularse).

**Votación de fechas → encuesta nativa de Telegram (`sendPoll`, `allows_multiple_answers=true`)**, una opción por fecha propuesta. Es el ajuste natural a `votos_disponibilidad`: cada persona marca todas las fechas en que puede. El bot recibe el evento `poll_answer` (funciona igual con polling, no requiere webhook) y llama a `voting_service` como ya lo hace el endpoint REST.

**El resto de las interacciones (pregunta de "¿tienes claro qué se juega?", valoración 1-5) → botones inline, sin máquina de estados persistida.** Todo el contexto necesario (`event_id`, `game_id`, paso de la conversación) viaja codificado en el `callback_data` del botón. Esto evita construir y mantener una tabla de estado conversacional bajo presión de tiempo, y es más robusto para una demo — no hay estado que se pueda perder o corromper entre reinicios.

**Los recordatorios pasan de log a envío real mediante un puerto de notificación (`NotificationPort`)**, para no acoplar `scheduler/jobs.py` a Telegram directamente — mañana podría ser WhatsApp y el scheduler no cambia.

---

## Estructura nueva

```
backend/
├── bot/
│   ├── main.py                    # entrypoint: Application.run_polling()
│   ├── handlers/
│   │   ├── onboarding.py          # /start <token>
│   │   ├── voting.py               # poll_answer handler
│   │   ├── game_check.py           # botones "lo tengo claro"/"dame sugerencias"/"recuérdame"
│   │   └── rating.py               # botones 1-5
│   └── callback_data.py            # encode/decode de callback_data (funciones puras, testeables)
└── app/
    └── services/
        └── notification_service.py # implementa NotificationPort usando el bot
```

`NotificationPort` (interfaz abstracta) vive en `app/services/ports.py`; `scheduler/jobs.py` depende de la interfaz, no de la implementación concreta — se inyecta la implementación de Telegram al arrancar `bot/main.py`.

---

## Pasos de implementación (orden sugerido, ~9h)

| # | Tarea | Detalle | Horas |
| --- | --- | --- | --- |
| 1 | Setup y esqueleto | Agregar `python-telegram-bot` a dependencias, `TELEGRAM_BOT_TOKEN` a `.env`, `bot/main.py` con `Application.run_polling()` respondiendo un `/start` genérico (sin lógica aún). Agregar servicio `bot` a `docker-compose.yml` | 1.5h |
| 2 | Onboarding por deep-link | Endpoint o función que genera el token por persona (puede ser el mismo `person_id` si no importa exponerlo en el demo, o un token aparte si prefieres no exponer UUIDs). Handler de `/start <token>` que resuelve la persona y llama `person_repository.set_telegram_user_id(...)`. Mensaje de confirmación | 1.5h |
| 3 | Notificación de recordatorio | `NotificationPort` + `TelegramNotificationService`. `scheduler/jobs.py` deja de loggear y llama al puerto. Mensaje con `text_mention` etiquetando a la persona | 1.5h |
| 4 | Votación de fechas | Al confirmar propuesta de fechas (mismo punto donde hoy se llama al endpoint REST), disparar `sendPoll` a cada miembro activo del grupo. Handler de `poll_answer` que llama `voting_service.register_vote(...)` | 2h |
| 5 | Pregunta de claridad del juego + sugerencias | Mensaje con botones inline ("Lo tengo claro" / "Dame sugerencias" / "Recuérdame más tarde"). La opción "Dame sugerencias" llama `recommender_service` y responde con el resultado. "Recuérdame más tarde" reprograma el mismo recordatorio (reutiliza el puerto de notificación) | 1.5h |
| 6 | Valoración post-juego | Mensaje con 5 botones (1 a 5) por `callback_data` con `event_id` + `game_id` codificados. El handler llama `rating_service.rate_game(...)` | 1h |

---

## Testing

Dado el enfoque pragmático ya usado en el resto del proyecto:

- **Unitarios sobre `callback_data.py`** (encode/decode) — son funciones puras, rápidas de testear, y es donde más fácil se cuela un bug silencioso (parsear mal un `callback_data` no truena, simplemente hace nada).
- **Unitarios sobre el handler de onboarding** (resolución de token → persona), con el bot mockeado.
- No se testea la integración real contra la API de Telegram — se verifica a mano en el bot real antes de la demo, como ya se hizo con Swagger vía curl/navegador.

---

## Qué NO se toca

- `services/` y `repositories/` existentes — el bot los llama, no los modifica.
- El esquema de base de datos — no se necesita ninguna tabla nueva (el token de onboarding puede vivir en `people` como columna, o derivarse del `person_id` si se decide no ocultarlo).
- Los endpoints REST — Swagger sigue funcionando exactamente igual, en paralelo.

---

## Siguiente paso

Empezamos por el paso 1 (setup y esqueleto) — ¿tienes ya el bot creado en @BotFather con su token, o lo creamos como parte de este primer paso?

## Extra

Ya cree el bot con fatherbot de telegram.

```txt
Done! Congratulations on your new bot. You will find it at t.me/where_do_x_bot. You can now add a description, about section and profile picture for your bot, see /help for a list of commands. By the way, when you've finished creating your cool bot, ping our Bot Support if you want a better username for it. Just make sure the bot is fully operational before you do this.

Use this token to access the HTTP API:
{num_values}:{alpha_num_values}
Keep your token secure and store it safely, it can be used by anyone to control your bot.

For a description of the Bot API, see this page: https://core.telegram.org/bots/api
```
