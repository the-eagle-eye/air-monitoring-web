# Guia Completa de Despliegue - Air Monitoring Project

## Tabla de Contenidos

1. [Resumen de Arquitectura](#1-resumen-de-arquitectura)
2. [Requisitos Previos](#2-requisitos-previos)
3. [Paso 1: Crear Cuenta AWS y Configurar CLI](#paso-1-crear-cuenta-aws-y-configurar-cli)
4. [Paso 2: Crear la VPC y Redes](#paso-2-crear-la-vpc-y-redes)
5. [Paso 3: Crear la Base de Datos RDS PostgreSQL](#paso-3-crear-la-base-de-datos-rds-postgresql)
6. [Paso 4: Almacenar Secretos en AWS Secrets Manager](#paso-4-almacenar-secretos-en-aws-secrets-manager)
7. [Paso 5: Subir Artefactos ML a S3](#paso-5-subir-artefactos-ml-a-s3)
8. [Paso 6: Crear Repositorios en ECR](#paso-6-crear-repositorios-en-ecr)
9. [Paso 7: Construir y Subir Imagenes Docker a ECR](#paso-7-construir-y-subir-imagenes-docker-a-ecr)
10. [Paso 8: Crear el Cluster ECS y Task Definitions](#paso-8-crear-el-cluster-ecs-y-task-definitions)
11. [Paso 9: Crear el Application Load Balancer](#paso-9-crear-el-application-load-balancer-alb)
12. [Paso 10: Crear los Servicios ECS](#paso-10-crear-los-servicios-ecs)
13. [Paso 11: Configurar Service Discovery (Cloud Map)](#paso-11-configurar-service-discovery-cloud-map)
14. [Paso 12: Ejecutar Migraciones de Base de Datos](#paso-12-ejecutar-migraciones-de-base-de-datos)
15. [Paso 13: Desplegar el Frontend en Vercel](#paso-13-desplegar-el-frontend-en-vercel)
16. [Paso 14: Configurar CI/CD con GitHub Actions](#paso-14-configurar-cicd-con-github-actions)
17. [Paso 15: Verificacion Final](#paso-15-verificacion-final)
18. [Costos Estimados](#costos-estimados)
19. [Troubleshooting](#troubleshooting)

---

## 1. Resumen de Arquitectura

```
                    INTERNET
                       |
          +------------+-------------+
          |                          |
     VERCEL (Frontend)         AWS ALB (HTTPS)
     Next.js SSR/SSG           api.tudominio.com
     CDN Global                      |
          |                    +-----+------+
          |                    | api-gateway |  (ECS Fargate, puerto 8000)
          +----- REST -------->| JWT + RBAC  |
                               +-----+------+
                                     |  Cloud Map (DNS interno)
                    +----------------+----------------+
                    |                |                 |
              iot-service      ml-service        ops-service
              (Fargate:8001)   (Fargate:8002)    (Fargate:8003)
                    |                |                 |
                    +-------+--------+-----------------+
                            |
                    RDS PostgreSQL
                    (VPC Privada)

              S3 Bucket: ml_artifacts (model.pkl, scaler.pkl, etc.)
```

**Flujo de autenticacion:**

```
Frontend (login) --POST /api/v1/auth/login--> api-gateway
                                                  |
                                            api-gateway consulta
                                            ops-service para validar
                                            usuario y password
                                                  |
                                            ops-service devuelve
                                            usuario con password_hash
                                                  |
                                            api-gateway verifica
                                            bcrypt y genera JWT
                                                  |
                                            Frontend recibe
                                            access_token + refresh_token
                                                  |
                                            Todas las peticiones
                                            siguientes incluyen:
                                            Authorization: Bearer <token>
```

**Rutas manejadas directamente por api-gateway (NO se proxean):**
- `/api/v1/auth/*` (login, refresh, logout, me)
- `/api/v1/dashboard/kpis` (agrega KPIs de todos los servicios)
- `/health`

**Rutas proxy (api-gateway reenvía al servicio correspondiente):**
- `/api/v1/iot/*` -> iot-service
- `/api/v1/predictions/*`, `/api/v1/alerts/*` -> ml-service
- `/api/v1/equipos/*`, `/api/v1/incidencias/*`, `/api/v1/calibraciones/*`, `/api/v1/usuarios/*`, `/api/v1/dashboard/*` -> ops-service

**Roles y permisos (RBAC):**

| Rol | Lectura | Escritura |
|-----|---------|-----------|
| administrador | Todo | Todo (incluido CRUD usuarios) |
| tecnico | Todo | Incidencias, calibraciones, equipos |
| coordinador | Todo | Solo lectura |

**Rutas publicas (sin auth):**
- POST `/api/v1/auth/login`, `/api/v1/auth/refresh`
- POST `/api/v1/iot/readings` (los equipos IoT envian lecturas sin auth)
- GET `/health`

**Componentes AWS que vamos a crear:**

| # | Servicio AWS | Para que |
|---|-------------|----------|
| 1 | VPC + Subnets | Red privada aislada |
| 2 | RDS PostgreSQL | Base de datos |
| 3 | Secrets Manager | Guardar credenciales |
| 4 | S3 | Artefactos del modelo ML |
| 5 | ECR | Registry de imagenes Docker |
| 6 | ECS Fargate | Ejecutar los 4 microservicios |
| 7 | ALB | Balanceador de carga / punto de entrada |
| 8 | Cloud Map | Service Discovery (comunicacion interna) |
| 9 | CloudWatch | Logs centralizados |

---

## 2. Requisitos Previos

Antes de empezar, necesitas tener instalado en tu maquina local:

### 2.1 Instalar AWS CLI

**macOS:**
```bash
# Descargar el instalador
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Verificar instalacion
aws --version
# Debe mostrar algo como: aws-cli/2.x.x
```

**Windows:**
```
Descargar desde: https://awscli.amazonaws.com/AWSCLIV2.msi
Ejecutar el instalador y seguir los pasos.
Abrir un nuevo terminal y ejecutar: aws --version
```

### 2.2 Instalar Docker Desktop

Si no lo tienes, descargalo de https://www.docker.com/products/docker-desktop/
Verifica que funciona:
```bash
docker --version
docker compose version
```

### 2.3 Tener Node.js 20+

```bash
node --version   # Debe ser v20.x o superior
npm --version
```

### 2.4 Tener una cuenta de GitHub

Tu repositorio: `https://github.com/the-eagle-eye/air-monitoring-web.git`

### 2.5 Tener una cuenta de Vercel (gratuita)

Regístrate en https://vercel.com con tu cuenta de GitHub.

---

## Paso 1: Crear Cuenta AWS y Configurar CLI

### 1.1 Crear cuenta AWS

1. Ve a https://aws.amazon.com/
2. Click en "Crear una cuenta de AWS"
3. Ingresa tu email, nombre de cuenta
4. Agrega una tarjeta de credito (no te cobran si te mantienes en Free Tier)
5. Selecciona el plan "Basic Support - Free"
6. Espera la verificacion (puede tomar minutos)

### 1.2 Crear un usuario IAM (NO uses root)

> IMPORTANTE: Nunca uses la cuenta root para trabajar. Crea un usuario IAM.

1. Ingresa a la consola AWS: https://console.aws.amazon.com
2. Busca "IAM" en la barra de busqueda
3. En el menu izquierdo, click en "Users" -> "Create user"
4. Nombre de usuario: `airmon-admin`
5. Marca "Provide user access to the AWS Management Console"
6. Selecciona "I want to create an IAM user"
7. Password: genera o crea una password segura
8. Click "Next"
9. En "Set permissions", selecciona "Attach policies directly"
10. Busca y marca estas politicas:
    - `AmazonVPCFullAccess`
    - `AmazonRDSFullAccess`
    - `AmazonECS_FullAccess`
    - `AmazonEC2ContainerRegistryFullAccess`
    - `ElasticLoadBalancingFullAccess`
    - `AmazonS3FullAccess`
    - `SecretsManagerReadWrite`
    - `CloudWatchFullAccess`
    - `AmazonRoute53FullAccess` (opcional, si usas dominio propio)
11. Click "Next" -> "Create user"
12. **GUARDA** las credenciales que se muestran

### 1.3 Crear Access Keys para CLI

1. Dentro de IAM -> Users -> `airmon-admin`
2. Tab "Security credentials"
3. Seccion "Access keys" -> "Create access key"
4. Selecciona "Command Line Interface (CLI)"
5. Marca el checkbox de confirmacion -> "Next"
6. Click "Create access key"
7. **COPIA Y GUARDA** el Access Key ID y Secret Access Key

### 1.4 Configurar AWS CLI en tu terminal

```bash
aws configure
```

Te pedira:
```
AWS Access Key ID [None]: TU_ACCESS_KEY_ID
AWS Secret Access Key [None]: TU_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json
```

> Usaremos la region `us-east-1` (N. Virginia). Es la mas barata y tiene todos los servicios.

### 1.5 Verificar que funciona

```bash
aws sts get-caller-identity
```

Debes ver algo como:
```json
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/airmon-admin"
}
```

**Guarda tu Account ID** (el numero de 12 digitos). Lo usaremos muchas veces.

```bash
# Guardalo como variable de entorno para los siguientes pasos
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
```

---

## Paso 2: Crear la VPC y Redes

La VPC (Virtual Private Cloud) es la red privada donde vivirán todos tus servicios.

### 2.1 Crear la VPC

Abre la consola AWS -> busca "VPC" -> "Create VPC"

**Opcion rapida (recomendada para empezar):**

1. Selecciona "VPC and more" (esto crea todo automaticamente)
2. Configura:
   - Name tag: `airmon`
   - IPv4 CIDR: `10.0.0.0/16`
   - Number of Availability Zones: `2`
   - Number of public subnets: `2`
   - Number of private subnets: `2`
   - NAT gateways: `In 1 AZ` (necesario para que los servicios privados accedan a internet)
   - VPC endpoints: `None`
3. Click "Create VPC"

Esto creara automaticamente:
- 1 VPC
- 2 subnets publicas (para el ALB)
- 2 subnets privadas (para ECS y RDS)
- 1 Internet Gateway
- 1 NAT Gateway
- Route tables configuradas

### 2.2 Anotar los IDs creados

Cuando termine, ve a VPC -> "Your VPCs" y anota:

```bash
# Anota estos valores, los usaremos despues
export VPC_ID="vpc-xxxxxxxxx"

# Ve a VPC -> Subnets y anota los IDs
export PUBLIC_SUBNET_1="subnet-xxxxx"   # airmon-subnet-public1-us-east-1a
export PUBLIC_SUBNET_2="subnet-xxxxx"   # airmon-subnet-public2-us-east-1b
export PRIVATE_SUBNET_1="subnet-xxxxx"  # airmon-subnet-private1-us-east-1a
export PRIVATE_SUBNET_2="subnet-xxxxx"  # airmon-subnet-private2-us-east-1b
```

### 2.3 Crear Security Groups

Necesitamos 3 Security Groups (son como firewalls):

**a) Security Group para el ALB (publico):**

```bash
aws ec2 create-security-group \
  --group-name airmon-alb-sg \
  --description "Security group for ALB" \
  --vpc-id $VPC_ID

# Guardar el ID que devuelve
export ALB_SG="sg-xxxxx"

# Permitir trafico HTTP y HTTPS desde internet
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

**b) Security Group para ECS (backend services):**

```bash
aws ec2 create-security-group \
  --group-name airmon-ecs-sg \
  --description "Security group for ECS tasks" \
  --vpc-id $VPC_ID

export ECS_SG="sg-xxxxx"

# Permitir trafico desde el ALB en los puertos de nuestros servicios
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp --port 8000 --source-group $ALB_SG

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp --port 8001 --source-group $ALB_SG

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp --port 8002 --source-group $ALB_SG

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp --port 8003 --source-group $ALB_SG

# Permitir trafico entre los propios servicios ECS (comunicacion interna)
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp --port 8000-8003 --source-group $ECS_SG
```

**c) Security Group para RDS (base de datos):**

```bash
aws ec2 create-security-group \
  --group-name airmon-rds-sg \
  --description "Security group for RDS" \
  --vpc-id $VPC_ID

export RDS_SG="sg-xxxxx"

# Solo permitir trafico desde ECS en el puerto de PostgreSQL
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG \
  --protocol tcp --port 5432 --source-group $ECS_SG
```

---

## Paso 3: Crear la Base de Datos RDS PostgreSQL

### 3.1 Crear un Subnet Group para RDS

RDS necesita un grupo de subnets (minimo 2 en diferentes AZs):

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name airmon-db-subnet \
  --db-subnet-group-description "Subnets for Air Monitoring RDS" \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2
```

### 3.2 Crear la instancia RDS

```bash
aws rds create-db-instance \
  --db-instance-identifier airmon-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version "15" \
  --master-username airmon \
  --master-user-password "$DB_MASTER_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --db-name airmonitoring \
  --vpc-security-group-ids $RDS_SG \
  --db-subnet-group-name airmon-db-subnet \
  --no-publicly-accessible \
  --backup-retention-period 7 \
  --port 5432 \
  --tags Key=Project,Value=air-monitoring
```

> IMPORTANTE: Define primero una password segura en una variable de entorno, p.ej.
> `export DB_MASTER_PASSWORD="$(openssl rand -base64 24)"`. Nunca la escribas en texto
> plano en el comando ni la commitees al repositorio.

### 3.3 Esperar a que este disponible

Esto tarda entre 5-10 minutos:

```bash
aws rds wait db-instance-available --db-instance-identifier airmon-db
echo "RDS lista!"
```

### 3.4 Obtener el endpoint de la base de datos

```bash
aws rds describe-db-instances \
  --db-instance-identifier airmon-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

Veras algo como: `airmon-db.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com`

```bash
export RDS_ENDPOINT="airmon-db.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com"
export DATABASE_URL="postgresql://airmon:${DB_MASTER_PASSWORD}@${RDS_ENDPOINT}:5432/airmonitoring"

echo "DATABASE_URL: $DATABASE_URL"
```

---

## Paso 4: Almacenar Secretos en AWS Secrets Manager

Guardaremos las credenciales de forma segura para que ECS las inyecte como variables de entorno.

```bash
aws secretsmanager create-secret \
  --name airmon/database-url \
  --description "PostgreSQL connection string" \
  --secret-string "$DATABASE_URL"

aws secretsmanager create-secret \
  --name airmon/secret-key \
  --description "JWT Secret Key for API Gateway" \
  --secret-string "$(openssl rand -hex 32)"
```

> **Nota sobre variables de autenticacion:** Las variables `ACCESS_TOKEN_EXPIRE_MINUTES` y
> `REFRESH_TOKEN_EXPIRE_DAYS` NO necesitan estar en Secrets Manager. Son valores de configuracion
> normales (no sensibles) y se configuran como `environment` en las task definitions de ECS
> (ver Paso 8.4). Solo `SECRET_KEY` y `DATABASE_URL` son secretos.

Anota los ARNs que devuelve cada comando:
```bash
export SECRET_DB_ARN="arn:aws:secretsmanager:us-east-1:${AWS_ACCOUNT_ID}:secret:airmon/database-url-xxxxx"
export SECRET_KEY_ARN="arn:aws:secretsmanager:us-east-1:${AWS_ACCOUNT_ID}:secret:airmon/secret-key-xxxxx"
```

---

## Paso 5: Subir Artefactos ML a S3

### 5.1 Crear el bucket

```bash
aws s3 mb s3://airmon-ml-artifacts-${AWS_ACCOUNT_ID} --region $AWS_REGION

# Habilitar versionado (para rollback de modelos)
aws s3api put-bucket-versioning \
  --bucket airmon-ml-artifacts-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled
```

### 5.2 Subir los artefactos actuales

Desde la raiz de tu proyecto:
```bash
aws s3 sync services/ml-service/ml_artifacts/ \
  s3://airmon-ml-artifacts-${AWS_ACCOUNT_ID}/ml_artifacts/ \
  --exclude ".gitkeep"
```

### 5.3 Verificar

```bash
aws s3 ls s3://airmon-ml-artifacts-${AWS_ACCOUNT_ID}/ml_artifacts/
```

Debes ver:
```
feature_names.json
model_metadata.json
scaler.pkl
```

---

## Paso 6: Crear Repositorios en ECR

ECR (Elastic Container Registry) es donde guardaremos las imagenes Docker de cada servicio.

### 6.1 Crear un repositorio por servicio

```bash
for service in api-gateway iot-service ml-service ops-service; do
  aws ecr create-repository \
    --repository-name airmon/${service} \
    --image-scanning-configuration scanOnPush=true \
    --region $AWS_REGION
  echo "Creado: airmon/${service}"
done
```

### 6.2 Obtener la URL del registry

```bash
export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
echo "ECR Registry: $ECR_REGISTRY"
```

---

## Paso 7: Construir y Subir Imagenes Docker a ECR

### 7.1 Login en ECR

```bash
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY
```

Debe responder: `Login Succeeded`

### 7.2 Modificar Dockerfiles para produccion

Antes de construir, necesitamos hacer cambios menores en los Dockerfiles.
Los Dockerfiles actuales usan `--reload` (modo desarrollo). Para produccion debemos quitarlo.

**No modifiques los Dockerfiles originales**. Crea versiones de produccion:

Crea el archivo `services/api-gateway/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/api-gateway/app/ /app/app/

ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Crea el archivo `services/iot-service/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY services/iot-service/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/iot-service/app/ /app/app/
COPY services/iot-service/migrations/ /app/migrations/
COPY services/iot-service/alembic.ini /app/alembic.ini

ENV PYTHONPATH="/app"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2"]
```

Crea el archivo `services/ml-service/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY services/ml-service/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/ml-service/app/ /app/app/
COPY services/ml-service/ml_artifacts/ /app/ml_artifacts/
COPY services/ml-service/migrations/ /app/migrations/
COPY services/ml-service/alembic.ini /app/alembic.ini

ENV PYTHONPATH="/app"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 2"]
```

Crea el archivo `services/ops-service/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY services/ops-service/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=3 -r requirements.txt

COPY shared/ /app/shared/
COPY services/ops-service/app/ /app/app/
COPY services/ops-service/migrations/ /app/migrations/
COPY services/ops-service/alembic.ini /app/alembic.ini

ENV PYTHONPATH="/app"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 2"]
```

### 7.3 Construir las imagenes

Desde la raiz del proyecto (`air_monitoring_project/`):

```bash
# api-gateway
docker build -f services/api-gateway/Dockerfile.prod -t airmon/api-gateway:latest .

# iot-service
docker build -f services/iot-service/Dockerfile.prod -t airmon/iot-service:latest .

# ml-service
docker build -f services/ml-service/Dockerfile.prod -t airmon/ml-service:latest .

# ops-service
docker build -f services/ops-service/Dockerfile.prod -t airmon/ops-service:latest .
```

### 7.4 Etiquetar y subir a ECR

```bash
for service in api-gateway iot-service ml-service ops-service; do
  # Etiquetar con la URL de ECR
  docker tag airmon/${service}:latest ${ECR_REGISTRY}/airmon/${service}:latest

  # Subir a ECR
  docker push ${ECR_REGISTRY}/airmon/${service}:latest

  echo "Subido: ${service}"
done
```

Cada push tarda 1-3 minutos dependiendo del tamano.

### 7.5 Verificar en ECR

```bash
for service in api-gateway iot-service ml-service ops-service; do
  echo "--- ${service} ---"
  aws ecr describe-images \
    --repository-name airmon/${service} \
    --query 'imageDetails[0].{tag:imageTags[0],size:imageSizeInBytes,pushed:imagePushedAt}' \
    --output table
done
```

---

## Paso 8: Crear el Cluster ECS y Task Definitions

### 8.1 Crear el Cluster ECS

```bash
aws ecs create-cluster \
  --cluster-name airmon-cluster \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1
```

### 8.2 Crear el IAM Role para las tasks de ECS

ECS necesita un rol para ejecutar las tareas (pull images, leer secrets, escribir logs):

**a) Crear el Execution Role (para que ECS pueda arrancar las tasks):**

```bash
# Crear el rol
aws iam create-role \
  --role-name airmon-ecs-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Adjuntar la politica base de ECS
aws iam attach-role-policy \
  --role-name airmon-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Adjuntar acceso a Secrets Manager
aws iam put-role-policy \
  --role-name airmon-ecs-execution-role \
  --policy-name SecretsAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:airmon/*"
    }]
  }'
```

**b) Crear el Task Role (para que los containers accedan a S3):**

```bash
aws iam create-role \
  --role-name airmon-ecs-task-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Dar acceso a S3 (para ml-service)
aws iam put-role-policy \
  --role-name airmon-ecs-task-role \
  --policy-name S3ArtifactsAccess \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:GetObject\", \"s3:ListBucket\"],
      \"Resource\": [
        \"arn:aws:s3:::airmon-ml-artifacts-${AWS_ACCOUNT_ID}\",
        \"arn:aws:s3:::airmon-ml-artifacts-${AWS_ACCOUNT_ID}/*\"
      ]
    }]
  }"
```

### 8.3 Crear Log Groups en CloudWatch

```bash
for service in api-gateway iot-service ml-service ops-service; do
  aws logs create-log-group --log-group-name /ecs/airmon/${service}
  echo "Log group creado: /ecs/airmon/${service}"
done
```

### 8.4 Crear las Task Definitions

Cada task definition describe como ejecutar un servicio (imagen, CPU, memoria, variables de entorno, etc.).

**a) Task Definition: api-gateway**

Crea un archivo `task-definitions/api-gateway.json`:
```json
{
  "family": "airmon-api-gateway",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "api-gateway",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/airmon/api-gateway:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "IOT_SERVICE_URL", "value": "http://iot-service.airmon.local:8001"},
        {"name": "ML_SERVICE_URL", "value": "http://ml-service.airmon.local:8002"},
        {"name": "OPS_SERVICE_URL", "value": "http://ops-service.airmon.local:8003"},
        {"name": "ACCESS_TOKEN_EXPIRE_MINUTES", "value": "30"},
        {"name": "REFRESH_TOKEN_EXPIRE_DAYS", "value": "7"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:airmon/database-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:airmon/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/airmon/api-gateway",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**b) Task Definition: iot-service**

Crea `task-definitions/iot-service.json`:
```json
{
  "family": "airmon-iot-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "iot-service",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/airmon/iot-service:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "IOT_SERVICE_URL", "value": "http://iot-service.airmon.local:8001"},
        {"name": "ML_SERVICE_URL", "value": "http://ml-service.airmon.local:8002"},
        {"name": "OPS_SERVICE_URL", "value": "http://ops-service.airmon.local:8003"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:airmon/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/airmon/iot-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\" || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**c) Task Definition: ml-service**

Crea `task-definitions/ml-service.json`:
```json
{
  "family": "airmon-ml-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "ml-service",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/airmon/ml-service:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8002,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ML_ARTIFACTS_PATH", "value": "/app/ml_artifacts"},
        {"name": "IOT_SERVICE_URL", "value": "http://iot-service.airmon.local:8001"},
        {"name": "ML_SERVICE_URL", "value": "http://ml-service.airmon.local:8002"},
        {"name": "OPS_SERVICE_URL", "value": "http://ops-service.airmon.local:8003"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:airmon/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/airmon/ml-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8002/health')\" || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

> Nota: ml-service tiene mas CPU (512) y memoria (1024) porque ejecuta modelos ML.

**d) Task Definition: ops-service**

Crea `task-definitions/ops-service.json`:
```json
{
  "family": "airmon-ops-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/airmon-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "ops-service",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/airmon/ops-service:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8003,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "IOT_SERVICE_URL", "value": "http://iot-service.airmon.local:8001"},
        {"name": "ML_SERVICE_URL", "value": "http://ml-service.airmon.local:8002"},
        {"name": "OPS_SERVICE_URL", "value": "http://ops-service.airmon.local:8003"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:airmon/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/airmon/ops-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8003/health')\" || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### 8.5 Registrar las Task Definitions

> ANTES de ejecutar, reemplaza `ACCOUNT_ID` en todos los archivos JSON:

```bash
# Reemplazar ACCOUNT_ID en todos los task definitions
for file in task-definitions/*.json; do
  sed -i '' "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" "$file"
  echo "Actualizado: $file"
done
```

Luego registra cada task definition:

```bash
for service in api-gateway iot-service ml-service ops-service; do
  aws ecs register-task-definition \
    --cli-input-json file://task-definitions/${service}.json
  echo "Task definition registrada: ${service}"
done
```

---

## Paso 9: Crear el Application Load Balancer (ALB)

El ALB es el punto de entrada publico a tu backend.

### 9.1 Crear el ALB

```bash
aws elbv2 create-load-balancer \
  --name airmon-alb \
  --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application

# Anotar el ARN y DNS name que devuelve
export ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:${AWS_ACCOUNT_ID}:loadbalancer/app/airmon-alb/xxxx"
export ALB_DNS="airmon-alb-xxxx.us-east-1.elb.amazonaws.com"
echo "ALB DNS: $ALB_DNS"
```

### 9.2 Crear Target Groups (uno por servicio)

```bash
# api-gateway (target principal)
aws elbv2 create-target-group \
  --name airmon-tg-api-gateway \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_API_GATEWAY_ARN="arn:aws:elasticloadbalancing:...:targetgroup/airmon-tg-api-gateway/xxxx"

# iot-service
aws elbv2 create-target-group \
  --name airmon-tg-iot-service \
  --protocol HTTP \
  --port 8001 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_IOT_SERVICE_ARN="arn:aws:elasticloadbalancing:...:targetgroup/airmon-tg-iot-service/xxxx"

# ml-service
aws elbv2 create-target-group \
  --name airmon-tg-ml-service \
  --protocol HTTP \
  --port 8002 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_ML_SERVICE_ARN="arn:aws:elasticloadbalancing:...:targetgroup/airmon-tg-ml-service/xxxx"

# ops-service
aws elbv2 create-target-group \
  --name airmon-tg-ops-service \
  --protocol HTTP \
  --port 8003 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_OPS_SERVICE_ARN="arn:aws:elasticloadbalancing:...:targetgroup/airmon-tg-ops-service/xxxx"
```

### 9.3 Crear el Listener HTTP (puerto 80)

```bash
# Listener por defecto -> api-gateway
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_API_GATEWAY_ARN

# Anotar el ARN del listener
export LISTENER_ARN="arn:aws:elasticloadbalancing:...:listener/app/airmon-alb/xxxx/xxxx"
```

### 9.4 Ruteo: Enfoque simplificado (recomendado)

El `api-gateway` ya tiene un **proxy inteligente** integrado que enruta las peticiones
al servicio correcto internamente (via Cloud Map). Por lo tanto, **no necesitas reglas
path-based en el ALB**. Todo el trafico va al api-gateway y este se encarga de:

1. Autenticacion JWT y verificacion de permisos RBAC
2. Reenvio al servicio correcto segun el path:
   - `/api/v1/iot/*` -> iot-service
   - `/api/v1/predictions/*`, `/api/v1/alerts/*` -> ml-service
   - `/api/v1/equipos/*`, `/api/v1/incidencias/*`, `/api/v1/calibraciones/*`, `/api/v1/usuarios/*`, `/api/v1/dashboard/*`, `/api/v1/repuestos/*`, `/api/v1/proveedores/*` -> ops-service
3. Manejo directo de `/api/v1/auth/*` y `/api/v1/dashboard/kpis` (sin proxy)

Con el Listener del paso 9.3 (default -> api-gateway) ya tienes todo lo necesario.

> **Nota:** Si en el futuro necesitas acceso directo a servicios individuales (bypass del gateway),
> puedes agregar reglas path-based al ALB. Pero para produccion, es mejor que todo pase por
> el api-gateway para garantizar autenticacion y autorizacion centralizadas.

### 9.4 (Alternativa) Reglas path-based directas

Solo si necesitas que el ALB enrute directamente a los servicios sin pasar por el api-gateway:

```bash
# Regla: /api/v1/iot/* -> iot-service (prioridad 10)
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 10 \
  --conditions Field=path-pattern,Values='/api/v1/iot/*' \
  --actions Type=forward,TargetGroupArn=$TG_IOT_SERVICE_ARN

# Regla: /api/v1/predictions/* -> ml-service (prioridad 20)
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 20 \
  --conditions Field=path-pattern,Values='/api/v1/predictions/*' \
  --actions Type=forward,TargetGroupArn=$TG_ML_SERVICE_ARN

# Regla: /api/v1/alerts/* -> ml-service (prioridad 21)
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 21 \
  --conditions Field=path-pattern,Values='/api/v1/alerts/*' \
  --actions Type=forward,TargetGroupArn=$TG_ML_SERVICE_ARN

# Reglas ops-service (prioridad 30-36)
for path_priority in "equipos:30" "incidencias:31" "calibraciones:32" "usuarios:33" "repuestos:34" "proveedores:35" "dashboard:36"; do
  path_name=$(echo $path_priority | cut -d: -f1)
  priority=$(echo $path_priority | cut -d: -f2)
  aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority $priority \
    --conditions Field=path-pattern,Values="/api/v1/${path_name}/*" \
    --actions Type=forward,TargetGroupArn=$TG_OPS_SERVICE_ARN
  echo "Regla creada: /api/v1/${path_name}/* -> ops-service (prioridad ${priority})"
done
```

> **ADVERTENCIA:** Si usas ruteo directo, los endpoints NO pasaran por la autenticacion JWT
> del api-gateway. Solo usa esta alternativa si implementas autenticacion en cada servicio individual.

---

## Paso 10: Crear los Servicios ECS

### 10.1 Crear los 4 servicios

```bash
# api-gateway (1 task)
aws ecs create-service \
  --cluster airmon-cluster \
  --service-name api-gateway \
  --task-definition airmon-api-gateway \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_API_GATEWAY_ARN,containerName=api-gateway,containerPort=8000"

# iot-service (1 task)
aws ecs create-service \
  --cluster airmon-cluster \
  --service-name iot-service \
  --task-definition airmon-iot-service \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_IOT_SERVICE_ARN,containerName=iot-service,containerPort=8001"

# ml-service (1 task)
aws ecs create-service \
  --cluster airmon-cluster \
  --service-name ml-service \
  --task-definition airmon-ml-service \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ML_SERVICE_ARN,containerName=ml-service,containerPort=8002"

# ops-service (1 task)
aws ecs create-service \
  --cluster airmon-cluster \
  --service-name ops-service \
  --task-definition airmon-ops-service \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_OPS_SERVICE_ARN,containerName=ops-service,containerPort=8003"
```

### 10.2 Verificar que los servicios estan corriendo

```bash
aws ecs list-services --cluster airmon-cluster --output table
```

Para ver el estado detallado de cada servicio:
```bash
for service in api-gateway iot-service ml-service ops-service; do
  echo "=== ${service} ==="
  aws ecs describe-services \
    --cluster airmon-cluster \
    --services ${service} \
    --query 'services[0].{status:status,running:runningCount,desired:desiredCount,pending:pendingCount}' \
    --output table
done
```

Espera hasta que `runningCount = 1` para todos. Puede tardar 2-5 minutos.

---

## Paso 11: Configurar Service Discovery (Cloud Map)

Cloud Map permite que los servicios se comuniquen entre si usando nombres DNS internos (como en Docker Compose).

### 11.1 Crear el namespace

```bash
aws servicediscovery create-private-dns-namespace \
  --name airmon.local \
  --vpc $VPC_ID \
  --description "Air Monitoring internal service discovery"

# Anotar el ID del namespace
export NAMESPACE_ID="ns-xxxxxxxxxxxxx"
```

### 11.2 Registrar cada servicio

```bash
for entry in "iot-service:8001" "ml-service:8002" "ops-service:8003"; do
  service_name=$(echo $entry | cut -d: -f1)
  port=$(echo $entry | cut -d: -f2)

  aws servicediscovery create-service \
    --name ${service_name} \
    --namespace-id $NAMESPACE_ID \
    --dns-config "NamespaceId=${NAMESPACE_ID},DnsRecords=[{Type=A,TTL=10}]" \
    --health-check-custom-config FailureThreshold=1

  echo "Registrado: ${service_name}.airmon.local"
done
```

### 11.3 Actualizar servicios ECS para registrar en Cloud Map

Necesitas actualizar cada servicio ECS para que registre su IP en Cloud Map. Esto se hace en la consola de AWS:

1. Ve a ECS -> Clusters -> `airmon-cluster`
2. Click en el servicio (ej: `iot-service`)
3. Click "Update service"
4. En "Service discovery", selecciona el namespace `airmon.local` y el servicio correspondiente
5. Click "Update"

Repite para `ml-service` y `ops-service`.

Ahora el `api-gateway` puede comunicarse con los otros servicios usando:
- `http://iot-service.airmon.local:8001`
- `http://ml-service.airmon.local:8002`
- `http://ops-service.airmon.local:8003`

Que es exactamente lo que configuramos en las task definitions (Paso 8.4).

---

## Paso 12: Ejecutar Migraciones de Base de Datos

Las migraciones se ejecutan automaticamente en los CMD de los Dockerfiles (`alembic upgrade head`).
Cada servicio tiene sus propias migraciones y una tabla de version independiente:

| Servicio | Tabla de version | Migraciones | Que crea |
|----------|-----------------|-------------|----------|
| iot-service | `alembic_version_iot` | `001`, `002` | Tablas `equipos` y `lecturas_iot` + 3 equipos seed + campos expandidos |
| ml-service | `alembic_version_ml` | `ml_001` | Tablas `predicciones` y `alertas` |
| ops-service | `alembic_version_ops` | `ops_001`, `ops_002` | 8 tablas (usuarios, incidencias, calibraciones, etc.) + seed data extenso + password hashes |

### 12.0 Orden de arranque recomendado

> **IMPORTANTE:** El `api-gateway` depende de `ops-service` para autenticacion (consulta
> la tabla `usuarios` via HTTP). Por lo tanto, el orden de arranque debe ser:
>
> 1. **iot-service** y **ml-service** y **ops-service** (pueden arrancar en paralelo)
> 2. **api-gateway** (debe arrancar despues de que ops-service este healthy)
>
> En ECS, esto se maneja con los health checks. El api-gateway seguira intentando
> conectar a ops-service hasta que este disponible. No fallara, pero el login no
> funcionara hasta que ops-service este corriendo.

### 12.0.1 Usuarios seed (credenciales iniciales)

La migracion `ops_001` + `ops_002` crea 3 usuarios con passwords hasheados (bcrypt):

| Email | Password | Rol | Permisos |
|-------|----------|-----|----------|
| `admin@oefa.gob.pe` | `admin123` | administrador | Acceso total (incluido CRUD usuarios) |
| `tecnico1@oefa.gob.pe` | `tecnico123` | tecnico | Lectura total + escritura en incidencias, calibraciones, equipos |
| `coordinador1@oefa.gob.pe` | `coord123` | coordinador | Solo lectura |

> **IMPORTANTE para produccion:** Cambiar estas passwords inmediatamente despues del primer
> deploy. Usa el endpoint `PUT /api/v1/usuarios/{id}` o actualiza directamente en la BD.

### 12.1 Opcion A: Ya se ejecutaron al iniciar los servicios

Si los servicios arrancaron correctamente (runningCount = 1), las migraciones ya se ejecutaron.
Puedes verificar en los logs:

```bash
# Ver logs del iot-service
aws logs get-log-events \
  --log-group-name /ecs/airmon/iot-service \
  --log-stream-name $(aws logs describe-log-streams \
    --log-group-name /ecs/airmon/iot-service \
    --order-by LastEventTime \
    --descending \
    --limit 1 \
    --query 'logStreams[0].logStreamName' \
    --output text) \
  --limit 20 \
  --query 'events[*].message' \
  --output text
```

### 12.2 Opcion B: Ejecutar manualmente con ECS Run Task

```bash
aws ecs run-task \
  --cluster airmon-cluster \
  --task-definition airmon-iot-service \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_1],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --overrides '{
    "containerOverrides": [{
      "name": "iot-service",
      "command": ["sh", "-c", "alembic upgrade head"]
    }]
  }'
```

---

## Paso 13: Desplegar el Frontend en Vercel

### 13.1 Crear cuenta en Vercel

1. Ve a https://vercel.com
2. Click "Sign Up"
3. Selecciona "Continue with GitHub"
4. Autoriza el acceso a tu cuenta de GitHub (`the-eagle-eye`)
5. Completa tu perfil

### 13.2 Importar el proyecto

1. En el dashboard de Vercel, click "Add New..." -> "Project"
2. En "Import Git Repository", busca `air-monitoring-web`
3. Click "Import"

### 13.3 Configurar el proyecto

En la pantalla de configuracion:

| Campo | Valor |
|-------|-------|
| **Project Name** | `air-monitoring` |
| **Framework Preset** | Next.js (se detecta automaticamente) |
| **Root Directory** | `frontend` (IMPORTANTE: click en "Edit" y escribir `frontend`) |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |
| **Install Command** | `npm ci` (default) |

### 13.4 Configurar Variables de Entorno

En la misma pantalla, seccion "Environment Variables", agrega:

| Key | Value | Nota |
|-----|-------|------|
| `NEXT_PUBLIC_API_GATEWAY_URL` | `http://airmon-alb-xxxx.us-east-1.elb.amazonaws.com` | Requerido - auth y proxy principal |
| `NEXT_PUBLIC_IOT_SERVICE_URL` | `http://airmon-alb-xxxx.us-east-1.elb.amazonaws.com` | Mismo ALB DNS |
| `NEXT_PUBLIC_ML_SERVICE_URL` | `http://airmon-alb-xxxx.us-east-1.elb.amazonaws.com` | Mismo ALB DNS |
| `NEXT_PUBLIC_OPS_SERVICE_URL` | `http://airmon-alb-xxxx.us-east-1.elb.amazonaws.com` | Mismo ALB DNS |

> Usa el DNS del ALB que obtuviste en el Paso 9.1 (`$ALB_DNS`).
> Cuando tengas dominio propio con HTTPS, cambialo a `https://api.tudominio.com`.

**IMPORTANTE:** Las 4 variables apuntan al **mismo ALB DNS**. Esto es correcto porque
el `api-gateway` actua como proxy y enruta las peticiones al servicio correcto internamente.
El frontend actual (`frontend/src/lib/api.ts`) referencia las 4 URLs, por eso se deben configurar
todas. Ademas, el api-gateway maneja la autenticacion JWT y RBAC centralizadamente.

### 13.5 Deploy

1. Click "Deploy"
2. Espera a que termine el build (1-3 minutos)
3. Vercel te dara una URL como: `https://air-monitoring-xxxx.vercel.app`

### 13.6 Verificar

Abre la URL que te dio Vercel en tu navegador. Deberias ver tu aplicacion.

### 13.7 Configurar dominio personalizado (opcional)

1. En Vercel -> tu proyecto -> "Settings" -> "Domains"
2. Agrega tu dominio (ej: `airmon.tudominio.com`)
3. Vercel te dara registros DNS para configurar:
   - Si usas un dominio propio: agrega un CNAME apuntando a `cname.vercel-dns.com`
   - Vercel genera el certificado SSL automaticamente

### 13.8 Deploys automaticos

Vercel ya esta configurado para hacer deploy automatico cada vez que hagas push a `main`.

- Push a `main` -> Deploy a produccion
- Push a otra rama / PR -> Deploy de preview (URL temporal)

No necesitas configurar nada mas. Cada PR tendra su propia URL de preview.

---

## Paso 14: Configurar CI/CD con GitHub Actions

### 14.1 Agregar secretos a GitHub

Ve a tu repo en GitHub -> Settings -> Secrets and variables -> Actions -> "New repository secret":

| Secret Name | Valor |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Tu Access Key ID del Paso 1.3 |
| `AWS_SECRET_ACCESS_KEY` | Tu Secret Access Key del Paso 1.3 |
| `AWS_REGION` | `us-east-1` |
| `AWS_ACCOUNT_ID` | Tu Account ID de 12 digitos |

### 14.2 Actualizar el workflow de backend CI/CD

Reemplaza el contenido de `.github/workflows/backend-ci.yml` con:

```yaml
name: Backend CI/CD

on:
  push:
    branches: [main, dev, qa]
  pull_request:
    branches: [main, dev, qa]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

jobs:
  # Job 1: Lint y Tests (se ejecuta en todas las ramas)
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api-gateway, iot-service, ml-service, ops-service]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: airmon
          POSTGRES_PASSWORD: airmon123
          POSTGRES_DB: airmonitoring
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd services/${{ matrix.service }}
          pip install -r requirements-dev.txt

      - name: Lint with flake8
        run: |
          cd services/${{ matrix.service }}
          flake8 app/ tests/

      - name: Run tests
        env:
          DATABASE_URL: postgresql://airmon:airmon123@localhost:5432/airmonitoring
          PYTHONPATH: ${{ github.workspace }}:${{ github.workspace }}/services/${{ matrix.service }}
        run: |
          cd services/${{ matrix.service }}
          pytest -v

  # Job 2: Build y Deploy (solo en push a main)
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - service: api-gateway
            ecs_service: api-gateway
            task_family: airmon-api-gateway
          - service: iot-service
            ecs_service: iot-service
            task_family: airmon-iot-service
          - service: ml-service
            ecs_service: ml-service
            task_family: airmon-ml-service
          - service: ops-service
            ecs_service: ops-service
            task_family: airmon-ops-service

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        run: |
          IMAGE_TAG="${{ github.sha }}"
          REPO="${{ env.ECR_REGISTRY }}/airmon/${{ matrix.service }}"

          docker build \
            -f services/${{ matrix.service }}/Dockerfile.prod \
            -t ${REPO}:${IMAGE_TAG} \
            -t ${REPO}:latest \
            .

          docker push ${REPO}:${IMAGE_TAG}
          docker push ${REPO}:latest

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster airmon-cluster \
            --service ${{ matrix.ecs_service }} \
            --force-new-deployment

          echo "Deployment iniciado para ${{ matrix.service }}"
```

### 14.3 Flujo resultante

```
Developer hace push a main
  |
  +--> GitHub Actions:
  |      1. Lint (flake8)
  |      2. Tests (pytest)
  |      3. Build Docker image
  |      4. Push a ECR
  |      5. Update ECS service (rolling deployment)
  |
  +--> Vercel (automatico):
         1. Build Next.js
         2. Deploy a CDN global
```

---

## Paso 15: Verificacion Final

### 15.1 Verificar el backend (health checks)

```bash
# Health check del API Gateway a traves del ALB
curl http://${ALB_DNS}/health

# Respuesta esperada:
# {
#   "status": "ok",
#   "service": "api-gateway",
#   "services": {
#     "iot-service": "ok",
#     "ml-service": "ok",
#     "ops-service": "ok"
#   }
# }
```

### 15.2 Verificar autenticacion

```bash
# 1. Probar login con usuario administrador
curl -s -X POST http://${ALB_DNS}/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@oefa.gob.pe","password":"admin123"}'

# Respuesta esperada:
# {
#   "access_token": "eyJhbG...",
#   "refresh_token": "eyJhbG...",
#   "token_type": "bearer",
#   "usuario": {"id": 1, "email": "admin@oefa.gob.pe", "rol": "administrador", ...}
# }

# 2. Guardar el token y probar endpoint protegido
TOKEN=$(curl -s -X POST http://${ALB_DNS}/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@oefa.gob.pe","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtenido: ${TOKEN:0:20}..."

# 3. Probar acceso a endpoint protegido (dashboard KPIs)
curl -s -H "Authorization: Bearer $TOKEN" http://${ALB_DNS}/api/v1/dashboard/kpis

# 4. Probar acceso a equipos IoT (protegido)
curl -s -H "Authorization: Bearer $TOKEN" http://${ALB_DNS}/api/v1/iot/equipos

# 5. Verificar que sin token da 401
curl -s http://${ALB_DNS}/api/v1/iot/equipos
# Respuesta esperada: {"detail": "No autenticado"}

# 6. Verificar RBAC (coordinador no puede crear usuarios)
TOKEN_COORD=$(curl -s -X POST http://${ALB_DNS}/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"coordinador1@oefa.gob.pe","password":"coord123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST -H "Authorization: Bearer $TOKEN_COORD" \
  -H "Content-Type: application/json" \
  http://${ALB_DNS}/api/v1/usuarios \
  -d '{"email":"test@test.com","nombre":"Test","apellido":"User","rol":"tecnico","password":"test123"}'
# Respuesta esperada: {"detail": "No tiene permisos para esta accion"} (403)

# 7. Verificar que IoT readings son publicas (no requieren auth)
curl -s -X POST http://${ALB_DNS}/api/v1/iot/readings \
  -H "Content-Type: application/json" \
  -d '{"equipo":"T101","SO2_ppb":25.0,"H2S_ppb":2.0,"Reaction_Temp":35.0,"IZS_Temp":34.0,"PMT_Temp":36.0,"SampleFlow":452.0,"Pressure":29.7,"UVLampIntensity":403.0,"Box_Temp":33.7,"HVPS_V":671.0,"Conv_Temp":35.9,"Ozone_flow":480.0,"timestamp":"2026-03-15 12:00:00"}'
# Debe retornar 200/201 sin necesidad de token
```

### 15.3 Verificar el frontend

1. Abre la URL de Vercel en tu navegador
2. Deberias ser redirigido automaticamente a `/login`
3. Inicia sesion con `admin@oefa.gob.pe` / `admin123`
4. Verifica que el dashboard carga datos y KPIs
5. Navega a Equipos, Lecturas, Predicciones, Alertas
6. Navega a Operaciones -> Incidencias y Calibraciones
7. Verifica que el boton "Salir" cierra la sesion y redirige a login

### 15.4 Verificar los logs

```bash
# Ver logs en tiempo real de cualquier servicio
aws logs tail /ecs/airmon/api-gateway --follow
aws logs tail /ecs/airmon/iot-service --follow
aws logs tail /ecs/airmon/ml-service --follow
aws logs tail /ecs/airmon/ops-service --follow
```

### 15.5 Checklist final

**Infraestructura:**
- [ ] AWS CLI configurado y funcionando
- [ ] VPC con subnets publicas y privadas creada
- [ ] Security Groups creados (ALB, ECS, RDS)
- [ ] RDS PostgreSQL corriendo y accesible desde ECS
- [ ] Secretos almacenados en Secrets Manager (DATABASE_URL + SECRET_KEY)
- [ ] Artefactos ML subidos a S3

**Contenedores:**
- [ ] 4 repositorios ECR creados con imagenes
- [ ] Cluster ECS creado
- [ ] 4 Task Definitions registradas (api-gateway con env vars de auth)
- [ ] ALB creado con listener default -> api-gateway
- [ ] 4 servicios ECS corriendo (runningCount = 1)
- [ ] Service Discovery configurado (Cloud Map)

**Base de datos:**
- [ ] Migraciones iot-service ejecutadas (equipos + lecturas_iot)
- [ ] Migraciones ml-service ejecutadas (predicciones + alertas)
- [ ] Migraciones ops-service ejecutadas (8 tablas + seed data + password hashes)

**Autenticacion:**
- [ ] Login con admin@oefa.gob.pe funciona y devuelve tokens JWT
- [ ] Token JWT permite acceso a endpoints protegidos
- [ ] RBAC bloquea escritura para coordinador (403)
- [ ] POST /api/v1/iot/readings funciona sin token (ruta publica)
- [ ] SECRET_KEY es consistente (mismo valor en Secrets Manager)

**Frontend:**
- [ ] Frontend desplegado en Vercel
- [ ] 4 variables NEXT_PUBLIC_* apuntan al ALB DNS
- [ ] Frontend redirige a /login si no hay token
- [ ] Login funciona y redirige al dashboard
- [ ] Navegacion completa: Dashboard, Equipos, Lecturas, Predicciones, Alertas, Incidencias, Calibraciones

**CI/CD:**
- [ ] CI/CD configurado en GitHub Actions
- [ ] Push a main ejecuta: lint -> test -> build -> push ECR -> deploy ECS
- [ ] Health check de todos los servicios responde OK

---

## Costos Estimados

### AWS (mensual)

| Servicio | Detalle | Costo estimado |
|----------|---------|----------------|
| RDS PostgreSQL | db.t3.micro, 20GB (Free Tier 12 meses) | $0 (luego ~$15) |
| ECS Fargate | 4 tasks (0.25vCPU + 0.5GB cada una, ml con 0.5+1GB) | ~$20-30 |
| ALB | 1 load balancer + LCUs | ~$16 + trafico |
| NAT Gateway | 1 en 1 AZ | ~$32 + trafico |
| ECR | Storage de imagenes (~2GB) | ~$0.20 |
| S3 | Artefactos ML (~100MB) | < $0.10 |
| CloudWatch | Logs (5GB Free Tier) | $0 |
| Secrets Manager | 2 secretos x $0.40 | $0.80 |
| **Total AWS** | | **~$70-80/mes** |

> **Tip para reducir costos**: El NAT Gateway es el componente mas caro (~$32/mes).
> Alternativa mas barata: usar `assignPublicIp=ENABLED` en las tasks de ECS y colocarlas
> en subnets publicas (elimina la necesidad del NAT Gateway). Reduce el costo a ~$40/mes.
> Es menos seguro pero aceptable para un proyecto academico.

### Vercel (mensual)

| Plan | Costo |
|------|-------|
| Hobby (Free) | $0 |
| Incluye | 100GB bandwidth, builds ilimitados, SSL, preview deploys |

### Total: ~$70-80/mes (AWS) + $0 (Vercel) = ~$70-80/mes

---

## Troubleshooting

### Problema: ECS task falla al iniciar (STOPPED)

```bash
# Ver la razon del fallo
aws ecs describe-tasks \
  --cluster airmon-cluster \
  --tasks $(aws ecs list-tasks --cluster airmon-cluster --service-name api-gateway --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{status:lastStatus,reason:stoppedReason,container:containers[0].reason}'
```

**Causas comunes:**
- `CannotPullContainerError` -> La imagen no existe en ECR. Verificar el push.
- `ResourceNotFoundException` -> El secreto no existe en Secrets Manager.
- `Essential container exited` -> Error en la aplicacion. Ver logs en CloudWatch.

### Problema: No puedo conectar a RDS desde ECS

1. Verificar que el Security Group de RDS permite trafico desde el SG de ECS
2. Verificar que las subnets de ECS y RDS estan en la misma VPC
3. Verificar el DATABASE_URL en Secrets Manager

### Problema: Los servicios no se comunican entre si

1. Verificar Cloud Map: los servicios deben resolverse por `nombre.airmon.local`
2. Verificar Security Group de ECS: debe permitir trafico en puertos 8000-8003 desde si mismo
3. Probar desde dentro de un container:
```bash
# Ejecutar una task temporal para debug
aws ecs run-task \
  --cluster airmon-cluster \
  --task-definition airmon-api-gateway \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"api-gateway","command":["sh","-c","pip install httpie && http http://iot-service.airmon.local:8001/health"]}]}'
```

### Problema: Login devuelve 503 (Service Unavailable)

El api-gateway no puede comunicarse con ops-service para validar credenciales.

1. Verificar que ops-service esta corriendo: `aws ecs describe-services --cluster airmon-cluster --services ops-service`
2. Verificar que Cloud Map resuelve `ops-service.airmon.local`
3. Verificar logs de ops-service en CloudWatch (puede haber fallado la migracion)
4. Verificar que el Security Group permite trafico en puerto 8003 entre tasks ECS

### Problema: Login devuelve 401 (Unauthorized)

Credenciales incorrectas o usuario no existe en la base de datos.

1. Verificar que las migraciones `ops_001` y `ops_002` se ejecutaron correctamente
2. Revisar logs de ops-service para confirmar que los INSERT de seed data se ejecutaron
3. Probar acceso directo a ops-service (si tienes conectividad):
   ```bash
   # Desde dentro de la VPC o usando una task temporal
   curl http://ops-service.airmon.local:8003/api/v1/usuarios/by-email/admin@oefa.gob.pe
   ```
4. Si el usuario existe pero el login falla, el password_hash puede estar corrupto. Re-ejecutar migracion `ops_002`.

### Problema: Frontend redirige siempre a /login

1. **SECRET_KEY diferente entre deploys:** Si recreas el api-gateway con un SECRET_KEY diferente, los tokens existentes se invalidan. Asegurate de usar siempre el mismo secreto de Secrets Manager.
2. **Token expirado:** El access_token dura 30 minutos. El frontend deberia hacer refresh automatico, pero si el refresh_token tambien expiro (7 dias), el usuario debe hacer login de nuevo.
3. **Verificar en el navegador:** Abre DevTools (F12) -> Application -> Local Storage. Debe existir `token` y `refresh_token`.

### Problema: Error 403 en operaciones de escritura

El usuario no tiene permisos RBAC para la operacion solicitada.

| Operacion | Roles permitidos |
|-----------|-----------------|
| CRUD usuarios | Solo `administrador` |
| CRUD incidencias | `tecnico`, `administrador` |
| CRUD calibraciones | `tecnico`, `administrador` |
| CRUD equipos | `tecnico`, `administrador` |
| Lectura (GET) | Todos los roles |
| POST /api/v1/iot/readings | Publico (sin auth) |

Solucion: Iniciar sesion con un usuario que tenga el rol adecuado.

### Problema: Frontend no conecta al backend (CORS)

Tu `api-gateway` ya tiene CORS configurado con `allow_origins=["*"]`. Si aun asi falla:
1. Verifica que `NEXT_PUBLIC_API_GATEWAY_URL` apunte al ALB correcto
2. Abre la consola del navegador (F12 -> Network) y verifica la URL de los requests
3. Si usas HTTPS en Vercel pero HTTP en el ALB, el navegador bloqueara las peticiones (mixed content). Solucion: configurar HTTPS en el ALB con un certificado ACM.

### Problema: Vercel build falla

1. Verifica que el "Root Directory" esta configurado como `frontend`
2. Verifica que `npm run build` funciona localmente:
```bash
cd frontend
npm ci
npm run build
```

### Comando util: reiniciar un servicio

```bash
# Forzar nuevo deployment (reinicia las tasks)
aws ecs update-service \
  --cluster airmon-cluster \
  --service api-gateway \
  --force-new-deployment
```

### Comando util: escalar un servicio

```bash
# Escalar a 2 tasks (alta disponibilidad)
aws ecs update-service \
  --cluster airmon-cluster \
  --service api-gateway \
  --desired-count 2
```

### Comando util: ver todos los costos

```bash
# Ver costos del mes actual
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output table
```
