"""
二阶挖掘执行器 (Second Order Executor)
作者：e.e.
日期：2025.09.05

负责执行二阶因子挖掘，包括：
- 基于一阶符合条件因子生成二阶因子
- 持续监控一阶挖掘产出
- 进度跟踪
- 模拟执行
"""

import os
import sys
import random
from collections import defaultdict
from typing import List, Dict, Tuple

from .base_executor import BaseExecutor

try:
    from lib.data_client import get_alphas
    from lib.factor_generator import transform, get_group_second_order_factory
    from digging.utils.common_utils import get_filtered_operators
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    from lib.data_client import get_alphas
    from lib.factor_generator import transform, get_group_second_order_factory
    from digging.utils.common_utils import get_filtered_operators


class SecondOrderExecutor(BaseExecutor):
    """二阶挖掘执行器 - 负责执行二阶因子挖掘的完整流程"""
    
    def get_stage_number(self) -> int:
        """获取执行器对应的阶段号"""
        return 2
    
    def get_qualified_first_order_factors(self) -> Tuple[List[str], List[str], int]:
        """获取符合条件的一阶因子
        
        Returns:
            Tuple[List[str], List[str], int]: (next因子列表, decay因子列表, 总数量)
        """
        step1_tag = self.config_manager.generate_tag(self.current_dataset, 1)
        
        # 计算最近一年的日期范围（end_date使用明天避免时差问题）
        from datetime import datetime, timedelta
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 获取符合条件的一阶因子
        fo_tracker = get_alphas(start_date, end_date,
                               0.75, 0.5, 100, 100,
                               self.config_manager.region, 
                               self.config_manager.universe, 
                               self.config_manager.delay, 
                               self.config_manager.instrument_type,
                               500, "track", tag=step1_tag)
        
        next_factors = fo_tracker.get('next', [])
        decay_factors = fo_tracker.get('decay', [])
        total_qualified = len(next_factors) + len(decay_factors)
        
        return next_factors, decay_factors, total_qualified
    
    def generate_second_order_factors(self, next_factors: List[str], decay_factors: List[str]) -> List[Tuple[str, int]]:
        """生成二阶因子列表
        
        Args:
            next_factors: next类型的一阶因子
            decay_factors: decay类型的一阶因子
            
        Returns:
            List[Tuple[str, int]]: 二阶因子表达式和衰减值的元组列表
        """
        # 转换一阶因子格式
        fo_layer = transform(next_factors + decay_factors)
        
        # 获取过滤后的操作符
        ts_ops, basic_ops, group_ops = get_filtered_operators()
        
        # 生成二阶因子
        second_order_factors = []
        self.logger.info(f"请构建二阶因子表达式")

        for expr, decay in fo_layer:
            for alpha in get_group_second_order_factory([expr], group_ops, self.config_manager.region):
                second_order_factors.append((alpha, decay))

        random.shuffle(second_order_factors)
        
        if self.logger:
            self.logger.info(f"📊 生成二阶因子: {len(second_order_factors):,} 个")
        
        return second_order_factors
    
    def filter_completed_second_order_factors(self, all_factors: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """过滤已完成的二阶因子
        
        Args:
            all_factors: 所有二阶因子列表
            
        Returns:
            List[Tuple[str, int]]: 待处理的二阶因子列表
        """
        completed_expressions = self.progress_tracker.get_completed_expressions(
            self.current_dataset, step=2
        )
        
        valid_factors = [alpha_decay for alpha_decay in all_factors 
                        if alpha_decay[0] not in completed_expressions]
        
        completion_rate = len(completed_expressions) / len(all_factors) * 100 if all_factors else 0
        
        if self.logger:
            self.progress_tracker.log_progress_summary(
                self.current_dataset, 2, len(completed_expressions), 
                len(all_factors), completion_rate
            )
        
        return valid_factors
    
    async def execute_second_order_batch(self, valid_factors: List[Tuple[str, int]]) -> List[Dict]:
        """执行二阶因子模拟批次
        
        Args:
            valid_factors: 待处理的二阶因子列表
            
        Returns:
            List[Dict]: 执行结果列表
        """
        if not valid_factors:
            return []
        
        # 分离Alpha表达式和衰减值
        alpha_list = [alpha_decay[0] for alpha_decay in valid_factors]
        decay_list = [alpha_decay[1] for alpha_decay in valid_factors]
        
        # 准备其他参数
        region_list = [(self.config_manager.region, self.config_manager.universe)] * len(alpha_list)
        delay_list = [self.config_manager.delay] * len(alpha_list)
        stone_bag = []
        step2_tag = self.config_manager.generate_tag(self.current_dataset, 2)
        
        # 执行模拟 - 传递规范tag
        await self.simulation_executor.execute_batch(
            alpha_list, self.current_dataset, stage=2, tags=[step2_tag]
        )
        
        return [{'alpha': alpha, 'tag': step2_tag} for alpha in alpha_list]
    
    async def run_continuous_monitoring(self, retry_count: int = 0) -> List[Dict]:
        """运行持续监控模式（递归监控一阶挖掘产出）
        
        Args:
            retry_count: 重试计数
            
        Returns:
            List[Dict]: 执行结果列表
        """
        all_results = []
        
        while True:
            try:
                # 1. 获取符合条件的一阶因子
                next_factors, decay_factors, total_qualified = self.get_qualified_first_order_factors()
                
                if self.logger:
                    self.logger.info(f"📊 符合条件一阶因子: next{len(next_factors):,}个 + decay{len(decay_factors):,}个 = 总计{total_qualified:,}个")
                
                if total_qualified == 0:
                    total_wait_hours = retry_count + 1
                    if self.logger:
                        self.logger.warning(f"⚠️  暂无符合条件的一阶因子 (第{retry_count + 1}次检查，已等待{retry_count}小时)")
                        self.logger.info(f"🔄 二阶挖掘持续等待一阶挖掘产生符合条件的因子...")
                        self.logger.info(f"💡 这是正常现象：二阶挖掘依赖一阶挖掘的输出，需要耐心等待")
                    
                    await self.simulation_executor.sleep_with_countdown(3600, "等待一阶挖掘产生更多因子")
                    retry_count += 1
                    continue
                
                # 2. 生成二阶因子
                second_order_factors = self.generate_second_order_factors(next_factors, decay_factors)
                
                # 3. 过滤已完成的二阶因子
                valid_factors = self.filter_completed_second_order_factors(second_order_factors)
                
                if not valid_factors:
                    if self.logger:
                        self.logger.info(f"✅ 数据集 {self.current_dataset} 二阶挖掘当前批次已完成")
                        self.logger.info(f"🔄 继续监控一阶挖掘，等待新的符合条件因子...")
                    
                    await self.simulation_executor.sleep_with_countdown(1800, "等待一阶挖掘产生新的符合条件因子")  # 30分钟
                    retry_count += 1
                    continue
                
                # 4. 执行二阶挖掘
                batch_results = await self.execute_second_order_batch(valid_factors)
                all_results.extend(batch_results)
                
                if self.logger:
                    self.logger.info(f"✅ 二阶挖掘批次完成: {len(batch_results):,}个因子")
                
                # 完成当前批次后，继续监控新的符合条件因子
                if self.logger:
                    self.logger.info(f"🔄 当前批次完成，继续监控一阶挖掘产生新的符合条件因子...")
                
                await self.simulation_executor.sleep_with_countdown(1800, "等待一阶挖掘产生新的符合条件因子")  # 30分钟
                retry_count += 1
                
            except KeyboardInterrupt:
                if self.logger:
                    self.logger.info(f"⚠️  用户中断，二阶挖掘停止")
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ 二阶挖掘监控循环异常: {e}")
                    import traceback
                    traceback.print_exc()
                # 等待一段时间后重试
                await self.simulation_executor.sleep_with_countdown(300, "异常恢复等待")
                retry_count += 1
        
        return all_results
    
    async def execute(self) -> List[Dict]:
        """执行二阶挖掘的完整流程
        
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
                self.logger.info(f"\n🔄 二阶挖掘 | 数据集: {self.current_dataset}")
            
            # 2. 运行持续监控模式
            results = await self.run_continuous_monitoring()
            
            
            self.log_execution_end(stage, results, success=True)
            return results
            
        except Exception as e:
            self.handle_execution_error(stage, e)
            self.log_execution_end(stage, [], success=False)
            return []
