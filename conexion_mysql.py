import mysql.connector

conexion = mysql.connector.connect(
    host="localhost",       # porque expusiste el puerto 3306
    port=3306,
    database="testdb",      # la base creada en docker-compose
    user="testuser",        # el usuario definido en docker-compose
    password="testpass"     # la contraseña definida en docker-compose
)

if conexion.is_connected():
    print("✅ ¡Conexión exitosa a MySQL!")
info = conexion.server_info
print(f"   Versión de MySQL: {info}")

cursor = conexion.cursor()
cursor.close()
conexion.close()
print("Conexión cerrada.")

