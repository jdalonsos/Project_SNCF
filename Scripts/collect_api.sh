#!/bin/bash

# src/data/collect_api.sh
# Script de collecte des données SNCF vers JSON

set -e  # Arrête en cas d'erreur

# ====================================
# CONFIGURATION
# ====================================
BASE_URL="https://ressources.data.sncf.com/api/records/1.0/search/"
DATASET="regularite-mensuelle-tgv-aqst"
OUTPUT_FILE="data/raw/sncf_data.json"
ROWS_PER_REQUEST=10000
MAX_REQUESTS=20

# ====================================
# PRÉPARATION
# ====================================
# Création du répertoire de sortie
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "🚄 Collecte des données SNCF"
echo "============================"

# ====================================
# COLLECTE
# ====================================
all_records="[]"
offset=0

for ((i=1; i<=MAX_REQUESTS; i++)); do
    
    # Appel API
    response=$(curl -s "${BASE_URL}?dataset=${DATASET}&rows=${ROWS_PER_REQUEST}&start=${offset}&sort=date")
    
    # Extraction des records
    records=$(echo "$response" | jq -c '.records // []')
    record_count=$(echo "$records" | jq 'length')
    
    # Si aucun record, on arrête
    if [ "$record_count" -eq 0 ]; then
        break
    fi
    
    
    # Fusion des records
    all_records=$(echo "$all_records $records" | jq -s 'add')
    
    # Mise à jour de l'offset
    offset=$((offset + record_count))
    
    # Si moins de records que demandé, on a tout
    if [ "$record_count" -lt "$ROWS_PER_REQUEST" ]; then
        break
    fi
done

# ====================================
# EXTRACTION ET SAUVEGARDE
# ====================================
# Extraction uniquement des champs (pas de métadonnées)
echo "$all_records" | jq '[.[] | .fields]' > "$OUTPUT_FILE"

total=$(jq 'length' "$OUTPUT_FILE")
file_size=$(du -h "$OUTPUT_FILE" | cut -f1)

echo "============================"
echo "✅ Collecte terminée"
echo "📊 $total enregistrements"
echo "💾 Fichier: $OUTPUT_FILE"
echo "📦 Taille: $file_size"