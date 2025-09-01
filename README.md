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

Cuando corrí los tests, me encontré conq que dos de ellos fallaban por una superposición en las configuraciones: había configuraciones de log level tanto en las variables de entorno como en los archivos. Los tests fallaban porque la configuración esperada era la provista por el archivo de configuración, pero se adoptaba la provista por las variables de entorno.

Para resolver esto se me ocurrieron dos formas:
1. Hacer que se prioricen las configuraciones de los archivos sobre las de las variables de entorno.
2. Quitar las configuraciones mediante variables de entorno de los servicios en el docker compose.

Decidí tomar la segunda estrategia, ya que en las descripciones encontradas en `server/main.py` y en `client/main.go` se menciona que se priorizan las configuraciones provistas por las variables de entorno antes que las encontradas en archivos de configuración. 

Para no cambiar esa decisión de diseño provista por la cátedra, adopté la segunda estrategia.

## Ejercicio 3
El script creado para este ejercicio (`validar-echo-server.sh`) inicia un nuevo contenedor de Docker y lo conecta a la red virtual generada por el Docker Compose (`tp0_testing_net`). Por lo tanto, para que el script corra correctamente es condición necesaria que el servidor haya sido iniciado previamente utilizando un archivo de Docker Compose generado con el script creado en el ejercicio 1.

Primero se busca el puerto del servidor en el archivo de configuración del mismo (`server/config.ini`). 

Luego valida que la red virtual esté creada, si no lo está, lo más probable es que no se haya iniciado el servidor utilizando Docker Compose. 

Finalmente, se inicia un nuevo contenedor en la red virtual y se ejecuta la prueba de netcat contra el puerto encontrado y la ip `server`. Usar la palabra `server`como dirección IP es válido sólo si el servidor se inició utilizando el Docker Compose, y sirve para referenciar la IP del servicio con ese nombre dentro de la red virtual.

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

En este caso solo manejamos la señal `SIGTERM` con una función que cierra la conexión con el servidor y actualiza el estado interno `running` a falso.

Se modificó el hilo principal del cliente para que se cierre agraciadamente frente a esos eventos.

## Ejercicio 5

### Comunicación
Se implementaron módulos de comunicación tanto para el cliente como para el servidor.

Ambos módulos hacen escencialmente lo mismo, aunque pueden diferir en pequeños detalles de implementación ya que están en lenguajes distintos.

Ideé un protocolo de comunicación básico e independiente del modelo de dominio del sistema. El protocolo consiste básicamente de un header de 5 bytes, el primero para especificar el tipo de mensaje que se está enviando y los otros 4 para el largo del cuerpo del mensaje. Los bytes del largo del body se envían en big endian.

```
BYTE 0      1      2      3      4      5      6      7      8
     +------+------+------+------+------+------+------+------+---
     | TYPE |           LENGTH          |   BODY (VARIABLE)   ...
     +------+------+------+------+------+------+------+------+---
      
```

Para este ejercicio sólo implementé un tipo de mensaje, el tipo `0x01` en el cual se envía un único String codificado con UTF-8 en el body.

### Cliente
Se modificó el comportamiento del cliente para que envíe al servidor solamente dos mensajes. El primero informa su número de agencia, y el segundo envia los datos necesarios para la apuesta de una persona separados por coma en el siguiente orden:

```
nombre, apellido, documento, nacimiento, número
```

Los datos requeridos para enviar los datos de la apuesta son tomados de variables de entorno como pide la consigna, y el número de agencia es el que se obtiene mediante el archivo de configuración.

Luego, espera que el servidor responda con los mismos datos que se le enviaron para confirmar la recepción del mensaje.

Adicionalmente, para que pasen los tests, fue necesario modificar nuevamente el test `generar-compose.py` para agregar variables de entorno con datos de una apuesta. Se hardcodearon los mismos datos propuestos por la consigna.

### Servidor
El servidor se comporta de la manera esperada como se describió para el cliente.
Primero espera recibir el número de agencia, luego los datos para una apuesta. Si los datos fueron enviados en el formato correcto, se almacena la apuesta utilizando la función `store_bet` y luego se le responde al cliente con una copia del mensaje que envió. Finalmente cierra la conexión con el cliente.

### Short Reads y Short Writes
Para evitar los **short reads** siempre se esperan recibir 5 bytes para el header. Luego, teniendo el largo del payload o body del mensaje, se espera recibir esa cantidad de bytes. Si no ocurre ningún error pero no se obtienen los bytes suficientes, se sigue esperando hasta obtener los indicados. Si ocurre algún error antes de obtener los bytes necesarios, se eleva ese ese error.

Para evitar los **short writes** en el servidor se utiliza la función `socket.sendall` que no retorna hasta haber enviado todos los bytes indicados o hasta que ocurra un error. En el cliente no existe una función como `sendall`, por lo que si se retorna sin haber enviado los bytes indicados se continúa enviando los faltantes hasta que se logren enviar todos u ocurra un error.