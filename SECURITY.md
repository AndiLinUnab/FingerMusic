# Política de seguridad

## Versiones con soporte

FingerMusic es un proyecto académico. Solo se da soporte a la última versión
publicada en la rama principal.

## Cómo reportar un problema de seguridad

Si encuentras una vulnerabilidad, **no abras un issue público**. Usa los
mecanismos de seguridad de GitHub del repositorio:

1. Entra a la pestaña **Security** del repositorio.
2. Selecciona **Report a vulnerability** (reporte privado de vulnerabilidades),
   si el autor lo tiene habilitado.

Describe el problema, los pasos para reproducirlo y su posible impacto.

## Alcance

La aplicación se ejecuta localmente, no abre puertos de red, no usa Internet
durante la ejecución y no almacena credenciales. El video de la cámara se procesa
en memoria y **no se guarda ni se envía a ningún lugar**. Solo se escribe un
archivo de log local (`logs/fingermusic.log`) que no contiene imágenes.
