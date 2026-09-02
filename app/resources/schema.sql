-- HealthCure - CardioPredict
-- Base de datos MySQL

CREATE DATABASE IF NOT EXISTS healthcure_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE healthcure_db;

-- ============================================================
-- 1. USUARIOS (sistema de autenticación)
-- ============================================================
CREATE TABLE usuarios (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(150)  NOT NULL,
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    rol             ENUM('admin', 'usuario') NOT NULL DEFAULT 'usuario',
    activo          BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX ix_usuarios_email (email)
);

-- ============================================================
-- 2. PACIENTES (datos administrativos)
-- ============================================================
CREATE TABLE pacientes (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(150)  NOT NULL,
    documento_identidad VARCHAR(30)   NOT NULL UNIQUE,
    fecha_nacimiento    DATE          NOT NULL,
    sexo                ENUM('M', 'F') NOT NULL,
    usuario_creador_id  BIGINT        NULL,
    talla_cm            DECIMAL(5,1)  NULL,
    peso_kg             DECIMAL(5,1)  NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX ix_pacientes_documento (documento_identidad)
);

-- ============================================================
-- 3. EVALUACIONES (cada predicción cardíaca)
-- ============================================================
CREATE TABLE evaluaciones (
    id                      BIGINT AUTO_INCREMENT PRIMARY KEY,
    paciente_id             BIGINT      NOT NULL,
    usuario_id              BIGINT      NOT NULL,

    -- Variables predictoras
    edad                    SMALLINT    NOT NULL,
    presion_alta            BOOLEAN     NOT NULL DEFAULT FALSE,
    colesterol_alto         BOOLEAN     NOT NULL DEFAULT FALSE,
    tabaquismo              BOOLEAN     NOT NULL DEFAULT FALSE,
    actividad_fisica        BOOLEAN     NOT NULL DEFAULT FALSE,
    antecedente_acv         BOOLEAN     NOT NULL DEFAULT FALSE,
    diabetes                BOOLEAN     NOT NULL DEFAULT FALSE,
    salud_general           SMALLINT    NOT NULL DEFAULT 3,
    dificultad_para_caminar BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Resultado del modelo
    probabilidad            DECIMAL(7,6) NOT NULL,
    clasificacion           ENUM('bajo', 'moderado', 'alto') NOT NULL,
    modelo_version          VARCHAR(50)  NULL,

    created_at              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_evaluacion_paciente
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_evaluacion_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT,

    INDEX ix_evaluaciones_paciente_id (paciente_id),
    INDEX ix_evaluaciones_created_at (created_at)
);
