# SPEC — Migración a AWS (arquitectura EC2 simple + Terraform)

**Proyecto:** Air Monitoring (monitoreo predictivo de calidad de aire, caso OEFA).
**Contexto:** entregable final de tesis. Objetivo = correr el sistema en la nube de
forma **simple, barata (free-tier) y reproducible**, priorizando aprendizaje y una
demo sólida sobre escalabilidad de producción.
**Versión:** 1.0 (2026-07-05).
**Documentos hermanos:** `plan-implementacion-aws.md` (fases), `guia-aws-paso-a-paso.md`
(comando por comando). Reemplaza a `docs/AWS_DEPLOYMENT.md` (arquitectura Fargate,
más compleja y desactualizada tras el retiro del RF — ver §8).

---

## 1. Resumen ejecutivo

Se despliega el stack **tal cual** (los mismos contenedores Docker que corren en local
vía `docker-compose`) sobre **una única instancia EC2**, con la base de datos en **RDS
PostgreSQL** gestionada y el correo vía **Mailtrap** (sin cambios). Toda la infra
(red, EC2, RDS, S3, security groups, secretos) se define en **Terraform**, de modo que
se puede crear y destruir con un comando — clave para una demo de tesis y para no
incurrir en costos cuando no se usa.

```
                          Internet
                             │  HTTP(S)
                    ┌────────▼──────────────┐
                    │  EC2  t3.small         │   ← 1 sola VM en subred pública
                    │  (Amazon Linux 2023)   │
                    │  ┌──────────────────┐  │
                    │  │ docker compose   │  │   ← docker-compose.prod.yml
                    │  │  frontend  :3000 │  │
                    │  │  gateway   :8000 │  │   (Caddy/nginx opcional → 80/443)
                    │  │  iot       :8001 │  │
                    │  │  ml        :8002 │  │
                    │  │  ops       :8003 │  │
                    │  └────────┬─────────┘  │
                    └───────────┼────────────┘
                    Security Group (5432 solo EC2→RDS)
                    ┌───────────▼────────────┐
                    │  RDS PostgreSQL 15      │   ← db.t3.micro (free-tier)
                    │  1 base: airmonitoring  │      subred privada, sin IP pública
                    └─────────────────────────┘

  Artefactos ML (.pkl del ensemble) ──► S3 ──► descargados al arrancar la EC2
  Email ──► Mailtrap (externo, sin cambios)
  Todo ──► definido en Terraform (VPC, EC2, RDS, S3, SG, IAM, secretos SSM)
```

**Contenedores desplegados: 6** (frontend + api-gateway + iot + ml + ops + [Caddy]).
La base de datos NO va como contenedor (se usa RDS). `ml-service-isolation` **se
excluye** (backend v3 alternativo, no está en git, `ML_BACKEND=legacy` no lo usa; ver §5).

---

## 2. Decisiones de arquitectura (con alternativas descartadas)

### D1 — Cómputo: una sola EC2 con docker-compose ✅

| Opción | Esfuerzo | Costo | Cloud-native | Veredicto |
|---|---|---|---|---|
| **EC2 única + docker-compose** ✅ | **Bajo** (reusa tu stack) | **~Free-tier** | Medio | **Elegida** |
| ECS Fargate + ALB + Cloud Map | Alto (task defs, IAM, redes, ECR por servicio) | Medio ($30-70/mes) | Alto | Descartada: complejidad y costo innecesarios para el volumen de una tesis |
| Lambda + API Gateway (serverless) | Muy alto (reescribir 5 FastAPI a handlers, cold starts, sin procesos APScheduler) | Bajo si idle | Muy alto | Descartada: reescritura completa; el scheduler del ml-service (watchdog/θ/retrain) no encaja en Lambda |

**Por qué EC2 única:** reusas exactamente los mismos `Dockerfile` y `docker-compose`
que ya funcionan; una VM `t3.small` corre los 6 contenedores sin problema; y Terraform
te da el "cloud real" reproducible que defiende la tesis. Fargate queda documentado como
**camino de escalado futuro** (§8), no como el entregable.

> **Nota de free-tier:** `t2.micro`/`t3.micro` (1 GB RAM) entran en free-tier pero se
> quedan cortos con 2 imágenes ML (sklearn+pandas+numpy) + frontend Node + Postgres
> client. Recomendación realista: **`t3.small` (2 GB)**, ~$15/mes on-demand, o `t3.micro`
> free-tier si se acepta agregar swap y tolerar lentitud. Se justifica en §7 (costos).

### D2 — Base de datos: RDS PostgreSQL gestionada ✅

- **Elegida:** RDS `db.t3.micro`, PostgreSQL 15, **una sola base** `airmonitoring`
  (igual que hoy: los 4 servicios comparten la BD con tablas de versión alembic
  distintas — `alembic_version_iot/ml/ml_isolation/ops`). Free-tier el primer año
  (750 h/mes db.t3.micro + 20 GB).
- **Descartada:** Postgres como contenedor en la misma EC2. Más simple/barato pero
  los datos viven en el disco de la VM (se pierden si se recrea), sin backups
  automáticos. RDS da backups, es "de libro" para la tesis y sigue siendo free-tier.

### D3 — Notificaciones: Mailtrap (sin cambios) ✅

- **Elegida:** seguir con Mailtrap (`sandbox.smtp.mailtrap.io:2525`). Cero migración:
  `ops-service` ya lee `SMTP_HOST/PORT/USER/PASSWORD/FROM`. Suficiente para la demo
  (captura los correos en un inbox de prueba).
- **Descartada:** Amazon SES. Más "AWS-nativo" pero requiere verificar dominio y salir
  del sandbox (fricción y tiempo que no aporta a la tesis). Queda como mejora futura;
  migrar sería solo cambiar 5 variables de entorno (el código no cambia).

### D4 — Infraestructura como código: Terraform ✅

- **Elegida:** Terraform. Toda la infra (VPC, subredes, EC2, RDS, S3, security groups,
  roles IAM, parámetros SSM) en código versionado. `terraform apply` la crea,
  `terraform destroy` la elimina (evita costos cuando no demuestras). Reproducible y
  demostrable — argumento fuerte en la defensa.
- **Alternativa (AWS CDK):** también válida, pero Terraform tiene menor curva y
  documentación más abundante para nivel básico. El viejo `AWS_DEPLOYMENT.md` usaba
  comandos CLI manuales; Terraform los reemplaza con un estado declarativo.

### D5 — Punto de entrada / HTTPS

- **MVP demo:** EC2 en subred pública con IP elástica; el frontend expone `:3000` y el
  gateway `:8000` directamente (security group abre 80/443/3000/8000 a Internet).
- **Recomendado (poco esfuerzo extra):** un contenedor **Caddy** como reverse-proxy en
  el `:80/:443` que sirve el frontend y proxya `/api/*` al gateway, con **HTTPS
  automático** (Let's Encrypt) si hay un dominio/subdominio. Documentado en el plan como
  paso opcional. Sin dominio, se usa la IP pública por HTTP (aceptable para demo).

---

## 3. Mapeo local → AWS (qué cambia y qué no)

| Pieza local (docker-compose) | En AWS | Cambio requerido |
|---|---|---|
| `db` (contenedor postgres:15) | **RDS PostgreSQL 15** | Quitar el servicio `db` del compose; apuntar `DATABASE_URL` al endpoint RDS |
| `api-gateway`, `iot`, `ml`, `ops`, `frontend` | **6 contenedores en la EC2** | Nuevo `docker-compose.prod.yml`: sin bind-mounts, sin `--reload`, con `restart: unless-stopped` |
| `ml-service-isolation` | **Excluido** | No está en git y `ML_BACKEND=legacy` no lo usa (§5) |
| DNS interno `http://ml-service:8002` | **Igual** | Se conserva: en una sola EC2, docker-compose mantiene la red interna y el DNS por nombre de servicio |
| Bind-mount `ml_artifacts_ensemble_v1/` (`.pkl` gitignored) | **S3 → descarga al arrancar** | Los 15 `.pkl` no están en git; se suben a S3 y un script los baja a la EC2 antes de `docker compose up` (§4) |
| `NEXT_PUBLIC_*=http://localhost:8000` | **Hostname público** | Rebuild del frontend con la IP/dominio público del gateway (build-time, §6) |
| Secretos en compose (DB pw, JWT, SMTP) | **SSM Parameter Store (SecureString)** | Se inyectan como env vars al arrancar; nunca en git (§4) |
| `alembic upgrade head` por servicio al arrancar | **Igual** | Se conserva; corre contra RDS. Ver nota de concurrencia (§9) |

**Lo que NO cambia (clave para el bajo esfuerzo):** el código de los 5 servicios, los
Dockerfiles (salvo quitar `--reload` en prod), la red interna docker-compose, el DNS por
nombre de servicio, y el flujo de auth/RBAC. Es un "lift-and-shift" casi literal.

---

## 4. Gestión de secretos y artefactos

### 4.1 Secretos (SSM Parameter Store, tipo SecureString)

Hoy están **hardcodeados en `docker-compose.yml`** (riesgo). En AWS se mueven a SSM y se
inyectan como variables de entorno al levantar el compose en la EC2:

> **Nota de seguridad:** los valores actuales de estos secretos están hardcodeados en el
> `docker-compose.yml` del repo (dev). **Todos deben rotarse** al migrar y NO se
> reproducen aquí. Consulta los valores vigentes en tu compose local / Mailtrap.

| Parámetro SSM | Origen del valor actual (a rotar) | Lo consume |
|---|---|---|
| `/airmon/db_password` | `POSTGRES_PASSWORD` en compose → **rotar** | RDS + `DATABASE_URL` de todos los servicios |
| `/airmon/secret_key` | `SECRET_KEY` en compose → **generar nuevo** (`openssl rand -hex 32`) | api-gateway (firma JWT HS256) |
| `/airmon/smtp_user` | `SMTP_USER` en compose (Mailtrap) | ops-service |
| `/airmon/smtp_password` | `SMTP_PASSWORD` en compose → **rotar en Mailtrap** | ops-service |

> SSM Parameter Store es **gratis** para parámetros estándar (SecureString incluido).
> Alternativa Secrets Manager cuesta ~$0.40/secreto/mes — innecesario para la tesis.

### 4.2 Artefactos del ensemble (S3)

- El ml-service necesita `ml_artifacts_ensemble_v1/` en runtime, pero **los 15 `.pkl`
  están gitignored** (solo los 6 `.json` están versionados). Clonar el repo en la EC2
  NO los trae.
- **Solución:** bucket S3 `airmon-artifacts-<accountid>`; se suben los `.pkl` una vez
  (`aws s3 sync`), y un `user-data`/script de arranque de la EC2 los descarga a
  `./services/ml-service/ml_artifacts_ensemble_v1/` antes de `docker compose up`. El
  bind-mount del compose los monta en el contenedor como en local.
- El dataset de ~730 MB (`ml-proposal/dataset`, gitignored) **no se sube**: solo lo usan
  los scripts de entrenamiento offline, no el runtime. En prod ese bind-mount se elimina.

---

## 5. Alcance: qué se despliega y qué no

**Se despliega (6 contenedores):** frontend, api-gateway, iot-service, ml-service,
ops-service, y (opcional) Caddy como reverse-proxy HTTPS.

**Se excluye `ml-service-isolation`:**
- No está en git (todo el directorio `services/ml-service-isolation/` está gitignored),
  así que no forma parte de un deploy reproducible desde el repo.
- Es el backend **v3 alternativo** (detección por episodios), seleccionable solo con
  `ML_BACKEND=isolation`. El default `legacy` **no lo usa**; el api-gateway solo lo
  necesita si se activa ese flag.
- Para la tesis se despliega el camino `legacy` (ensemble AE+IF vía ml-service). Si en
  el futuro se quisiera incluir isolation, habría que versionarlo primero.

---

## 6. Frontend en AWS

> ✅ **Resuelto (2026-07):** ya existe `frontend/Dockerfile.prod` (`next build && next
> start`) con las `NEXT_PUBLIC_*` como build args, y `docker-compose.prod.yml` las
> apunta al gateway público. Esta sección explica el porqué del diseño.

- Hoy el contenedor de dev corre `next dev` con `NEXT_PUBLIC_*` apuntando a `localhost` (válido
  solo si el navegador está en la misma máquina que los contenedores). En AWS el
  navegador del evaluador está en otro lugar → deben apuntar al **hostname/IP pública**
  de la EC2 (o al dominio, si se usa Caddy).
- Como son variables `NEXT_PUBLIC_*`, Next.js las **inyecta en el bundle del cliente**.
  Con `next dev` se leen al arrancar; si se pasa a `next build` (producción, recomendado)
  se **hornean en build-time** → deben pasarse como *build args* al construir la imagen.
- **Decisión:** para prod, `Dockerfile` de frontend con `next build && next start` y
  `NEXT_PUBLIC_API_GATEWAY_URL` = URL pública del gateway (o `/api` si Caddy proxya en el
  mismo origen — la opción más limpia: mismo dominio, sin CORS).

---

## 7. Costos estimados (mensual, us-east-1)

| Recurso | Free-tier (año 1) | Fuera de free-tier |
|---|---|---|
| EC2 `t3.small` (2 GB) | ❌ no aplica | ~$15/mes on-demand (o ~$0 si se apaga entre demos) |
| EC2 `t3.micro` (1 GB) | ✅ 750 h/mes | ~$7.5/mes |
| RDS `db.t3.micro` + 20 GB | ✅ 750 h/mes | ~$13/mes |
| S3 (artefactos, <1 GB) | ✅ 5 GB | ~$0.02/mes |
| IP elástica (asociada) | gratis mientras esté asociada | $0.005/h si sin usar |
| Transferencia de datos | ✅ 100 GB/mes salida | mínima para demo |
| SSM Parameter Store | ✅ gratis (estándar) | — |

**Estimado realista para la tesis:** **$0** el primer año si se usa `t3.micro` + free-tier
y se **apaga la EC2 y RDS cuando no se demuestra** (o `terraform destroy`). Con `t3.small`
y todo encendido 24/7: ~$28/mes. Recomendación: `t3.small` + apagar entre sesiones, o
`terraform destroy`/`apply` bajo demanda (5-10 min recrear todo).

---

## 8. Alternativa de escalado futuro: ECS Fargate

Para producción real (multi-instancia, autoescalado, cero VM que administrar), la
arquitectura de contenedores gestionados es **ECS Fargate + ALB + Cloud Map + ECR**.
El documento `docs/AWS_DEPLOYMENT.md` (archivado) la detalla paso a paso, pero:

- Está **desactualizado tras C2** (menciona el RF: `/predictions`, `/alerts`, tablas
  `predicciones`/`alertas`, `ml_artifacts/`, y 3 tablas alembic cuando ml ya no crea
  predicciones/alertas). Si se retomara, hay que corregirlo al modelo ensemble actual.
- Es **más caro y complejo** (task definitions por servicio, roles IAM, redes privadas,
  NAT gateway ~$32/mes, ECR, ALB ~$16/mes) — innecesario para una tesis.

**Recomendación:** presentar EC2-simple como la solución del entregable, y citar Fargate
como "evolución natural a producción" (demuestra que se evaluó el trade-off).

---

## 9. Seguridad y consideraciones operativas

1. **Secretos fuera de git:** rotar DB password, `SECRET_KEY` (JWT) y credenciales
   Mailtrap; moverlos a SSM SecureString. Nunca commitear el `docker-compose.prod.yml`
   con valores reales (usar `${VAR}` interpolado desde el entorno de la EC2).
2. **RDS sin IP pública:** en subred privada; su security group solo acepta 5432 desde
   el security group de la EC2. La EC2 es el único punto de entrada.
3. **Security group de la EC2:** abrir solo 22 (SSH, idealmente restringido a tu IP),
   80/443 (web). Evitar exponer 8001-8003 (servicios internos) a Internet — solo el
   gateway `:8000` y el frontend/Caddy deben ser públicos.
4. **Migraciones concurrentes:** los 4 servicios corren `alembic upgrade head` al
   arrancar contra la misma RDS. Las tablas de versión distintas evitan colisión de
   revisión, pero el arranque paralelo puede competir en DDL. Mitigación simple: en el
   compose de prod, un `depends_on` escalonado o un contenedor `migrate` de un solo uso
   que corra las 4 migraciones en orden antes de levantar los servicios.
5. **Sin auto-recuperación hoy:** ningún servicio tiene `restart:` ni healthcheck (salvo
   db). En prod: `restart: unless-stopped` + healthchecks en el compose de prod.
6. **HTTPS:** para la demo, HTTP por IP es aceptable; con Caddy + un subdominio gratuito
   (p.ej. DuckDNS) se obtiene HTTPS automático sin costo.

---

## 10. Criterios de aceptación (definición de "migrado")

- [ ] `terraform apply` crea VPC + EC2 + RDS + S3 + SG + IAM + parámetros SSM sin errores.
- [ ] La EC2 arranca, descarga los `.pkl` de S3 y levanta los 6 contenedores.
- [ ] Las 4 migraciones alembic corren contra RDS (tablas creadas + seed data).
- [ ] El frontend carga por la IP/dominio público y el login funciona
      (`admin@oefa.gob.pe`), demostrando la cadena frontend→gateway→ops (auth).
- [ ] Una lectura IoT (`POST /api/v1/iot/readings`) dispara el ensemble y el dashboard
      muestra el estado de salud (cadena iot→ml→ops end-to-end).
- [ ] Un correo de incidencia llega a Mailtrap.
- [ ] `terraform destroy` elimina toda la infra (verificable en la consola AWS).

---

## 11. Documentos relacionados

- **`plan-implementacion-aws.md`** — fases de implementación (Terraform → RDS → EC2 →
  artefactos → deploy → verificación → HTTPS opcional), con checklist.
- **`guia-aws-paso-a-paso.md`** — guía nivel básico, comando por comando, con qué
  aprender en cada paso y troubleshooting.
- **`docs/AWS_DEPLOYMENT.md`** — [ARCHIVADO] alternativa Fargate (avanzada, desactualizada
  tras C2). Referencia para el escalado futuro descrito en §8.
