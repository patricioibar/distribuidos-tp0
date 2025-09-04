# TP0: Docker + Comunicaciones + Concurrencia

## Ejercicio 1

La resolución de este ejercicio incluye un script bash (`generar-compose.sh`) que ejecuta un script de python (`generar-compose.py`). Éste último genera el archivo docker compose con el nombre y cantidad de clientes indicados.

El archivo se escribe sin utilizar ninguna librería externa. Simplemente se escriben los strings necesarios para generar el archivo de forma correcta.

No se agrega ni modifica nada de la estructura base del docker compose provista por la cátedra.

### Ejecución

El script se ejecuta de la misma manera que se muestra en el enunciado del ejercicio.

```./generar-compose.sh <nombre_archivo> <cantidad_clientes>```

## Ejercicio 2

Este ejercicio lo resolví modificando exclusivamente el script `generar-compose.py` creado en el ejercicio anterior.

Para resolverlo, bastó con crear un volumen en cada servicio (server y client). Los volúmenes montan los archivos `config.ini` y `config.yaml` para el servidor y los clientes respectivamente en los contenedores donde se ejecutan. De esta manera, los cambios que se hagan sobre esos archivos en la computadora host serán inmediatamente visibles en los contenedores, sin necesidad de reconstruir las imágenes de Docker.

### Superposición entre variables de entorno y archivo de configuración

Cuando corrí los tests, me encontré con que dos de ellos fallaban por una superposición en las configuraciones: había configuraciones de log level tanto en las variables de entorno como en los archivos. Los tests fallaban porque la configuración esperada era la provista por el archivo de configuración, pero se adoptaba la provista por las variables de entorno.

Para resolver esto se me ocurrieron dos formas:
1. Hacer que se prioricen las configuraciones de los archivos sobre las de las variables de entorno.
2. Quitar las configuraciones mediante variables de entorno de los servicios en el docker compose.

Decidí tomar la segunda estrategia, ya que en las descripciones encontradas en `server/main.py` y en `client/main.go` se menciona que se priorizan las configuraciones provistas por las variables de entorno antes que las encontradas en archivos de configuración. 

Para no cambiar esa decisión de diseño provista por la cátedra, adopté la segunda estrategia.

### Ejecución
Este ejercicio sólo modifica un poco el script del ejercicio anterior. Para ejecutarlo hace falta correr el script de nuevo, como se detalla en la sección de ejecución del ejercicio 1.