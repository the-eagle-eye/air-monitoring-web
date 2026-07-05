# GUÍA paso a paso — Desplegar en AWS (nivel básico)

Guía práctica, comando por comando, para llevar Air Monitoring a AWS según
`spec-migracion-aws.md` y `plan-implementacion-aws.md`. Pensada para **nivel AWS
básico**: cada sección explica *qué* haces, *por qué*, y *qué aprendes*.

> **Convención:** los bloques ` ```bash ` se ejecutan en tu terminal local; los marcados
> `# [EN LA EC2]` se ejecutan por SSH dentro del servidor. Reemplaza los `<placeholders>`.

**Índice**
0. [Conceptos AWS en 2 minutos](#0-conceptos-aws-en-2-minutos)
1. [Preparar tu máquina](#1-preparar-tu-máquina)
2. [Rotar secretos](#2-rotar-secretos)
3. [Preparar el repo para producción](#3-preparar-el-repo-para-producción)
4. [Terraform: crear la infraestructura](#4-terraform-crear-la-infraestructura)
5. [Subir los artefactos ML a S3](#5-subir-los-artefactos-ml-a-s3)
6. [Desplegar la app en la EC2](#6-desplegar-la-app-en-la-ec2)
7. [Verificar la demo](#7-verificar-la-demo)
8. [HTTPS con dominio (opcional)](#8-https-con-dominio-opcional)
9. [Apagar y recrear (ahorrar dinero)](#9-apagar-y-recrear-ahorrar-dinero)
10. [Troubleshooting](#10-troubleshooting)

---

## 0. Conceptos AWS en 2 minutos

| Término | Qué es | Analogía |
|---|---|---|
| **EC2** | Una máquina virtual (servidor) en la nube | Tu PC, pero remota y encendida 24/7 |
| **RDS** | Base de datos gestionada (PostgreSQL) | Como tu contenedor `db`, pero AWS la administra |
| **S3** | Almacenamiento de archivos | Un Google Drive por API |
| **VPC** | Tu red privada aislada en AWS | El router+LAN de tu casa |
| **Security Group** | Firewall de un recurso | "Qué puertos están abiertos y a quién" |
| **IAM** | Usuarios, roles y permisos | Quién puede hacer qué |
| **SSM Parameter Store** | Guarda secretos cifrados | Un llavero seguro |
| **Terraform** | Describes la infra en archivos `.tf` y AWS la crea | "Infra como código": `apply` crea, `destroy` borra |
| **Elastic IP** | IP pública fija para tu EC2 | Tu dirección pública que no cambia |

**La idea:** Terraform crea una EC2 + RDS + red. La EC2 corre tus contenedores Docker
(igual que en tu laptop). La RDS es la base de datos. Los modelos `.pkl` viajan por S3.

---

## 1. Preparar tu máquina

### 1.1 Instalar AWS CLI v2 (macOS)
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version   # aws-cli/2.x.x
```

### 1.2 Instalar Terraform (macOS, con Homebrew)
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform version   # >= 1.6
```

### 1.3 Crear usuario IAM y configurar el CLI
1. Consola AWS → **IAM** → Users → Create user → nombre `airmon-deployer`.
2. Permisos: para la tesis, adjunta `AdministratorAccess` (simple). *Producción real:
   permisos mínimos, pero para aprender está bien empezar amplio.*
3. En el usuario → Security credentials → **Create access key** → "Command Line
   Interface" → copia el **Access Key ID** y **Secret**.
4. Configura el CLI:
```bash
aws configure
# AWS Access Key ID:     <tu-access-key>
# AWS Secret Access Key: <tu-secret>
# Default region name:   us-east-1
# Default output format:  json

aws sts get-caller-identity   # debe devolver tu Account ID (12 dígitos)
```
> **Aprendes:** cómo AWS autentica desde tu terminal. Guarda tu Account ID:
> `export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)`

### 1.4 Crear una llave SSH para la EC2
```bash
ssh-keygen -t ed25519 -f ~/.ssh/airmon_ec2 -N ""
cat ~/.ssh/airmon_ec2.pub   # esta clave pública va a Terraform
```

---

## 2. Rotar secretos

Los secretos actuales están en el `docker-compose.yml` (inseguro). Genera nuevos y
guárdalos en un archivo local **que nunca commitees**:

```bash
# Genera secretos nuevos
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)"
# SMTP: entra a mailtrap.io y rota/copia las credenciales de tu inbox sandbox
```
Anótalos temporalmente en un `secrets.local.txt` (fuera del repo). Los cargarás en SSM
vía Terraform (§4).

> **Aprendes:** por qué los secretos nunca van en git ni en la imagen Docker.

---

## 3. Preparar el repo para producción

El stack de dev usa bind-mounts y `--reload` (recarga en caliente). En un servidor
necesitas el código *dentro* de la imagen y sin reload. Crea `docker-compose.prod.yml`
en la raíz del repo:

```yaml
# docker-compose.prod.yml — para la EC2 (usa RDS, sin bind-mounts, sin --reload)
services:
  api-gateway:
    build: { context: ., dockerfile: services/api-gateway/Dockerfile }
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - IOT_SERVICE_URL=http://iot-service:8001
      - ML_SERVICE_URL=http://ml-service:8002
      - OPS_SERVICE_URL=http://ops-service:8003
      - ML_BACKEND=legacy
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped

  iot-service:
    build: { context: ., dockerfile: services/iot-service/Dockerfile }
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - IOT_SERVICE_URL=http://iot-service:8001
      - ML_SERVICE_URL=http://ml-service:8002
      - OPS_SERVICE_URL=http://ops-service:8003
    restart: unless-stopped

  ml-service:
    build: { context: ., dockerfile: services/ml-service/Dockerfile }
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 2"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - IOT_SERVICE_URL=http://iot-service:8001
      - ML_SERVICE_URL=http://ml-service:8002
      - OPS_SERVICE_URL=http://ops-service:8003
      - ENSEMBLE_ARTIFACTS_PATH=/app/ml_artifacts_ensemble_v1
    volumes:
      - ./services/ml-service/ml_artifacts_ensemble_v1:/app/ml_artifacts_ensemble_v1
    restart: unless-stopped

  ops-service:
    build: { context: ., dockerfile: services/ops-service/Dockerfile }
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 2"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - IOT_SERVICE_URL=http://iot-service:8001
      - ML_SERVICE_URL=http://ml-service:8002
      - OPS_SERVICE_URL=http://ops-service:8003
      - SMTP_HOST=sandbox.smtp.mailtrap.io
      - SMTP_PORT=2525
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_FROM=noreply@airmonitoring.oefa.gob.pe
      - FRONTEND_URL=${FRONTEND_URL}
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        - NEXT_PUBLIC_API_GATEWAY_URL=${PUBLIC_API_URL}
    ports: ["3000:3000"]
    restart: unless-stopped
```

> **Notas:**
> - No hay servicio `db` — usamos RDS (el `DATABASE_URL` apunta al endpoint de RDS).
> - No hay `ml-service-isolation` (no está en git; `ML_BACKEND=legacy` no lo usa).
> - Los secretos vienen de `${VAR}` — se exportan en la EC2 antes de `up`, nunca se
>   escriben en el archivo.
> - Para el frontend en producción, ajusta su `Dockerfile` a `next build && next start`
>   y acepta `NEXT_PUBLIC_API_GATEWAY_URL` como build arg (hoy usa `next dev`).

Añade a `.gitignore`: `docker-compose.prod.yml` puede ir versionado (usa `${VAR}`), pero
`secrets.local.txt`, `terraform.tfvars` y `*.tfstate` **nunca**.

> **Aprendes:** la diferencia entre una imagen de desarrollo y una de producción.

---

## 4. Terraform: crear la infraestructura

Crea la carpeta `infra/terraform/` y estos archivos. Es la parte que más "cloud" te
enseña: describes lo que quieres y Terraform lo crea.

### 4.1 `variables.tf`
```hcl
variable "region"        { default = "us-east-1" }
variable "instance_type" { default = "t3.small" }   # t3.micro si insistes en free-tier
variable "db_password"   { type = string, sensitive = true }
variable "secret_key"    { type = string, sensitive = true }
variable "smtp_user"     { type = string, sensitive = true }
variable "smtp_password" { type = string, sensitive = true }
variable "ssh_public_key"{ type = string }   # contenido de ~/.ssh/airmon_ec2.pub
variable "my_ip"         { type = string }   # tu IP pública /32 para SSH
```

### 4.2 `main.tf`
```hcl
terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}
provider "aws" { region = var.region }

data "aws_availability_zones" "available" { state = "available" }
```

### 4.3 `network.tf`
```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "airmon-vpc" }
}
resource "aws_internet_gateway" "igw" { vpc_id = aws_vpc.main.id }

resource "aws_subnet" "public" {
  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags = { Name = "airmon-public" }
}
# RDS exige subnets en >= 2 AZ, aunque no sean públicas
resource "aws_subnet" "private_a" {
  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
}
resource "aws_subnet" "private_b" {
  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0", gateway_id = aws_internet_gateway.igw.id }
}
resource "aws_route_table_association" "public" {
  subnet_id = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

### 4.4 `security.tf`
```hcl
resource "aws_security_group" "ec2" {
  name = "airmon-ec2-sg", vpc_id = aws_vpc.main.id
  ingress { from_port=22  to_port=22  protocol="tcp" cidr_blocks=["${var.my_ip}/32"] }
  ingress { from_port=80  to_port=80  protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  ingress { from_port=443 to_port=443 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  ingress { from_port=3000 to_port=3000 protocol="tcp" cidr_blocks=["0.0.0.0/0"] } # frontend (demo)
  ingress { from_port=8000 to_port=8000 protocol="tcp" cidr_blocks=["0.0.0.0/0"] } # gateway (demo)
  egress  { from_port=0 to_port=0 protocol="-1" cidr_blocks=["0.0.0.0/0"] }
}
resource "aws_security_group" "rds" {
  name = "airmon-rds-sg", vpc_id = aws_vpc.main.id
  ingress { from_port=5432 to_port=5432 protocol="tcp" security_groups=[aws_security_group.ec2.id] }
  egress  { from_port=0 to_port=0 protocol="-1" cidr_blocks=["0.0.0.0/0"] }
}
```

### 4.5 `rds.tf`
```hcl
resource "aws_db_subnet_group" "main" {
  name = "airmon-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}
resource "aws_db_instance" "main" {
  identifier = "airmon-db"
  engine = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  storage_type = "gp3"
  db_name = "airmonitoring"
  username = "airmon"
  password = var.db_password
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible = false
  skip_final_snapshot = true
  backup_retention_period = 7
}
```

### 4.6 `s3.tf`
```hcl
resource "aws_s3_bucket" "artifacts" {
  bucket = "airmon-artifacts-${data.aws_caller_identity.current.account_id}"
}
data "aws_caller_identity" "current" {}
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}
```

### 4.7 `ssm.tf` (secretos cifrados)
```hcl
resource "aws_ssm_parameter" "db_password"   { name="/airmon/db_password"   type="SecureString" value=var.db_password }
resource "aws_ssm_parameter" "secret_key"    { name="/airmon/secret_key"    type="SecureString" value=var.secret_key }
resource "aws_ssm_parameter" "smtp_user"     { name="/airmon/smtp_user"     type="SecureString" value=var.smtp_user }
resource "aws_ssm_parameter" "smtp_password" { name="/airmon/smtp_password" type="SecureString" value=var.smtp_password }
```

### 4.8 `ec2.tf` (rol IAM + instancia + user_data que instala Docker)
```hcl
# Rol para que la EC2 lea S3 y SSM sin claves hardcodeadas
resource "aws_iam_role" "ec2" {
  name = "airmon-ec2-role"
  assume_role_policy = jsonencode({
    Version="2012-10-17",
    Statement=[{Effect="Allow", Principal={Service="ec2.amazonaws.com"}, Action="sts:AssumeRole"}]
  })
}
resource "aws_iam_role_policy" "ec2" {
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version="2012-10-17",
    Statement=[
      {Effect="Allow", Action=["s3:GetObject","s3:ListBucket"],
       Resource=[aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]},
      {Effect="Allow", Action=["ssm:GetParameter","ssm:GetParameters","ssm:GetParametersByPath"],
       Resource="arn:aws:ssm:${var.region}:*:parameter/airmon/*"}
    ]
  })
}
resource "aws_iam_instance_profile" "ec2" { name="airmon-ec2-profile" role=aws_iam_role.ec2.name }

resource "aws_key_pair" "main" { key_name="airmon-key" public_key=var.ssh_public_key }

data "aws_ami" "al2023" {
  most_recent = true
  owners = ["amazon"]
  filter { name="name" values=["al2023-ami-*-x86_64"] }
}

resource "aws_instance" "app" {
  ami = data.aws_ami.al2023.id
  instance_type = var.instance_type
  subnet_id = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile = aws_iam_instance_profile.ec2.name
  key_name = aws_key_pair.main.key_name
  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y docker git
    systemctl enable --now docker
    usermod -aG docker ec2-user
    # docker compose v2 plugin
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -sL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  EOF
  tags = { Name = "airmon-app" }
}
resource "aws_eip" "app" { instance = aws_instance.app.id }
```

### 4.9 `outputs.tf`
```hcl
output "ec2_public_ip" { value = aws_eip.app.public_ip }
output "rds_endpoint"  { value = aws_db_instance.main.address }
output "s3_bucket"     { value = aws_s3_bucket.artifacts.bucket }
```

### 4.10 Aplicar
```bash
cd infra/terraform

# terraform.tfvars (NO commitear — contiene secretos)
cat > terraform.tfvars <<EOF
db_password    = "<tu-db-password>"
secret_key     = "<tu-secret-key>"
smtp_user      = "<mailtrap-user>"
smtp_password  = "<mailtrap-password>"
ssh_public_key = "$(cat ~/.ssh/airmon_ec2.pub)"
my_ip          = "$(curl -s ifconfig.me)"
EOF

terraform init      # descarga el provider aws
terraform plan      # muestra QUÉ va a crear (revísalo)
terraform apply     # escribe 'yes' — tarda ~5-10 min (RDS es lo lento)

terraform output    # anota ec2_public_ip, rds_endpoint, s3_bucket
```

> **Aprendes:** el ciclo `init → plan → apply` de Terraform, y cómo un rol IAM permite
> que la EC2 lea S3/SSM sin claves. Guarda los outputs:
> ```bash
> export EC2_IP=$(terraform output -raw ec2_public_ip)
> export RDS_HOST=$(terraform output -raw rds_endpoint)
> export S3_BUCKET=$(terraform output -raw s3_bucket)
> ```

---

## 5. Subir los artefactos ML a S3

Los 15 `.pkl` del ensemble **no están en git** (gitignored). Súbelos a S3:

```bash
# desde la raíz del repo, en tu máquina local
aws s3 sync services/ml-service/ml_artifacts_ensemble_v1/ s3://$S3_BUCKET/ensemble/
aws s3 ls s3://$S3_BUCKET/ensemble/    # debes ver 15 .pkl + 6 .json
```

> **Aprendes:** por qué hay archivos que el repo no versiona (binarios pesados) y cómo
> S3 resuelve ese "hueco" en el despliegue.

---

## 6. Desplegar la app en la EC2

### 6.1 Entrar por SSH
```bash
ssh -i ~/.ssh/airmon_ec2 ec2-user@$EC2_IP
```

### 6.2 [EN LA EC2] Clonar el repo y bajar los artefactos
```bash
# [EN LA EC2]
git clone https://github.com/the-eagle-eye/air-monitoring-web.git
cd air-monitoring-web

# descargar los .pkl desde S3 (el rol IAM ya da permiso, sin claves)
aws s3 sync s3://<TU_BUCKET>/ensemble/ services/ml-service/ml_artifacts_ensemble_v1/
ls services/ml-service/ml_artifacts_ensemble_v1/   # 21 archivos
```

### 6.3 [EN LA EC2] Cargar secretos desde SSM como variables de entorno
```bash
# [EN LA EC2]
export DB_PASSWORD=$(aws ssm get-parameter --name /airmon/db_password --with-decryption --query Parameter.Value --output text)
export SECRET_KEY=$(aws ssm get-parameter --name /airmon/secret_key --with-decryption --query Parameter.Value --output text)
export SMTP_USER=$(aws ssm get-parameter --name /airmon/smtp_user --with-decryption --query Parameter.Value --output text)
export SMTP_PASSWORD=$(aws ssm get-parameter --name /airmon/smtp_password --with-decryption --query Parameter.Value --output text)

# construir DATABASE_URL apuntando a RDS
export RDS_HOST="<rds_endpoint de terraform output>"
export DATABASE_URL="postgresql://airmon:${DB_PASSWORD}@${RDS_HOST}:5432/airmonitoring"
export FRONTEND_URL="http://${EC2_IP}:3000"      # o tu dominio
export PUBLIC_API_URL="http://${EC2_IP}:8000"    # el frontend llamará aquí
```

### 6.4 [EN LA EC2] Levantar el stack
```bash
# [EN LA EC2]
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps    # los 5 servicios 'Up'
docker compose -f docker-compose.prod.yml logs -f ml-service   # ver que carga los .pkl
```

Las migraciones alembic corren solas al arrancar cada servicio (crean tablas + seed).

> **Aprendes:** que tu `docker-compose` corre igual en la nube que en tu laptop; lo único
> distinto es de dónde vienen la BD (RDS) y los secretos (SSM).

---

## 7. Verificar la demo

```bash
# desde tu máquina
open http://$EC2_IP:3000            # carga el frontend
```
1. **Login** `admin@oefa.gob.pe / admin123` → entra al dashboard (prueba
   frontend→gateway→ops).
2. **Enviar una lectura IoT** (dispara el ensemble):
```bash
curl -X POST http://$EC2_IP:8000/api/v1/iot/readings \
  -H "Content-Type: application/json" \
  -d '{"equipo":"T101","SO2_ppb":4.0,"SampleFlow":0.45,"Reaction_Temp":31,"UVLampIntensity":102}'
```
3. **Dashboard** → el equipo muestra estado de salud (cadena iot→ml→ops).
4. **Mailtrap** → si se genera una incidencia, revisa tu inbox sandbox.

Si todo responde, la migración está **completa** (criterios del spec §10).

---

## 8. HTTPS con dominio (opcional, recomendado para la defensa)

La forma más simple sin pagar dominio:

1. **DuckDNS** (gratis): crea `airmon-tesis.duckdns.org` → apúntalo a `$EC2_IP`.
2. Añade un servicio **Caddy** al `docker-compose.prod.yml`:
```yaml
  caddy:
    image: caddy:2
    ports: ["80:80","443:443"]
    volumes: ["./Caddyfile:/etc/caddy/Caddyfile", "caddy_data:/data"]
    restart: unless-stopped
```
3. `Caddyfile`:
```
airmon-tesis.duckdns.org {
    handle /api/* { reverse_proxy api-gateway:8000 }
    handle       { reverse_proxy frontend:3000 }
}
```
4. Reconstruye el frontend con `PUBLIC_API_URL=https://airmon-tesis.duckdns.org/api` (mismo
   origen → sin CORS). Caddy obtiene el certificado HTTPS automáticamente.

> **Aprendes:** qué es un reverse-proxy y cómo se obtiene HTTPS gratis (Let's Encrypt).

---

## 9. Apagar y recrear (ahorrar dinero)

**Para no gastar entre demos** (recomendado para la tesis):

```bash
# Opción A: apagar (conserva datos, sigues pagando disco/EIP mínimos)
aws ec2 stop-instances --instance-ids <id>
aws rds stop-db-instance --db-instance-identifier airmon-db

# Opción B: destruir TODO (costo ~$0; recrear tarda ~10 min)
cd infra/terraform
terraform destroy    # escribe 'yes'
```

Para recrear: `terraform apply` + repetir §5-6. Si quieres conservar la BD antes de
destruir: `aws rds create-db-snapshot --db-instance-identifier airmon-db --db-snapshot-identifier airmon-snap`.

> **Aprendes:** el mayor beneficio de IaC — la infra es desechable y reproducible.

---

## 10. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `docker compose up` falla en ml-service: "artifacts not found" | Los `.pkl` no se bajaron | Reejecuta el `aws s3 sync` de §6.2; verifica 21 archivos |
| ml-service se reinicia / OOM | `t3.micro` sin RAM (2 imágenes ML) | Sube a `t3.small` (cambia `instance_type` y `terraform apply`), o añade swap |
| Login falla ("connection refused" a ops) | ops-service aún migrando o caído | `docker compose logs ops-service`; el gateway reintenta al conectar |
| Frontend carga pero las llamadas API fallan (CORS/refused) | `NEXT_PUBLIC_API_GATEWAY_URL` mal (apunta a localhost) | Reconstruye frontend con `PUBLIC_API_URL=http://$EC2_IP:8000` (o `/api` con Caddy) |
| No conecta a RDS | Security group o `DATABASE_URL` mal | Verifica que el SG de RDS permite 5432 desde el SG de la EC2; revisa el endpoint |
| `terraform apply` error de permisos | Usuario IAM sin permisos | Adjunta `AdministratorAccess` al usuario (tesis) |
| SSH "permission denied" | Llave o IP mal | Usa `-i ~/.ssh/airmon_ec2`; verifica que `my_ip` en tfvars es tu IP actual |
| Migraciones se pisan al arrancar | Race de DDL concurrente | Levanta primero un servicio, espera, luego el resto; o usa un contenedor `migrate` de un solo uso |

---

## Resumen del flujo completo

```
1. aws configure + ssh-keygen           (tu máquina lista)
2. rotar secretos                        (nuevos SECRET_KEY, DB pw)
3. docker-compose.prod.yml               (repo listo para servidor)
4. terraform init/plan/apply             (infra creada: EC2+RDS+S3+red)
5. aws s3 sync ...ensemble_v1            (modelos .pkl a S3)
6. ssh → clonar → bajar .pkl → up -d     (app corriendo)
7. login + lectura IoT + Mailtrap        (demo verificada)
8. Caddy + DuckDNS                        (HTTPS, opcional)
9. terraform destroy entre demos          (costo ~$0)
```

Con esto tienes el sistema en AWS, reproducible y barato — y entiendes cada pieza.
