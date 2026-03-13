"""配置管理模块"""
import os
import yaml
from typing import Any, Optional


class Config:
    """配置管理类"""

    _config = {}

    @classmethod
    def load(cls, config_file: str = "config.yaml"):
        """加载配置文件"""
        # 首先尝试加载 config.yaml
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f) or {}
        else:
            # 回退到 config.example.yaml
            example_file = "config.example.yaml"
            if os.path.exists(example_file):
                with open(example_file, 'r', encoding='utf-8') as f:
                    cls._config = yaml.safe_load(f) or {}
            else:
                cls._config = {}

        # 处理环境变量
        cls._process_env_vars()

        print(f"配置加载完成")
        return cls._config

    @classmethod
    def _process_env_vars(cls):
        """处理环境变量引用 ${VAR_NAME}"""
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str):
                if obj.startswith('${') and obj.endswith('}'):
                    var_name = obj[2:-1]
                    return os.environ.get(var_name, obj)
                return obj
            return obj

        cls._config = replace_env_vars(cls._config)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的键"""
        if not cls._config:
            cls.load()

        keys = key.split('.')
        value = cls._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @classmethod
    def set(cls, key: str, value: Any):
        """设置配置值"""
        if not cls._config:
            cls.load()

        keys = key.split('.')
        config = cls._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @classmethod
    def save(cls, config_file: str = "config.yaml"):
        """保存配置到文件"""
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(cls._config, f, allow_unicode=True, default_flow_style=False)

    @classmethod
    def all(cls) -> dict:
        """获取所有配置"""
        if not cls._config:
            cls.load()
        return cls._config


# 全局配置实例
cfg = Config()
