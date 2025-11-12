"""
一阶挖掘执行器 (First Order Executor)
作者：e.e.
日期：2025.09.05

负责执行一阶因子挖掘，包括：
- 字段获取和处理
- 一阶因子生成
- 进度跟踪和通知
- 模拟执行
"""

import random
import json
import os
import sys
from typing import List, Dict
from datetime import datetime

from .base_executor import BaseExecutor

try:
    from lib.data_client import get_datafields, process_datafields
    from lib.factor_generator import first_order_factory
    from digging.utils.common_utils import get_filtered_operators
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    from lib.data_client import get_datafields, process_datafields
    from lib.factor_generator import first_order_factory
    from digging.utils.common_utils import get_filtered_operators


class FirstOrderExecutor(BaseExecutor):
    """一阶挖掘执行器 - 负责执行一阶因子挖掘的完整流程"""
    
    def get_stage_number(self) -> int:
        """获取执行器对应的阶段号"""
        return 1
    
    def get_pc_fields(self):
        """获取PC字段列表
        
        Returns:
            List[str]: PC字段列表
        """
        if self.config_manager.use_recommended_fields:
            # 使用配置文件中的推荐字段
            return self.config_manager.get_recommended_fields()
        else:
            # 通过API获取字段
            df = get_datafields(
                self.session, 
                dataset_id=self.current_dataset, 
                region=self.config_manager.region, 
                universe=self.config_manager.universe, 
                delay=self.config_manager.delay
            )
            pc_fields = process_datafields(df, "matrix") + process_datafields(df, "vector")
            
            # 如果API获取字段失败，尝试刷新会话并重试
            if not pc_fields:
                if self.logger:
                    self.logger.warning(f"⚠️  数据集 {self.current_dataset} API获取字段失败，尝试刷新会话并重试")
                
                if self.refresh_session_if_needed():
                    # 使用新session重试
                    df = get_datafields(
                        self.session, 
                        dataset_id=self.current_dataset, 
                        region=self.config_manager.region, 
                        universe=self.config_manager.universe, 
                        delay=self.config_manager.delay
                    )
                    pc_fields = process_datafields(df, "matrix") + process_datafields(df, "vector")
                    
                    if not pc_fields:
                        if self.logger:
                            self.logger.error(f"❌ 会话更新后仍无法获取字段")
                        raise Exception(f"无法获取数据集 {self.current_dataset} 的字段信息")
                    else:
                        if self.logger:
                            self.logger.info(f"✅ 会话更新后成功获取字段")
                else:
                    raise Exception(f"会话刷新失败，无法获取数据集 {self.current_dataset} 的字段信息")
            
            return pc_fields
    
    def generate_first_order_factors(self, pc_fields: List[str]) -> List[str]:
        """生成一阶因子列表
        
        Args:
            pc_fields: PC字段列表
            
        Returns:
            List[str]: 一阶因子表达式列表
        """
        # 获取过滤后的操作符
        ts_ops, basic_ops, group_ops = get_filtered_operators()
        # first_order = []
        first_order = first_order_factory(pc_fields, ts_ops)
        for factor in first_order:
            print("Generated first order factors:",factor)
        self.logger.info(f"请构建一阶因子表达式")
        
        if self.logger:
            self.logger.info(f"📊 生成一阶因子: {len(first_order):,} 个")
        
        return first_order
    
    def filter_completed_factors(self, all_factors: List[str]) -> List[str]:
        """过滤已完成的因子
        
        Args:
            all_factors: 所有因子列表
            
        Returns:
            List[str]: 待处理的因子列表
        """
        completed_expressions = self.progress_tracker.get_completed_expressions(
            self.current_dataset, step=1
        )
        valid_alphas = [alpha for alpha in all_factors if alpha not in completed_expressions]
        
        completion_rate = len(completed_expressions) / len(all_factors) * 100 if all_factors else 0
        
        if self.logger:
            self.progress_tracker.log_progress_summary(
                self.current_dataset, 1, len(completed_expressions), 
                len(all_factors), completion_rate
            )
        
        return valid_alphas, completed_expressions, completion_rate
    
    async def execute(self) -> List[Dict]:
        """执行一阶挖掘的完整流程
        
        Returns:
            List[Dict]: 执行结果列表
        """
        stage = self.get_stage_number()
        self.log_execution_start(stage)
        
        try:
            # 1. 初始化会话和操作符
            if not self.ensure_session_and_operators():
                raise Exception("会话和操作符初始化失败")
            
            if self.logger:
                self.logger.info(f"\n🔍 开始一阶挖掘 (数据集: {self.current_dataset}, 完整执行)")
            
            # 2. 获取字段和生成因子
            if self.logger:
                self.logger.info(f"📊 获取数据集字段...")
            
            pc_fields = self.get_pc_fields()
            
            if self.logger:
                self.logger.info(f"📊 使用字段: {len(pc_fields)} 个字段")
            
            # 3. 生成一阶因子
            if self.logger:
                self.logger.info(f"🔨 生成一阶因子...")
            
            first_order = self.generate_first_order_factors(pc_fields)
            
            # 4. 过滤已完成的因子
            if self.logger:
                self.logger.info(f"🔍 过滤已完成因子...")
            
            valid_alphas, completed_expressions, completion_rate = self.filter_completed_factors(first_order)
            
            if not valid_alphas:
                if self.logger:
                    self.logger.info(f"✅ 数据集 {self.current_dataset} 一阶挖掘已完成")
                
                # 不再发送完成通知 - 仅在执行过程中达到阈值时发送
                
                self.log_execution_end(stage, [], success=True)
                return []
            
            # 5. 准备执行模拟
            if self.logger:
                self.logger.info(f"📦 准备执行: {len(valid_alphas):,}个因子")
            
            # 随机打乱因子顺序
            random.shuffle(valid_alphas)
            
            # 6. 执行模拟 - 传递规范tag
            step1_tag = self.config_manager.generate_tag(self.current_dataset, stage)
            results = await self.simulation_executor.execute_batch(
                valid_alphas, self.current_dataset, stage, tags=[step1_tag]
            )
            
            if self.logger:
                self.logger.info(f"✅ 一阶挖掘完成: {len(valid_alphas):,}个因子")
            
            # 模拟完成后，重新检查完成度并发送通知
            try:
                updated_completed = self.progress_tracker.get_completed_expressions(
                    self.current_dataset, step=1
                )
                updated_completion_rate = len(updated_completed) / len(first_order) * 100 if first_order else 0
                updated_remaining = len(first_order) - len(updated_completed)
                
                if self.logger:
                    self.logger.info(f"📊 模拟后统计: 完成度{updated_completion_rate:.1f}% | 剩余{updated_remaining:,}个")
                
                # 检查是否需要发送更新的完成度通知
                self.progress_tracker.check_and_send_completion_notification(
                    self.current_dataset, updated_completion_rate, len(updated_completed), 
                    len(first_order), updated_remaining, self.start_time, stage=1
                )
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"⚠️ 模拟后通知检查失败: {e}")
            
            
            self.log_execution_end(stage, results, success=True)
            return results
            
        except Exception as e:
            self.handle_execution_error(stage, e)
            self.log_execution_end(stage, [], success=False)
            return []
