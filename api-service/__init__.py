"""
双时序记忆系统 API 服务包

本包提供双时序记忆系统的核心API服务，包括：
1. 双时序实体管理
2. 关系时间管理
3. 高级功能（模式检测、因果推理、实时看板）
4. 批量导入导出
"""

__version__ = "1.0.0"
__author__ = "双时序记忆系统团队"

# 导出主要服务类
__all__ = [
    "EnhancedGraphitiService",
    "CausalInferenceService",
    "PatternDetectionService",
    "RealtimeDashboardService",
    "BatchImportExportService"
]
