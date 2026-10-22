"""
services/generador_pdf.py
Servicio para generar certificados en formato PDF utilizando fpdf2.
Formato: A4 Horizontal (Landscape).
Estilo: Institucional con bordes y acentos en Azul Marino (#14213D) y Dorado (#B8923D).
"""

import io
from typing import Dict, Any
from fpdf import FPDF


class CertificadoPDF(FPDF):
    def __init__(self):
        # A4 Landscape: 297mm de ancho por 210mm de alto
        super().__init__(orientation="landscape", unit="mm", format="A4")
        self.set_auto_page_break(auto=False, margin=0)

    def dibujar_marco_decorativo(self):
        """Dibuja un marco ornamental azul marino y dorado alrededor de la página."""
        # Fondo sutil o márgenes limpios
        ancho = 297
        alto = 210

        # Marco exterior azul marino (#14213D)
        self.set_line_width(2.5)
        self.set_draw_color(20, 33, 61)
        self.rect(8, 8, ancho - 16, alto - 16)

        # Marco interior dorado (#B8923D)
        self.set_line_width(0.8)
        self.set_draw_color(184, 146, 61)
        self.rect(11, 11, ancho - 22, alto - 22)

        # Esquinas decorativas doradas
        self.set_draw_color(184, 146, 61)
        self.set_line_width(1.5)
        # Superior izquierda
        self.line(13, 13, 25, 13)
        self.line(13, 13, 13, 25)
        # Superior derecha
        self.line(ancho - 25, 13, ancho - 13, 13)
        self.line(ancho - 13, 13, ancho - 13, 25)
        # Inferior izquierda
        self.line(13, alto - 13, 25, alto - 13)
        self.line(13, alto - 13, 13, alto - 25)
        # Inferior derecha
        self.line(ancho - 25, alto - 13, ancho - 13, alto - 13)
        self.line(ancho - 13, alto - 13, ancho - 13, alto - 25)


def crear_pdf_certificado(estudiante: Dict[str, Any]) -> bytes:
    """
    Genera el archivo PDF en memoria para un estudiante elegible.
    Retorna los bytes del PDF generado.
    """
    pdf = CertificadoPDF()
    pdf.add_page()
    pdf.dibujar_marco_decorativo()

    estado = estudiante.get("estado", "Aprobación")
    titulo_tipo = (
        "CERTIFICADO DE APROBACIÓN"
        if estado == "Aprobación"
        else "CERTIFICADO DE PARTICIPACIÓN"
    )

    # 1. Encabezado institucional
    pdf.set_y(22)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(184, 146, 61)  # Dorado
    pdf.cell(0, 7, "LA ACADEMIA DE CAPACITACIÓN PROFESIONAL", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "OTORGA EL PRESENTE RECONOCIMIENTO OFICIAL", align="C", new_x="LMARGIN", new_y="NEXT")

    # 2. Título de Certificado según Tipo
    pdf.set_y(38)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(20, 33, 61)  # Azul Marino
    pdf.cell(0, 12, titulo_tipo, align="C", new_x="LMARGIN", new_y="NEXT")

    # Línea divisoria decorativa dorada bajo el título
    pdf.set_draw_color(184, 146, 61)
    pdf.set_line_width(0.7)
    pdf.line(90, 52, 207, 52)

    # 3. Texto introductorio
    pdf.set_y(57)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "A favor de:", align="C", new_x="LMARGIN", new_y="NEXT")

    # 4. Nombre del estudiante
    pdf.set_y(66)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 33, 61)
    nombre = estudiante.get("nombre_completo", "").upper()
    pdf.cell(0, 10, nombre, align="C", new_x="LMARGIN", new_y="NEXT")

    # 5. Identificación
    pdf.set_y(78)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    ident = estudiante.get("identificacion", "")
    pdf.cell(0, 6, f"Identificación: {ident}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 6. Texto del logro y programa
    pdf.set_y(90)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)
    texto_cumplimiento = (
        "Por haber aprobado satisfactoriamente todos los requisitos académicos del programa:"
        if estado == "Aprobación"
        else "Por haber participado con dedicación en las sesiones lectivas del programa:"
    )
    pdf.cell(0, 6, texto_cumplimiento, align="C", new_x="LMARGIN", new_y="NEXT")

    # 7. Nombre del Programa
    pdf.set_y(99)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(184, 146, 61)
    programa = estudiante.get("programa", "")
    pdf.cell(0, 9, programa, align="C", new_x="LMARGIN", new_y="NEXT")

    # 8. Cohorte y métricas de desempeño
    cohorte = estudiante.get("cohorte") or "2026-A"
    promedio = estudiante.get("promedio_nota", 0.0)
    asistencia = estudiante.get("promedio_asistencia", 0.0)

    pdf.set_y(112)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, f"Cohorte: {cohorte}", align="C", new_x="LMARGIN", new_y="NEXT")

    # Recuadro resumen de desempeño académico
    pdf.set_y(124)
    recuadro_w = 120
    recuadro_x = (297 - recuadro_w) / 2
    pdf.set_fill_color(244, 246, 249)
    pdf.set_draw_color(210, 215, 225)
    pdf.set_line_width(0.3)
    pdf.rect(recuadro_x, 122, recuadro_w, 14, style="FD")

    pdf.set_x(recuadro_x)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 33, 61)
    texto_metricas = f"Promedio Final: {promedio:.2f} / 100    |    Asistencia Registrada: {asistencia:.2f}%"
    pdf.cell(recuadro_w, 14, texto_metricas, align="C")

    # 9. Firmas y pie institucional
    y_firmas = 162
    pdf.set_draw_color(184, 146, 61)
    pdf.set_line_width(0.5)

    # Firma 1: Dirección Académica
    pdf.line(55, y_firmas, 115, y_firmas)
    pdf.set_y(y_firmas + 3)
    pdf.set_x(55)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 33, 61)
    pdf.cell(60, 4, "Dirección Académica", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(55)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(60, 4, "Academia de Certificación", align="C")

    # Firma 2: Coordinación del Programa
    pdf.line(182, y_firmas, 242, y_firmas)
    pdf.set_y(y_firmas + 3)
    pdf.set_x(182)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 33, 61)
    pdf.cell(60, 4, "Coordinación General", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(182)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(60, 4, "Acreditación y Registros", align="C")

    # Código de verificación al pie
    pdf.set_y(192)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 4, f"ID de Certificado: {ident}-{programa[:3].upper()}-2026  |  Documento oficial digitalmente verificado", align="C")

    return bytes(pdf.output())
