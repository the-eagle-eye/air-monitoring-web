#!/bin/bash
# Redeploy in-place en la EC2 (llamado por SSM Run Command desde
# .github/workflows/deploy.yml). NO reemplaza la EC2 — solo swap del código
# y `docker compose up -d --build`.
#
# Uso:
#   aws-remote-deploy.sh <stage_dir> <aws_region> <s3_bucket>
#
# stage_dir  Directorio donde ya se extrajo el bundle (contiene este script).
# region     Región AWS (para descargar artefactos ML si falta el volumen).
# s3_bucket  Bucket de artefactos.
#
# Contrato con user_data.sh.tftpl:
#   - APP_DIR debe existir (creado la primera vez que arrancó la EC2)
#   - .env.prod ya existe (generado por user_data desde SSM)
#   - services/ml-service/ml_artifacts_ensemble_v1/ ya tiene los .pkl
#
# Logs → /var/log/airmon-deploy.log (mismo archivo que el user_data)
set -euxo pipefail
exec > >(tee -a /var/log/airmon-deploy.log) 2>&1

STAGE_DIR="${1:?stage_dir requerido}"
AWS_REGION="${2:?region requerido}"
S3_BUCKET="${3:?s3_bucket requerido}"
APP_DIR=/home/ec2-user/air-monitoring-web

echo "=== airmon deploy $(date -u +%FT%TZ) ==="

# rsync no viene en Amazon Linux 2023 por defecto. Instalar si falta
# (idempotente — dnf salta si ya está instalado).
if ! command -v rsync >/dev/null 2>&1; then
  dnf install -y rsync
fi

if [ ! -d "$APP_DIR" ]; then
  echo "APP_DIR $APP_DIR no existe. La EC2 debió inicializarse con user_data primero." >&2
  exit 1
fi

if [ ! -f "$APP_DIR/.env.prod" ]; then
  echo ".env.prod no existe. La EC2 debió inicializarse con user_data primero." >&2
  exit 1
fi

# rsync --delete refleja el estado exacto del bundle en APP_DIR (borra archivos
# que ya no existan en el commit deployado), preservando:
#   - .env.prod          (generado en el arranque desde SSM, no vive en git)
#   - artefactos ML      (montados como volumen, gitignored, se rehidratan de S3)
#   - .git y node_modules por si el árbol tuviera restos manuales
rsync -a --delete \
  --exclude='.env.prod' \
  --exclude='services/ml-service/ml_artifacts_ensemble_v1/' \
  --exclude='.git/' \
  --exclude='node_modules/' \
  "$STAGE_DIR"/ "$APP_DIR"/

chown -R ec2-user:ec2-user "$APP_DIR"

cd "$APP_DIR"

# Docker compose necesita las variables de entorno. Ejecutar como ec2-user
# (está en el grupo docker desde user_data). `--build` reconstruye imágenes
# que cambiaron; imágenes iguales se re-usan de caché → deploy rápido si solo
# tocaste 1 servicio.
sudo -u ec2-user docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  up -d --build

# Prune imágenes viejas — sin esto el disco se llena tras varios deploys
# (30 GB gp3 se queda corto con 5+ imágenes ML de ~800 MB cada una).
sudo -u ec2-user docker image prune -f

echo "=== airmon deploy OK ==="
