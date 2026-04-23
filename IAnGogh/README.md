# IAnGogh (Python MVP)

Sistema maestro local para empleabilidad con integración estable hacia UiPath (Elchapi/Joao).

## Stack
- Python 3.11+
- FastAPI (API local localhost)
- MongoDB (persistencia local)
- Cifrado por campo con Fernet (clave por entorno)

## Ejecutar
1. Configura `.env` (puedes copiar de `.env.example`).
2. Inicia MongoDB local.
3. Instala dependencias: `pip install -e .`
4. Levanta API: `python -m app_integration_localapi.main`
5. Abre: `http://127.0.0.1:8787/`

## Estructura
- `src/app_domain`: modelos de dominio/DTOs
- `src/app_core`: servicios de negocio (perfiles, documentos, backup, contratos)
- `src/app_infrastructure`: acceso Mongo, seguridad, filesystem
- `src/app_integration_localapi`: endpoints localhost para app <-> UiPath
- `contracts`: contratos JSON de intercambio
- `docs`: arquitectura, roadmap y decisiones técnicas
