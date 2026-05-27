# Applique le schema PostgreSQL sur le serveur OVH (10.8.0.6, via VPN).
# Identifiants : PG_USER / PG_PASSWORD du fichier .env ; base PG_DBNAME (defaut erp_db).
# Prerequis : pip install -r migration\requirements.txt  (psycopg2-binary)
# Usage :
#   .\migration\apply_ovh.ps1            # applique
#   .\migration\apply_ovh.ps1 --dry-run  # apercu sans executer
#   .\migration\apply_ovh.ps1 --reset    # DROP SCHEMA CASCADE avant (POC vierge)
& "$PSScriptRoot\..\venv\Scripts\python.exe" "$PSScriptRoot\apply_schema.py" --host 10.8.0.6 @args
