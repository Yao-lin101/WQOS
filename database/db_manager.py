#!/usr/bin/env python3
"""
作者：e.e.
日期：2025.09.10
功能：SQLite数据库管理器，提供高级数据库操作接口
"""

import os
import sqlite3
import pandas as pd
import threading
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import sys
import json

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.config import ROOT_PATH

class FactorDatabaseManager:
    """因子数据库管理器"""
    
    def __init__(self, db_path='database/factors.db'):
        """初始化数据库管理器"""
        self.db_path = os.path.join(ROOT_PATH, db_path)
        self._local = threading.local()  # 线程本地存储
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 初始化数据库（如果不存在）
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        if not os.path.exists(self.db_path):
            schema_path = os.path.join(ROOT_PATH, 'database', 'schema.sql')
            if os.path.exists(schema_path):
                with self.get_connection() as conn:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        conn.executescript(f.read())
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")  # 提升并发性能
        
        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise
        else:
            self._local.connection.commit()
    
    # ====================================================================
    # 因子表达式相关操作
    # ====================================================================
    
    def add_factor_expression(self, expression: str, dataset_id: str, region: str, step: int) -> bool:
        """添加因子表达式"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO factor_expressions 
                    (expression, dataset_id, region, step) 
                    VALUES (?, ?, ?, ?)
                """, (expression, dataset_id, region, step))
                return True
        except Exception as e:
            print(f"添加因子表达式失败: {e}")
            return False
    
    def add_factor_expressions_batch(self, expressions: List[str], dataset_id: str, region: str, step: int) -> int:
        """批量添加因子表达式"""
        try:
            with self.get_connection() as conn:
                data = [(expr, dataset_id, region, step) for expr in expressions]
                cursor = conn.executemany("""
                    INSERT OR IGNORE INTO factor_expressions 
                    (expression, dataset_id, region, step) 
                    VALUES (?, ?, ?, ?)
                """, data)
                return cursor.rowcount
        except Exception as e:
            print(f"批量添加因子表达式失败: {e}")
            return 0
    
    def get_factor_expressions(self, dataset_id: str, region: str, step: int) -> List[str]:
        """获取因子表达式列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT expression FROM factor_expressions 
                    WHERE dataset_id = ? AND region = ? AND step = ?
                    ORDER BY created_at
                """, (dataset_id, region, step))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"获取因子表达式失败: {e}")
            return []
    
    def is_expression_exists(self, expression: str, dataset_id: str, region: str, step: int) -> bool:
        """检查表达式是否存在"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM factor_expressions 
                    WHERE expression = ? AND dataset_id = ? AND region = ? AND step = ?
                """, (expression, dataset_id, region, step))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"检查表达式存在性失败: {e}")
            return False
    
    # ====================================================================
    # 已检查因子相关操作
    # ====================================================================
    
    def add_checked_alpha(self, alpha_id: str, dataset_id: str, region: str, step: int) -> bool:
        """添加已检查的Alpha ID"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO checked_alphas 
                    (alpha_id, dataset_id, region, step) 
                    VALUES (?, ?, ?, ?)
                """, (alpha_id, dataset_id, region, step))
                return True
        except Exception as e:
            print(f"添加已检查Alpha失败: {e}")
            return False
    
    def add_checked_alphas_batch(self, alpha_ids: List[str], dataset_id: str, region: str, step: int) -> int:
        """批量添加已检查的Alpha ID"""
        try:
            with self.get_connection() as conn:
                data = [(alpha_id, dataset_id, region, step) for alpha_id in alpha_ids]
                cursor = conn.executemany("""
                    INSERT OR IGNORE INTO checked_alphas 
                    (alpha_id, dataset_id, region, step) 
                    VALUES (?, ?, ?, ?)
                """, data)
                return cursor.rowcount
        except Exception as e:
            print(f"批量添加已检查Alpha失败: {e}")
            return 0
    
    def get_checked_alphas(self, dataset_id: str, region: str, step: int) -> List[str]:
        """获取已检查的Alpha ID列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT alpha_id FROM checked_alphas 
                    WHERE dataset_id = ? AND region = ? AND step = ?
                    ORDER BY checked_at
                """, (dataset_id, region, step))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"获取已检查Alpha失败: {e}")
            return []
    
    def is_alpha_checked(self, alpha_id: str, dataset_id: str, region: str, step: int) -> bool:
        """检查Alpha是否已被检查"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM checked_alphas 
                    WHERE alpha_id = ? AND dataset_id = ? AND region = ? AND step = ?
                """, (alpha_id, dataset_id, region, step))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"检查Alpha检查状态失败: {e}")
            return False
    
    # ====================================================================
    # 可提交因子相关操作
    # ====================================================================
    
    def add_submitable_alpha(self, alpha_data: Dict[str, Any]) -> bool:
        """添加可提交因子"""
        try:
            with self.get_connection() as conn:
                # 构建插入SQL
                columns = list(alpha_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)
                
                sql = f"""
                    INSERT OR REPLACE INTO submitable_alphas ({column_names})
                    VALUES ({placeholders})
                """
                
                conn.execute(sql, list(alpha_data.values()))
                return True
        except Exception as e:
            print(f"添加可提交因子失败: {e}")
            return False
    
    def get_submitable_alphas(self) -> pd.DataFrame:
        """获取所有可提交因子"""
        try:
            with self.get_connection() as conn:
                # 为了兼容性，将alpha_id重命名为id
                return pd.read_sql_query("""
                    SELECT alpha_id as id, type, author, instrument_type, region, universe, 
                           delay, decay, neutralization, truncation, pasteurization, 
                           unit_handling, nan_handling, language, visualization, code, 
                           description, operator_count, date_created, date_submitted, 
                           date_modified, name, favorite, hidden, color, category, 
                           tags, classifications, grade, stage, status, pnl, book_size,
                           long_count, short_count, turnover, returns, drawdown, margin,
                           fitness, sharpe, start_date, checks, os, train, test, prod,
                           competitions, themes, team, pyramids, aggressive_mode, 
                           self_corr, prod_corr, created_at
                    FROM submitable_alphas 
                    ORDER BY self_corr , prod_corr 
                """, conn)
        except Exception as e:
            print(f"获取可提交因子失败: {e}")
            return pd.DataFrame()
    
    def remove_submitable_alpha(self, alpha_id: str) -> bool:
        """移除可提交因子"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("DELETE FROM submitable_alphas WHERE alpha_id = ?", (alpha_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"移除可提交因子失败: {e}")
            return False
    
    def remove_submitable_alphas_batch(self, alpha_ids: List[str]) -> int:
        """批量移除可提交因子"""
        try:
            with self.get_connection() as conn:
                placeholders = ', '.join(['?' for _ in alpha_ids])
                cursor = conn.execute(f"DELETE FROM submitable_alphas WHERE alpha_id IN ({placeholders})", alpha_ids)
                return cursor.rowcount
        except Exception as e:
            print(f"批量移除可提交因子失败: {e}")
            return 0
    
    def is_alpha_submitable(self, alpha_id: str) -> bool:
        """检查Alpha是否可提交"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM submitable_alphas WHERE alpha_id = ?", (alpha_id,))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"检查Alpha可提交状态失败: {e}")
            return False
    
    def get_alphas_by_color(self, color: str) -> List[Dict]:
        """获取指定颜色的Alpha列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT alpha_id as id, type, author, instrument_type, region, universe, 
                           delay, decay, neutralization, truncation, pasteurization, 
                           unit_handling, nan_handling, language, visualization, code, 
                           description, operator_count, date_created, date_submitted, 
                           date_modified, name, favorite, hidden, color, category, 
                           tags, classifications, grade, stage, status, pnl, book_size,
                           long_count, short_count, turnover, returns, drawdown, margin,
                           fitness, sharpe, start_date, checks, os, train, test, prod,
                           competitions, themes, team, pyramids, aggressive_mode, 
                           self_corr, prod_corr, recheck_flag, created_at
                    FROM submitable_alphas 
                    WHERE color = ?
                    ORDER BY date_created DESC
                """, (color,))
                
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                # 转换为字典列表
                result = []
                for row in rows:
                    alpha_dict = dict(zip(columns, row))
                    
                    # 处理复杂字段的JSON反序列化
                    complex_fields = ['tags', 'classifications', 'checks', 'os', 'train', 'test', 'prod', 'competitions', 'themes', 'team', 'pyramids']
                    for field in complex_fields:
                        if field in alpha_dict and alpha_dict[field]:
                            try:
                                alpha_dict[field] = json.loads(alpha_dict[field])
                            except (json.JSONDecodeError, TypeError):
                                alpha_dict[field] = []
                    
                    result.append(alpha_dict)
                
                return result
        except Exception as e:
            print(f"获取{color}颜色Alpha失败: {e}")
            return []
    
    # ====================================================================
    # 复查标记相关操作
    # ====================================================================
    
    def set_recheck_flag(self, alpha_ids: List[str], recheck_flag: bool = True) -> int:
        """设置Alpha的复查标记"""
        try:
            with self.get_connection() as conn:
                placeholders = ', '.join(['?' for _ in alpha_ids])
                cursor = conn.execute(f"""
                    UPDATE submitable_alphas 
                    SET recheck_flag = ? 
                    WHERE alpha_id IN ({placeholders})
                """, [recheck_flag] + alpha_ids)
                return cursor.rowcount
        except Exception as e:
            print(f"设置复查标记失败: {e}")
            return 0
    
    def get_alphas_for_recheck(self, region: str = None) -> List[Dict]:
        """获取需要复查的Alpha列表"""
        try:
            with self.get_connection() as conn:
                where_clause = "WHERE recheck_flag = TRUE"
                params = []
                if region:
                    where_clause += " AND region = ?"
                    params.append(region)
                
                cursor = conn.execute(f"""
                    SELECT alpha_id as id, type, author, instrument_type, region, universe, 
                           delay, decay, neutralization, truncation, pasteurization, 
                           unit_handling, nan_handling, language, visualization, code, 
                           description, operator_count, date_created, date_submitted, 
                           date_modified, name, favorite, hidden, color, category, 
                           tags, classifications, grade, stage, status, pnl, book_size,
                           long_count, short_count, turnover, returns, drawdown, margin,
                           fitness, sharpe, start_date, checks, os, train, test, prod,
                           competitions, themes, team, pyramids, aggressive_mode, 
                           self_corr, prod_corr, recheck_flag, created_at
                    FROM submitable_alphas 
                    {where_clause}
                    ORDER BY date_created DESC
                """, params)
                
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                # 转换为字典列表
                result = []
                for row in rows:
                    alpha_dict = dict(zip(columns, row))
                    
                    # 处理复杂字段的JSON反序列化
                    complex_fields = ['tags', 'classifications', 'checks', 'os', 'train', 'test', 'prod', 'competitions', 'themes', 'team', 'pyramids']
                    for field in complex_fields:
                        if field in alpha_dict and alpha_dict[field]:
                            try:
                                alpha_dict[field] = json.loads(alpha_dict[field])
                            except (json.JSONDecodeError, TypeError):
                                alpha_dict[field] = []
                    
                    result.append(alpha_dict)
                
                return result
        except Exception as e:
            print(f"获取复查Alpha列表失败: {e}")
            return []
    
    def clear_recheck_flags(self, alpha_ids: List[str] = None) -> int:
        """清除复查标记"""
        try:
            with self.get_connection() as conn:
                if alpha_ids:
                    placeholders = ', '.join(['?' for _ in alpha_ids])
                    cursor = conn.execute(f"""
                        UPDATE submitable_alphas 
                        SET recheck_flag = FALSE 
                        WHERE alpha_id IN ({placeholders})
                    """, alpha_ids)
                else:
                    # 清除所有复查标记
                    cursor = conn.execute("UPDATE submitable_alphas SET recheck_flag = FALSE")
                return cursor.rowcount
        except Exception as e:
            print(f"清除复查标记失败: {e}")
            return 0
    
    # ====================================================================
    # 已通知因子保持文件存储方式
    # notified_alphas.txt 等通知日志文件不迁移到数据库
    # ====================================================================
    
    # ====================================================================
    # 系统配置相关操作
    # ====================================================================
    
    def get_config(self, key: str, default_value: str = None) -> Optional[str]:
        """获取配置值"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT config_value FROM system_config WHERE config_key = ?", (key,))
                result = cursor.fetchone()
                return result[0] if result else default_value
        except Exception as e:
            print(f"获取配置失败: {e}")
            return default_value
    
    def set_config(self, key: str, value: str, description: str = None) -> bool:
        """设置配置值"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (key, value, description))
                return True
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False
    
    def get_system_config(self, key: str, default_value: str = None) -> Optional[str]:
        """获取系统配置值（get_config的别名）"""
        return self.get_config(key, default_value)
    
    def set_system_config(self, key: str, value: str, description: str = None) -> bool:
        """设置系统配置值（set_config的别名）"""
        return self.set_config(key, value, description)
    
    # ====================================================================
    # 统计和分析相关操作
    # ====================================================================
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            with self.get_connection() as conn:
                # 获取各表记录数
                stats = {}
                
                cursor = conn.execute("SELECT COUNT(*) FROM factor_expressions")
                stats['total_expressions'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM checked_alphas")
                stats['total_checked'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM submitable_alphas")
                stats['total_submitable'] = cursor.fetchone()[0]
                
                # 获取各数据集统计
                cursor = conn.execute("""
                    SELECT dataset_id, region, step, COUNT(*) as count
                    FROM factor_expressions 
                    GROUP BY dataset_id, region, step
                """)
                stats['expression_breakdown'] = cursor.fetchall()
                
                return stats
        except Exception as e:
            print(f"获取系统统计失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """清理旧数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM checked_alphas 
                    WHERE checked_at < datetime('now', '-{} days')
                """.format(days))
                return cursor.rowcount
        except Exception as e:
            print(f"清理旧数据失败: {e}")
            return 0
    
    # ====================================================================
    # 每日提交统计相关方法
    # ====================================================================
    
    def get_daily_submit_stats(self, date: str, timezone: str = 'UTC') -> Dict[str, Any]:
        """
        获取指定日期的提交统计（支持时区转换查询）
        
        :param date: 日期字符串 YYYY-MM-DD
        :param timezone: 时区字符串
        :return: 统计数据字典
        """
        try:
            with self.get_connection() as conn:
                # 使用日期和时区双条件精准查询
                cursor = conn.execute("""
                    SELECT successful_submits, total_attempts, timezone, last_updated
                    FROM daily_submit_stats 
                    WHERE date = ? AND timezone = ?
                """, (date, timezone))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'date': date,
                        'successful_submits': result[0],
                        'total_attempts': result[1],
                        'timezone': result[2],
                        'last_updated': result[3],
                        'remaining_quota': None  # 将在调用方计算
                    }
                
                # 如果没有找到精确匹配，返回空记录
                return {
                    'date': date,
                    'successful_submits': 0,
                    'total_attempts': 0,
                    'timezone': timezone,
                    'last_updated': None,
                    'remaining_quota': None
                }
        except Exception as e:
            print(f"获取每日提交统计失败: {e}")
            return {
                'date': date,
                'successful_submits': 0,
                'total_attempts': 0,
                'timezone': timezone,
                'last_updated': None,
                'remaining_quota': None
            }
    

    def update_daily_submit_stats(self, date: str, successful_increment: int = 0, 
                                 attempt_increment: int = 0, timezone: str = 'UTC') -> bool:
        """
        更新指定日期的提交统计
        
        :param date: 日期字符串 YYYY-MM-DD
        :param successful_increment: 成功提交增量
        :param attempt_increment: 尝试提交增量  
        :param timezone: 时区字符串
        :return: 操作是否成功
        """
        try:
            with self.get_connection() as conn:
                # 使用 INSERT OR REPLACE 语句，确保查询时同时匹配日期和时区
                conn.execute("""
                    INSERT OR REPLACE INTO daily_submit_stats 
                    (date, successful_submits, total_attempts, timezone, last_updated)
                    VALUES (
                        ?,
                        COALESCE((SELECT successful_submits FROM daily_submit_stats WHERE date = ? AND timezone = ?), 0) + ?,
                        COALESCE((SELECT total_attempts FROM daily_submit_stats WHERE date = ? AND timezone = ?), 0) + ?,
                        ?,
                        datetime('now')
                    )
                """, (date, date, timezone, successful_increment, date, timezone, attempt_increment, timezone))
                
                return True
        except Exception as e:
            print(f"更新每日提交统计失败: {e}")
            return False
    
    def get_recent_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近几天的提交统计
        
        :param days: 天数
        :return: 统计数据列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT date, successful_submits, total_attempts, timezone, last_updated,
                           CASE 
                               WHEN total_attempts > 0 
                               THEN ROUND(successful_submits * 100.0 / total_attempts, 1)
                               ELSE 0
                           END as success_rate
                    FROM daily_submit_stats 
                    WHERE date >= date('now', '-{} days')
                    ORDER BY date DESC
                """.format(days))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'date': row[0],
                        'successful_submits': row[1],
                        'total_attempts': row[2], 
                        'timezone': row[3],
                        'last_updated': row[4],
                        'success_rate': row[5]
                    })
                
                return results
        except Exception as e:
            print(f"获取最近每日统计失败: {e}")
            return []

    def get_recent_daily_stats_by_timezone(self, days: int = 3, timezone: str = '-4') -> List[Dict[str, Any]]:
        """
        按指定时区获取最近几天的提交统计
        
        :param days: 天数
        :param timezone: 时区字符串
        :return: 统计数据列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT date, successful_submits, total_attempts, timezone, last_updated,
                           CASE 
                               WHEN total_attempts > 0 
                               THEN ROUND(successful_submits * 100.0 / total_attempts, 1)
                               ELSE 0
                           END as success_rate
                    FROM daily_submit_stats 
                    WHERE timezone = ? AND date >= date('now', '-{} days')
                    ORDER BY date DESC
                """.format(days), (timezone,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'date': row[0],
                        'successful_submits': row[1],
                        'total_attempts': row[2], 
                        'timezone': row[3],
                        'last_updated': row[4],
                        'success_rate': row[5]
                    })
                
                return results
        except Exception as e:
            print(f"获取最近每日统计失败: {e}")
            return []

    def get_recent_factor_expressions_by_dataset(self, days: int = 3, target_timezone: str = 'UTC-4') -> List[Dict[str, Any]]:
        """
        获取最近几天各数据集新增的因子表达式统计（按指定时区计算日期）
        
        :param days: 天数
        :param target_timezone: 目标时区（如 'UTC-4'）
        :return: 按日期和数据集分组的统计列表
        """
        try:
            with self.get_connection() as conn:
                # 计算时区偏移小时数
                if target_timezone.startswith('UTC'):
                    tz_offset = target_timezone[3:]  # 获取 '+8' 或 '-4'
                    if tz_offset.startswith('+'):
                        offset_hours = int(tz_offset[1:])
                    elif tz_offset.startswith('-'):
                        offset_hours = -int(tz_offset[1:])
                    else:
                        offset_hours = 0
                else:
                    offset_hours = 0
                
                # 构建SQL查询，使用时区偏移调整日期
                cursor = conn.execute("""
                    SELECT 
                        date(created_at, '{} hours') as local_date,
                        dataset_id,
                        region,
                        step,
                        COUNT(*) as new_expressions
                    FROM factor_expressions 
                    WHERE date(created_at, '{} hours') >= date('now', '{} hours', '-{} days')
                    GROUP BY date(created_at, '{} hours'), dataset_id, region, step
                    ORDER BY local_date DESC, dataset_id, region, step
                """.format(
                    '+' + str(offset_hours) if offset_hours >= 0 else str(offset_hours),
                    '+' + str(offset_hours) if offset_hours >= 0 else str(offset_hours),
                    '+' + str(offset_hours) if offset_hours >= 0 else str(offset_hours),
                    days,
                    '+' + str(offset_hours) if offset_hours >= 0 else str(offset_hours)
                ))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'date': row[0],
                        'dataset_id': row[1],
                        'region': row[2],
                        'step': row[3],
                        'new_expressions': row[4],
                        'timezone': target_timezone
                    })
                
                return results
        except Exception as e:
            print(f"获取最近因子表达式统计失败: {e}")
            return []

    # ====================================================================
    # 失败表达式相关操作
    # ====================================================================
    
    def add_failed_expression(self, expression: str, dataset_id: str, region: str, step: int,
                            failure_reason: str = None, error_details: str = None) -> bool:
        """
        添加失败的因子表达式记录
        
        Args:
            expression: 失败的因子表达式
            dataset_id: 数据集ID
            region: 地区
            step: 步骤
            failure_reason: 失败原因 (如 "Unexpected end of input", "Syntax error")
            error_details: 详细错误信息 (API返回的原始错误)
            
        Returns:
            bool: 是否添加成功
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO failed_expressions 
                    (expression, dataset_id, region, step, failure_reason, error_details) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (expression, dataset_id, region, step, failure_reason, error_details))
                return True
        except Exception as e:
            print(f"添加失败表达式记录失败: {e}")
            return False
    
    def get_failed_expressions(self, dataset_id: str = None, region: str = None, 
                             step: int = None, failure_reason: str = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取失败的因子表达式列表
        
        Args:
            dataset_id: 数据集ID过滤
            region: 地区过滤
            step: 步骤过滤
            failure_reason: 失败原因过滤
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 失败表达式记录列表
        """
        try:
            with self.get_connection() as conn:
                # 构建WHERE条件
                conditions = []
                params = []
                
                if dataset_id:
                    conditions.append("dataset_id = ?")
                    params.append(dataset_id)
                if region:
                    conditions.append("region = ?")
                    params.append(region)
                if step is not None:
                    conditions.append("step = ?")
                    params.append(step)
                if failure_reason:
                    conditions.append("failure_reason LIKE ?")
                    params.append(f"%{failure_reason}%")
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                cursor = conn.execute(f"""
                    SELECT id, expression, dataset_id, region, step, failure_reason, 
                           error_details, created_at
                    FROM failed_expressions 
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ?
                """, params + [limit])
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'expression': row[1],
                        'dataset_id': row[2],
                        'region': row[3],
                        'step': row[4],
                        'failure_reason': row[5],
                        'error_details': row[6],
                        'created_at': row[7]
                    })
                
                return results
        except Exception as e:
            print(f"获取失败表达式列表失败: {e}")
            return []
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """
        获取失败统计信息
        
        Returns:
            Dict: 包含各种失败统计的字典
        """
        try:
            with self.get_connection() as conn:
                # 总失败记录数
                cursor = conn.execute("SELECT COUNT(*) FROM failed_expressions")
                total_failures = cursor.fetchone()[0]
                
                # 唯一失败表达式数
                cursor = conn.execute("SELECT COUNT(DISTINCT expression) FROM failed_expressions")
                unique_failed_expressions = cursor.fetchone()[0]
                
                # 按失败原因统计
                cursor = conn.execute("""
                    SELECT failure_reason, COUNT(*) as count, 
                           COUNT(DISTINCT expression) as unique_count,
                           COUNT(DISTINCT dataset_id) as affected_datasets
                    FROM failed_expressions
                    WHERE failure_reason IS NOT NULL
                    GROUP BY failure_reason
                    ORDER BY count DESC
                    LIMIT 10
                """)
                failure_reasons = [{'reason': row[0], 'count': row[1], 
                                  'unique_expressions': row[2], 'affected_datasets': row[3]} 
                                 for row in cursor.fetchall()]
                
                # 按数据集统计
                cursor = conn.execute("""
                    SELECT dataset_id, region, step, COUNT(*) as count,
                           COUNT(DISTINCT expression) as unique_expressions,
                           COUNT(DISTINCT failure_reason) as failure_types
                    FROM failed_expressions
                    GROUP BY dataset_id, region, step
                    ORDER BY count DESC
                    LIMIT 10
                """)
                dataset_failures = [{'dataset_id': row[0], 'region': row[1], 'step': row[2], 
                                   'count': row[3], 'unique_expressions': row[4], 'failure_types': row[5]} 
                                  for row in cursor.fetchall()]
                
                # 最近24小时失败数
                cursor = conn.execute("""
                    SELECT COUNT(*) 
                    FROM failed_expressions
                    WHERE created_at >= datetime('now', '-1 day')
                """)
                recent_failures = cursor.fetchone()[0]
                
                # 表达式长度统计
                cursor = conn.execute("""
                    SELECT AVG(LENGTH(expression)) as avg_length,
                           MIN(LENGTH(expression)) as min_length,
                           MAX(LENGTH(expression)) as max_length
                    FROM failed_expressions
                """)
                length_stats = cursor.fetchone()
                
                return {
                    'total_failures': total_failures,
                    'unique_failed_expressions': unique_failed_expressions,
                    'recent_24h_failures': recent_failures,
                    'failure_by_reason': failure_reasons,
                    'failure_by_dataset': dataset_failures,
                    'expression_length_stats': {
                        'avg_length': round(length_stats[0], 2) if length_stats[0] else 0,
                        'min_length': length_stats[1] or 0,
                        'max_length': length_stats[2] or 0
                    }
                }
        except Exception as e:
            print(f"获取失败统计信息失败: {e}")
            return {}
    
    def cleanup_old_failed_expressions(self, days: int = 30) -> int:
        """
        清理旧的失败表达式记录
        
        Args:
            days: 保留天数，默认30天
            
        Returns:
            int: 删除的记录数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM failed_expressions 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))
                return cursor.rowcount
        except Exception as e:
            print(f"清理旧失败表达式记录失败: {e}")
            return 0

# 全局数据库管理器实例
db_manager = FactorDatabaseManager()

# ====================================================================
# 兼容性函数：替换现有文件操作
# ====================================================================

def read_completed_alphas(dataset_id: str, region: str, step: int) -> List[str]:
    """读取已完成的Alpha列表（替换文件读取）"""
    return db_manager.get_checked_alphas(dataset_id, region, step)

def write_completed_alpha(alpha_id: str, dataset_id: str, region: str, step: int) -> bool:
    """写入已完成的Alpha（替换文件写入）"""
    return db_manager.add_checked_alpha(alpha_id, dataset_id, region, step)

def get_submitable_alphas_df() -> pd.DataFrame:
    """获取可提交因子DataFrame（替换CSV读取）"""
    return db_manager.get_submitable_alphas()

def add_submitable_alpha_df(alpha_df: pd.DataFrame) -> bool:
    """添加可提交因子DataFrame（替换CSV写入）"""
    try:
        for _, row in alpha_df.iterrows():
            alpha_data = row.to_dict()
            db_manager.add_submitable_alpha(alpha_data)
        return True
    except Exception as e:
        print(f"添加可提交因子DataFrame失败: {e}")
        return False

def remove_submitted_alphas(alpha_ids: List[str]) -> int:
    """移除已提交的因子（替换CSV操作）"""
    return db_manager.remove_submitable_alphas_batch(alpha_ids)

# notified_alphas 相关功能保持原有文件操作方式
# 不提供数据库替换函数

def get_start_date() -> str:
    """获取开始日期（替换文件读取）"""
    return db_manager.get_config('start_date', '2024-10-07')

def set_start_date(date: str) -> bool:
    """设置开始日期（替换文件写入）"""
    return db_manager.set_config('start_date', date, '因子挖掘开始日期')