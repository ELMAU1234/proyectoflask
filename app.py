from flask import Flask, render_template, request, redirect, url_for, flash, session
import MySQLdb
from datetime import datetime
import math
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "1234"


db = MySQLdb.connect(
    host=os.environ.get("DB_HOST"),
    user=os.environ.get("DB_USERNAME"),
    passwd=os.environ.get("DB_PASSWORD"),
    db=os.environ.get("DB_NAME"),
    port=int(os.environ.get("DB_PORT", 3306)),
    charset="utf8"
)

# DECORADOR LOGIN REQUIRED
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debe iniciar sesión primero", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


# CALCULAR TARIFA
def calcular_tarifa(tipo, ingreso, salida):
    segundos = (salida - ingreso).total_seconds()
    horas = math.ceil(segundos / 3600)

    if tipo.lower() in ["automóvil", "automovil"]:
        return 5.00 if horas <= 1 else 5.00 + (horas - 1) * 3.00
    elif tipo.lower() == "moto":
        return horas * 2.00
    else:
        return horas * 4.00


# INDEX
@app.route("/")
@login_required
def index():
    cur = db.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM espacio WHERE estado='libre'")
        libres = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM espacio WHERE estado='ocupado'")
        ocupados = cur.fetchone()[0]

        cur.execute("""
            SELECT r.id_registro, r.placa, v.tipo_vehiculo, r.id_espacio, r.hora_ingreso
            FROM registro_estacionamiento r
            LEFT JOIN vehiculo v ON r.placa = v.placa
            WHERE r.hora_salida IS NULL
        """)
        activos = cur.fetchall()


        cur.execute("SELECT id_espacio, estado FROM espacio ORDER BY id_espacio")
        espacios = cur.fetchall()

    finally:
        cur.close()

    return render_template("index.html", libres=libres, ocupados=ocupados, activos=activos, espacios=espacios)
    


# INGRESAR VEHÍCULO
@app.route("/ingresar", methods=["GET", "POST"])
@login_required
def ingresar():
    cur = db.cursor()
    try:
        if request.method == "POST":
            placa = request.form["placa"]
            tipo = request.form["tipo"]
            nombre = request.form["nombre"]
            identificacion = request.form["identificacion"]

            cur.execute("INSERT INTO cliente(nombre, identificacion) VALUES(%s, %s)", (nombre, identificacion))
            db.commit()
            id_cliente = cur.lastrowid

            cur.execute("INSERT INTO vehiculo(placa, tipo_vehiculo, id_cliente) VALUES(%s,%s,%s)", (placa, tipo, id_cliente))
            db.commit()

            cur.execute("SELECT id_espacio FROM espacio WHERE estado='libre' LIMIT 1")
            espacio = cur.fetchone()
            if not espacio:
                flash("No hay espacios disponibles", "danger")
                return redirect(url_for("index"))

            id_espacio = espacio[0]

            cur.execute("INSERT INTO registro_estacionamiento(placa,id_espacio,hora_ingreso) VALUES(%s,%s,NOW())", (placa, id_espacio))
            cur.execute("UPDATE espacio SET estado='ocupado' WHERE id_espacio=%s", (id_espacio,))
            db.commit()

            flash("Vehículo ingresado correctamente", "success")
            return redirect(url_for("index"))
    finally:
        cur.close()

    return render_template("ingresar.html")


# REGISTRAR SALIDA
# REGISTRAR SALIDA
@app.route("/salida", methods=["GET", "POST"])
@login_required
def salida():
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT r.id_registro, r.placa, v.tipo_vehiculo, r.id_espacio, r.hora_ingreso
            FROM registro_estacionamiento r
            LEFT JOIN vehiculo v ON r.placa = v.placa
            WHERE r.hora_salida IS NULL
            ORDER BY r.hora_ingreso ASC
        """)
        activos = cur.fetchall()
        
        if request.method == "POST":
            placa = request.form["placa"]

            cur.execute("""
                SELECT r.id_registro, r.hora_ingreso, v.tipo_vehiculo, r.id_espacio
                FROM registro_estacionamiento r
                LEFT JOIN vehiculo v ON r.placa=v.placa
                WHERE r.placa=%s AND r.hora_salida IS NULL
            """, (placa,))
            data = cur.fetchone()


            id_registro, hora_ingreso, tipo, id_espacio = data
            hora_salida = datetime.now()
            tarifa = calcular_tarifa(tipo, hora_ingreso, hora_salida)

            cur.execute("UPDATE registro_estacionamiento SET hora_salida=%s, monto_pagado=%s WHERE id_registro=%s",
                        (hora_salida, tarifa, id_registro))
            cur.execute("UPDATE espacio SET estado='libre' WHERE id_espacio=%s", (id_espacio,))
            db.commit()

            flash(f"Pago registrado: ${tarifa}", "success")
            return redirect(url_for("salida"))
    finally:
        cur.close()

    return render_template("salida.html", activos=activos)



# REPORTES
@app.route("/reportes", methods=["GET", "POST"])
@login_required
def reportes():
    total = 0
    fecha1 = ""
    fecha2 = ""

    if request.method == "POST":
        fecha1 = request.form["fecha1"]
        fecha2 = request.form["fecha2"]

        cur = db.cursor()
        try:
            cur.execute("SELECT SUM(monto_pagado) FROM registro_estacionamiento WHERE DATE(hora_salida) BETWEEN %s AND %s", (fecha1, fecha2))
            total = cur.fetchone()[0] or 0
        finally:
            cur.close()

    return render_template("reportes.html", total=total, fecha1=fecha1, fecha2=fecha2)


# VER REGISTROS
@app.route("/registros")
@login_required
def registros():
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT r.id_registro, r.placa, v.tipo_vehiculo, r.id_espacio, r.hora_ingreso, r.hora_salida, r.monto_pagado
            FROM registro_estacionamiento r
            LEFT JOIN vehiculo v ON r.placa = v.placa
            ORDER BY r.id_registro DESC
        """)
        datos = cur.fetchall()
    finally:
        cur.close()

    return render_template("registros.html", registros=datos)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = False

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cur = db.cursor()
        try:
            cur.execute("SELECT id, password FROM usuarios WHERE username=%s", (username,))
            user = cur.fetchone()
        finally:
            cur.close()

        if user is not None:
            usuario_id = user[0]
            contraseña_guardada = user[1]
            if password == contraseña_guardada:
                session["user_id"] = usuario_id  
                session["username"] = username
                return redirect(url_for("index"))
            else:
                error = True
        else:
            error = True

    return render_template("login.html", error=error)


import re  

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        username = request.form["username"]
        password = request.form["password"]
        if len(password) != 8 or not re.search("[A-Za-z]", password) or not re.search("[0-9]", password):
            return "La contraseña debe tener 8 caracteres y contener letras y números"

        cur = db.cursor()

        try:
            cur.execute("INSERT INTO usuarios(nombre, username, password) VALUES(%s, %s, %s)", 
                        (nombre, username, password))
            db.commit()
        finally:
            cur.close()

        return redirect(url_for("login"))

    return render_template("register.html")




if __name__ == "__main__":
    app.run(debug=True)
