-- ============================================================================
-- UC-SC-02: Waste Prediction & Reduction — Analytics Schema DDL
-- ============================================================================
-- Purpose:  Create 8 analytics tables on aws-luckyus-dbatest-rw → schema test
-- Usage:    mysql -h aws-luckyus-dbatest-rw < sql/02_create_analytics_schema.sql
-- Author:   DBA/Infrastructure Team
-- Created:  2026-02-18
-- ============================================================================

USE test;

-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 1: waste_daily_detail                                            │
-- │ Row-level waste tracking per (date, store, SKU)                        │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_daily_detail (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    -- Dimensional keys
    waste_date                 DATE          NOT NULL  COMMENT '废弃日期 / Waste event date',
    shop_dept_id               BIGINT        NOT NULL  COMMENT '门店ID / Store ID',
    shop_name                  VARCHAR(100)            COMMENT '门店名称 / Store name (denorm)',
    goods_code                 VARCHAR(32)   NOT NULL  COMMENT '货物编号(GS) / Goods code',
    goods_name                 VARCHAR(200)            COMMENT '货物名称 / Goods name (denorm)',
    large_class_name           VARCHAR(100)            COMMENT '大类名称 / Category name',
    -- Shelf-life attributes
    shelf_life_tier            ENUM('ULTRA_SHORT','SHORT','MEDIUM','LONG')
                                                       COMMENT '保质期层级 / Shelf-life tier',
    shelf_life_hours           INT                     COMMENT '保质期(小时) / Shelf life in hours',
    storage_type               ENUM('NORMAL','FROZEN','REFRIGERATED')
                                                       COMMENT '存储类型 / Storage type',
    -- Waste quantities
    waste_qty_normal           DECIMAL(12,2) DEFAULT 0 COMMENT '常温废弃量 / Room-temp waste qty',
    waste_qty_frozen           DECIMAL(12,2) DEFAULT 0 COMMENT '冷冻废弃量 / Frozen waste qty',
    waste_qty_refrigerated     DECIMAL(12,2) DEFAULT 0 COMMENT '冷藏废弃量 / Refrigerated waste qty',
    waste_qty_total            DECIMAL(12,2)           COMMENT '总废弃量 / Total waste qty',
    -- Financial impact
    unit_cost                  DECIMAL(10,4)           COMMENT '单位成本 / Unit cost estimate',
    waste_cost                 DECIMAL(12,2)           COMMENT '废弃成本 / Waste cost = qty * unit_cost',
    -- Context
    consumption_qty            DECIMAL(12,2)           COMMENT '当日消耗量 / Same-day consumption for ratio',
    waste_pct                  DECIMAL(10,4)           COMMENT '废弃率 / waste_qty / (consumption + waste)',
    -- Source tracking
    abandon_task_ids           TEXT                    COMMENT '废弃任务ID列表 / Source abandon task IDs',
    expiry_print_count         INT                     COMMENT '到期标签数 / Expiry labels printed that day',
    -- Metadata
    computed_at                DATETIME      DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_shop   (waste_date, shop_dept_id),
    INDEX idx_date_goods  (waste_date, goods_code),
    INDEX idx_shop_goods  (shop_dept_id, goods_code),
    INDEX idx_date        (waste_date),
    INDEX idx_tier        (shelf_life_tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 每日废弃明细 / Daily waste detail by store-SKU';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 2: waste_consumption_daily                                       │
-- │ Daily consumption actuals per (date, store, SKU) — forecast foundation │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_consumption_daily (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    consumption_date           DATE          NOT NULL  COMMENT '消耗日期 / Consumption date',
    shop_dept_id               BIGINT        NOT NULL  COMMENT '门店ID / Store ID',
    goods_code                 VARCHAR(32)   NOT NULL  COMMENT '货物编号(GS) / Goods code',
    -- Consumption from stock changes (reason_code IN 025,1001,1002 AND total_adjust_num < 0)
    actual_consumption         DECIMAL(12,2)           COMMENT '实际消耗量 / Actual consumption qty',
    -- Context features for forecasting
    day_of_week                TINYINT                 COMMENT '星期几(1=Mon) / Day of week',
    is_weekend                 BOOLEAN                 COMMENT '是否周末 / Weekend flag',
    -- Rolling averages (populated by sp_build_consumption_features)
    consumption_7d_avg         DECIMAL(12,2)           COMMENT '7日滚动均值 / 7-day rolling avg',
    consumption_7d_stddev      DECIMAL(12,2)           COMMENT '7日滚动标准差 / 7-day rolling stddev',
    consumption_14d_avg        DECIMAL(12,2)           COMMENT '14日滚动均值 / 14-day rolling avg',
    consumption_30d_avg        DECIMAL(12,2)           COMMENT '30日滚动均值 / 30-day rolling avg',
    same_dow_4wk_avg           DECIMAL(12,2)           COMMENT '同星期4周均值 / Same DOW 4-week avg',
    consumption_trend_7d       DECIMAL(10,4)           COMMENT '7日趋势 / (7d_avg-14d_avg)/14d_avg',
    -- Prediction comparison (from ireplenishment)
    predicted_demand           DECIMAL(12,2)           COMMENT '预测需求 / Algorithm predicted demand',
    predicted_order_qty        DECIMAL(12,2)           COMMENT '预测订货量 / Algorithm order suggestion',
    forecast_error             DECIMAL(12,2)           COMMENT '预测误差 / predicted - actual',
    abs_pct_error              DECIMAL(10,4)           COMMENT '绝对百分比误差 / APE',
    -- Forecast model v1 output
    v1_forecast                DECIMAL(12,2)           COMMENT 'v1预测值 / Forecast model v1 output',
    v1_forecast_error          DECIMAL(12,2)           COMMENT 'v1预测误差 / v1 forecast - actual',
    v1_abs_pct_error           DECIMAL(10,4)           COMMENT 'v1绝对百分比误差 / v1 APE',
    -- Metadata
    computed_at                DATETIME      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_date_shop_goods (consumption_date, shop_dept_id, goods_code),
    INDEX idx_date        (consumption_date),
    INDEX idx_shop        (shop_dept_id),
    INDEX idx_goods       (goods_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 每日消耗量 / Daily consumption actuals for forecasting';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 3: waste_shelf_life_config                                       │
-- │ Materialized shelf-life configuration per SKU                          │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_shelf_life_config (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    goods_code                 VARCHAR(32)   NOT NULL  COMMENT '货物编号 / Goods code (GS)',
    goods_name                 VARCHAR(200)            COMMENT '货物名称 / Goods name',
    large_class_name           VARCHAR(100)            COMMENT '大类名称 / Category',
    -- Shelf-life configs (from t_goods_expiry_config)
    open_expiry_hours          INT                     COMMENT '开封有效期(小时) / Open-package expiry hours',
    container_expiry_hours     INT                     COMMENT '容器存储有效期(小时) / Container storage expiry hours',
    thaw_expiry_hours          INT                     COMMENT '解冻有效期(小时) / Thaw/unfreeze expiry hours',
    min_expiry_hours           INT                     COMMENT '最短有效期(小时) / Shortest applicable expiry',
    -- Tier classification
    shelf_life_tier            ENUM('ULTRA_SHORT','SHORT','MEDIUM','LONG')
                                                       COMMENT '保质期层级 / Tier (ULTRA:<24h, SHORT:1-3d, MEDIUM:3-14d, LONG:14d+)',
    -- Status
    is_active                  BOOLEAN       DEFAULT TRUE COMMENT '是否有效 / Active flag',
    -- Metadata
    synced_at                  DATETIME      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_goods   (goods_code),
    INDEX idx_tier           (shelf_life_tier),
    INDEX idx_category       (large_class_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 保质期配置 / Materialized shelf-life config per SKU';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 4: waste_batch_risk_score                                        │
-- │ Per-batch expiry risk scoring                                          │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_batch_risk_score (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    score_date                 DATE          NOT NULL  COMMENT '评分日期 / Score computation date',
    shop_dept_id               BIGINT        NOT NULL  COMMENT '门店ID / Store ID',
    goods_code                 VARCHAR(32)   NOT NULL  COMMENT '货物编号 / Goods code',
    -- Batch identification
    batch_id                   VARCHAR(64)             COMMENT '批次号 / Batch/collection code',
    receipt_time               DATETIME                COMMENT '收货时间 / Receipt timestamp',
    expiry_time                DATETIME                COMMENT '到期时间 / Expiry timestamp',
    -- Risk calculation inputs
    hours_remaining            DECIMAL(8,1)            COMMENT '剩余小时数 / Hours until expiry',
    current_stock_qty          DECIMAL(12,2)           COMMENT '当前库存量 / Current on-hand qty',
    forecast_consumption_24h   DECIMAL(12,2)           COMMENT '未来24h预测消耗 / Forecasted consumption next 24h',
    forecast_consumption_48h   DECIMAL(12,2)           COMMENT '未来48h预测消耗 / Forecasted consumption next 48h',
    -- Risk component scores (0.0 to 1.0)
    expiry_urgency_score       DECIMAL(5,2)            COMMENT '到期紧迫分 / Expiry urgency (0-1)',
    excess_inventory_score     DECIMAL(5,2)            COMMENT '库存过剩分 / Excess inventory (0-1)',
    volatility_score           DECIMAL(5,2)            COMMENT '波动性分 / Demand volatility (0-1)',
    shelf_tier_penalty_score   DECIMAL(5,2)            COMMENT '保质期惩罚分 / Shelf tier penalty (0-1)',
    -- Final risk score
    risk_score                 DECIMAL(5,2)            COMMENT '风险分(0-100) / Risk score 0-100',
    risk_tier                  ENUM('LOW','MEDIUM','HIGH','CRITICAL')
                                                       COMMENT '风险等级 / Risk tier',
    -- Recommended action
    recommended_action         ENUM('HOLD','PROMOTE','TRANSFER','DISCOUNT','DISPOSE')
                                                       COMMENT '建议操作 / Recommended action',
    transfer_candidate_store   BIGINT                  COMMENT '建议调拨门店 / Suggested transfer destination store',
    -- Metadata
    computed_at                DATETIME      DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_shop   (score_date, shop_dept_id),
    INDEX idx_risk        (risk_tier, score_date),
    INDEX idx_expiry      (expiry_time),
    INDEX idx_goods       (goods_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 批次过期风险评分 / Batch-level expiry risk scores';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 5: waste_transfer_recommendations                                │
-- │ Cross-store transfer optimization                                      │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_transfer_recommendations (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    recommendation_date        DATE          NOT NULL  COMMENT '建议日期 / Recommendation date',
    -- Transfer details
    source_store_id            BIGINT        NOT NULL  COMMENT '调出门店ID / Source store',
    source_store_name          VARCHAR(100)            COMMENT '调出门店名 / Source store name',
    dest_store_id              BIGINT        NOT NULL  COMMENT '调入门店ID / Destination store',
    dest_store_name            VARCHAR(100)            COMMENT '调入门店名 / Destination store name',
    goods_code                 VARCHAR(32)   NOT NULL  COMMENT '货物编号 / Goods code',
    goods_name                 VARCHAR(200)            COMMENT '货物名称 / Goods name',
    -- Quantities
    transfer_qty               DECIMAL(12,2)           COMMENT '建议调拨量 / Recommended transfer qty',
    source_excess_qty          DECIMAL(12,2)           COMMENT '来源过剩量 / Source excess (stock - forecast)',
    dest_deficit_qty           DECIMAL(12,2)           COMMENT '目标缺口量 / Dest deficit (forecast - stock)',
    -- Risk context
    source_hours_to_expiry     DECIMAL(8,1)            COMMENT '来源剩余小时 / Hours to expiry at source',
    source_risk_score          DECIMAL(5,2)            COMMENT '来源风险分 / Source risk score',
    -- Financial impact
    waste_savings_est          DECIMAL(10,2)           COMMENT '预计节约废弃成本 / Est. waste cost saved',
    transfer_cost_est          DECIMAL(10,2)           COMMENT '预计调拨成本 / Est. transfer logistics cost',
    net_benefit                DECIMAL(10,2)           COMMENT '净效益 / Net benefit (savings - cost)',
    -- Status
    status                     ENUM('PENDING','APPROVED','EXECUTED','EXPIRED','CANCELLED')
                                            DEFAULT 'PENDING' COMMENT '状态 / Recommendation status',
    -- Metadata
    computed_at                DATETIME      DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date        (recommendation_date),
    INDEX idx_source      (source_store_id, recommendation_date),
    INDEX idx_dest        (dest_store_id, recommendation_date),
    INDEX idx_status      (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 跨店调拨建议 / Cross-store transfer recommendations';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 6: waste_summary                                                 │
-- │ Aggregated waste metrics by period and dimension                       │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_summary (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    -- Period
    period_type                ENUM('DAILY','WEEKLY','MONTHLY','ROLLING_7D','ROLLING_30D')
                                            NOT NULL  COMMENT '汇总周期 / Period type',
    period_start               DATE                   COMMENT '周期起始 / Period start',
    period_end                 DATE                   COMMENT '周期截止 / Period end',
    -- Dimension
    dimension_type             ENUM('OVERALL','STORE','PRODUCT','CATEGORY','SHELF_TIER','DOW','STORAGE_TYPE')
                                            NOT NULL  COMMENT '维度类型 / Dimension type',
    dimension_value            VARCHAR(100)            COMMENT '维度值 / Dimension value',
    dimension_name             VARCHAR(200)            COMMENT '维度名称 / Dimension display name',
    -- Waste metrics
    total_waste_qty            DECIMAL(14,2)           COMMENT '总废弃量 / Total waste quantity',
    total_waste_cost           DECIMAL(14,2)           COMMENT '总废弃成本 / Total waste cost ($)',
    total_consumption          DECIMAL(14,2)           COMMENT '总消耗量 / Total consumption',
    waste_rate                 DECIMAL(10,4)           COMMENT '废弃率 / Waste rate %',
    -- Forecast accuracy (waste-specific)
    waste_mape                 DECIMAL(10,4)           COMMENT '消耗预测MAPE / Consumption forecast MAPE',
    waste_wmape                DECIMAL(10,4)           COMMENT '消耗预测WMAPE / Weighted MAPE',
    waste_bias                 DECIMAL(12,4)           COMMENT '预测偏差 / Forecast bias (+=over)',
    -- Risk distribution
    batches_critical           INT                     COMMENT '高风险批次数 / Critical risk batch count',
    batches_high               INT                     COMMENT '较高风险批次数 / High risk batch count',
    -- Transfer metrics
    transfers_recommended      INT                     COMMENT '建议调拨次数 / Recommended transfers',
    transfers_executed         INT                     COMMENT '执行调拨次数 / Executed transfers',
    transfer_savings           DECIMAL(12,2)           COMMENT '调拨节约成本 / Transfer savings ($)',
    -- Volume
    record_count               INT                     COMMENT '记录数 / Number of detail records',
    sku_count                  INT                     COMMENT 'SKU数 / Distinct SKU count',
    -- Metadata
    computed_at                DATETIME      DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period    (period_type, period_start),
    INDEX idx_dimension (dimension_type, dimension_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 废弃汇总指标 / Aggregated waste metrics by period & dimension';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 7: waste_alerts                                                  │
-- │ Threshold-based alerting for waste anomalies                           │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_alerts (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    alert_timestamp            DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '预警时间 / Alert time',
    alert_date                 DATE          NOT NULL  COMMENT '预警日期 / Alert date',
    alert_type                 ENUM('CRITICAL','WARNING','BIAS','COVERAGE','TREND','EXPIRY_SURGE')
                                            NOT NULL  COMMENT '预警类型 / Alert type',
    entity_type                ENUM('STORE','PRODUCT','CATEGORY','BATCH','SYSTEM')
                                            NOT NULL  COMMENT '实体类型 / Entity type',
    entity_id                  VARCHAR(50)             COMMENT '实体ID / Entity identifier',
    entity_name                VARCHAR(200)            COMMENT '实体名称 / Entity name',
    metric_name                VARCHAR(50)             COMMENT '指标名称 / Metric name',
    metric_value               DECIMAL(10,4)           COMMENT '指标值 / Current value',
    threshold_value            DECIMAL(10,4)           COMMENT '阈值 / Threshold breached',
    baseline_value             DECIMAL(10,4)           COMMENT '基线值 / Historical baseline',
    description                TEXT                    COMMENT '描述 / Alert description',
    recommended_action         TEXT                    COMMENT '建议措施 / Recommended action',
    is_acknowledged            BOOLEAN       DEFAULT FALSE COMMENT '是否已确认 / Acknowledged flag',
    acknowledged_by            VARCHAR(100)            COMMENT '确认人 / Acknowledged by',
    acknowledged_at            DATETIME                COMMENT '确认时间 / Ack timestamp',
    INDEX idx_type_time (alert_type, alert_timestamp),
    INDEX idx_date      (alert_date),
    INDEX idx_entity    (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 废弃预警记录 / Waste quality alerts with ack workflow';


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLE 8: waste_pipeline_run_log                                        │
-- │ ETL pipeline execution tracking (mirrors UC-SC-01 pattern)             │
-- └─────────────────────────────────────────────────────────────────────────┘

CREATE TABLE IF NOT EXISTS test.waste_pipeline_run_log (
    id                         BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    run_id                     VARCHAR(64)   NOT NULL  COMMENT '运行ID / UUID',
    pipeline_name              VARCHAR(100)  NOT NULL  COMMENT '管道名称 / Pipeline name',
    step_name                  VARCHAR(100)            COMMENT '步骤名称 / Step name',
    run_start                  DATETIME      NOT NULL  COMMENT '开始时间 / Start time',
    run_end                    DATETIME                COMMENT '结束时间 / End time',
    duration_seconds           INT                     COMMENT '耗时(秒) / Duration',
    data_date_start            DATE                    COMMENT '数据起始 / Data start date',
    data_date_end              DATE                    COMMENT '数据截止 / Data end date',
    status                     ENUM('RUNNING','SUCCESS','FAILED','PARTIAL','SKIPPED')
                                            NOT NULL DEFAULT 'RUNNING',
    rows_extracted             INT,
    rows_transformed           INT,
    rows_loaded                INT,
    rows_errored               INT           DEFAULT 0,
    target_table               VARCHAR(100),
    error_message              TEXT,
    error_detail               TEXT,
    triggered_by               VARCHAR(100)  DEFAULT 'scheduler',
    host_name                  VARCHAR(100),
    config_snapshot            JSON,
    created_at                 DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_run_step        (run_id, step_name),
    INDEX idx_pipeline_status        (pipeline_name, status),
    INDEX idx_run_start              (run_start),
    INDEX idx_data_date              (data_date_start, data_date_end),
    INDEX idx_status                 (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02: 管道运行日志 / Waste pipeline execution tracking';


-- ============================================================================
-- STAGING TABLES (temporary, populated by Python orchestrator)
-- ============================================================================
-- These tables hold extracted data from source databases before SP processing.
-- Pattern: TRUNCATE → INSERT (idempotent per pipeline run).

CREATE TABLE IF NOT EXISTS test.tmp_stock_changes (
    id                BIGINT,
    shop_dept_id      BIGINT,
    goods_mid         VARCHAR(64),
    reason_code       VARCHAR(16),
    reason_type       INT,
    total_adjust_num  DECIMAL(14,2),
    operated_time     DATETIME,
    adjust_time       DATETIME,
    remark            VARCHAR(500),
    create_time       DATETIME,
    INDEX idx_shop_goods (shop_dept_id, goods_mid),
    INDEX idx_time       (operated_time),
    INDEX idx_reason     (reason_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: stock change records from scm-shopstock';

CREATE TABLE IF NOT EXISTS test.tmp_abandon_tasks (
    id                         BIGINT,
    dept_id                    BIGINT,
    spec_mid                   VARCHAR(64),
    abandoned_date             DATETIME,
    abandon_amount_normal      DECIMAL(12,2),
    abandon_amount_frozen      DECIMAL(12,2),
    abandon_amount_refrigerated DECIMAL(12,2),
    task_status                INT,
    create_time                DATETIME,
    update_time                DATETIME,
    INDEX idx_dept       (dept_id),
    INDEX idx_date       (abandoned_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: disposal tasks from opqualitycontrol';

CREATE TABLE IF NOT EXISTS test.tmp_expiry_prints (
    id                BIGINT,
    dept_id           BIGINT,
    spec_mid          VARCHAR(64),
    expire_time       DATETIME,
    print_time        DATETIME,
    print_type        INT,
    collection_code   VARCHAR(64),
    create_time       DATETIME,
    INDEX idx_dept    (dept_id),
    INDEX idx_expire  (expire_time),
    INDEX idx_batch   (collection_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: expiry label prints from opqualitycontrol';

CREATE TABLE IF NOT EXISTS test.tmp_shelf_life_config (
    id                     BIGINT,
    spec_mid               VARCHAR(64),
    goods_name             VARCHAR(200),
    open_time_data         INT,
    open_time_unit         INT,
    container_time_data    INT,
    container_time_unit    INT,
    thaw_time_data         INT,
    thaw_time_unit         INT,
    is_deleted             TINYINT,
    create_time            DATETIME,
    update_time            DATETIME,
    INDEX idx_spec (spec_mid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: shelf-life config from opqualitycontrol';

CREATE TABLE IF NOT EXISTS test.tmp_production (
    id                  BIGINT,
    dept_id             BIGINT,
    product_status      INT,
    order_create_time   DATETIME,
    order_complete_time DATETIME,
    create_time         DATETIME,
    INDEX idx_dept      (dept_id),
    INDEX idx_status    (product_status),
    INDEX idx_time      (order_create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: production orders from opproduction';

CREATE TABLE IF NOT EXISTS test.tmp_commodity (
    id                BIGINT,
    production_id     BIGINT,
    spu_code          VARCHAR(64),
    goods_code        VARCHAR(64),
    use_amount        DECIMAL(12,2),
    create_time       DATETIME,
    INDEX idx_prod    (production_id),
    INDEX idx_spu     (spu_code),
    INDEX idx_goods   (goods_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: commodity detail from opproduction';

CREATE TABLE IF NOT EXISTS test.tmp_predictions (
    id                BIGINT,
    dept_id           BIGINT,
    goods_code        VARCHAR(64),
    forecast_date     DATE,
    vlt_avg_demand    DECIMAL(12,2),
    order_num         DECIMAL(12,2),
    create_time       DATETIME,
    INDEX idx_dept_goods (dept_id, goods_code),
    INDEX idx_date       (forecast_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: demand forecasts from ireplenishment';

CREATE TABLE IF NOT EXISTS test.tmp_goods (
    id                BIGINT,
    goods_code        VARCHAR(64),
    goods_name        VARCHAR(200),
    large_class_code  VARCHAR(32),
    large_class_name  VARCHAR(100),
    middle_class_code VARCHAR(32),
    middle_class_name VARCHAR(100),
    unit_name         VARCHAR(20),
    status            INT,
    is_deleted        TINYINT,
    INDEX idx_goods   (goods_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: product master from pub-dm';

CREATE TABLE IF NOT EXISTS test.tmp_stores (
    id                BIGINT,
    dept_id           BIGINT,
    shop_name         VARCHAR(100),
    shop_code         VARCHAR(32),
    province          VARCHAR(50),
    city              VARCHAR(50),
    shop_status       INT,
    shop_type         INT,
    is_deleted        TINYINT,
    INDEX idx_dept    (dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: store master from opshop';

CREATE TABLE IF NOT EXISTS test.tmp_formula (
    id                BIGINT,
    spu_code          VARCHAR(64),
    goods_code        VARCHAR(64),
    dosage            DECIMAL(12,4),
    formula_status    INT,
    is_deleted        TINYINT,
    INDEX idx_spu     (spu_code),
    INDEX idx_goods   (goods_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='UC-SC-02 staging: BOM/recipes from scm-commodity';


-- ============================================================================
-- END OF ANALYTICS SCHEMA DDL
-- ============================================================================
-- Total: 8 analytics tables + 10 staging tables = 18 tables
-- All tables in schema: test
-- Target server: aws-luckyus-dbatest-rw
-- ============================================================================
