import os
import re
import shutil
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = r"D:\repos\aforix\data\raw\FT"

# Si True, crea copia .bak antes de modificar cada archivo
CREATE_BACKUP = True

# Si True, busca también dentro de subdirectorios
RECURSIVE = True


# ============================================================
# FUNCIONES
# ============================================================

def p_number_to_70_code(number_text):
    """
    Convierte:
    P3    -> 7003
    P8    -> 7008
    P13   -> 7013
    P91   -> 7091
    P0440 -> 70440

    Los ceros iniciales después de P se eliminan.
    """
    return f"70{int(number_text):02d}"


def process_xml_file(file_path):
    """
    Reemplaza en XML:
    <ref val="P3" />
    por:
    <ref val="7003" />
    """

    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        content = f.read()

    new_content, count = re.subn(
        r'(<ref\s+val=")P0*(\d+)(")',
        lambda m: f'{m.group(1)}{p_number_to_70_code(m.group(2))}{m.group(3)}',
        content,
        flags=re.IGNORECASE
    )

    if count > 0:
        save_modified_file(file_path, new_content)
        print(f"XML modificado: {file_path} | cambios: {count}")

    return count


def process_dis_file(file_path):
    """
    Reemplaza códigos P{número} solo en líneas de nombre de archivo.

    Ejemplos:
    File_Name                        P8.TXT.WAD   -> File_Name                        7008.TXT.WAD
    File_Name                        P0440.WAD    -> File_Name                        70440.WAD
    Nombre_Archivo                   P13.WAD      -> Nombre_Archivo                   7013.WAD

    Preserva correctamente los saltos de línea.
    """

    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()

    new_lines = []
    total_changes = 0

    # Acepta variantes en inglés y español.
    field_pattern = re.compile(
        r'^(\s*(?:File[_ ]?Name|Nombre[_ ]?(?:de[_ ]?)?Fichero|Nombre_del_Fichero|Fichero)\s+)(.*?)(\r\n|\n|\r)?$',
        re.IGNORECASE
    )

    # Busca códigos tipo P8, P08, P0440, P13, seguidos o no por extensiones:
    # P8.TXT.WAD, P0440.WAD, P13, etc.
    p_code_pattern = re.compile(
        r'\bP0*(\d+)(?=(?:\.[A-Za-z0-9]+)*\b)',
        re.IGNORECASE
    )

    for line in lines:
        match = field_pattern.match(line)

        if not match:
            new_lines.append(line)
            continue

        field_part = match.group(1)
        value_part = match.group(2)
        line_ending = match.group(3) or ""

        new_value_part, count = p_code_pattern.subn(
            lambda m: p_number_to_70_code(m.group(1)),
            value_part,
            count=1
        )

        new_lines.append(field_part + new_value_part + line_ending)
        total_changes += count

    if total_changes > 0:
        save_modified_file(file_path, "".join(new_lines))
        print(f"DIS modificado: {file_path} | cambios: {total_changes}")

    return total_changes


def save_modified_file(file_path, new_content):
    """
    Guarda el archivo modificado.
    Opcionalmente crea backup .bak.
    """

    if CREATE_BACKUP:
        backup_path = str(file_path) + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)


def main():
    base_path = Path(BASE_DIR)

    if not base_path.exists():
        raise FileNotFoundError(f"No existe el directorio base: {BASE_DIR}")

    files = base_path.rglob("*") if RECURSIVE else base_path.glob("*")

    total_files_checked = 0
    total_files_modified = 0
    total_changes = 0

    for file_path in files:
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()

        if ext not in [".xml", ".dis"]:
            continue

        total_files_checked += 1

        if ext == ".xml":
            changes = process_xml_file(file_path)
        elif ext == ".dis":
            changes = process_dis_file(file_path)
        else:
            changes = 0

        if changes > 0:
            total_files_modified += 1
            total_changes += changes
        else:
            print(f"Sin cambios: {file_path}")

    print("\n--- RESUMEN ---")
    print(f"Archivos revisados:   {total_files_checked}")
    print(f"Archivos modificados: {total_files_modified}")
    print(f"Cambios realizados:   {total_changes}")


if __name__ == "__main__":
    main()