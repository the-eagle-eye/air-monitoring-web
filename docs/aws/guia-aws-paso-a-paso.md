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

El stack de dev usa bind-mounts y `--reload` (recarga en caliente). Producción usa
artefactos separados **que ya están versionados en el repo** — no hay que crearlos a mano:

| Archivo | Qué es |
|---|---|
| `docker-compose.prod.yml` (raíz) | Compose de producción: sin `db` (usa RDS), sin `ml-service-isolation`, sin bind-mounts de código, `--workers` en vez de `--reload`, `restart: unless-stopped`, secretos por `${VAR}`. Solo el gateway (8000) y el frontend (3000) exponen puertos; iot/ml/ops son internos (el gateway los proxya). |
| `frontend/Dockerfile.prod` | Frontend en modo producción (`next build && next start`); las `NEXT_PUBLIC_*` se hornean en build-time como build args (apuntan al gateway público). |

> **Notas de diseño:**
> - **RDS, no contenedor `db`:** `DATABASE_URL` llega desde el entorno (`.env.prod`).
> - **`ml-service-isolation` excluido:** está gitignored y no forma parte del deploy;
>   `ML_BACKEND=legacy` (el default) no lo usa.
> - **Frontend → gateway:** las 4 `NEXT_PUBLIC_*` apuntan al gateway público; el gateway
>   proxya `/api/v1/iot/*` a iot-service, así el navegador solo necesita el puerto 8000.
> - **Secretos por `${VAR}`:** el `docker-compose.prod.yml` no contiene valores; se
>   inyectan vía `.env.prod`, que genera el `user_data` de la EC2 leyendo SSM (§6).

No necesitas escribir estos archivos: revísalos y valida el compose:
```bash
docker compose -f docker-compose.prod.yml config >/dev/null && echo "compose OK"
```

> **Aprendes:** la diferencia entre una imagen de desarrollo (bind-mounts + reload) y
> una de producción (código horneado, sin reload, secretos externos).

---

## 4. Terraform: crear la infraestructura

Toda la infra está definida y **validada** en `infra/terraform/` (HCL real, no
copy-paste). Archivos: `main.tf`, `variables.tf`, `network.tf`, `security.tf`,
`rds.tf`, `s3.tf`, `ssm.tf`, `ec2.tf` (+ `user_data.sh.tftpl`), `outputs.tf`.

### 4.1 Configura tus variables (secretos → NO se commitean)
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edita terraform.tfvars:
#   db_password / secret_key  -> genera nuevos (openssl rand)
#   smtp_user / smtp_password -> credenciales Mailtrap
#   ssh_public_key            -> cat ~/.ssh/airmon_ec2.pub
#   my_ip                     -> curl -s ifconfig.me
```
`terraform.tfvars` y `*.tfstate` están en `.gitignore` — nunca salen del repo local.

### 4.2 Aplica con tu perfil AWS
```bash
export AWS_PROFILE=airmon_v2      # el perfil ya configurado

terraform init      # (o: tofu init) descarga el provider aws
terraform validate  # debe decir "Success! The configuration is valid."
terraform plan      # revisa QUÉ va a crear
terraform apply     # 'yes' — tarda ~5-10 min (RDS es lo lento)

terraform output    # ec2_public_ip, rds_endpoint, s3_bucket, app_url, api_url, ssh
```

> **Qué crea:** VPC + subred pública + 2 privadas, security groups (RDS solo desde la
> EC2), RDS PostgreSQL 15, bucket S3, 4 parámetros SSM (secretos cifrados), rol IAM
> (EC2 lee S3+SSM sin claves), EC2 `t3.small` con Elastic IP y **deploy automático**
> (ver §6). Guarda los outputs:
> ```bash
> export S3_BUCKET=$(terraform output -raw s3_bucket)
> export EC2_IP=$(terraform output -raw ec2_public_ip)
> ```

> **Aprendes:** el ciclo `init → validate → plan → apply` y cómo un rol IAM permite que
> la EC2 lea S3/SSM sin claves hardcodeadas.

---

## 5. Subir código y artefactos a S3 (repo privado)

El repo es **privado**, así que la EC2 no hace `git clone`. En su lugar se sube un
**bundle del código** a S3; la EC2 lo baja con su rol IAM (sin credenciales git). Los
15 `.pkl` del ensemble tampoco están en git → también van por S3.

```bash
# desde la raíz del repo, en tu máquina local (con AWS_PROFILE=airmon_v2)

# (a) bundle del código (respeta .gitignore; solo lo versionado)
git archive --format=tar.gz -o airmon-app-bundle.tar.gz HEAD
aws s3 cp airmon-app-bundle.tar.gz "s3://$S3_BUCKET/app/airmon-app-bundle.tar.gz"

# (b) artefactos del ensemble (.pkl + .json gitignored)
aws s3 sync services/ml-service/ml_artifacts_ensemble_v1/ "s3://$S3_BUCKET/ensemble/"

# verifica
aws s3 ls "s3://$S3_BUCKET/app/"        # el bundle
aws s3 ls "s3://$S3_BUCKET/ensemble/"   # 15 .pkl + 6 .json
```

> **Importante:** el bundle sale de `git archive HEAD`, así que sube lo COMMITEADO.
> Commitea tus cambios antes. Cada re-deploy = re-subir el bundle + recrear la EC2
> (`terraform apply`, que detecta el cambio de `user_data`).

> **Aprendes:** cómo desplegar un repo privado sin poner credenciales de git en el
> servidor — el código y los binarios viajan por S3 con permisos IAM.

---

## 6. Deploy automático (lo hace la EC2 sola)

No hay pasos manuales de deploy: el `user_data` de la EC2 (en `ec2.tf` /
`user_data.sh.tftpl`) se ejecuta al arrancar y hace TODO:

1. Instala Docker + docker-compose.
2. Resuelve su IP pública (para las URLs del frontend).
3. Baja el **bundle de código** desde S3 y lo extrae.
4. Baja los **artefactos del ensemble** desde S3.
5. Lee los **secretos de SSM** (db_password, secret_key, smtp_*) y arma `.env.prod`.
6. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`.

Las migraciones alembic corren solas al arrancar cada servicio contra RDS.

### 6.1 Seguir el progreso del arranque
```bash
# SSH a la EC2 (el comando exacto lo da: terraform output -raw ssh)
ssh -i ~/.ssh/airmon_ec2 ec2-user@$EC2_IP

# [EN LA EC2] ver el log del deploy automático
sudo tail -f /var/log/airmon-deploy.log
# cuando termine:
docker compose -f air-monitoring-web/docker-compose.prod.yml ps   # 5 servicios Up
```

> El primer arranque tarda varios minutos (instala Docker + `npm ci` + `next build` +
> build de las 2 imágenes ML). Es normal.

> **Aprendes:** IaC de verdad — `terraform apply` deja el sistema corriendo sin tocar
> el servidor a mano; el user_data es el "deploy script" reproducible.

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
