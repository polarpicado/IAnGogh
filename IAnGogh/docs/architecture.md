# Arquitectura MVP (Python)

## Objetivo
Construir el sistema maestro local independiente de UiPath, con contratos estables para integración.

## Capas
- `app_domain`: modelos y entidades.
- `app_core`: casos de uso y servicios.
- `app_infrastructure`: MongoDB, filesystem y seguridad.
- `app_integration_localapi`: API local para app/UiPath.
- `app_desktop/templates`: dashboard visual liviano para operación.

## Persistencia
MongoDB local con colecciones:
- profiles
- personal_info
- documents
- job_opportunities
- application_attempts
- manual_review_alerts
- settings

## Seguridad
- cifrado por campo para datos sensibles (dirección, documento, teléfonos);
- clave en variable de entorno (`APP_ENCRYPTION_KEY`);
- no registrar valores sensibles en logs.

## Integración UiPath
- endpoints localhost + contratos JSON en `/contracts`.
- la app decide perfil activo y expone payload de mínimo privilegio.

## Documentos
- copia original en disco;
- PDF derivado automático (MVP con PDF placeholder para formatos complejos);
- hash SHA-256 para deduplicación;
- metadata en Mongo.
