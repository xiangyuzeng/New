#!/usr/bin/env python3
"""
UC-SC-02: Waste Prediction & Reduction — Pipeline Orchestrator

15-step pipeline:
  Steps 1-7:   Extract from 8 source databases → 10 staging tables
  Steps 8-15:  Call 7 stored procedures on analytics database

Usage:
  # Run for yesterday (default)
  python run_waste_pipeline.py

  # Run for specific date
  python run_waste_pipeline.py --date 2026-02-17

  # Backfill a date range
  python run_waste_pipeline.py --start-date 2025-11-01 --end-date 2026-02-17

  # Schema setup only
  python run_waste_pipeline.py --setup

  # Dry run (show steps without executing)
  python run_waste_pipeline.py --dry-run
"""

import argparse
import logging
import os
import socket
import sys
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pymysql

# Add parent directory for config imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# ─── Logging ────────────────────────────────────────────────────────────────

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
log = logging.getLogger('waste-pipeline')

# ─── Constants ──────────────────────────────────────────────────────────────

BATCH_SIZE = int(os.getenv('DEFAULT_BATCH_SIZE', config.DEFAULT_BATCH_SIZE))
SP_TIMEOUT = int(os.getenv('SP_TIMEOUT_SECONDS', config.SP_TIMEOUT_SECONDS))
STORES_IN = ','.join(str(s) for s in config.ACTIVE_STORES)
STORES_TUPLE = config.ACTIVE_STORES

# ─── Database Connections ───────────────────────────────────────────────────

def get_connection(prefix, read_timeout=300):
    """Create a PyMySQL connection using env-var prefix convention."""
    host = os.environ.get(f'{prefix}_HOST', 'localhost')
    port = int(os.environ.get(f'{prefix}_PORT', 3306))
    user = os.environ.get(f'{prefix}_USER', 'root')
    password = os.environ.get(f'{prefix}_PASSWORD', '')
    database = os.environ.get(f'{prefix}_DB', '')

    return pymysql.connect(
        host=host, port=port, user=user, password=password,
        database=database, charset='utf8mb4',
        connect_timeout=30, read_timeout=read_timeout, write_timeout=read_timeout,
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_analytics_conn(read_timeout=300):
    """Shortcut for analytics DB connection."""
    return get_connection('ANALYTICS', read_timeout=read_timeout)


# ─── Pipeline Run Logging ──────────────────────────────────────────────────

def log_pipeline_run(conn, run_id, step_name, status, start_ts,
                     rows_extracted=None, rows_loaded=None, rows_errored=0,
                     target_table=None, error_message=None,
                     data_date_start=None, data_date_end=None,
                     triggered_by='orchestrator'):
    """Insert or update a pipeline run log entry."""
    end_ts = datetime.now()
    duration = (end_ts - start_ts).total_seconds()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO test.waste_pipeline_run_log (
                    run_id, pipeline_name, step_name,
                    run_start, run_end, duration_seconds,
                    data_date_start, data_date_end,
                    status, rows_extracted, rows_loaded, rows_errored,
                    target_table, error_message, triggered_by, host_name
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    run_end = VALUES(run_end),
                    duration_seconds = VALUES(duration_seconds),
                    status = VALUES(status),
                    rows_extracted = VALUES(rows_extracted),
                    rows_loaded = VALUES(rows_loaded),
                    rows_errored = VALUES(rows_errored),
                    error_message = VALUES(error_message)
            """, (
                run_id, config.PIPELINE_NAME, step_name,
                start_ts, end_ts, duration,
                data_date_start, data_date_end,
                status, rows_extracted, rows_loaded, rows_errored,
                target_table, str(error_message)[:500] if error_message else None,
                triggered_by, socket.gethostname()[:100],
            ))
        conn.commit()
    except Exception as e:
        log.warning(f'Failed to log pipeline run: {e}')


# ─── Batch Insert Helper ───────────────────────────────────────────────────

def batch_insert(conn, table, columns, rows, batch_size=None):
    """Insert rows in batches. Returns total inserted count."""
    if not rows:
        return 0
    bs = batch_size or BATCH_SIZE
    placeholders = ','.join(['%s'] * len(columns))
    col_list = ','.join(columns)
    sql = f'INSERT INTO {table} ({col_list}) VALUES ({placeholders})'
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), bs):
            batch = rows[i:i + bs]
            cur.executemany(sql, batch)
            total += cur.rowcount
    conn.commit()
    return total


# ─── Extraction Steps (1-7) ────────────────────────────────────────────────

def extract_stock_changes(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 1: Extract stock changes from scm-shopstock (day-partitioned tables)."""
    step = 'extract_stock_changes'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting stock changes {start_date} → {end_date}')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    # Truncate staging table
    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_stock_changes')
    analytics_conn.commit()

    columns = [
        'id', 'shop_dept_id', 'goods_mid', 'reason_code', 'reason_type',
        'total_adjust_num', 'operated_time', 'adjust_time', 'remark', 'create_time',
    ]

    total_rows = 0
    try:
        source_conn = get_connection('SCM_SHOPSTOCK')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to scm-shopstock: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_stock_changes',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        # Iterate over each date to pick the right DOW table
        current = start_date
        while current <= end_date:
            dow_idx = current.weekday()  # 0=Monday
            table_name = config.DOW_TABLE_MAP[dow_idx]
            query = f"""
                SELECT id, shop_dept_id, goods_mid, reason_code, reason_type,
                       total_adjust_num, operated_time, adjust_time, remark, create_time
                FROM {table_name}
                WHERE shop_dept_id IN ({STORES_IN})
                  AND DATE(operated_time) = %s
            """
            with source_conn.cursor() as cur:
                cur.execute(query, (current,))
                rows = cur.fetchall()

            if rows:
                values = [tuple(r[c] for c in columns) for r in rows]
                inserted = batch_insert(analytics_conn, 'test.tmp_stock_changes', columns, values)
                total_rows += inserted
                log.info(f'[{step}] {current} ({table_name}): {inserted} rows')

            current += timedelta(days=1)

        log.info(f'[{step}] Total: {total_rows} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total_rows, rows_loaded=total_rows,
                         target_table='tmp_stock_changes',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         rows_extracted=total_rows, error_message=str(e),
                         target_table='tmp_stock_changes',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_rows


def extract_disposal(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 2: Extract disposal/abandon tasks from opqualitycontrol."""
    step = 'extract_disposal'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting disposal tasks {start_date} → {end_date}')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_abandon_tasks')
    analytics_conn.commit()

    columns = [
        'id', 'dept_id', 'spec_mid', 'abandoned_date',
        'abandon_amount_normal', 'abandon_amount_frozen',
        'abandon_amount_refrigerated', 'task_status', 'create_time', 'update_time',
    ]

    total_rows = 0
    try:
        source_conn = get_connection('OPQC')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to opqualitycontrol: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_abandon_tasks',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        query = """
            SELECT id, dept_id, spec_mid, abandoned_date,
                   abandon_amount_normal, abandon_amount_frozen,
                   abandon_amount_refrigerated, task_status, create_time, update_time
            FROM t_goods_abandon_task_form
            WHERE dept_id IN ({stores})
              AND abandoned_date BETWEEN %s AND %s
        """.format(stores=STORES_IN)

        with source_conn.cursor() as cur:
            cur.execute(query, (start_date, datetime.combine(end_date, datetime.max.time())))
            rows = cur.fetchall()

        if rows:
            values = [tuple(r[c] for c in columns) for r in rows]
            total_rows = batch_insert(analytics_conn, 'test.tmp_abandon_tasks', columns, values)

        log.info(f'[{step}] Total: {total_rows} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total_rows, rows_loaded=total_rows,
                         target_table='tmp_abandon_tasks',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_abandon_tasks',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_rows


def extract_expiry_labels(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 3: Extract expiry print logs from opqualitycontrol."""
    step = 'extract_expiry_labels'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting expiry labels {start_date} → {end_date}')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_expiry_prints')
    analytics_conn.commit()

    columns = [
        'id', 'dept_id', 'spec_mid', 'expire_time', 'print_time',
        'print_type', 'collection_code', 'create_time',
    ]

    total_rows = 0
    try:
        source_conn = get_connection('OPQC')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to opqualitycontrol: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_expiry_prints',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        # Get all labels for batches that expire on or after start_date
        query = """
            SELECT id, dept_id, spec_mid, expire_time, print_time,
                   print_type, collection_code, create_time
            FROM t_expiry_print_log
            WHERE dept_id IN ({stores})
              AND expire_time >= %s
        """.format(stores=STORES_IN)

        with source_conn.cursor() as cur:
            cur.execute(query, (start_date,))
            rows = cur.fetchall()

        if rows:
            values = [tuple(r[c] for c in columns) for r in rows]
            total_rows = batch_insert(analytics_conn, 'test.tmp_expiry_prints', columns, values)

        log.info(f'[{step}] Total: {total_rows} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total_rows, rows_loaded=total_rows,
                         target_table='tmp_expiry_prints',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_expiry_prints',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_rows


def extract_shelf_life_config(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 4: Extract shelf-life configuration from opqualitycontrol."""
    step = 'extract_shelf_life_config'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting shelf-life config')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_shelf_life_config')
    analytics_conn.commit()

    columns = [
        'id', 'spec_mid', 'goods_name', 'open_time_data', 'open_time_unit',
        'container_time_data', 'container_time_unit', 'thaw_time_data',
        'thaw_time_unit', 'is_deleted', 'create_time', 'update_time',
    ]

    total_rows = 0
    try:
        source_conn = get_connection('OPQC')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to opqualitycontrol: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_shelf_life_config',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        query = """
            SELECT id, spec_mid, goods_name, open_time_data, open_time_unit,
                   container_time_data, container_time_unit, thaw_time_data,
                   thaw_time_unit, is_deleted, create_time, update_time
            FROM t_goods_expiry_config
            WHERE is_deleted = 0
        """
        with source_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        if rows:
            values = [tuple(r[c] for c in columns) for r in rows]
            total_rows = batch_insert(analytics_conn, 'test.tmp_shelf_life_config', columns, values)

        log.info(f'[{step}] Total: {total_rows} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total_rows, rows_loaded=total_rows,
                         target_table='tmp_shelf_life_config',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_shelf_life_config',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_rows


def extract_production(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 5: Extract production orders and commodity detail from opproduction."""
    step = 'extract_production'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting production data {start_date} → {end_date}')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_production')
        cur.execute('TRUNCATE TABLE test.tmp_commodity')
    analytics_conn.commit()

    total_prod = 0
    total_comm = 0
    try:
        source_conn = get_connection('OPPROD')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to opproduction: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_production',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        # Production orders
        prod_cols = ['id', 'dept_id', 'product_status', 'order_create_time',
                     'order_complete_time', 'create_time']
        query = """
            SELECT id, dept_id, product_status, order_create_time,
                   order_complete_time, create_time
            FROM t_production
            WHERE dept_id IN ({stores})
              AND order_create_time BETWEEN %s AND %s
        """.format(stores=STORES_IN)

        with source_conn.cursor() as cur:
            cur.execute(query, (start_date, datetime.combine(end_date, datetime.max.time())))
            rows = cur.fetchall()

        if rows:
            values = [tuple(r[c] for c in prod_cols) for r in rows]
            total_prod = batch_insert(analytics_conn, 'test.tmp_production', prod_cols, values)
            log.info(f'[{step}] Production orders: {total_prod} rows')

            # Commodity detail for these production orders
            prod_ids = [r['id'] for r in rows]
            if prod_ids:
                comm_cols = ['id', 'production_id', 'spu_code', 'goods_code',
                             'use_amount', 'create_time']
                # Batch the production IDs query to avoid too-long IN clause
                for i in range(0, len(prod_ids), 1000):
                    batch_ids = prod_ids[i:i + 1000]
                    id_str = ','.join(str(pid) for pid in batch_ids)
                    query2 = f"""
                        SELECT id, production_id, spu_code, goods_code,
                               use_amount, create_time
                        FROM t_production_commodity_detail
                        WHERE production_id IN ({id_str})
                    """
                    with source_conn.cursor() as cur:
                        cur.execute(query2)
                        comm_rows = cur.fetchall()
                    if comm_rows:
                        cvalues = [tuple(r[c] for c in comm_cols) for r in comm_rows]
                        total_comm += batch_insert(
                            analytics_conn, 'test.tmp_commodity', comm_cols, cvalues)

                log.info(f'[{step}] Commodity details: {total_comm} rows')

        total = total_prod + total_comm
        log.info(f'[{step}] Total: {total} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total, rows_loaded=total,
                         target_table='tmp_production,tmp_commodity',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_production',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_prod + total_comm


def extract_predictions(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 6: Extract demand forecast predictions from ireplenishment."""
    step = 'extract_predictions'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting predictions {start_date} → {end_date}')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_predictions')
    analytics_conn.commit()

    columns = ['id', 'dept_id', 'goods_code', 'forecast_date',
               'vlt_avg_demand', 'order_num', 'create_time']

    total_rows = 0
    try:
        source_conn = get_connection('IREP')
    except Exception as e:
        log.error(f'[{step}] Cannot connect to ireplenishment: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_predictions',
                         data_date_start=start_date, data_date_end=end_date)
        return 0

    try:
        # Note: actual table name may be t_goods_vlt_day_forecast or similar.
        # Verify against ireplenishment schema if this fails.
        query = """
            SELECT id, dept_id, goods_code, forecast_date,
                   vlt_avg_demand, order_num, create_time
            FROM t_goods_vlt_day_forecast
            WHERE dept_id IN ({stores})
              AND forecast_date BETWEEN %s AND %s
        """.format(stores=STORES_IN)

        with source_conn.cursor() as cur:
            cur.execute(query, (start_date, end_date))
            rows = cur.fetchall()

        if rows:
            values = [tuple(r[c] for c in columns) for r in rows]
            total_rows = batch_insert(analytics_conn, 'test.tmp_predictions', columns, values)

        log.info(f'[{step}] Total: {total_rows} rows extracted')
        log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                         rows_extracted=total_rows, rows_loaded=total_rows,
                         target_table='tmp_predictions',
                         data_date_start=start_date, data_date_end=end_date)
    except Exception as e:
        log.error(f'[{step}] Error: {e}')
        log_pipeline_run(analytics_conn, run_id, step, 'FAILED', start_ts,
                         error_message=str(e), target_table='tmp_predictions',
                         data_date_start=start_date, data_date_end=end_date)
        raise
    finally:
        source_conn.close()

    return total_rows


def extract_master_data(run_id, start_date, end_date, analytics_conn, dry_run=False):
    """Step 7: Extract reference/master data (goods, stores, formulas)."""
    step = 'extract_master_data'
    start_ts = datetime.now()
    log.info(f'[{step}] Extracting master data')

    if dry_run:
        log.info(f'[{step}] DRY RUN — skipping')
        return 0

    with analytics_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE test.tmp_goods')
        cur.execute('TRUNCATE TABLE test.tmp_stores')
        cur.execute('TRUNCATE TABLE test.tmp_formula')
    analytics_conn.commit()

    total = 0

    # ── Goods master from pubdm ──
    try:
        pubdm_conn = get_connection('PUBDM')
        goods_cols = ['id', 'goods_code', 'goods_name', 'large_class_code',
                      'large_class_name', 'middle_class_code', 'middle_class_name',
                      'unit_name', 'status', 'is_deleted']
        query = """
            SELECT id, goods_code, goods_name, large_class_code, large_class_name,
                   middle_class_code, middle_class_name, unit_name, status, is_deleted
            FROM t_mdm_goods
            WHERE is_deleted = 0 AND status = 1
        """
        with pubdm_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        if rows:
            values = [tuple(r[c] for c in goods_cols) for r in rows]
            n = batch_insert(analytics_conn, 'test.tmp_goods', goods_cols, values)
            total += n
            log.info(f'[{step}] Goods: {n} rows')
        pubdm_conn.close()
    except Exception as e:
        log.warning(f'[{step}] Goods extraction failed: {e}')

    # ── Store master from opshop ──
    try:
        opshop_conn = get_connection('OPSHOP')
        store_cols = ['id', 'dept_id', 'shop_name', 'shop_code', 'province',
                      'city', 'shop_status', 'shop_type', 'is_deleted']
        query = """
            SELECT id, dept_id, shop_name, shop_code, province, city,
                   shop_status, shop_type, is_deleted
            FROM t_shop_info
            WHERE dept_id IN ({stores})
              AND is_deleted = 0
        """.format(stores=STORES_IN)
        with opshop_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        if rows:
            values = [tuple(r[c] for c in store_cols) for r in rows]
            n = batch_insert(analytics_conn, 'test.tmp_stores', store_cols, values)
            total += n
            log.info(f'[{step}] Stores: {n} rows')
        opshop_conn.close()
    except Exception as e:
        log.warning(f'[{step}] Store extraction failed: {e}')

    # ── BOM/recipes from scmcommodity ──
    try:
        scm_conn = get_connection('SCMCOMM')
        formula_cols = ['id', 'spu_code', 'goods_code', 'dosage',
                        'formula_status', 'is_deleted']
        query = """
            SELECT id, spu_code, goods_code, dosage, formula_status, is_deleted
            FROM t_formula_spu
            WHERE is_deleted = 0 AND formula_status = 1
        """
        with scm_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        if rows:
            values = [tuple(r[c] for c in formula_cols) for r in rows]
            n = batch_insert(analytics_conn, 'test.tmp_formula', formula_cols, values)
            total += n
            log.info(f'[{step}] Formulas: {n} rows')
        scm_conn.close()
    except Exception as e:
        log.warning(f'[{step}] Formula extraction failed: {e}')

    log.info(f'[{step}] Total: {total} rows extracted')
    log_pipeline_run(analytics_conn, run_id, step, 'SUCCESS', start_ts,
                     rows_extracted=total, rows_loaded=total,
                     target_table='tmp_goods,tmp_stores,tmp_formula',
                     data_date_start=start_date, data_date_end=end_date)
    return total


# ─── Stored Procedure Steps (8-15) ─────────────────────────────────────────

# Map config step names → (SP name, call_type)
# call_type: 'range' = (start_date, end_date), 'single' = (date)
SP_MAPPING = {
    'call_sp_consumption_daily':    ('sp_build_consumption_features', 'range'),
    'call_sp_consumption_features': (None, None),  # done by previous step
    'call_sp_consumption_forecast': ('sp_compute_consumption_forecast', 'range'),
    'call_sp_waste_landscape':      ('sp_compute_waste_landscape', 'range'),
    'call_sp_risk_scoring':         ('sp_compute_batch_risk_scores', 'single'),
    'call_sp_transfer_recs':        ('sp_compute_transfer_recommendations', 'single'),
    'call_sp_waste_summary':        ('sp_compute_waste_summary', 'single'),
    'call_sp_waste_alerts':         ('sp_check_waste_alerts', 'single'),
}


def call_stored_procedure(run_id, step_name, start_date, end_date,
                          analytics_conn, dry_run=False):
    """Call a stored procedure mapped from the pipeline step name."""
    start_ts = datetime.now()
    sp_name, call_type = SP_MAPPING.get(step_name, (None, None))

    if sp_name is None:
        log.info(f'[{step_name}] Skipping — handled by previous step')
        log_pipeline_run(analytics_conn, run_id, step_name, 'SKIPPED', start_ts,
                         data_date_start=start_date, data_date_end=end_date)
        return True

    log.info(f'[{step_name}] Calling test.{sp_name}')

    if dry_run:
        log.info(f'[{step_name}] DRY RUN — skipping')
        return True

    try:
        with analytics_conn.cursor() as cur:
            if call_type == 'range':
                cur.execute(f'CALL test.{sp_name}(%s, %s)', (start_date, end_date))
            else:
                # For single-date SPs, call once per date in the range
                current = start_date
                while current <= end_date:
                    cur.execute(f'CALL test.{sp_name}(%s)', (current,))
                    # Consume all result sets from the SP
                    while cur.nextset():
                        pass
                    current += timedelta(days=1)

            # Consume any remaining result sets
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass

        analytics_conn.commit()
        log.info(f'[{step_name}] Completed successfully')
        log_pipeline_run(analytics_conn, run_id, step_name, 'SUCCESS', start_ts,
                         data_date_start=start_date, data_date_end=end_date)
        return True

    except Exception as e:
        log.error(f'[{step_name}] Error calling {sp_name}: {e}')
        log_pipeline_run(analytics_conn, run_id, step_name, 'FAILED', start_ts,
                         error_message=str(e),
                         data_date_start=start_date, data_date_end=end_date)
        analytics_conn.rollback()
        return False


# ─── Extraction Dispatcher ──────────────────────────────────────────────────

EXTRACTION_DISPATCH = {
    'extract_stock_changes':     extract_stock_changes,
    'extract_disposal':          extract_disposal,
    'extract_expiry_labels':     extract_expiry_labels,
    'extract_shelf_life_config': extract_shelf_life_config,
    'extract_production':        extract_production,
    'extract_predictions':       extract_predictions,
    'extract_master_data':       extract_master_data,
}


# ─── Schema Setup ──────────────────────────────────────────────────────────

def setup_tables(analytics_conn):
    """Create analytics and staging tables from DDL file."""
    ddl_path = Path(__file__).resolve().parent.parent / 'sql' / '02_create_analytics_schema.sql'
    if not ddl_path.exists():
        log.error(f'DDL file not found: {ddl_path}')
        return False

    log.info(f'Reading DDL from {ddl_path}')
    ddl = ddl_path.read_text()

    # Split on semicolons and execute each statement
    statements = [s.strip() for s in ddl.split(';') if s.strip()]
    with analytics_conn.cursor() as cur:
        for stmt in statements:
            if stmt.startswith('--') or not stmt:
                continue
            # Only execute CREATE TABLE statements
            if 'CREATE TABLE' in stmt.upper():
                try:
                    cur.execute(stmt)
                    log.info(f'  Created: {stmt.split("(")[0].strip().split()[-1]}')
                except pymysql.err.OperationalError as e:
                    if e.args[0] == 1050:  # table already exists
                        log.info(f'  Already exists: {stmt.split("(")[0].strip().split()[-1]}')
                    else:
                        raise
    analytics_conn.commit()
    log.info('Schema setup complete')
    return True


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(start_date, end_date, dry_run=False):
    """Execute the full 15-step pipeline for a date range."""
    run_id = str(uuid.uuid4())[:12]
    run_start = datetime.now()

    log.info('=' * 70)
    log.info(f'UC-SC-02 Waste Pipeline — Run {run_id}')
    log.info(f'Date range: {start_date} → {end_date}')
    log.info(f'Dry run: {dry_run}')
    log.info('=' * 70)

    analytics_conn = None
    steps_ok = 0
    steps_failed = 0
    steps_skipped = 0

    try:
        analytics_conn = get_analytics_conn(read_timeout=SP_TIMEOUT)

        # Log pipeline start
        log_pipeline_run(analytics_conn, run_id, 'pipeline_master', 'RUNNING',
                         run_start, data_date_start=start_date, data_date_end=end_date,
                         triggered_by='cli')

        # ── Phase 1: Extraction (Steps 1-7) ──────────────────────────────
        log.info('── Phase 1: Extraction ─────────────────────────────')
        for step_name in config.EXTRACTION_STEPS:
            func = EXTRACTION_DISPATCH.get(step_name)
            if func is None:
                log.warning(f'Unknown extraction step: {step_name}')
                steps_skipped += 1
                continue
            try:
                func(run_id, start_date, end_date, analytics_conn, dry_run=dry_run)
                steps_ok += 1
            except Exception as e:
                log.error(f'Extraction step {step_name} failed: {e}')
                steps_failed += 1

        # ── Phase 2: Stored Procedures (Steps 8-15) ──────────────────────
        log.info('── Phase 2: Stored Procedures ────────────────────')

        # For backfills > 30 days, chunk into 7-day windows for range SPs
        date_chunks = []
        if (end_date - start_date).days > 30:
            chunk_start = start_date
            while chunk_start <= end_date:
                chunk_end = min(chunk_start + timedelta(days=6), end_date)
                date_chunks.append((chunk_start, chunk_end))
                chunk_start = chunk_end + timedelta(days=1)
            log.info(f'Backfill mode: {len(date_chunks)} chunks of ≤7 days')
        else:
            date_chunks = [(start_date, end_date)]

        for chunk_start, chunk_end in date_chunks:
            if len(date_chunks) > 1:
                log.info(f'── Chunk: {chunk_start} → {chunk_end} ──')
            for step_name in config.SP_STEPS:
                ok = call_stored_procedure(
                    run_id, step_name, chunk_start, chunk_end,
                    analytics_conn, dry_run=dry_run
                )
                if ok:
                    steps_ok += 1
                else:
                    steps_failed += 1

        # ── Final status ──────────────────────────────────────────────────
        if steps_failed == 0:
            status = 'SUCCESS'
        elif steps_ok > 0:
            status = 'PARTIAL'
        else:
            status = 'FAILED'

        log_pipeline_run(analytics_conn, run_id, 'pipeline_master', status,
                         run_start, data_date_start=start_date, data_date_end=end_date,
                         triggered_by='cli')

        elapsed = (datetime.now() - run_start).total_seconds()
        log.info('=' * 70)
        log.info(f'Pipeline {run_id} completed: {status}')
        log.info(f'  Steps OK: {steps_ok}  Failed: {steps_failed}  Skipped: {steps_skipped}')
        log.info(f'  Elapsed: {elapsed:.1f}s')
        log.info('=' * 70)

        return status == 'SUCCESS'

    except Exception as e:
        log.error(f'Pipeline failed: {e}')
        if analytics_conn:
            log_pipeline_run(analytics_conn, run_id, 'pipeline_master', 'FAILED',
                             run_start, error_message=str(e),
                             data_date_start=start_date, data_date_end=end_date,
                             triggered_by='cli')
        return False

    finally:
        if analytics_conn:
            analytics_conn.close()


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description='UC-SC-02: Waste Prediction Pipeline Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run for yesterday
  %(prog)s --date 2026-02-17            # Run for specific date
  %(prog)s --start-date 2025-11-01 --end-date 2026-02-17  # Backfill
  %(prog)s --setup                      # Create tables only
  %(prog)s --dry-run                    # Show steps without executing
        """,
    )
    parser.add_argument('--date', type=str, default=None,
                        help='Single target date (YYYY-MM-DD). Default: yesterday.')
    parser.add_argument('--start-date', type=str, default=None,
                        help='Backfill start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                        help='Backfill end date (YYYY-MM-DD)')
    parser.add_argument('--setup', action='store_true',
                        help='Create analytics/staging tables and exit')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show steps without executing queries')
    parser.add_argument('--env-file', type=str, default=None,
                        help='Path to .env file (default: orchestrator/.env)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable DEBUG logging')
    return parser.parse_args()


def load_env_file(path):
    """Load environment variables from a .env file."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load .env file
    env_path = args.env_file
    if env_path is None:
        env_path = str(Path(__file__).resolve().parent / '.env')
    load_env_file(env_path)

    # Schema setup mode
    if args.setup:
        conn = get_analytics_conn()
        try:
            setup_tables(conn)
        finally:
            conn.close()
        return

    # Determine date range
    if args.start_date and args.end_date:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    elif args.date:
        start_date = date.fromisoformat(args.date)
        end_date = start_date
    else:
        # Default: yesterday
        end_date = date.today() - timedelta(days=1)
        start_date = end_date

    if start_date > end_date:
        log.error(f'start_date ({start_date}) > end_date ({end_date})')
        sys.exit(1)

    ok = run_pipeline(start_date, end_date, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
