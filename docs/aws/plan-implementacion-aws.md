# PLAN de implementación — Migración a AWS (EC2 + Terraform)

Plan por fases para llevar el stack a AWS según `spec-migracion-aws.md`. Cada fase tiene
objetivo, entregable y checklist. La ejecución comando-por-comando está en
`guia-aws-paso-a-paso.md`; aquí está el **qué** y el **orden**, no el **cómo** detallado.

**Estrategia:** lift-and-shift a una EC2 con docker-compose + RDS gestionada, todo
provisionado con Terraform. Reproducible (`apply`/`destroy`).

---

## Prerrequisitos (Fase 0)

| # | Tarea | Verificación |
|---|---|---|
| 0.1 | Cuenta AWS + usuario IAM (no root) con acceso programático | `aws sts get-caller-identity` |
| 0.2 | AWS CLI v2 instalado y `aws configure` (región `us-east-1`) | `aws --version` |
| 0.3 | Terraform ≥ 1.6 instalado | `terraform version` |
| 0.4 | Docker en local (para construir imágenes si se hornean) | `docker --version` |
| 0.5 | Par de llaves SSH para la EC2 (`ssh-keygen`) | archivo `.pub` listo |
| 0.6 | Rotar secretos: nuevo `SECRET_KEY`, nuevo DB password, revisar Mailtrap | valores guardados localmente, NO en git |

**Entregable:** entorno local capaz de hablar con AWS y crear infra.

---

## Fase 1 — Preparar el repo para producción

Objetivo: tener artefactos de despliegue que NO dependan del modo dev (bind-mounts,
`--reload`, `localhost`).

| # | Tarea | Detalle |
|---|---|---|
| 1.1 | `docker-compose.prod.yml` | Sin servicio `db` (usa RDS); sin bind-mounts de código; sin `--reload`; `restart: unless-stopped`; healthchecks; `DATABASE_URL`, `SECRET_KEY`, `SMTP_*` desde `${VAR}` del entorno (no hardcode); mantiene el bind-mount de `ml_artifacts_ensemble_v1` |
| 1.2 | Dockerfiles de prod (o reutilizar con override de CMD) | Quitar `--reload` de uvicorn; frontend a `next build && next start` con `NEXT_PUBLIC_API_GATEWAY_URL` como build arg |
| 1.3 | Contenedor `migrate` de un solo uso (opcional pero recomendado) | Corre las 4 `alembic upgrade head` en orden (iot, ml, ops, [isolation excluido]) contra RDS antes de levantar los servicios — evita el race de DDL concurrente |
| 1.4 | Excluir `ml-service-isolation` del compose de prod | `ML_BACKEND=legacy`; no está en git |
| 1.5 | Reverse-proxy Caddy (opcional) | Servicio Caddy en `:80/:443` que sirve el frontend y proxya `/api/*` → gateway; HTTPS automático si hay dominio |

**Entregable:** `docker-compose.prod.yml` + Dockerfiles listos para correr en un servidor
sin el árbol de fuentes montado.

**Checklist:** `docker compose -f docker-compose.prod.yml config` valida; probar local
apuntando a un Postgres local antes de subir.

---

## Fase 2 — Infraestructura con Terraform

Objetivo: definir y crear toda la infra AWS de forma declarativa.

Estructura sugerida en `infra/terraform/`:

```
infra/terraform/
  main.tf          # provider aws, backend (local o S3 state)
  variables.tf     # region, instance_type, db_password (sensitive), ssh_key, etc.
  network.tf       # VPC, subred pública, subred privada, IGW, route tables
  security.tf      # security groups (ec2-sg, rds-sg)
  ec2.tf           # instancia EC2 + IP elástica + IAM role (acceso S3/SSM) + user_data
  rds.tf           # subnet group + instancia RDS PostgreSQL 15
  s3.tf            # bucket de artefactos
  ssm.tf           # parámetros SecureString (secretos)
  outputs.tf       # IP pública EC2, endpoint RDS, nombre bucket
  terraform.tfvars # valores (gitignored: contiene secretos)
```

| # | Recurso Terraform | Notas |
|---|---|---|
| 2.1 | VPC + subred pública + subred privada (2 AZ para RDS) + IGW | CIDR `10.0.0.0/16`; RDS exige subnet group en ≥2 AZ |
| 2.2 | Security group EC2 | ingress 22 (tu IP), 80, 443; egress all |
| 2.3 | Security group RDS | ingress 5432 **solo** desde el SG de la EC2 |
| 2.4 | RDS PostgreSQL 15 `db.t3.micro` | DB `airmonitoring`, user `airmon`, password desde `var.db_password`; `publicly_accessible=false`; 20 GB gp3 |
| 2.5 | Bucket S3 artefactos | versionado on; privado |
| 2.6 | Parámetros SSM SecureString | `/airmon/db_password`, `/airmon/secret_key`, `/airmon/smtp_user`, `/airmon/smtp_password` |
| 2.7 | IAM role + instance profile para la EC2 | permisos: leer el bucket S3 + leer los parámetros SSM `/airmon/*` |
| 2.8 | EC2 `t3.small` (o `t3.micro`) + Elastic IP | Amazon Linux 2023; `user_data` instala Docker + docker-compose plugin |

**Entregable:** `terraform apply` crea todo; `terraform output` da IP de la EC2 y
endpoint de RDS.

**Checklist:** `terraform plan` sin errores → `apply` → RDS `available` → poder hacer
SSH a la EC2 → `docker` disponible en la EC2.

---

## Fase 3 — Artefactos ML a S3

Objetivo: que el ml-service tenga sus `.pkl` en la EC2 (no están en git).

| # | Tarea |
|---|---|
| 3.1 | `aws s3 sync services/ml-service/ml_artifacts_ensemble_v1/ s3://<bucket>/ensemble/` (incluye los 15 `.pkl` + 6 `.json`) |
| 3.2 | Script de arranque (en `user_data` o manual) descarga `s3://<bucket>/ensemble/` a `./services/ml-service/ml_artifacts_ensemble_v1/` en la EC2 |
| 3.3 | Verificar 21 archivos presentes antes de `docker compose up` |

**Entregable:** artefactos disponibles en la EC2 para el bind-mount del ml-service.

---

## Fase 4 — Desplegar la aplicación en la EC2 (AUTOMÁTICO)

Objetivo: levantar los contenedores contra RDS. **Ya no es manual**: el `user_data`
de la EC2 (`infra/terraform/user_data.sh.tftpl`) hace todo el deploy al arrancar.

| # | Tarea | Cómo |
|---|---|---|
| 4.1 | Subir el bundle de código + artefactos a S3 (repo privado) | `git archive` → S3, `aws s3 sync` ensemble → S3 (guía §5) |
| 4.2 | `terraform apply` crea la EC2 y el user_data se ejecuta solo | baja bundle+artefactos de S3, lee secretos de SSM, arma `.env.prod` |
| 4.3 | Migraciones alembic | corren solas al arrancar cada servicio contra RDS |
| 4.4 | `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build` | lo lanza el user_data |
| 4.5 | Frontend en modo prod | `frontend/Dockerfile.prod` (`next build`), `NEXT_PUBLIC_*` = gateway público (build args) |
| 4.6 | (Opcional) Caddy `:80/:443` → frontend + `/api` → gateway | HTTPS con dominio |

**Entregable:** stack corriendo; seguir `sudo tail -f /var/log/airmon-deploy.log` en la
EC2, luego `docker compose -f docker-compose.prod.yml ps` muestra 5 contenedores Up.

---

## Fase 5 — Verificación end-to-end (criterios de aceptación del spec §10)

| # | Prueba | Resultado esperado |
|---|---|---|
| 5.1 | Abrir `http://<IP-o-dominio>` | Carga el frontend |
| 5.2 | Login `admin@oefa.gob.pe / admin123` | Entra al dashboard (cadena frontend→gateway→ops OK) |
| 5.3 | `POST /api/v1/iot/readings` con un payload de prueba | 200; dispara el ensemble (C1) |
| 5.4 | Dashboard muestra estado de salud del equipo | Cadena iot→ml→ops OK |
| 5.5 | Provocar una incidencia y revisar Mailtrap | Correo recibido |
| 5.6 | Revisar logs: `docker compose logs ml-service` | Ensemble carga los `.pkl` sin error |

**Entregable:** demo funcional en la nube, reproducible.

---

## Fase 6 — HTTPS y dominio (opcional, recomendado para la defensa)

| # | Tarea |
|---|---|
| 6.1 | Subdominio gratuito (DuckDNS / dominio propio) apuntando a la Elastic IP |
| 6.2 | Caddy con `tls` automático (Let's Encrypt) — HTTPS sin configurar certificados a mano |
| 6.3 | Rebuild del frontend con la URL `https://<dominio>/api` |

**Entregable:** `https://<dominio>` con candado válido.

---

## Fase 7 — Operación y limpieza

| # | Tarea |
|---|---|
| 7.1 | Apagar EC2/RDS entre demos (o `terraform destroy`) para costo ~$0 |
| 7.2 | `terraform apply` para recrear en 5-10 min cuando se necesite |
| 7.3 | Backups RDS automáticos (7 días) ya activos; snapshot manual antes de destroy si se quiere conservar datos |
| 7.4 | Documentar en el README de `infra/` cómo levantar/tumbar |

---

## Orden crítico y dependencias

```
Fase 0 (prereqs)
   └─► Fase 1 (repo prod) ──┐
   └─► Fase 2 (Terraform) ──┤
                            ├─► Fase 3 (artefactos S3) ─► Fase 4 (deploy) ─► Fase 5 (verificar)
                            │                                                      └─► Fase 6 (HTTPS opc)
                            └─ RDS debe estar 'available' antes de Fase 4.4 (migraciones)
```

- **Fase 1 y 2 son paralelizables** (preparar el repo mientras Terraform crea infra).
- **Fase 3 depende de Fase 2** (necesita el bucket) y **Fase 4 depende de 2+3**.
- **RDS debe estar `available`** (5-10 min) antes de correr migraciones (4.4).

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `t3.micro` (1 GB) se queda sin RAM con 2 imágenes ML + Node + Postgres client | Usar `t3.small` (2 GB), o agregar 2 GB de swap en `user_data` si se insiste en free-tier |
| Los `.pkl` no llegan a la EC2 (gitignored) | Fase 3 obligatoria (S3 sync + download); verificar 21 archivos antes de `up` |
| Migraciones concurrentes race en DDL | Contenedor `migrate` de un solo uso (Fase 1.3) |
| Frontend con URLs `localhost` baked | Rebuild con la URL pública como build arg (Fase 4.3); o Caddy en el mismo origen con `/api` |
| Costo inesperado | `terraform destroy` entre sesiones; alarma de billing en AWS |
| Secreto commiteado por error | `terraform.tfvars` y `docker-compose.prod.yml` con valores reales en `.gitignore`; usar `${VAR}` |

---

## Siguiente paso

Con este plan aprobado, la ejecución detallada (crear cada archivo Terraform, cada
comando `aws`, cada verificación) está en **`guia-aws-paso-a-paso.md`**.
