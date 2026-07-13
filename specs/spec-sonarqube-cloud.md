# Spec: SonarCloud para el monorepo `air-monitoring-web`

**Estado**: Implementación en curso — 2026-07-12 (setup Sonar + wire CI en rama `chore/frontend-testing-prettier`)
**Autor**: Equipo AirMon
**Alcance**: 4 servicios Python (api-gateway, iot-service, ml-service, ops-service) + 1 frontend Next 16/TS
**Repo**: https://github.com/the-eagle-eye/air-monitoring-web (público → SonarCloud gratis)

---

## 0. Adenda 2026-07-12 (segunda iteración) — Pivote a 1 proyecto

**Cambio de rumbo**: la arquitectura original de **5 proyectos independientes apuntando al mismo repo** no funcionó como se esperaba. Al bindear el repo a un proyecto SonarCloud, éste queda **"Already bound"** y bloqueado para el resto — el binding repo↔proyecto es 1:1 en el plan Free. Solo el primer proyecto (frontend) obtuvo binding activo; los otros 4 corrían el scan (los datos llegaban al dashboard de `main`) pero no publicaban status check en PRs ni PR Summary porque el scanner detectaba `Detected project binding: NOT_BOUND`.

**Nueva arquitectura**: **1 solo proyecto SonarCloud** `the-eagle-eye_air-monitoring-web` que analiza todo el monorepo (frontend + 4 servicios) desde un único `sonar-project.properties` en la raíz del repo. Un solo status check `SonarCloud Code Analysis` cubre toda la PR.

**Trade-offs asumidos**:
- Pierde umbrales de coverage distintos por servicio (§4.3). Queda un umbral global — se configura post-baseline.
- Métricas mezcladas: no se ve "coverage de ml-service" en la UI de Sonar, se ve global. Se puede filtrar por path en la vista de Measures.
- Un solo required check en branch protection en lugar de 5.

**Cambios técnicos aplicados**:
- `sonar-project.properties` en la raíz (proyecto único, sources y coverage paths múltiples).
- 5 `sonar-project.properties` distribuidos eliminados.
- `backend-ci.yml` y `frontend-ci.yml` ya no ejecutan `SonarSource/sonarqube-scan-action` — vuelven a ser workflows de test puro.
- Nuevo workflow `.github/workflows/sonarcloud.yml`: instala Python+Node, corre los 5 test suites con coverage, ejecuta 1 scan desde la raíz.
- Se añadió `sonar.sourceEncoding=UTF-8` y exclusión de binarios (`.ico`, imágenes, fonts, `public/**`) para eliminar el warning "Invalid character encountered in file favicon.ico".

**Pasos de UI Sonar (fuera del repo)**: borrar los 5 proyectos actuales, importar el repo como un solo proyecto (default key `the-eagle-eye_air-monitoring-web`), verificar Automatic Analysis = OFF y binding = repo GitHub.

Todo el resto de esta spec (§1-§10) queda como referencia histórica. Cualquier referencia a "5 proyectos" o `sonar.projectKey=air-monitoring-*` está **superseded** por esta adenda.

---

## 1. Motivación

Hoy el CI cubre linters y tests, pero no hay medición sistemática de:

- **Cobertura de código** por servicio (pytest-cov y jest --coverage existen puntualmente pero NO se agregan ni versionan).
- **Duplicación** — el proyecto tiene 5 servicios que reimplementan patrones similares (schemas, error handling, notify services) y no sabemos qué tanto se repite.
- **Complejidad cognitiva / ciclomática** — servicios como `ensemble_notify_service`, `retrain_service`, `incidencia_service` han crecido en el último sprint sin métrica.
- **Bugs / code smells / vulnerabilidades** de análisis estático más allá de flake8/eslint (que son sintácticos, no semánticos).
- **Security hotspots** — el proyecto tiene JWT, bcrypt, secrets, endpoints públicos: necesita análisis dedicado.
- **Technical debt ratio** — dato duro para negociar refactors con stakeholders.

SonarCloud aporta todo lo anterior con **PR decoration** (comentario automático en cada PR con delta vs. main) y un **quality gate** configurable como required check.

## 2. Decisiones de diseño

| Decisión | Elegido | Alternativa | Razón |
|---|---|---|---|
| Visibilidad repo | Público | Privado | Gratis ilimitado en SonarCloud. Ya es público. |
| Estructura Sonar | **1 org, 5 proyectos independientes** | Monorepo mode / 1 mezclado | El Free plan de SonarCloud NO incluye monorepo mode (feature de plan Team+). Se opta por **5 proyectos independientes** en la misma org, todos mapeados al mismo repo GitHub, diferenciados por `sonar.projectKey`. Un solo `SONAR_TOKEN` global sirve para los 5. Trade-off aceptado: no hay vista unificada nativa (se puede armar manual con el API). |
| Gate strictness | **Fase 1 informativo → Fase 2 bloqueante** | Bloqueante d1 / solo informativo | Permite establecer baseline sin bloquear PRs abiertos. |
| Analysis mode | **CI-based** (GitHub Actions) | Automatic analysis | Necesitamos subir coverage reports; automatic no lo permite. |
| Coverage focus | **New code** (Clean as You Code) | Overall code | Sonar recomienda; evita pelearse con deuda histórica. |

## 3. Arquitectura del setup

### 3.1 Organización SonarCloud

- **Org**: `the-eagle-eye` (display name: Luigi Aguirre)
- **Plan**: Free (público, ilimitado)
- **Analysis Method**: **CI-based** (Automatic Analysis desactivado — incompatible con upload de coverage reports)

### 3.2 Proyectos (5, independientes)

| Project Key | Path | Lenguaje | Coverage tool |
|---|---|---|---|
| `air-monitoring-api-gateway` | `services/api-gateway/` | Python 3.11 | pytest-cov → `coverage.xml` |
| `air-monitoring-iot-service` | `services/iot-service/` | Python 3.11 | pytest-cov → `coverage.xml` |
| `air-monitoring-ml-service` | `services/ml-service/` | Python 3.11 | pytest-cov → `coverage.xml` |
| `air-monitoring-ops-service` | `services/ops-service/` | Python 3.11 | pytest-cov → `coverage.xml` |
| `air-monitoring-frontend` | `frontend/` | TypeScript/React | jest --coverage → `lcov.info` |

Cada uno tiene su propio `sonar-project.properties` en el subdirectorio. Los 5 proyectos apuntan al **mismo repo GitHub** (`the-eagle-eye/air-monitoring-web`) y se diferencian por `sonar.projectKey`. El scanner se lanza desde CI con `projectBaseDir` apuntando al subdirectorio correspondiente.

### 3.3 CI-scanner por proyecto

Se aprovecha la matriz existente:

- **Backend CI** (`.github/workflows/backend-ci.yml`) — matriz de 4 servicios: cada job corre pytest con `--cov=app --cov-report=xml` y luego dispara el scanner Sonar apuntando al `sonar-project.properties` local.
- **Frontend CI** (`.github/workflows/frontend-ci.yml`) — job único: jest con `--coverage --coverageReporters=lcov` y luego scanner Sonar.

Trigger: `push` a `main`/`dev`/`qa` y `pull_request` — mismo trigger actual, sin nuevos workflows.

## 4. Métricas y Quality Gate

### 4.1 Métricas de análisis estático (todas provistas por Sonar)

| Métrica | Qué mide | Notas |
|---|---|---|
| **Bugs** | Errores de lógica probables (null refs, unreachable, off-by-one) | Cuenta absoluta + rating A-E |
| **Vulnerabilities** | Fallas de seguridad (SQLi, XSS, secrets hardcoded, JWT mal usado) | Rating A-E |
| **Security Hotspots** | Zonas que requieren revisión manual (crypto, IO, RCE) | Cuenta + % revisados |
| **Code Smells** | Anti-patrones de mantenibilidad | Rating A-E |
| **Coverage** | % líneas cubiertas por tests | Filtrable por new code |
| **Duplications** | % líneas duplicadas (bloques ≥100 tokens) | Filtrable por new code |
| **Cognitive Complexity** | Dificultad de leer/entender el código | Por función, warning >15 |
| **Cyclomatic Complexity** | Caminos de ejecución independientes | Por función |
| **Technical Debt** | Tiempo estimado para arreglar todos los smells | Ratio vs LOC |
| **LOC** | Líneas de código (excl. comentarios/blancos) | Split por lenguaje |

### 4.2 Quality Gate — "AirMon Standard"

Aplicado sobre **new code** (código añadido/modificado en la rama vs. main):

```
Conditions (fail if any is true):
  - Coverage on New Code           < 70%
  - Duplicated Lines on New Code   > 3%
  - Maintainability Rating         worse than A
  - Reliability Rating             worse than A
  - Security Rating                worse than A
  - Security Hotspots Reviewed     < 100%
```

**Overall code** (histórico): sin gate, solo tracking. Aplicamos filosofía **Clean as You Code**: el código viejo se limpia cuando se toca.

### 4.3 Umbrales específicos por sub-proyecto

Se sobreescriben en la UI de Sonar cuando aplique:

- **frontend**: coverage new code **60%** (componentes con Recharts no se unit-testean por decisión previa; ver [[project-frontend-testing-prettier]]).
- **ml-service**: coverage new code **65%** (código de ML con dependencias pesadas se cubre parcialmente en unit).
- **api-gateway, iot-service, ops-service**: coverage new code **70%** (regla estándar).

## 5. Plan de implementación (5 fases)

### Fase 1 — Preparación (0.5d) ✅ HECHO 2026-07-12
1. ✅ Org `the-eagle-eye` creada en https://sonarcloud.io (login con GitHub).
2. ✅ Un solo `SONAR_TOKEN` (Global Analysis Token) añadido a GitHub Secrets del repo. Sirve para los 5 proyectos.
3. ✅ 5 proyectos creados manualmente ("Set up manually" + "With GitHub Actions" en cada wizard), con estos keys:
   - `air-monitoring-api-gateway` (display: AirMon · API Gateway)
   - `air-monitoring-iot-service` (display: AirMon · IoT Service)
   - `air-monitoring-ml-service` (display: AirMon · ML Service)
   - `air-monitoring-ops-service` (display: AirMon · Ops Service)
   - `air-monitoring-frontend` (display: AirMon · Frontend)
4. ✅ Al elegir "With GitHub Actions" en cada wizard, Automatic Analysis quedó OFF por default.

**Nota**: originalmente la spec proponía monorepo mode (1 proyecto padre con sub-módulos). Se descartó porque **Free plan no lo incluye** (feature de plan Team+, ~$10/user/mes). Los 5 proyectos son independientes pero apuntan al mismo repo GitHub.

**Deliverable**: 5 proyectos visibles en sonarcloud.io/organizations/the-eagle-eye/projects, todos con "Project is not analyzed yet".

### Fase 2 — Instrumentar cobertura (1d) ✅ HECHO 2026-07-12
1. ✅ **Python** — añadido `pytest-cov==5.0.0` a los 4 `requirements-dev.txt`. Añadido `addopts = --cov=app --cov-report=xml --cov-report=term` a los 4 `pytest.ini` (default local + CI generan `coverage.xml`).
2. ✅ **Frontend** — `jest.config.mjs` ya tenía `collectCoverageFrom` (excluye `.d.ts`, `types/`, layouts). Los reporters `lcov` + `text` vienen por default de jest — `npm test -- --coverage` genera `frontend/coverage/lcov.info`.
3. ✅ **`.gitignore`** — añadido `coverage.xml` y `.scannerwork/` (el patrón `coverage/` ya estaba).

**Deliverable**: coverage generado localmente y en CI. Nota: `coverage.xml` de cada servicio es relativo a `services/<svc>/`.

### Fase 3 — Configuración Sonar (0.5d)
1. Crear `sonar-project.properties` en cada uno de los 5 subdirs. Ejemplo backend service:
   ```properties
   sonar.projectKey=air-monitoring-iot-service
   sonar.organization=the-eagle-eye
   sonar.sources=app
   sonar.tests=tests
   sonar.python.version=3.11
   sonar.python.coverage.reportPaths=coverage.xml
   sonar.exclusions=**/migrations/**,**/*.pyc
   sonar.coverage.exclusions=**/migrations/**,tests/**
   ```
   Frontend:
   ```properties
   sonar.projectKey=air-monitoring-frontend
   sonar.organization=the-eagle-eye
   sonar.sources=src
   sonar.tests=src,e2e
   sonar.test.inclusions=**/*.test.ts,**/*.test.tsx,e2e/**
   sonar.javascript.lcov.reportPaths=coverage/lcov.info
   sonar.exclusions=**/*.d.ts,**/next-env.d.ts,.next/**
   sonar.coverage.exclusions=**/*.test.*,e2e/**,jest.config.mjs,jest.setup.ts
   ```

**Deliverable**: ✅ HECHO 2026-07-12 — 5 archivos `sonar-project.properties` creados. Exclusiones específicas por servicio: `ml-service` excluye `ml_artifacts_ensemble_v1/` y `scripts/`; todos los backend excluyen `alembic/versions/**`; frontend excluye `.next/`, `playwright-report/`, `test-results/`.

### Fase 4 — Wire CI (0.5d)
1. **Backend CI** — al final del job, tras `pytest`, añadir:
   ```yaml
   - name: SonarCloud scan
     if: always()  # publicar incluso si tests fallan (útil para triage)
     uses: SonarSource/sonarqube-scan-action@v6
     with:
       projectBaseDir: services/${{ matrix.service }}
     env:
       SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```
2. **Frontend CI** — modificar `npm test` para incluir `-- --coverage` y añadir:
   ```yaml
   - name: SonarCloud scan
     if: always()
     uses: SonarSource/sonarqube-scan-action@v6
     with:
       projectBaseDir: frontend
     env:
       SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```
3. Correr el CI en un PR de prueba, verificar que:
   - Los 5 proyectos aparecen con datos en sonarcloud.io.
   - Aparece comentario automático de PR decoration en el PR.

**Estado**: ✅ HECHO 2026-07-12 (código) — pendiente verificar en el próximo push a la rama. Se añadió `fetch-depth: 0` en ambos checkouts (Sonar necesita historia completa para blame/new-code).

**Deliverable**: PR de prueba con Sonar reportando en los 5 proyectos.

### Fase 5 — Baseline + Gate (2-3 semanas)
1. **Semana 1-2 — Informativo**: dejar que Sonar corra en cada PR. NO configurar branch protection todavía. Equipo empieza a resolver los issues críticos y hotspots señalados en `Overall Code`.
2. **Semana 3 — Activar gate**: ir a `Quality Gate` → definir "AirMon Standard" (sección 4.2). Asignarlo como default a los 5 proyectos.
3. **Branch protection**: Settings → Branches → `main`/`dev` → Required status checks → añadir los 5 checks `SonarCloud Code Analysis` (uno por proyecto). Backend + Frontend CI ya son required; añadir los nuevos checks.

**Deliverable**: PRs bloqueados si el quality gate falla sobre new code.

## 6. Configuración técnica detallada

### 6.1 Archivos nuevos/modificados

```
.github/workflows/backend-ci.yml       (+step SonarCloud scan)
.github/workflows/frontend-ci.yml      (+step SonarCloud scan, jest --coverage)
services/api-gateway/sonar-project.properties     (NEW)
services/iot-service/sonar-project.properties     (NEW)
services/ml-service/sonar-project.properties      (NEW)
services/ops-service/sonar-project.properties     (NEW)
frontend/sonar-project.properties                 (NEW)
services/*/requirements-dev.txt                   (+pytest-cov)
services/*/pytest.ini or setup.cfg                (default --cov flags)
frontend/jest.config.mjs                          (coverageReporters, collectCoverageFrom)
.gitignore                                        (coverage/, coverage.xml, .scannerwork/)
```

### 6.2 Secrets requeridos

- `SONAR_TOKEN` — token de organización generado en Sonar (Account → Security → Generate token, tipo "Global Analysis Token" para toda la org).

`GITHUB_TOKEN` viene provisto automáticamente por Actions.

### 6.3 Trigger del scanner

- **push a main/dev/qa** → analiza rama, actualiza baseline overall.
- **pull_request** → analiza el diff, corre el gate sobre new code, deja comentario en el PR.

Nota: los PRs desde forks NO reciben SONAR_TOKEN (GitHub bloquea secrets en forks) → el scan no correrá. Aceptable porque el proyecto no acepta PRs externos.

## 7. Roles

| Rol | Responsabilidad |
|---|---|
| Tech lead | Crear org Sonar, gestionar secret, ajustar quality gate |
| Cada dev | Resolver issues señalados en su PR ANTES de merge (fase 2 en adelante) |
| Automation | Scanner corre automático en CI; no requiere acción manual |

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Fase 2 (bloqueante) bloquea el sprint por deuda vieja | Filosofía Clean as You Code: el gate aplica sobre **new code only**; deuda histórica queda en overall sin bloquear. |
| Coverage cae si añadimos features sin tests | Threshold 70% new code obliga a testear lo nuevo. Casos justificados (Recharts) están excluidos. |
| CI se vuelve lento | Scanner añade 30-60s por proyecto. Aceptable dado que corren en paralelo (matriz backend + job frontend). |
| Falsos positivos de Sonar en código Python con SQLAlchemy | Marcar como "won't fix" en la UI cuando aplique; ir refinando la baseline. |
| Secret leak si alguien forkea el repo | Los forks no reciben secrets en Actions (GitHub default). |

## 9. Métricas de éxito (para revisar en 3 meses)

- **Coverage overall** en los 5 proyectos ≥ 70% (línea base actual estimada: backend ~85%, frontend ~30%).
- **0 vulnerabilities** de severidad Critical/High en `main`.
- **100% security hotspots** revisados.
- **Duplicación** ≤ 5% en cualquier proyecto.
- **Technical debt ratio** ≤ 5% (Sonar rating A).
- **PRs bloqueados por Sonar** ≤ 10% (indicador de que el gate no es demasiado estricto).

## 10. Post-MVP / follow-ups

- **SonarLint en IDEs** de los devs (VSCode + PyCharm plugins) — feedback inmediato sin esperar CI.
- **Reglas custom** para patrones del proyecto (ej: prohibir `except:` sin tipo, requerir logging estructurado).
- **Integrar con dashboard/status** — mostrar badge de quality gate en el README.
- **Sincronizar con backlog** — issues Sonar → tickets en `docs/BACKLOG_POST_MVP.md` cuando pasen a "won't fix now".

---

## Referencias
- SonarCloud docs: https://docs.sonarcloud.io
- Monorepo mode: https://docs.sonarcloud.io/advanced-setup/monorepos/
- Clean as You Code: https://docs.sonarcloud.io/user-guide/clean-as-you-code/
- GitHub Action: https://github.com/SonarSource/sonarqube-scan-action
