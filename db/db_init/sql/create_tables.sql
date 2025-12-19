-- 所有表结构创建SQL

-- 总表结构
CREATE TABLE IF NOT EXISTS artifact (
    id INT AUTO_INCREMENT PRIMARY KEY, -- 文物ID
    name VARCHAR(128) NOT NULL,        -- 文物名称
    number VARCHAR(64),
    category_id INT,                   -- 文物类别ID  
    dynasty_id INT,                    -- 文物朝代ID
    image_id INT,                      -- 图片ID
    motif_and_pattern_id INT,          -- 纹饰与图案ID
    object_type_id INT,                -- 器物类型ID
    form_and_structure_id INT,         -- 形式与结构ID
    description TEXT,                  -- 文物描述
    sourced_id INT,                    -- 文物来源ID(外键博物馆museum_id)
    -- 外键约束
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasty(id) ON DELETE SET NULL,
    FOREIGN KEY (object_type_id) REFERENCES object_type(id) ON DELETE SET NULL,
    FOREIGN KEY (form_and_structure_id) REFERENCES form_and_structure(id) ON DELETE SET NULL,
    FOREIGN KEY (motif_and_pattern_id) REFERENCES motif_and_pattern(id) ON DELETE SET NULL,
    FOREIGN KEY (sourced_id) REFERENCES museum(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 博物馆表
CREATE TABLE IF NOT EXISTS museum (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 类别表（原项目中更细化的分类基础）
CREATE TABLE IF NOT EXISTS category (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 朝代表
CREATE TABLE IF NOT EXISTS dynasty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 图片表（image） - 用于存储文物多图
CREATE TABLE IF NOT EXISTS image (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL,          -- 图片路径或URL  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 纹饰与图案表（motif_and_pattern）
CREATE TABLE IF NOT EXISTS motif_and_pattern (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 器物类型表（object_type）
CREATE TABLE IF NOT EXISTS object_type (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 形式与结构表（form_and_structure）
CREATE TABLE IF NOT EXISTS form_and_structure (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    object_type_id INT,
    FOREIGN KEY (object_type_id) REFERENCES object_type(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 北京故宫文物主表
CREATE TABLE IF NOT EXISTS artifact_beijing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    category_id INT,
    number VARCHAR(64),
    dynasty_id INT,
    image_id INT,
    motif_and_pattern_id INT,
    object_type_id INT,
    form_and_structure_id INT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasty(id) ON DELETE SET NULL,
    FOREIGN KEY (image_id) REFERENCES image(id) ON DELETE SET NULL,
    FOREIGN KEY (motif_and_pattern_id) REFERENCES motif_and_pattern(id) ON DELETE SET NULL,
    FOREIGN KEY (object_type_id) REFERENCES object_type(id) ON DELETE SET NULL,
    FOREIGN KEY (form_and_structure_id) REFERENCES form_and_structure(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 台北故宫文物主表（结构与北京一致）
CREATE TABLE IF NOT EXISTS artifact_taipei (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    category_id INT,
    number VARCHAR(64),
    dynasty_id INT,
    image_id INT,
    motif_and_pattern_id INT,
    object_type_id INT,
    form_and_structure_id INT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasty(id) ON DELETE SET NULL,
    FOREIGN KEY (image_id) REFERENCES image(id) ON DELETE SET NULL,
    FOREIGN KEY (motif_and_pattern_id) REFERENCES motif_and_pattern(id) ON DELETE SET NULL,
    FOREIGN KEY (object_type_id) REFERENCES object_type(id) ON DELETE SET NULL,
    FOREIGN KEY (form_and_structure_id) REFERENCES form_and_structure(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户表（已存在，保持兼容）
CREATE TABLE IF NOT EXISTS user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role ENUM('admin', 'guest') DEFAULT 'guest',
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 操作日志表（log）
CREATE TABLE IF NOT EXISTS log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(128) NOT NULL,       -- 如 "create_artifact", "update_user", "import_excel"
    target_table VARCHAR(64),
    target_id INT,
    details TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alembic 版本表（Flask-Migrate 遗留，若不需要可忽略，本脚本保留兼容）
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
