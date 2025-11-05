#!/usr/bin/env python3
"""
作者：e.e.
日期：2025.09.10
功能：将现有文本文件数据迁移到SQLite数据库
"""

import os
import sys
import sqlite3
import pandas as pd
import re
from datetime import datetime
from pathlib import Path

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.config import RECORDS_PATH, ROOT_PATH

class FactorDataMigrator:
    def __init__(self, db_path='database/factors.db'):
        """初始化迁移器"""
        self.db_path = os.path.join(ROOT_PATH, db_path)
        self.records_path = RECORDS_PATH
        self.conn = None
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def connect_db(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            print(f"✅ 成功连接数据库: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
            
    def create_schema(self):
        """创建数据库表结构"""
        try:
            # 检查表是否已存在
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            # 定义需要的表
            required_tables = ['factor_expressions', 'checked_alphas', 'submitable_alphas', 'failed_expressions', 'system_config']
            
            # 如果所有表都存在，跳过创建
            if all(table in existing_tables for table in required_tables):
                print("✅ 数据库表结构已存在，跳过创建")
                # 检查并添加复查标记列
                self._add_recheck_flag_if_missing()
                return True
            
            # 读取并修改 schema.sql，添加 IF NOT EXISTS
            schema_path = os.path.join(ROOT_PATH, 'database', 'schema.sql')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 替换 CREATE TABLE 为 CREATE TABLE IF NOT EXISTS
            schema_sql = schema_sql.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ')
            # 替换 CREATE INDEX 为 CREATE INDEX IF NOT EXISTS  
            schema_sql = schema_sql.replace('CREATE INDEX ', 'CREATE INDEX IF NOT EXISTS ')
            # 替换 CREATE VIEW 为 CREATE VIEW IF NOT EXISTS
            schema_sql = schema_sql.replace('CREATE VIEW ', 'CREATE VIEW IF NOT EXISTS ')
            
            # 处理 INSERT 语句，使用 INSERT OR IGNORE
            schema_sql = schema_sql.replace('INSERT INTO system_config', 'INSERT OR IGNORE INTO system_config')
            
            # 执行SQL创建表
            self.conn.executescript(schema_sql)
            self.conn.commit()
            print("✅ 数据库表结构创建成功")
            
            # 检查并添加复查标记列
            self._add_recheck_flag_if_missing()
            return True
        except Exception as e:
            print(f"❌ 创建表结构失败: {e}")
            return False
            
    def _add_recheck_flag_if_missing(self):
        """检查并添加复查标记列（如果缺失）"""
        try:
            # 检查recheck_flag列是否存在
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(submitable_alphas)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'recheck_flag' not in columns:
                print("🔄 添加复查标记列...")
                
                # 添加复查标记列
                self.conn.execute("ALTER TABLE submitable_alphas ADD COLUMN recheck_flag BOOLEAN DEFAULT FALSE")
                
                # 创建索引
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_submitable_recheck_flag ON submitable_alphas(recheck_flag)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_submitable_region_recheck ON submitable_alphas(region, recheck_flag)")
                
                # 更新数据库版本
                self.conn.execute("""
                    INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_at)
                    VALUES ('db_version', '1.1', '数据库版本', datetime('now'))
                """)
                
                # 记录迁移
                self.conn.execute("""
                    INSERT OR REPLACE INTO system_config (config_key, config_value, description)
                    VALUES ('recheck_flag_migration', datetime('now'), '添加复查标记列的迁移时间')
                """)
                
                self.conn.commit()
                print("✅ 复查标记列添加成功")
            else:
                print("✅ 复查标记列已存在")
                
        except Exception as e:
            print(f"❌ 添加复查标记列失败: {e}")
            
    def parse_filename_info(self, filename):
        """解析文件名获取数据集和地区信息"""
        # 示例: analyst4_usa_1step_simulated_alpha_expression.txt
        # 示例: fundamental2_usa_1step_simulated_alpha_expression.txt
        patterns = [
            r'(\w+)_(\w+)_(\d+)step_simulated_alpha_expression\.txt',
            r'(\w+)_(\w+)_(\d+)step_checked_alpha_id\.txt'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                dataset_id = match.group(1)
                region = match.group(2).upper()
                step = int(match.group(3))
                return dataset_id, region, step
        
        return None, None, None
        
    def migrate_factor_expressions(self):
        """迁移因子表达式数据"""
        print("\n🔄 开始迁移因子表达式数据...")
        total_migrated = 0
        
        # 查找所有表达式文件
        expression_files = []
        for file in os.listdir(self.records_path):
            if file.endswith('_simulated_alpha_expression.txt'):
                expression_files.append(file)
        
        for filename in expression_files:
            dataset_id, region, step = self.parse_filename_info(filename)
            if not all([dataset_id, region, step]):
                print(f"⚠️  跳过无法解析的文件: {filename}")
                continue
                
            file_path = os.path.join(self.records_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    expressions = [line.strip() for line in f if line.strip()]
                
                # 批量插入数据库
                for expression in expressions:
                    try:
                        self.conn.execute("""
                            INSERT OR IGNORE INTO factor_expressions 
                            (expression, dataset_id, region, step) 
                            VALUES (?, ?, ?, ?)
                        """, (expression, dataset_id, region, step))
                    except Exception as e:
                        print(f"⚠️  插入表达式失败: {expression[:50]}... - {e}")
                
                self.conn.commit()
                count = len(expressions)
                total_migrated += count
                print(f"✅ {filename}: 迁移 {count} 条表达式")
                
            except Exception as e:
                print(f"❌ 处理文件 {filename} 失败: {e}")
        
        print(f"📊 因子表达式迁移完成，总计: {total_migrated} 条")
        
    def migrate_checked_alphas(self):
        """迁移已检查因子数据"""
        print("\n🔄 开始迁移已检查因子数据...")
        total_migrated = 0
        
        # 查找所有已检查文件
        checked_files = []
        for file in os.listdir(self.records_path):
            if file.endswith('_checked_alpha_id.txt'):
                checked_files.append(file)
        
        for filename in checked_files:
            dataset_id, region, step = self.parse_filename_info(filename)
            if not all([dataset_id, region, step]):
                print(f"⚠️  跳过无法解析的文件: {filename}")
                continue
                
            file_path = os.path.join(self.records_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    alpha_ids = [line.strip() for line in f if line.strip()]
                
                # 批量插入数据库
                for alpha_id in alpha_ids:
                    try:
                        self.conn.execute("""
                            INSERT OR IGNORE INTO checked_alphas 
                            (alpha_id, dataset_id, region, step) 
                            VALUES (?, ?, ?, ?)
                        """, (alpha_id, dataset_id, region, step))
                    except Exception as e:
                        print(f"⚠️  插入Alpha ID失败: {alpha_id} - {e}")
                
                self.conn.commit()
                count = len(alpha_ids)
                total_migrated += count
                print(f"✅ {filename}: 迁移 {count} 个Alpha ID")
                
            except Exception as e:
                print(f"❌ 处理文件 {filename} 失败: {e}")
        
        print(f"📊 已检查因子迁移完成，总计: {total_migrated} 条")
        
    def migrate_submitable_alphas(self):
        """迁移可提交因子数据"""
        print("\n🔄 开始迁移可提交因子数据...")
        
        csv_path = os.path.join(self.records_path, 'submitable_alpha.csv')
        if not os.path.exists(csv_path):
            print("⚠️  submitable_alpha.csv 文件不存在")
            return
            
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_path)
            
            if df.empty:
                print("⚠️  submitable_alpha.csv 文件为空")
                return
            
            # 转换列名：驼峰转下划线
            column_mapping = {}
            for col in df.columns:
                # 将驼峰命名转换为下划线命名
                snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', col).lower()
                column_mapping[col] = snake_case
            
            df = df.rename(columns=column_mapping)
            
            # 逐行插入数据库，避免重复
            for _, row in df.iterrows():
                try:
                    # 使用INSERT OR IGNORE避免重复插入
                    columns = ', '.join(row.index)
                    placeholders = ', '.join(['?' for _ in range(len(row))])
                    query = f"INSERT OR IGNORE INTO submitable_alphas ({columns}) VALUES ({placeholders})"
                    self.conn.execute(query, tuple(row.values))
                except Exception as e:
                    print(f"⚠️  插入可提交因子失败: {row.get('id', 'Unknown')} - {e}")
            
            self.conn.commit()
            
            count = len(df)
            print(f"✅ 可提交因子迁移完成: {count} 条")
            
        except Exception as e:
            print(f"❌ 迁移可提交因子失败: {e}")
            
    # notified_alphas.txt 不需要迁移到数据库
    # 这类通知日志文件保持文件存储方式即可
            
    def migrate_config(self):
        """迁移配置数据"""
        print("\n🔄 开始迁移配置数据...")
        
        # 迁移开始日期
        start_date_path = os.path.join(self.records_path, 'start_date.txt')
        if os.path.exists(start_date_path):
            try:
                with open(start_date_path, 'r', encoding='utf-8') as f:
                    start_date = f.read().strip()
                
                self.conn.execute("""
                    INSERT OR REPLACE INTO system_config 
                    (config_key, config_value, description) 
                    VALUES (?, ?, ?)
                """, ('start_date', start_date, '因子挖掘开始日期'))
                
                self.conn.commit()
                print(f"✅ 开始日期配置迁移完成: {start_date}")
                
            except Exception as e:
                print(f"❌ 迁移开始日期配置失败: {e}")
        
    def verify_migration(self):
        """验证迁移结果"""
        print("\n📊 验证迁移结果...")
        
        try:
            # 查询各表数据量
            tables = ['factor_expressions', 'checked_alphas', 'submitable_alphas', 'system_config']
            
            for table in tables:
                cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} 条记录")
            
            # 显示系统概览
            print("\n📈 数据分布统计:")
            cursor = self.conn.execute("SELECT * FROM system_overview")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} 条记录，最新更新: {row[2]}")
                
        except Exception as e:
            print(f"❌ 验证迁移结果失败: {e}")
            
    def run_migration(self):
        """执行完整迁移流程"""
        print("🚀 开始数据迁移...")
        
        if not self.connect_db():
            return False
            
        try:
            # 1. 创建表结构
            if not self.create_schema():
                return False
            
            # 2. 迁移各类数据
            self.migrate_factor_expressions()
            self.migrate_checked_alphas()
            self.migrate_submitable_alphas()
            self.migrate_config()
            
            print("📝 注意: notified_alphas.txt 等通知日志文件保持原有文件存储方式")
            
            # 3. 验证结果
            self.verify_migration()
            
            print("\n✅ 数据迁移完成！")
            print(f"📍 数据库位置: {self.db_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 迁移过程中发生错误: {e}")
            return False
            
        finally:
            if self.conn:
                self.conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("  WorldQuant 因子系统数据迁移工具")
    print("  从文本文件迁移到SQLite数据库")
    print("=" * 60)
    
    migrator = FactorDataMigrator()
    success = migrator.run_migration()
    
    if success:
        print("\n🎉 迁移成功！现在可以使用数据库进行因子管理了。")
    else:
        print("\n💥 迁移失败，请检查错误信息并重试。")
        sys.exit(1)

if __name__ == "__main__":
    main()