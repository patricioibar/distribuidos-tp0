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

## Ejercicio 3
El script creado para este ejercicio (`validar-echo-server.sh`) inicia un nuevo contenedor de Docker y lo conecta a la red virtual generada por el Docker Compose (`tp0_testing_net`). Esto se hace con el parámetro `--network=$NET_NAME` del comando `docker run`.

Por lo tanto, para que el script corra correctamente es condición necesaria que el servidor haya sido iniciado previamente utilizando un archivo de Docker Compose generado con el script creado en el ejercicio 1. 

### Funcionamiento del script
A continuación una breve descripción de lo que hace el script:

Primero se busca el puerto del servidor en el archivo de configuración del mismo (`server/config.ini`). 

Luego valida que la red virtual esté creada, si no lo está, lo más probable es que no se haya iniciado el servidor utilizando Docker Compose. 

Finalmente, se inicia un nuevo contenedor en la red virtual y se ejecuta la prueba de netcat contra el puerto encontrado y la ip `server`. Usar la palabra `server`como dirección IP es válido sólo si el servidor se inició utilizando el Docker Compose, y sirve para referenciar la IP del servicio con ese nombre dentro de la red virtual. Si el script falla porque la dirección `server` es unreacheable, significa que hubo un error o no se ejecutó el echo server a través de docker compose.

### Ejecución
Para ejecutar este ejercicio es estrictamente necesario ejecutar primero el servidor mediante el archivo de Docker Compose, luego se debe ejecutar el script `validar-echo-server.sh`.

Un ejemplo para cómo ejecutar el ejercicio es el siguiente:
```
./generar_compose.sh docker-compose-dev.yaml 0
sudo make docker-compose-up
./validar-echo-server.sh
```
Luego, si no se seguirá utilizando el servidor, correr
```
sudo make docker-compose-up
```

## Ejercicio 4
Para la resolución de este ejercicio se agregaron funcionalidades tanto al servidor como a los clientes para ejecutar funciones determinadas al recibir una señal del tipo `SIGTERM`. 

Al recibir esta señal, las aplicaciones liberan los recursos que estaban utilizando, logean esas liberaciones y luego terminan su ejecución.

Tanto para el cliente como el servidor, si el thread estaba bloqueado utilizando un socket y el mismo se cierra, se desbloquea lanzando una excepción. Cuando se recibe la señal `SIGTERM` también se actualizan los estados internos `running` a falso, para que esta excepción no sea tenida en cuenta y se termine las ejecuciones de forma agraciada.

### Servidor
En Python, se pueden asignar handlers para señales del sistema operativo utilizando la función `signal` de la librería con el mismo nombre.

En este caso, se asigna que el handler sea el método `close` de la clase `Server`. De esta manera, el servidor puede encargarse de liberar sus propios recursos. 

Al recibir la señal `SIGTERM`, el servidor cierra su socket de escucha para nuevas conexiones y, si hay algún cliente conectado, también cierra ese socket. En el futuro cuando se implemente la feature de múltiples clientes deberán cerrarse todos los sockets que puedan estar abiertos.

### Cliente
En Go, se utiliza `os.Signal` para crear un canal por el cual se transmitirán las señales, y se utiliza `signal.Notify` para determinar qué señales deben pasarse a ese canal.

Decidí dejar una Go Routine en la espera de la señal, bloqueada en el canal creado. Preferí esto antes que utilizar una estrategia con select para aprovechar las herramientas propias del lenguaje. Las Go Routines son considerablemente más "ligeras" que un thread, y están ideadas para realizar tareas concurrentes manteniendo el modelo claro y legible.

En este caso solo manejamos la señal `SIGTERM` con una función que cierra la conexión con el servidor y actualiza el estado interno `running` a falso.

Se modificó el hilo principal del cliente para que se cierre agraciadamente frente a esos eventos.

### Ejecución
Este ejercicio implementa el cierre agraciado de los procesos. Para ejecutarlo, se debe primero iniciar los contenedores del Docker Compose para que realicen la ejecución normal (por ejemplo, utilizando `make docker-compose-up`) y luego cerrarse utilizando el parámetro `-t` al hacer `docker compose down`, para que se envíe la señal `SIGTERM` a los servicios del compose. 

`make docker-compose-down` está configurado para utilizar dicho parámetro.