## Uso de los Comandos Administrativos

El proyecto utiliza un archivo `manage.py` para ejecutar comandos administrativos, similar a Django.

### Comandos Disponibles

- **startrabbit**

  Controla el servidor RabbitMQ utilizando Docker.

  - Iniciar el servidor:

    ```bash
    python manage.py startrabbit start
    ```

  - Detener el servidor:

    ```bash
    python manage.py startrabbit stop
    ```

  - Reiniciar el servidor:

    ```bash
    python manage.py startrabbit restart
    ```

- **runapp**

  Ejecuta la aplicación RabbitFlow en diferentes modos.

  - Ejecutar la aplicación en modo `all`:

    ```bash
    python manage.py runapp --mode all
    ```

  - Ejecutar solo el decodificador:

    ```bash
    python manage.py runapp --mode decoder
    ```

  - Ejecutar solo el validador:

    ```bash
    python manage.py runapp --mode validator
    ```

  - Ejecutar solo el procesador:

    ```bash
    python manage.py runapp --mode processor
    ```

### Configuración

- **settings.py**

  Define el nombre de la aplicación y otras configuraciones.

- **conexion.py**

  Configura los parámetros de conexión a RabbitMQ.

### Notas de Seguridad

- La configuración del servidor RabbitMQ con el usuario `guest` y permitiendo conexiones remotas es insegura y **solo debe usarse para desarrollo o pruebas**.

- Para entornos de producción, configura usuarios y contraseñas seguros, y limita las conexiones remotas.

