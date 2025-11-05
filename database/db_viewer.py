#!/usr/bin/env python3
"""
作者：e.e.
日期：2025.09.10
功能：数据库查看工具，提供友好的数据查询界面
"""

import os
import sys
import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config import ROOT_PATH
except ImportError:
    ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

from database.db_manager import FactorDatabaseManager

class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self):
        self.db_manager = FactorDatabaseManager()
        
    def show_overview(self):
        """显示数据库概览"""
        print("📊 数据库概览")
        print("="*50)
        
        stats = self.db_manager.get_system_stats()
        
        print(f"📈 数据统计:")
        print(f"  - 因子表达式总数: {stats.get('total_expressions', 0):,}")
        print(f"  - 已检查因子总数: {stats.get('total_checked', 0):,}")
        print(f"  - 可提交因子总数: {stats.get('total_submitable', 0):,}")
        
        print(f"\n📋 各数据集分布:")
        breakdown = stats.get('expression_breakdown', [])
        for dataset_id, region, step, count in breakdown:
            print(f"  - {dataset_id}_{region}_{step}step: {count:,} 条表达式")
        
        # 显示最近活动
        print(f"\n⏰ 最近活动:")
        try:
            with self.db_manager.get_connection() as conn:
                # 最新的因子表达式
                cursor = conn.execute("""
                    SELECT dataset_id, region, step, COUNT(*) as count, MAX(created_at) as latest
                    FROM factor_expressions 
                    GROUP BY dataset_id, region, step
                    ORDER BY latest DESC
                    LIMIT 3
                """)
                recent_expressions = cursor.fetchall()
                
                for dataset_id, region, step, count, latest in recent_expressions:
                    print(f"  - {dataset_id}_{region}_{step}step: {count:,} 条表达式 (最新: {latest})")
                
                # 最新的检查记录
                cursor = conn.execute("""
                    SELECT dataset_id, region, step, COUNT(*) as count, MAX(checked_at) as latest
                    FROM checked_alphas 
                    GROUP BY dataset_id, region, step
                    ORDER BY latest DESC
                    LIMIT 3
                """)
                recent_checks = cursor.fetchall()
                
                print(f"\n🔍 最近检查:")
                for dataset_id, region, step, count, latest in recent_checks:
                    print(f"  - {dataset_id}_{region}_{step}step: {count:,} 个已检查 (最新: {latest})")
                    
        except Exception as e:
            print(f"⚠️  获取最近活动失败: {e}")
    
    def search_expressions(self, keyword: str = "", dataset_id: str = "", region: str = "", step: int = None, limit: int = 10):
        """搜索因子表达式"""
        print(f"🔍 搜索因子表达式")
        print("="*50)
        
        try:
            with self.db_manager.get_connection() as conn:
                # 构建查询条件
                conditions = []
                params = []
                
                if keyword:
                    conditions.append("expression LIKE ?")
                    params.append(f"%{keyword}%")
                
                if dataset_id:
                    conditions.append("dataset_id = ?")
                    params.append(dataset_id)
                    
                if region:
                    conditions.append("region = ?")
                    params.append(region)
                    
                if step is not None:
                    conditions.append("step = ?")
                    params.append(step)
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                sql = f"""
                    SELECT id, expression, dataset_id, region, step, created_at
                    FROM factor_expressions 
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                results = cursor.fetchall()
                
                if not results:
                    print("❌ 未找到匹配的表达式")
                    return
                
                print(f"📋 找到 {len(results)} 条结果:")
                print()
                
                for i, (id, expression, ds_id, reg, stp, created) in enumerate(results, 1):
                    print(f"{i:2d}. ID: {id}")
                    print(f"    表达式: {expression}")
                    print(f"    数据集: {ds_id}_{reg}_{stp}step")
                    print(f"    创建时间: {created}")
                    print()
                    
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    
    def show_checked_alphas(self, dataset_id: str = "", region: str = "", step: int = None, limit: int = 20):
        """显示已检查的因子"""
        print(f"✅ 已检查因子列表")
        print("="*50)
        
        try:
            with self.db_manager.get_connection() as conn:
                # 构建查询条件
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
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                sql = f"""
                    SELECT alpha_id, dataset_id, region, step, checked_at
                    FROM checked_alphas 
                    WHERE {where_clause}
                    ORDER BY checked_at DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                results = cursor.fetchall()
                
                if not results:
                    print("❌ 未找到已检查的因子")
                    return
                
                print(f"📋 最近检查的 {len(results)} 个因子:")
                print()
                
                # 按数据集分组显示
                grouped = {}
                for alpha_id, ds_id, reg, stp, checked in results:
                    key = f"{ds_id}_{reg}_{stp}step"
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append((alpha_id, checked))
                
                for key, alphas in grouped.items():
                    print(f"📊 {key}:")
                    for alpha_id, checked in alphas[:10]:  # 每组最多显示10个
                        print(f"  - {alpha_id} (检查时间: {checked})")
                    if len(alphas) > 10:
                        print(f"  ... 还有 {len(alphas) - 10} 个")
                    print()
                    
        except Exception as e:
            print(f"❌ 查询失败: {e}")
    
    def show_submitable_alphas(self):
        """显示可提交因子"""
        print(f"🚀 可提交因子列表")
        print("="*50)
        
        try:
            df = self.db_manager.get_submitable_alphas()
            
            if df.empty:
                print("❌ 当前没有可提交的因子")
                return
            
            print(f"📋 共有 {len(df)} 个可提交因子:")
            print()
            
            # 显示关键信息
            display_columns = ['alpha_id', 'region', 'universe', 'self_corr', 'prod_corr']
            available_columns = [col for col in display_columns if col in df.columns]
            
            for i, row in df.iterrows():
                print(f"{i+1:2d}. Alpha ID: {row.get('id', 'N/A')}")
                if 'region' in row and 'universe' in row:
                    print(f"    市场: {row['region']}-{row['universe']}")
                if 'self_corr' in row:
                    print(f"    自相关: {row['self_corr']:.3f}")
                if 'prod_corr' in row:
                    print(f"    生产相关: {row['prod_corr']:.3f}")
                print()
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")
    
    def show_config(self):
        """显示系统配置"""
        print(f"⚙️  系统配置")
        print("="*50)
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT config_key, config_value, description, updated_at FROM system_config ORDER BY config_key")
                configs = cursor.fetchall()
                
                if not configs:
                    print("❌ 未找到系统配置")
                    return
                
                print(f"📋 当前配置:")
                print()
                
                for key, value, desc, updated in configs:
                    print(f"🔧 {key}")
                    print(f"   值: {value}")
                    if desc:
                        print(f"   描述: {desc}")
                    print(f"   更新时间: {updated}")
                    print()
                    
        except Exception as e:
            print(f"❌ 查询失败: {e}")

    def show_daily_submit_limit(self):
        """显示每日提交限额状态"""
        print("📅 每日提交限额状态")
        print("="*50)
        
        try:
            # 导入配置和时区函数
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
            from src.machine_lib_ee import load_digging_config, get_current_date_with_timezone
            
            # 加载配置
            config = load_digging_config()
            daily_limit = config.get('daily_submit_limit', 0)
            limit_timezone = config.get('daily_limit_timezone', 'UTC')
            
            print(f"⚙️  配置信息:")
            print(f"  - 每日限额: {daily_limit} 个/天" + (" (无限制)" if daily_limit == 0 else ""))
            print(f"  - 时区设置: {limit_timezone}")
            
            if daily_limit > 0:
                # 获取当前日期
                current_date = get_current_date_with_timezone(limit_timezone)
                
                # 获取今日统计
                daily_stats = self.db_manager.get_daily_submit_stats(current_date, limit_timezone)
                today_successful = daily_stats['successful_submits']
                today_attempts = daily_stats['total_attempts']
                remaining_quota = daily_limit - today_successful
                
                print(f"\n📊 今日状态 [{current_date}]:")
                print(f"  - ✅ 成功提交: {today_successful} 个")
                print(f"  - 🎯 总尝试数: {today_attempts} 个")
                print(f"  - 📈 成功率: {today_successful/today_attempts*100:.1f}%" if today_attempts > 0 else "  - 📈 成功率: N/A")
                print(f"  - 🔄 剩余配额: {remaining_quota} 个")
                
                # 状态指示
                if remaining_quota <= 0:
                    print(f"  - ⚠️  状态: 限额已用完")
                elif remaining_quota <= daily_limit * 0.2:  # 少于20%
                    print(f"  - 🔸 状态: 配额不足")
                else:
                    print(f"  - ✅ 状态: 配额充足")
            
            # 获取最近几天的统计
            print(f"\n📈 最近7天统计:")
            recent_stats = self.db_manager.get_recent_daily_stats(7)
            if recent_stats:
                print(f"{'日期':>12} {'成功':>6} {'尝试':>6} {'成功率':>8} {'剩余配额':>8}")
                print("-" * 50)
                for stat in recent_stats:
                    date = stat['date']
                    successful = stat['successful_submits']
                    attempts = stat['total_attempts']
                    success_rate = stat['success_rate']
                    remaining = daily_limit - successful if daily_limit > 0 else "无限制"
                    
                    print(f"{date:>12} {successful:>6} {attempts:>6} {success_rate:>7}% {str(remaining):>8}")
            else:
                print("  暂无历史数据")
        
        except Exception as e:
            print(f"❌ 获取每日限额状态失败: {e}")
    
    def run_custom_query(self, sql: str):
        """执行自定义SQL查询"""
        print(f"🔧 执行自定义查询")
        print("="*50)
        print(f"SQL: {sql}")
        print()
        
        try:
            with self.db_manager.get_connection() as conn:
                if sql.strip().upper().startswith('SELECT'):
                    df = pd.read_sql_query(sql, conn)
                    if df.empty:
                        print("❌ 查询结果为空")
                    else:
                        print(f"📊 查询结果 ({len(df)} 行):")
                        print(df.to_string(index=False, max_rows=20))
                        if len(df) > 20:
                            print(f"... 还有 {len(df) - 20} 行")
                else:
                    cursor = conn.execute(sql)
                    print(f"✅ 查询执行成功，影响 {cursor.rowcount} 行")
                    
        except Exception as e:
            print(f"❌ 查询执行失败: {e}")

def show_menu():
    """显示菜单"""
    print("\n" + "="*60)
    print("  WorldQuant 因子数据库查看器")
    print("="*60)
    print("1. 📊 数据库概览")
    print("2. 🔍 搜索因子表达式")
    print("3. ✅ 查看已检查因子")
    print("4. 🚀 查看可提交因子")
    print("5. ⚙️  查看系统配置")
    print("6. 📅 每日提交限额状态")
    print("7. 🔧 执行自定义SQL查询")
    print("8. 📈 数据分析报告")
    print("0. 退出")
    print("="*60)

def generate_analysis_report(viewer: DatabaseViewer):
    """生成数据分析报告"""
    print("📈 数据分析报告")
    print("="*50)
    
    try:
        with viewer.db_manager.get_connection() as conn:
            # 1. 因子表达式分析
            print("📊 因子表达式分析:")
            cursor = conn.execute("""
                SELECT 
                    dataset_id,
                    region,
                    step,
                    COUNT(*) as total_count,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM factor_expressions 
                GROUP BY dataset_id, region, step
                ORDER BY total_count DESC
            """)
            
            for dataset_id, region, step, count, first, last in cursor.fetchall():
                print(f"  - {dataset_id}_{region}_{step}step: {count:,} 条")
                print(f"    首次创建: {first}")
                print(f"    最近创建: {last}")
            
            # 2. 检查率分析
            print(f"\n🔍 检查率分析:")
            cursor = conn.execute("""
                SELECT 
                    fe.dataset_id,
                    fe.region,
                    fe.step,
                    COUNT(fe.id) as total_expressions,
                    COUNT(ca.alpha_id) as checked_count,
                    ROUND(COUNT(ca.alpha_id) * 100.0 / COUNT(fe.id), 2) as check_rate
                FROM factor_expressions fe
                LEFT JOIN checked_alphas ca ON 
                    fe.dataset_id = ca.dataset_id AND 
                    fe.region = ca.region AND 
                    fe.step = ca.step
                GROUP BY fe.dataset_id, fe.region, fe.step
                ORDER BY check_rate DESC
            """)
            
            for dataset_id, region, step, total, checked, rate in cursor.fetchall():
                print(f"  - {dataset_id}_{region}_{step}step: {checked:,}/{total:,} ({rate}%)")
            
            # 3. 表达式复杂度分析
            print(f"\n🧮 表达式复杂度分析:")
            cursor = conn.execute("""
                SELECT 
                    LENGTH(expression) as expr_length,
                    COUNT(*) as count
                FROM factor_expressions 
                GROUP BY LENGTH(expression)
                ORDER BY expr_length
                LIMIT 10
            """)
            
            lengths = cursor.fetchall()
            if lengths:
                total_expressions = sum(count for _, count in lengths)
                print(f"  表达式长度分布 (前10种):")
                for length, count in lengths:
                    percentage = count * 100.0 / total_expressions
                    print(f"    {length} 字符: {count:,} 条 ({percentage:.1f}%)")
            
            # 4. 常用操作符分析
            print(f"\n🔧 常用操作符分析:")
            operators = ['ts_rank', 'ts_mean', 'ts_sum', 'rank', 'winsorize', 'ts_zscore', 'ts_delta']
            
            for op in operators:
                cursor = conn.execute("SELECT COUNT(*) FROM factor_expressions WHERE expression LIKE ?", (f"%{op}%",))
                count = cursor.fetchone()[0]
                cursor = conn.execute("SELECT COUNT(*) FROM factor_expressions")
                total = cursor.fetchone()[0]
                percentage = count * 100.0 / total if total > 0 else 0
                print(f"    {op}: {count:,} 次使用 ({percentage:.1f}%)")
            
            # 5. 数据库文件大小
            db_path = os.path.join(ROOT_PATH, 'database', 'factors.db')
            if os.path.exists(db_path):
                size_mb = os.path.getsize(db_path) / 1024 / 1024
                print(f"\n💾 数据库文件大小: {size_mb:.1f} MB")
            
    except Exception as e:
        print(f"❌ 分析报告生成失败: {e}")

def main():
    """主函数"""
    viewer = DatabaseViewer()
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择操作 (0-8): ").strip()
            
            if choice == '0':
                print("\n👋 再见！")
                break
            elif choice == '1':
                viewer.show_overview()
            elif choice == '2':
                print("\n🔍 搜索因子表达式")
                keyword = input("关键词 (可选): ").strip()
                dataset_id = input("数据集ID (可选): ").strip()
                region = input("地区 (可选): ").strip()
                step_str = input("步骤 (1/2，可选): ").strip()
                step = int(step_str) if step_str.isdigit() else None
                limit_str = input("显示数量 (默认10): ").strip()
                limit = int(limit_str) if limit_str.isdigit() else 10
                
                viewer.search_expressions(keyword, dataset_id, region, step, limit)
            elif choice == '3':
                print("\n✅ 查看已检查因子")
                dataset_id = input("数据集ID (可选): ").strip()
                region = input("地区 (可选): ").strip()
                step_str = input("步骤 (1/2，可选): ").strip()
                step = int(step_str) if step_str.isdigit() else None
                limit_str = input("显示数量 (默认20): ").strip()
                limit = int(limit_str) if limit_str.isdigit() else 20
                
                viewer.show_checked_alphas(dataset_id, region, step, limit)
            elif choice == '4':
                viewer.show_submitable_alphas()
            elif choice == '5':
                viewer.show_config()
            elif choice == '6':
                viewer.show_daily_submit_limit()
            elif choice == '7':
                print("\n🔧 执行自定义SQL查询")
                print("提示: 只支持SELECT查询以确保安全")
                sql = input("SQL查询: ").strip()
                if sql:
                    viewer.run_custom_query(sql)
            elif choice == '8':
                generate_analysis_report(viewer)
            else:
                print("❌ 无效选择，请重试")
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    main()