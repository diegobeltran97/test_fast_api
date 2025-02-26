from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
import pandas as pd
import shutil
import os
from datetime import datetime

app = FastAPI()

# Carpeta para subir archivos
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Montar la carpeta donde está el index.html
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

@app.get("/")
def home():
    return {"message": "¡FastAPI funcionando!"}

def calculate_work_hours(df):
    """Función que calcula las horas trabajadas a partir del DataFrame."""
    
    # Renombrar columnas para asegurarnos de que coincidan
    df.rename(columns={"Tipo de registro": "Tipo Registro"}, inplace=True)

    # Asegurar que las columnas esperadas existen
    expected_columns = ["Nombre", "Fecha/Hora", "Tipo Registro"]
    if not all(col in df.columns for col in expected_columns):
        return {"error": f"El archivo debe contener las columnas: {expected_columns}, pero tiene {df.columns.tolist()}"}

    # Convertir la columna de fecha/hora a formato datetime
    df["Fecha/Hora"] = pd.to_datetime(df["Fecha/Hora"])

    # Mapeo de días en inglés a español
    dias_espanol = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }

    # Agrupar por nombre y fecha
    df["Fecha"] = df["Fecha/Hora"].dt.date
    df["Día de la Semana"] = df["Fecha/Hora"].dt.strftime("%A").map(dias_espanol)  # Traducir a español

    work_hours = []

    for (name, date), group in df.groupby(["Nombre", "Fecha"]):
        group = group.sort_values("Fecha/Hora")  # Ordenar por tiempo
        records = group["Fecha/Hora"].tolist()
        types = group["Tipo Registro"].tolist()
        day_of_week = group["Día de la Semana"].iloc[0]  # Obtener el día de la semana en español

        total_seconds = 0
        for i in range(0, len(records) - 1, 2):
            if types[i] == "in" and types[i + 1] == "out":
                total_seconds += (records[i + 1] - records[i]).total_seconds()

        total_hours = total_seconds / 3600  # Convertir a horas
        work_hours.append({
            "Nombre": name,
            "Fecha": str(date),
            "Día de la Semana": day_of_week,
            "Horas Trabajadas": round(total_hours, 2)
        })

    return {"data": work_hours}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    
    # Guardar el archivo en la carpeta "uploads"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Leer el archivo con pandas
    try:
        if file.filename.endswith(".xls"):
            df = pd.read_excel(file_path, engine="xlrd")  # Para archivos .xls
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(file_path, engine="openpyxl")  # Para archivos .xlsx
        else:
            return {"error": "Formato no soportado. Solo .xls y .xlsx"}
        
        # Llamar a la función para calcular horas trabajadas
        result = calculate_work_hours(df)

        return {
            "message": "Archivo recibido y procesado",
            "filename": file.filename,
            "columns": df.columns.tolist(),  # Lista de columnas
            "rows": len(df),  # Número de filas
            "hours_worked": result  # Resultado de cálculo de horas
        }
    except Exception as e:
        return {"error": f"No se pudo leer el archivo: {str(e)}"}
