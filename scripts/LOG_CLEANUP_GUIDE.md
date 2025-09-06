# 日志清理指南

## 🚨 问题描述

系统中存在大量孤儿日志文件（没有对应数据库记录的历史日志），导致磁盘空间浪费。

### 🔍 问题表现
- 日志目录下有很多历史日志文件
- 删除历史任务时，只删除一个日志文件，其他相关日志文件仍然存在
- 磁盘空间被大量无用日志文件占用

## 🛠️ 解决方案

### 1. 立即清理孤儿日志文件

#### 📋 预览清理操作（推荐先执行）
```bash
cd /path/to/WorldQuant
python3 scripts/cleanup_orphan_logs.py --dry-run
```

#### 🗑️ 执行实际清理
```bash
cd /path/to/WorldQuant
python3 scripts/cleanup_orphan_logs.py --execute
```

#### ⏰ 只清理超过指定天数的文件
```bash
# 只清理超过7天的孤儿日志
python3 scripts/cleanup_orphan_logs.py --execute --days 7

# 只清理超过3天的孤儿日志
python3 scripts/cleanup_orphan_logs.py --execute --days 3
```

### 2. 清理脚本功能说明

#### 🔍 自动识别功能
- **孤儿日志检测**：自动识别没有数据库记录的日志文件
- **脚本类型分析**：支持 `check_optimized`、`correlation_checker`、`unified_digging` 等
- **大小统计**：显示每个类型的文件数量和占用空间
- **安全预览**：默认预览模式，避免误删

#### 📊 清理报告示例
```
🧹 孤儿日志文件清理工具
==================================================
📂 扫描日志目录: /path/to/logs
📊 发现 43 个日志文件，总大小: 487.23 MB
  📄 check_optimized: 15 个文件，234.56 MB
  📄 correlation_checker: 18 个文件，198.34 MB  
  📄 unified_digging: 10 个文件，54.33 MB

📋 数据库中有 4 个日志文件记录

📊 清理报告
==================================================
🔍 发现 39 个孤儿日志文件，总大小: 456.78 MB
  📄 check_optimized: 13 个文件，212.34 MB
  📄 correlation_checker: 16 个文件，178.12 MB
  📄 unified_digging: 10 个文件，66.32 MB

✅ 清理完成:
  🗑️ 已删除: 39 个文件
  💾 释放空间: 456.78 MB
```

### 3. 改进的日志删除逻辑

#### 🔧 新的删除任务时清理逻辑
现在删除任务时会智能清理相关日志：

1. **轮转日志文件**：`filename.log.1`, `filename.log.2` 等
2. **同PID关联日志**：同一进程产生的其他日志文件
3. **安全保护**：不会误删正在运行任务的日志

#### 📝 日志文件命名规范
```
格式: {script_type}_{YYYYMMDD}_{HHMMSS}_{pid}.log

示例:
- check_optimized_20250904_015221_186.log
- correlation_checker_20250904_020020_296.log  
- unified_digging_20250904_073040_1822.log
```

## 🔄 定期维护建议

### 📅 建议清理频率
- **每周清理**：清理超过7天的孤儿日志
- **每月清理**：完整扫描和清理所有孤儿日志
- **紧急清理**：磁盘空间不足时立即清理

### 🤖 自动化清理（可选）
添加到 crontab 中进行定期自动清理：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周日凌晨2点清理超过7天的孤儿日志）
0 2 * * 0 cd /path/to/WorldQuant && python3 scripts/cleanup_orphan_logs.py --execute --days 7 >> /var/log/log_cleanup.log 2>&1
```

### 📊 监控磁盘使用
```bash
# 检查logs目录大小
du -sh /path/to/WorldQuant/logs

# 检查系统磁盘使用
df -h

# 持续监控（可选）
watch -n 300 'du -sh /path/to/WorldQuant/logs'
```

## 🚨 紧急情况处理

### 💾 磁盘空间不足
```bash
# 1. 立即检查日志目录大小
du -sh /path/to/WorldQuant/logs

# 2. 紧急清理所有孤儿日志
python3 scripts/cleanup_orphan_logs.py --execute

# 3. 如果仍不足，清理超过1天的文件
python3 scripts/cleanup_orphan_logs.py --execute --days 1

# 4. 检查系统其他大文件
find /path/to/WorldQuant -size +100M -type f
```

### 🔧 脚本执行问题
```bash
# 检查Python环境
python3 --version

# 检查依赖
python3 -c "import sqlalchemy; print('SQLAlchemy OK')"

# 检查数据库连接
python3 -c "
import sys, os
sys.path.append('/path/to/WorldQuant/digging-dashboard/backend')
from app.db.models import DiggingProcess
print('Database models OK')
"

# 检查权限
ls -la scripts/cleanup_orphan_logs.py
```

## 📝 使用注意事项

### ⚠️ 安全提醒
1. **先预览再执行**：建议总是先使用 `--dry-run` 预览
2. **备份重要日志**：如有需要，先备份重要的日志文件
3. **避免删除活动任务日志**：脚本会自动保护数据库中有记录的日志

### 🎯 最佳实践
1. **定期清理**：建立定期清理机制，避免积累过多
2. **监控空间**：定期检查磁盘空间使用情况
3. **适当保留**：可以使用 `--days` 参数保留最近几天的日志
4. **日志轮转**：确保Docker容器的日志轮转正常工作

## 🆘 支持与故障排除

### 常见问题
1. **权限错误**：确保脚本有执行权限和日志目录的写权限
2. **数据库连接失败**：检查数据库文件路径是否正确
3. **Python依赖缺失**：确保安装了必要的Python包

### 获取帮助
```bash
# 查看脚本帮助
python3 scripts/cleanup_orphan_logs.py --help

# 查看详细执行过程
python3 scripts/cleanup_orphan_logs.py --execute --days 7 2>&1 | tee cleanup.log
```
