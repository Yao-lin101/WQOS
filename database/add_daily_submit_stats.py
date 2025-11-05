#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加每日提交统计表
为现有的factors.db数据库添加daily_submit_stats表及相关视图
"""

import os
import sys
import sqlite3
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.config import ROOT_PATH

def check_table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def check_view_exists(cursor, view_name):
    """检查视图是否存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='view' AND name=?
    """, (view_name,))
    return cursor.fetchone() is not None

def main():
    """主函数"""
    print("🚀 每日提交统计表迁移脚本")
    print("="*50)
    
    # 数据库路径
    db_path = os.path.join(ROOT_PATH, 'database', 'factors.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("   请先运行挖掘脚本创建数据库或使用 ./control.sh db-test")
        return False
    
    print(f"📂 数据库路径: {db_path}")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("✅ 数据库连接成功")
        
        # 检查是否已经存在daily_submit_stats表
        if check_table_exists(cursor, 'daily_submit_stats'):
            print("ℹ️  daily_submit_stats表已存在，跳过创建")
        else:
            print("📝 创建daily_submit_stats表...")
            cursor.execute("""
                CREATE TABLE daily_submit_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,                    -- 日期 YYYY-MM-DD
                    successful_submits INTEGER DEFAULT 0,         -- 当日成功提交数量
                    total_attempts INTEGER DEFAULT 0,             -- 当日总尝试数量
                    timezone VARCHAR(20) DEFAULT 'UTC',           -- 使用的时区
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 约束检查
                    CHECK (successful_submits >= 0),
                    CHECK (total_attempts >= successful_submits)
                )
            """)
            print("✅ daily_submit_stats表创建成功")
        
        # 检查索引是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_daily_submit_stats_date'
        """)
        if cursor.fetchone() is None:
            print("📝 创建日期索引...")
            cursor.execute("""
                CREATE INDEX idx_daily_submit_stats_date ON daily_submit_stats(date)
            """)
            print("✅ 日期索引创建成功")
        else:
            print("ℹ️  日期索引已存在，跳过创建")
        
        # 检查是否已经存在daily_submit_overview视图
        if check_view_exists(cursor, 'daily_submit_overview'):
            print("ℹ️  daily_submit_overview视图已存在，跳过创建")
        else:
            print("📝 创建daily_submit_overview视图...")
            cursor.execute("""
                CREATE VIEW daily_submit_overview AS
                SELECT 
                    date,
                    successful_submits,
                    total_attempts,
                    timezone,
                    CASE 
                        WHEN total_attempts > 0 THEN ROUND(successful_submits * 100.0 / total_attempts, 1)
                        ELSE 0
                    END as success_rate,
                    last_updated
                FROM daily_submit_stats
                ORDER BY date DESC
            """)
            print("✅ daily_submit_overview视图创建成功")
        
        # 更新system_overview视图
        if check_view_exists(cursor, 'system_overview'):
            print("📝 更新system_overview视图...")
            cursor.execute("DROP VIEW system_overview")
            cursor.execute("""
                CREATE VIEW system_overview AS
                SELECT 
                    'factor_expressions' as table_name,
                    COUNT(*) as record_count,
                    MAX(created_at) as latest_update
                FROM factor_expressions
                UNION ALL
                SELECT 
                    'checked_alphas' as table_name,
                    COUNT(*) as record_count,
                    MAX(checked_at) as latest_update
                FROM checked_alphas
                UNION ALL
                SELECT 
                    'submitable_alphas' as table_name,
                    COUNT(*) as record_count,
                    MAX(created_at) as latest_update
                FROM submitable_alphas
                UNION ALL
                SELECT 
                    'daily_submit_stats' as table_name,
                    COUNT(*) as record_count,
                    MAX(last_updated) as latest_update
                FROM daily_submit_stats
            """)
            print("✅ system_overview视图更新成功")
        
        # 提交更改
        conn.commit()
        
        # 验证迁移结果
        print("\n🔍 迁移结果验证:")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(daily_submit_stats)")
        columns = cursor.fetchall()
        print(f"  - daily_submit_stats表有 {len(columns)} 个字段")
        
        # 检查数据
        cursor.execute("SELECT COUNT(*) FROM daily_submit_stats")
        count = cursor.fetchone()[0]
        print(f"  - daily_submit_stats表有 {count} 条记录")
        
        # 测试视图
        try:
            cursor.execute("SELECT * FROM daily_submit_overview LIMIT 1")
            print("  - daily_submit_overview视图工作正常")
        except Exception as e:
            print(f"  - ⚠️  daily_submit_overview视图测试失败: {e}")
        
        try:
            cursor.execute("SELECT * FROM system_overview WHERE table_name='daily_submit_stats'")
            result = cursor.fetchone()
            if result:
                print("  - system_overview视图包含daily_submit_stats")
            else:
                print("  - ⚠️  system_overview视图未包含daily_submit_stats")
        except Exception as e:
            print(f"  - ⚠️  system_overview视图测试失败: {e}")
        
        print(f"\n🎉 迁移完成!")
        print(f"💡 现在可以使用以下命令查看每日提交限额状态:")
        print(f"   ./control.sh db-daily-limit")
        print(f"   python database/quick_queries.py daily-limit")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()
            print("📝 数据库连接已关闭")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)