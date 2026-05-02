import os
import shutil

def copy_all_dis(base_dir, destination_dir):
    """
    Recorre recursivamente base_dir, encuentra todos los .dis
    y los copia a destination_dir.
    """

    # Crear destino si no existe
    os.makedirs(destination_dir, exist_ok=True)

    total_found = 0
    total_copied = 0

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith(".dis"):
                total_found += 1

                source_path = os.path.join(root, file)
                destination_path = os.path.join(destination_dir, file)

                # Evitar sobreescritura
                if os.path.exists(destination_path):
                    base, ext = os.path.splitext(file)
                    counter = 1
                    while os.path.exists(destination_path):
                        new_name = f"{base}_{counter}{ext}"
                        destination_path = os.path.join(destination_dir, new_name)
                        counter += 1

                shutil.copy2(source_path, destination_path)
                total_copied += 1

                print(f"📄 Copiado: {source_path} → {destination_path}")

    print("\n--- Resumen ---")
    print(f".dis encontrados: {total_found}")
    print(f".dis copiados:   {total_copied}")


if __name__ == "__main__":
    # 🔧 DEFINIR PATHS
    BASE_DIR = r"D:\Dropbox\MADI\DINAGUA_SL\03-Proces_Info_DIN\01-Salidas_campo"
    DEST_DIR = r"D:\Dropbox\MADI\DINAGUA_SL\03-Proces_Info_DIN\04-Codigo\aforix\data\raw\FT"

    print("🟢 Iniciando copia de archivos .dis...\n")
    copy_all_dis(BASE_DIR, DEST_DIR)