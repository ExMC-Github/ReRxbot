# 不是我（ExRFy）写的，我看这代码像GLM-5.2帮我写的
import os
from loguru import logger
from typing import Dict, Optional


class AIManager:
    """AI管理器，用于管理rules文件夹中的提示词"""
    
    def __init__(self, rules_dir: str = "rules", default_rule: str = "default.txt"):
        """
        初始化AI管理器
        
        Args:
            rules_dir: rules文件夹路径
            default_rule: 默认规则文件名
        """
        self.rules_dir = rules_dir
        self.default_rule = default_rule
        self.rules: Dict[str, str] = {}
        self.current_rule: str = default_rule
        
        # 确保rules文件夹存在
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir)
            logger.warning(f"rules文件夹不存在，已创建: {rules_dir}")
        
        # 加载所有规则
        self.load_all_rules()
        
        # 设置默认规则
        if default_rule.replace(".txt", "") in self.rules:
            self.set_rule(default_rule.replace(".txt", ""))
        else:
            logger.warning(f"默认规则文件 {default_rule} 不存在")
    
    def load_rule(self, rule_name: str) -> Optional[str]:
        """
        加载单个规则文件
        
        Args:
            rule_name: 规则名称（不带.txt后缀）
        
        Returns:
            规则内容，如果文件不存在则返回None
        """
        rule_file = os.path.join(self.rules_dir, f"{rule_name}.txt")
        
        if not os.path.exists(rule_file):
            logger.warning(f"规则文件不存在: {rule_file}")
            return None
        
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            self.rules[rule_name] = content
            logger.info(f"已加载规则: {rule_name}")
            return content
        except Exception as e:
            logger.error(f"加载规则文件 {rule_file} 失败: {e}")
            return None
    
    def load_all_rules(self):
        """加载rules文件夹中的所有规则文件"""
        if not os.path.exists(self.rules_dir):
            logger.warning(f"rules文件夹不存在: {self.rules_dir}")
            return
        
        rule_files = [f for f in os.listdir(self.rules_dir) if f.endswith('.txt')]
        
        if not rule_files:
            logger.warning(f"rules文件夹中没有找到规则文件")
            return
        
        for rule_file in rule_files:
            rule_name = rule_file.replace('.txt', '')
            self.load_rule(rule_name)
        
        logger.info(f"已加载 {len(self.rules)} 个规则")
    
    def get_rule(self, rule_name: Optional[str] = None) -> str:
        """
        获取指定规则内容
        
        Args:
            rule_name: 规则名称，如果为None则返回当前规则
        
        Returns:
            规则内容
        """
        if rule_name is None:
            rule_name = self.current_rule
        
        if rule_name not in self.rules:
            logger.warning(f"规则 {rule_name} 不存在，返回默认规则")
            return self.rules.get(self.default_rule.replace('.txt', ''), "")
        
        return self.rules[rule_name]
    
    def set_rule(self, rule_name: str) -> bool:
        """
        设置当前使用的规则
        
        Args:
            rule_name: 规则名称
        
        Returns:
            是否设置成功
        """
        if rule_name not in self.rules:
            logger.warning(f"规则 {rule_name} 不存在")
            return False
        
        self.current_rule = rule_name
        logger.info(f"已切换到规则: {rule_name}")
        return True
    
    def list_rules(self) -> list:
        """列出所有可用的规则名称"""
        return list(self.rules.keys())
    
    def reload_rules(self):
        """重新加载所有规则"""
        self.rules.clear()
        self.load_all_rules()
        logger.info("已重新加载所有规则")