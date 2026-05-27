# Applique le schema PostgreSQL sur le serveur INTERNE (192.168.1.203).
# Identifiants : PG_USER / PG_PASSWORD du fichier .env ; base PG_DBNAME (defaut erp_db).
# Prerequis : pip install -r migration\requirements.txt  (psycopg2-binary)
# Usage :
#   .\migration\apply_interne.ps1            # applique
#   .\migration\apply_interne.ps1 --dry-run  # apercu sans executer
#   .\migration\apply_interne.ps1 --reset    # DROP SCHEMA CASCADE avant (POC vierge)
& "$PSScriptRoot\..\venv\Scripts\python.exe" "$PSScriptRoot\apply_schema.py" --host 192.168.1.203 @args
