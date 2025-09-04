def generar_compose(nombre_archivo, cantidad):
    with open(nombre_archivo, 'w') as archivo:
        archivo.write("name: tp0\n")
        archivo.write("services:\n")
        escribir_servidor(archivo, cantidad)
        for i in range(1, cantidad + 1):
            escribir_cliente(archivo, i)
        escribir_network(archivo)

def escribir_servidor(archivo, numero):
    archivo.write(
        "  server:\n"
        "    container_name: server\n"
        "    image: server:latest\n"
        "    entrypoint: python3 /main.py\n"
        "    environment:\n"
        "      - PYTHONUNBUFFERED=1\n"
        f"      - TOTAL_AGENCIES={numero}\n"
        "    networks:\n"
        "      - testing_net\n"
        "    volumes:\n"
        "      - ./server/config.ini:/config.ini\n"
    )

def escribir_cliente(archivo, numero):
    archivo.write(
        f"  client{numero}:\n"
        f"    container_name: client{numero}\n"
        f"    image: client:latest\n"
        f"    entrypoint: /client\n"
        f"    environment:\n"
        f"      - CLI_ID={numero}\n"
        f"      - NOMBRE=Santiago Lionel\n"
        f"      - APELLIDO=Lorca\n"
        f"      - DOCUMENTO=30904465\n"
        f"      - NACIMIENTO=1999-03-17\n"
        f"      - NUMERO=7574\n"
        f"    networks:\n"
        f"      - testing_net\n"
        f"    depends_on:\n"
        f"      - server\n"
        f"    volumes:\n"
        f"      - ./client/config.yaml:/config.yaml\n"
        f"      - ./.data/agency-{numero}.csv:/data/agency-{numero}.csv\n"
    )
    
def escribir_network(archivo):
    archivo.write(
        "networks:\n"
        "  testing_net:\n"
        "    ipam:\n"
        "      driver: default\n"
        "      config:\n"
        "        - subnet: 172.25.125.0/24\n"
    )
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python3 generar-compose.py <nombre_archivo> <cantidad_clientes>")
        sys.exit(1)
    
    nombre_archivo = sys.argv[1]
    try:
        cantidad = int(sys.argv[2])
        if cantidad < 0:
            raise ValueError
    except ValueError:
        print("La cantidad de clientes debe ser un entero positivo.")
        sys.exit(1)
    
    generar_compose(nombre_archivo, cantidad)