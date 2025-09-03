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

## Ejercicio 6

### Comunicación

#### String List
Para enviar eficientemente los batches, implementé el otro tipo de mensaje en el protocolo de comunicación. Es el tipo "StringList" (código `0x02`) que , como dice su nombre, contiene una lista de strings. Ya que gracias al header se sabe la longitud del payload, decidí que el body de este tipo de mensaje esté estructurado de la siguiente manera:

```
BYTE    0      1      2      3      4      5
        +------+------+------+------+------+----
        | 1ST STRING LEN (N) | 1ST STRING     ...
        +------+------+------+------+------+----
```

```
BYTE   3+N   3+N+1  3+N+2  3+N+3  3+N+4  3+N+5
    ----+------+------+------+------+------+----
   ...   2ND STRING LEN (N) | 2ND STRING      ...
    ----+------+------+------+------+------+----
```

#### Protocolo de Aplicación
Modifiqué el protocolo de aplicación para el correcto funcionamiento del ejercicio, de paso haciéndolo más genérico y extensible.

El servidor espera que al recibir una nueva conexión de un cliente, el primer mensaje sea del tipo "String" y que contenga, separados por coma, la request que se quiere hacer y el identificador de la agencia que se conecta.

Para este ejercicio sólo implementé la request para cargar batches de apuestas (`LOAD_BATCHES`).

Luego de recibir esta request se espera obtener una cantidad indefinida de mensajes "StringList", cada una representando un batch de apuestas. 

El cliente debe especificar cuándo se detiene de enviar batches de datos utilizando un mensaje de tipo "String" que debe contener dentro el mensaje `END`.

### Servidor
Fuera del protocolo de comunicación, la principal funcionalidad del servidor para este ejercicio se encuentra en el método `_load_batches_request` del archivo `server/common/server.py`. 

Al recibir cada batch simplemente se parsean los strings que contienen cada apuesta y se almacenan utilizando la función `store_bets` provista por la cátedra. Si ocurre algún error parseando alguna apuesta, se descarta el batch completo y se dejan de recibir los próximos batches. Esto podría implementarse fácilmente de otra manera, pero según mi interpretación de la consigna ese es el comportamiento esperado.

El servidor muestra un log por cada batch correctamente almacenado. Nuevamente interpreté que ese es el comportamiento esperado según el enunciado y lo que esperan los tests, pero podría ser cambiado muy fácilmente.

### Cliente
El archivo CSV se inyecta al contenedor del cliente mediante **docker volumes** como se especifica en la consigna.

Para procesar el archivo, utilizo el objeto `Scanner` de la librería `bufio`. Este objeto no solo facilita leer el archivo línea a línea, sino que optimiza la lectura utilizando un buffer (véase [bufio.Scanner](https://pkg.go.dev/bufio#Scanner) y [Scanner.Buffer](https://pkg.go.dev/bufio#Scanner.Buffer))

Probé mediante fuerza bruta que con batches de 174 entradas no se superan los 8kiB (8*1024B) de paquete, y con 171 no se superan los 8kB (8*1000B) para los datasets provistos por la cátedra. Escogí el tamaño default del buffer arbitrariamente como **170**, ya que es redondo y porque no estaba seguro si la consigna hace referencia a 8kiB u 8kB, pero contempla ambos casos.

Fuera del protocolo de comunicación, la principal funcionalidad del cliente para este ejercicio se encuentra en el método `sendBatchedData` del archivo `client/common/client.go`. 

Sin importar como se salga de la función `sendBatchedData` (ya sea un cierre convencional, por algún error, o si se recibe una señal para concluir la ejecución del cliente), se asegura el correcto cierre del archivo con `defer file.close()`.

El comportamiento del cliente es sencillo. Simplemente lee el archivo línea a línea, agrupándolas secuencialmente de a batches con el tamaño máximo definido por el parámetro de configuración `MaxBatchSize`. Si se llena un batch con el tamaño máximo, se envía al servidor y se continúa leyendo el archivo. Si se termina de leer el archivo, se envía el batch hasta donde se llenó y luego se envía un mensaje `END`.

## Ejercicio 7
Para este ejercicio acabé implementando dos soluciones. La solución subida actualmente es la final, pero explicaré ambas.

### Primer Intento
En la solución que implementé incialmente, la cual puede verse en commits anteriores al titulado "servidor atiende servidores secuencialmente." (tuve un error al escribir ese commit, debería ser servidor atiende clientes secuencialmente), el servidor mantenía las conexiones de los clientes abiertas hasta que todas las agencias acaben de subir sus apuestas. Una vez sucedido eso, el servidor respondería a todos los clientes con sus resultados.

De esta manera los clientes quedaban bloqueados esperando a que estén las respuestas. Implementé esta solución inicialmente ya que me parecía preferible que los clientes hagan esto a que tengan que reintentar cada vez que pidan los resultados y aún no estén disponibles.

Sin embargo, noté que esto podría considerarse "multicliente" (lo cual está reservado para el ejercicio 8) así que lo decidí replantear mi solución. Además aproveché para quitar el uso innecesario de multithreading que había hecho en esta solución.

### Solución final
En la solución final, el servidor atiende los clientes de manera secuencial. Los clientes pueden realizar una única request por "conexión". Para hacer más de una request, tendrán que reconectarse con el servidor.

Las request soportadas son:
- Subir apuestas por batches
- Notificar que ya se subieron todos los datos
- Solicitar los resultados del sorteo

Cuando una agencia avisa que ya no subirá más datos, se toma registro para que cuando todas terminen se "haga el sorteo". 

Si una agencia solicita los resultados del sorteo y estos aún no están disponibles, el servidor enviará un mensaje notificando que el sorteo aún está en curso y los clientes deberán reintentar la solicitud más tarde. El servidor notifica que el sorteo aún está en curso utilizando un mensaje de tipo String, cuyo contenido es `"LOTERY_IN_PROGRESS"`. Los clientes tienen sus reintentos configurados para ser cada 3 segundos.

Si todas las agencias subieron sus apuestas, se considera que el sorteo concluyó y se comenzará a responder las consultas sobre los resultados. Cuando una agencia consulta sobre los resultados, el servidor responderá con un mensaje "StringList" conteniendo una lista de todos los DNI de los usuarios que ganaron el sorteo. Si la agencia no tuvo ningún ganador, se responderá con una lista vacía.

## Ejercicio 8
Decidí implementar este ejercicio utilizando múltiples threads, usando la librería `threading` de Python.

Si bien la consigna advierte tener en consideración las limitaciones de Python por su Global Interpreter Lock (GIL), éste no supone un problema para la implementación necesaria en este trabajo práctico. El GIL impide que dos threads accedan al mismo bytecode al mismo tiempo, dicho de otra forma, dos threads no pueden ejecutar las mismas líneas de código al mismo tiempo.

Esto supondría un problema para tareas intensivas en procesamiento (CPU intensive). No supone problemas para tareas intensivas de entrada salida, ya que cuando los threads se bloquean a la espera de un recurso liberan el GIL y permiten que otros threads ejecuten el código.

Ya que el servidor sólo realiza tareas intensivas de entrada salida (leer y escribir en archivos y sockets) y no realiza ninguna tarea intensiva en procesamiento, se puede decir que el GIL no afecatará al rendimiento del programa.

### Nueva feature en clientes
Ya que los clientes ya no deben actuar de forma colaborativa, se agregó una funcionalidad para que puedan enviar requests secuencialmente a través del mismo socket (en una misma conexión).

### Error de sincronización cuando un cliente envía requests de forma paralela
Antes de implementar que el cliente pueda enviar varias requests en una misma conexión, me encontré con una race condition: el cliente podía indicar que había terminado de subir sus apuestas cuando el servidor aún estaba recibiéndolas y guardándolas en el archivo. Esto generaba que algunas veces se pueda dar los resultados sin que estén todos las apuestas en memoria aún.

Esto podría solucionarse exigiendo que el cliente no pueda hacer requests de forma paralela, y que obligatoriamente deba enviar la notificación de "todas las apuestas subidas" mediante la misma conexión en que subió los batches. Pero no me quería conformar con eso.

Agregué una pequeña sincronización mediante `threading.Events`, en la cual la notificación del cliente de que "todas las apuestas fueron subidas" no se procesa hasta haber terminado de guardar en el archivo. En específico, guardo una lista de `threading.Events`, ya que se considera que el cliente podría tener múltiples conexiones subiendo múltiples flujos de batches.

### Uso de archivos thread-safe
El uso de archivos en el servidor es exclusivamente mediante la utilización de las funciones `store_bets` (escritura) y `load_bets` (lectura).

Para garantizar que la escritura sea correcta, sólo debe haber un thread escribiendo en el archivo al mismo tiempo. Para esto se agregó un lock, el cual debe ser adquirido obligatoriamente antes de emplear la función `store_bets`.

La correcta lectura se garantiza intrínsecamente por el diseño del protocolo. Para leer el archivo, primero se debe confirmar que no se escribirá más en él. Esto se garantiza gracias al protocolo implementado en el ejercicio 7: para poder dar resultados (que es el único momento en que se leen las apuestas guardadas) primero se debe tener la certeza que no se escribirá más en el archivo. La sincronización de la sección anterior también es necesaria para que esto se cumpla.

Por otro lado, la función `load_bets` dice no ser thread-safe, pero la manera en que es utilizada garantiza que sí lo sea. Cada thread utiliza la función generadora `load_bets` una vez teniendo la certeza que no habrá más escritores, y además abriendo un nuevo file descriptor para cada thread. Esto permite que cada thread pueda realizar la lectura en forma paralela, sin conflictos y con su propio cursor.